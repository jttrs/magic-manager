"""Feature flags: gate internal-only features (e.g. the Mana Pool cart check).

Layers, lowest first (§25.1 H6):

1. ``config/features.toml`` — the declared flags and their defaults (internal OFF);
2. ``config/features.local.toml`` (git-ignored) — this machine's overrides;
3. the ``MM_FEATURES`` environment variable (``cart_check,-other``);
4. hosted only: the signed-in user's **per-user overrides**, set by an admin and
   stored in ``auth.db`` (``mm auth flag`` / the Admin page).

Layers 1–3 are process config (the TOML files are read once per process; restart
``mm serve`` after editing). Layer 4 is read for the user bound to the current
request or job (``layout.bound_user``) — no user id is threaded through the engine.
Only flags declared in features.toml exist; unknown names are ignored.

A flag never unlocks a path that runs on the owner's machine or with the owner's
logins: those are pinned to admins by :mod:`magic_manager.owner_machine`,
whatever the flags say.
"""
from __future__ import annotations

import os

from . import config


def _table(name: str, key: str = "features") -> dict:
    return config.load_toml(name).get(key) or {}


def base_flags() -> dict[str, bool]:
    """Every declared flag with its value from the process layers (files + env)."""
    out = {k: bool(v) for k, v in _table("features.toml").items()}
    for k, v in _table("features.local.toml").items():
        if k in out:
            out[k] = bool(v)
    for raw in (os.environ.get("MM_FEATURES") or "").split(","):
        name = raw.strip()
        off = name.startswith("-")
        name = name.lstrip("-+")
        if name in out:
            out[name] = not off
    return out


def about() -> dict[str, str]:
    """One plain sentence per declared flag (``[about]`` in features.toml)."""
    return {k: str(v) for k, v in _table("features.toml", "about").items()}


def _hosted() -> bool:
    from .analytics import consent
    return consent.mode() == "hosted"


def user_overrides(user_id: str | None) -> dict[str, bool]:
    """The admin-set overrides of ``user_id`` (hosted only; else none)."""
    if not user_id or not _hosted():
        return {}
    from .auth import store
    return store.overrides(user_id)


def flags_for(user_id: str | None) -> dict[str, bool]:
    """Every declared flag's effective value for one user (process layers + their overrides)."""
    out = base_flags()
    for k, v in user_overrides(user_id).items():
        if k in out:
            out[k] = v
    return out


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
