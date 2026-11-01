"""Sign-in for the hosted app (§25.1 H4/H5): invite-only Discord/Google OAuth.

Only ``MM_MODE=hosted`` turns any of it on; local mode has no login (H11). This module
holds the hosted configuration; ``store`` is ``auth.db``, ``oauth`` the provider flows,
``ratelimit`` the in-memory limits, and ``magic_manager.web.auth_routes`` the web gate.

**Profiles rail.** Each signed-in user has their own collection file (step 5:
``users/<id>.db``, bound per request), but until step 6 pins the features that use
the owner's machine or logins (cart check, store tabs, the analytics dashboard, the
deck fetch's Moxfield session) only admins may hold a session: :data:`PROFILES_OPEN`
is False, ``mm auth invite`` mints only ``--admin`` invites, and a non-admin sign-in
is refused ("Profiles open soon"). Step 6 flips the constant.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from .. import db
from .. import secrets as secrets_mod
from ..analytics import consent as _consent

PROFILES_OPEN = False
PROFILES_SOON = "Profiles open soon — for now only the admin can sign in."

PROVIDER_TITLES = {"discord": "Discord", "google": "Google"}

# Secret names in the gitignored .env / environment (never logged, never sent to the client).
SECRET_NAMES = {
    "discord": ("MM_OAUTH_DISCORD_CLIENT_ID", "MM_OAUTH_DISCORD_CLIENT_SECRET"),
    "google": ("MM_OAUTH_GOOGLE_CLIENT_ID", "MM_OAUTH_GOOGLE_CLIENT_SECRET"),
}
SECRETS = tuple(n for pair in SECRET_NAMES.values() for n in pair)


def may_sign_in(is_admin: bool) -> bool:
    """The step-5 rail in one place: until profiles open, only admins sign in."""
    return PROFILES_OPEN or is_admin


class HostedConfigError(RuntimeError):
    """Hosted mode can't start: a required setting is missing or malformed."""


def hosted() -> bool:
    return _consent.mode() == "hosted"


def public_origin() -> str | None:
    """``MM_PUBLIC_ORIGIN`` normalized to ``scheme://host[:port]``; None if unset.
    Raises :class:`HostedConfigError` when it is set but isn't a bare origin."""
    raw = (os.environ.get("MM_PUBLIC_ORIGIN") or "").strip()
    if not raw:
        return None
    u = urlsplit(raw)
    if u.scheme not in ("http", "https") or not u.hostname or u.path not in ("", "/") or u.query or u.fragment or u.username:
        raise HostedConfigError(f"MM_PUBLIC_ORIGIN must be an origin like https://example.com (got {raw!r})")
    if u.scheme == "http" and u.hostname not in ("localhost", "127.0.0.1"):
        raise HostedConfigError("MM_PUBLIC_ORIGIN must use https (plain http is only allowed for localhost)")
    # Browsers serialize Origin without a default port, so the stored origin must too.
    port = u.port
    host = u.hostname.lower()
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    default = 443 if u.scheme == "https" else 80
    return f"{u.scheme}://{host}" + (f":{port}" if port and port != default else "")


def secure_cookies() -> bool:
    origin = public_origin()
    return bool(origin and origin.startswith("https://"))


@dataclass(frozen=True)
class Credentials:
    client_id: str
    client_secret: str


def credentials(provider: str) -> Credentials | None:
    names = SECRET_NAMES.get(provider)
    if not names:
        return None
    cid, secret = (secrets_mod.get(n) for n in names)
    return Credentials(cid, secret) if cid and secret else None


def configured_providers() -> list[str]:
    return [p for p in SECRET_NAMES if credentials(p)]


def check_hosted() -> str:
    """Refuse to serve hosted without a public origin and at least one provider.
    Returns the origin."""
    origin = public_origin()
    if not origin:
        raise HostedConfigError("MM_MODE=hosted needs MM_PUBLIC_ORIGIN (e.g. https://cards.example.com).")
    if db.layout_kind() != "split":
        raise HostedConfigError(
            "MM_MODE=hosted needs the split layout: MM_LAYOUT=split and MM_DATA_DIR=<dir> holding catalog.db "
            "+ users/ (`mm db split --to <dir>`), and no MAGIC_MANAGER_DB — each user gets their own file.")
    if not configured_providers():
        raise HostedConfigError(
            "MM_MODE=hosted needs at least one sign-in provider: set MM_OAUTH_DISCORD_CLIENT_ID + "
            "MM_OAUTH_DISCORD_CLIENT_SECRET and/or MM_OAUTH_GOOGLE_CLIENT_ID + MM_OAUTH_GOOGLE_CLIENT_SECRET "
            "(environment or the gitignored .env).")
    return origin
