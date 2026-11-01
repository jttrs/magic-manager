"""Admin operations on ``auth.db`` (hosted; §25.4 step 6) — one engine for the Admin
page (``web/admin_routes.py``) and its CLI twins (``mm auth …``).

What an admin can do: list who can sign in, mint an invite (shown once), sign a
user out everywhere, disable / re-enable them, and set per-user feature-flag
overrides. What they can't (§25.0): act as a user or see anyone's collection —
nothing here opens a collection file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from urllib.parse import urlencode

from .. import features, owner_machine
from . import HostedConfigError, public_origin
from . import store


class SelfLockout(ValueError):
    """An admin tried to disable themselves."""


@dataclass(frozen=True)
class FlagState:
    name: str
    about: str
    default: bool                 # the process layers (files + MM_FEATURES)
    override: bool | None         # this user's admin-set value; None = default
    effective: bool
    owner_paths: list[str] = field(default_factory=list)   # pinned paths in this flag's surface


@dataclass(frozen=True)
class UserRow:
    id: str
    display_name: str
    email: str | None
    providers: list[str]
    is_admin: bool
    created_at: str
    last_seen_at: str | None
    disabled_at: str | None
    sessions: int
    flags: list[FlagState]


def _paths_by_feature() -> dict[str | None, list[str]]:
    out: dict[str | None, list[str]] = {}
    for p in owner_machine.PATHS.values():
        out.setdefault(p.feature, []).append(p.key)
    return out


def flag_states(overrides: dict[str, bool], *, base: dict[str, bool] | None = None) -> list[FlagState]:
    base = features.base_flags() if base is None else base
    about = features.about()
    paths = _paths_by_feature()
    return [FlagState(name, about.get(name, ""), default, overrides.get(name),
                      overrides.get(name, default), paths.get(name, []))
            for name, default in base.items()]


def users() -> list[UserRow]:
    base = features.base_flags()
    over = store.all_overrides()
    live = store.session_counts()
    return [UserRow(u.id, u.display_name, u.email, provs, u.is_admin, u.created_at, u.last_seen_at, u.disabled_at,
                    live.get(u.id, 0), flag_states(over.get(u.id, {}), base=base))
            for u, provs in store.users()]


def user(user_id: str) -> UserRow:
    for row in users():
        if row.id == user_id:
            return row
    raise LookupError(f"no user {user_id!r}")


@dataclass(frozen=True)
class MintedInvite:
    code: str
    url: str | None
    is_admin: bool
    expires_at: str


def invite_url(code: str) -> str | None:
    try:
        origin = public_origin()
    except HostedConfigError:
        origin = None
    return f"{origin}/?{urlencode({'invite': code})}" if origin else None


def mint_invite(*, is_admin: bool, expires_in: timedelta, created_by: str | None = None) -> MintedInvite:
    """A single-use invite; its code is returned ONCE (only the hash is stored)."""
    from . import PROFILES_SOON, may_sign_in
    if not may_sign_in(is_admin):
        raise PermissionError(PROFILES_SOON)
    inv = store.create_invite(is_admin=is_admin, expires_in=expires_in, created_by=created_by)
    return MintedInvite(inv.code, invite_url(inv.code), inv.is_admin, inv.expires_at)


def sign_out(user_id: str) -> int:
    """End every session of a user. Returns how many."""
    return store.revoke(user_id)


def disable(user_id: str, *, actor: str | None = None) -> int:
    """Block a user from signing in and end their sessions (not yourself)."""
    if actor is not None and actor == user_id:
        raise SelfLockout("You can't disable yourself — ask another admin, or use `mm auth revoke --disable`.")
    return store.revoke(user_id, disable=True)


def enable(user_id: str) -> None:
    store.enable(user_id)


def set_flag(user_id: str, flag: str, value: bool | None, *, actor: str | None = None) -> None:
    """Override one flag for one user (``None`` = back to the default). Pinned
    owner-machine paths ignore it: owner_machine checks admin status, not flags."""
    if flag not in features.base_flags():
        raise ValueError(f"unknown flag {flag!r} (declared in config/features.toml: {', '.join(features.base_flags())})")
    store.set_override(user_id, flag, value, set_by=actor)
