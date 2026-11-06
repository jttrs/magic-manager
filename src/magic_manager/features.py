"""Feature flags: gate internal-only features (e.g. the Mana Pool cart check).

Layers, lowest first (§25.1 H6):

1. ``config/features.toml`` — the declared flags (``[flags.<name>]``: default, title,
   about, kind, dates); a plain ``[features]`` table (name → default) is accepted too;
2. ``config/features.local.toml`` (git-ignored, ``[features]``) — this machine's overrides;
3. **everyone** — instance-wide values set at runtime from the flag picker /
   ``mm flags set`` and stored in ``auth.db`` (``feature_defaults``); local and hosted;
4. the ``MM_FEATURES`` environment variable (``cart_check,-other``) — a pin;
5. hosted only: the signed-in user's **per-user overrides**, stored in ``auth.db``
   (the flag picker's "just me", ``mm auth flag``, the Admin page).

Layers 1, 2 and 4 are process config (the TOML files are read once per process;
restart ``mm serve`` after editing). Layers 3 and 5 are read per call, so a toggle
applies without a restart. Layer 5 is read for the user bound to the current request
or job (``layout.bound_user``) — no user id is threaded through the engine. Only
flags declared in features.toml exist; unknown names are ignored.

A flag never unlocks a path that runs on the owner's machine or with the owner's
logins: those are pinned to admins by :mod:`magic_manager.owner_machine`,
whatever the flags say.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from . import config

KINDS = ("release", "ops", "permission")
Source = Literal["default", "local_file", "everyone", "env", "user"]


@dataclass(frozen=True)
class FlagDef:
    name: str
    default: bool
    title: str
    about: str
    kind: str
    added: str | None
    review_by: str | None


@dataclass(frozen=True)
class Resolved:
    value: bool
    source: Source
    pinned_by_env: bool
    everyone: bool | None
    mine: bool | None


def _simple(name: str) -> dict[str, bool]:
    """The plain ``[features]`` table (name → bool) of one config file."""
    return {k: bool(v) for k, v in (config.load_toml(name).get("features") or {}).items()}


def declared() -> dict[str, FlagDef]:
    """Every declared flag, in file order (``[flags.<name>]`` tables, then legacy ``[features]``)."""
    data = config.load_toml("features.toml")
    out: dict[str, FlagDef] = {}
    for name, t in (data.get("flags") or {}).items():
        t = t or {}
        out[name] = FlagDef(name, bool(t.get("default", False)), str(t.get("title", name)), str(t.get("about", "")),
                            str(t.get("kind", "release")), t.get("added"), t.get("review_by"))
    for name, v in _simple("features.toml").items():
        out.setdefault(name, FlagDef(name, v, name, "", "release", None, None))
    return out


def file_flags() -> dict[str, bool]:
    """Declared flags with features.toml defaults and features.local.toml applied."""
    out = {k: d.default for k, d in declared().items()}
    for k, v in _simple("features.local.toml").items():
        if k in out:
            out[k] = v
    return out


def env_pins() -> dict[str, bool]:
    """``MM_FEATURES`` as name → on/off (declared names only; ``-name`` = off)."""
    known = declared()
    out: dict[str, bool] = {}
    for raw in (os.environ.get("MM_FEATURES") or "").split(","):
        name = raw.strip()
        off = name.startswith("-")
        name = name.lstrip("-+")
        if name in known:
            out[name] = not off
    return out


def instance_flags() -> dict[str, bool]:
    """The 'everyone' layer from auth.db. Never creates auth.db (absent → none)."""
    from .auth import store
    if not store.path().exists():
        return {}
    known = declared()
    return {k: v for k, v in store.defaults().items() if k in known}


def base_flags() -> dict[str, bool]:
    """Every declared flag with its value from the layers below a per-user override."""
    out = file_flags()
    out.update(instance_flags())
    out.update(env_pins())
    return out


def about() -> dict[str, str]:
    """One plain sentence per declared flag."""
    return {k: d.about for k, d in declared().items()}


def _hosted() -> bool:
    from .analytics import consent
    return consent.mode() == "hosted"


def user_overrides(user_id: str | None) -> dict[str, bool]:
    """The admin-set overrides of ``user_id`` (hosted only; else none)."""
    if not user_id or not _hosted():
        return {}
    from .auth import store
    return store.overrides(user_id)


def resolve(user_id: str | None) -> dict[str, Resolved]:
    """The one evaluator: every declared flag's value, the layer that set it, and the
    'everyone' / 'just me' values (``mine`` only hosted with a user)."""
    out = {k: d.default for k, d in declared().items()}
    source: dict[str, Source] = dict.fromkeys(out, "default")
    for k, v in _simple("features.local.toml").items():
        if k in out:
            out[k], source[k] = v, "local_file"
    everyone = instance_flags()
    pins = env_pins()
    mine = {k: v for k, v in user_overrides(user_id).items() if k in out}
    for layer, name in ((everyone, "everyone"), (pins, "env"), (mine, "user")):
        for k, v in layer.items():
            out[k], source[k] = v, name
    return {k: Resolved(out[k], source[k], k in pins, everyone.get(k), mine.get(k)) for k in out}


def flags_for(user_id: str | None) -> dict[str, bool]:
    """Every declared flag's effective value for one user (all layers)."""
    return {k: r.value for k, r in resolve(user_id).items()}


def set_instance(flag: str, value: bool | None, *, actor: str | None = None) -> None:
    """Set a flag for everyone (``None`` = back to the file default). Logged in auth.db."""
    known = declared()
    if flag not in known:
        raise ValueError(f"unknown flag {flag!r} (declared in config/features.toml: {', '.join(known)})")
    from .auth import store
    store.set_default(flag, value, set_by=actor)


def flags() -> dict[str, bool]:
    """Every declared flag's effective value for the bound user (hosted) or this machine (local)."""
    from . import layout
    return flags_for(layout.bound_user() if _hosted() else None)


def enabled(name: str) -> bool:
    return flags().get(name, False)


class FeatureDisabled(PermissionError):
    """Raised by a gated operation when its flag is off."""


def require(name: str) -> None:
    if not enabled(name):
        where = "for your profile" if _hosted() else "on this machine"
        raise FeatureDisabled(f"the {name!r} feature is turned off {where}")
