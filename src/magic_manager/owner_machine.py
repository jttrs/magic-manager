"""Owner-machine paths, pinned to admins when hosted (§25.1 H9 interim).

Some server paths run on the OWNER's machine or with the owner's logins: the cart
read with the server's ``.env`` Mana Pool login, reading Chrome tabs and open-tab
store pages on the server Mac with AppleScript, the Analytics dashboard (every
user's pseudonymous activity), and the deck fetch's Moxfield read — which drives a
browser on the server (anonymous, or with its saved Moxfield session / login).
Hosted, each is **admin-only regardless of any flag or
per-user override** — the pin is checked separately from the flags, so an
override can't unlock it. Locally (no login) the user IS the owner: all allowed.

Paths that run in the user's OWN browser (the companion: cart lines, supplied
tabs, Moxfield/Archidekt reads, orders) are not pinned; their flags decide. Since
Phase 3 step 9 (H12) members use ONLY those: the server never opens a browser or
reads the server Mac's tabs for anyone but an admin.

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
    instead: str = ""     # what a member uses instead (shown in the refusal)


PATHS: dict[str, OwnerPath] = {p.key: p for p in (
    OwnerPath("manapool.server_login", "cart_check", "Read the Mana Pool cart with this server’s login",
              "Read your cart with the browser companion or the cart bookmarklet instead."),
    OwnerPath("deals.mac_tabs", "deals", "Read open tabs and store pages in this server’s Chrome",
              "Read your tabs with the browser companion instead."),
    OwnerPath("analytics.dashboard", "analytics", "The Analytics dashboard (everyone’s activity)"),
    OwnerPath("decks.moxfield_server", None, "Read Moxfield decks with this server’s browser and Moxfield login",
              "Read it with the browser companion instead — it reads the deck in your own browser."),
)}


class AdminOnly(Exception):
    """Something only an admin may do, asked for by someone who isn't (403 ``auth.admin_only``)."""

    error_code = CODE


class OwnerOnly(AdminOnly):
    """A pinned owner-machine path asked for by someone who isn't an admin."""

    def __init__(self, key: str) -> None:
        self.key = key
        p = PATHS[key]
        super().__init__(" ".join(x for x in (f"{p.title} runs on the owner’s machine — only an admin can use it here.", p.instead) if x))


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
