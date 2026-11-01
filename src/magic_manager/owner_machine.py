"""Owner-machine paths, pinned to admins when hosted (§25.1 H9 interim).

Some server paths run on the OWNER's machine or with the owner's logins: the cart
read with the server's ``.env`` Mana Pool login, reading Chrome tabs and open-tab
store pages on the server Mac with AppleScript, the Analytics dashboard (every
user's pseudonymous activity), and the deck fetch's escalation to the server's
Moxfield session / login. Hosted, each is **admin-only regardless of any flag or
per-user override** — the pin is checked separately from the flags, so an
override can't unlock it. Locally (no login) the user IS the owner: all allowed.

Paths that run in the user's OWN browser (the companion: cart lines, supplied
tabs, Moxfield/Archidekt reads, orders) are not pinned; their flags decide.

Who is asking comes from the bound user (``layout.bound_user``: the gate binds the
signed-in user per request, the job worker binds the submitter). Nothing bound →
not an admin: fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass

CODE = "auth.admin_only"


@dataclass(frozen=True)
class OwnerPath:
    key: str
    feature: str | None   # the flag whose surface it belongs to (None = unflagged)
    title: str


PATHS: dict[str, OwnerPath] = {p.key: p for p in (
    OwnerPath("manapool.server_login", "cart_check", "Read the Mana Pool cart with this server’s login"),
    OwnerPath("deals.mac_tabs", "deals", "Read open tabs and store pages in this server’s Chrome"),
    OwnerPath("analytics.dashboard", "analytics", "The Analytics dashboard (everyone’s activity)"),
    OwnerPath("decks.moxfield_login", None, "Fetch private Moxfield decks with this server’s Moxfield login"),
)}


class AdminOnly(Exception):
    """Something only an admin may do, asked for by someone who isn't (403 ``auth.admin_only``)."""

    error_code = CODE


class OwnerOnly(AdminOnly):
    """A pinned owner-machine path asked for by someone who isn't an admin."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"{PATHS[key].title} runs on the owner’s machine — only an admin can use it here.")


def _hosted() -> bool:
    from .analytics import consent
    return consent.mode() == "hosted"


def is_admin() -> bool:
    """Is the bound user an enabled admin? Always True locally (the owner's own machine)."""
    if not _hosted():
        return True
    from . import layout
    from .auth import store
    uid = layout.bound_user()
    if not uid:
        return False
    user = store.get_user(uid)
    return bool(user and user.is_admin and not user.disabled)


def allowed(key: str) -> bool:
    if key not in PATHS:
        raise KeyError(f"unknown owner-machine path {key!r}")
    return is_admin()


def require(key: str) -> None:
    if not allowed(key):
        raise OwnerOnly(key)


def access() -> dict[str, bool]:
    """Every pinned path → may the bound user use it here (one admin lookup)."""
    ok = is_admin()
    return {k: ok for k in PATHS}
