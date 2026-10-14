"""OAuth sign-in flows: Discord (``identify email``) and Google OIDC (``openid email profile``).

Both use the authorization-code flow with ``state`` + PKCE S256; Google also binds a
``nonce`` and its ID token is verified (signature against Google's JWKS, issuer,
audience, expiry, nonce). A pending sign-in lives in memory for ten minutes, keyed by
``state``, and carries the PKCE verifier, the nonce, the invite (never put in a URL
the provider sees) and the same-origin path to return to.

What we keep from a provider (H10): the subject id, a display name and an email
(only when the provider says it's verified). Access tokens are used once to read the
profile and dropped. Nothing here logs codes, tokens or secrets.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx
from authlib.common.security import generate_token
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet

from . import PROVIDER_TITLES, Credentials, credentials

PENDING_TTL = 600.0
PENDING_MAX = 2_000
HTTP_TIMEOUT = 10.0
JWKS_TTL = 3600.0


class OAuthFailed(Exception):
    """The provider exchange failed; ``code`` is a short machine code for the UI."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    authorize_url: str
    token_url: str
    scopes: str


DISCORD = ProviderSpec("discord", "https://discord.com/oauth2/authorize",
                       "https://discord.com/api/oauth2/token", "identify email")
DISCORD_ME = "https://discord.com/api/users/@me"
GOOGLE = ProviderSpec("google", "https://accounts.google.com/o/oauth2/v2/auth",
                      "https://oauth2.googleapis.com/token", "openid email profile")
GOOGLE_JWKS = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ["https://accounts.google.com", "accounts.google.com"]
SPECS = {s.name: s for s in (DISCORD, GOOGLE)}


@dataclass(frozen=True)
class Profile:
    provider: str
    subject: str
    display_name: str
    email: str | None


@dataclass
class Pending:
    provider: str
    verifier: str
    nonce: str
    invite: str | None
    next_path: str
    created: float = field(default_factory=time.monotonic)


_pending: dict[str, Pending] = {}
_pending_lock = threading.Lock()


def redirect_uri(origin: str, provider: str) -> str:
    return f"{origin}/api/auth/callback/{provider}"


def safe_next(path: str | None) -> str:
    """A same-origin path to land on after sign-in; anything else becomes ``/``."""
    if not path or not path.startswith("/") or path.startswith("//") or "\\" in path or any(c < " " for c in path):
        return "/"
    return path[:512]


def begin(provider: str, origin: str, *, invite: str | None, next_path: str | None) -> tuple[str, str]:
    """Start a sign-in: returns ``(state, authorize_url)`` and remembers the pending login."""
    spec = SPECS[provider]
    creds = credentials(provider)
    if creds is None:
        raise OAuthFailed("provider_unavailable", f"{PROVIDER_TITLES[provider]} sign-in isn't set up on this server.")
    state, verifier, nonce = generate_token(43), generate_token(64), generate_token(32)
    now = time.monotonic()
    with _pending_lock:
        for k in [k for k, p in _pending.items() if now - p.created > PENDING_TTL]:
            del _pending[k]
        if len(_pending) >= PENDING_MAX:
            for k in sorted(_pending, key=lambda k: _pending[k].created)[: PENDING_MAX // 4]:
                del _pending[k]
        _pending[state] = Pending(provider, verifier, nonce, invite, safe_next(next_path), now)
    params = {
        "response_type": "code",
        "client_id": creds.client_id,
        "redirect_uri": redirect_uri(origin, provider),
        "scope": spec.scopes,
        "state": state,
        "code_challenge": create_s256_code_challenge(verifier),
        "code_challenge_method": "S256",
    }
    if provider == "google":
        params["nonce"] = nonce
    return state, f"{spec.authorize_url}?{urlencode(params)}"


def take_pending(state: str, provider: str) -> Pending:
    """Pop the pending login for ``state`` (single use); refuses unknown/expired/mismatched."""
    with _pending_lock:
        p = _pending.pop(state, None)
    if p is None or p.provider != provider or time.monotonic() - p.created > PENDING_TTL:
        raise OAuthFailed("state", "That sign-in link expired. Start again.")
    return p


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=False)


async def _exchange(spec: ProviderSpec, creds: Credentials, code: str, pending: Pending, origin: str,
                    http: httpx.AsyncClient) -> dict:
    try:
        r = await http.post(spec.token_url, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(origin, spec.name),
            "code_verifier": pending.verifier,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
        }, headers={"Accept": "application/json"})
    except httpx.HTTPError as e:
        raise OAuthFailed("provider_error", f"Couldn't reach {PROVIDER_TITLES[spec.name]} ({type(e).__name__}).") from e
    if r.status_code != 200:
        raise OAuthFailed("provider_error", f"{PROVIDER_TITLES[spec.name]} refused the sign-in (HTTP {r.status_code}).")
    try:
        return r.json()
    except ValueError as e:
        raise OAuthFailed("provider_error", f"{PROVIDER_TITLES[spec.name]} sent an unreadable answer.") from e


def _clip(s: object, n: int = 80) -> str:
    return str(s or "").strip()[:n]


async def _discord_profile(tokens: dict, http: httpx.AsyncClient) -> Profile:
    access = tokens.get("access_token")
    if not access:
        raise OAuthFailed("provider_error", "Discord sent no access token.")
    try:
        r = await http.get(DISCORD_ME, headers={"Authorization": f"Bearer {access}"})
    except httpx.HTTPError as e:
        raise OAuthFailed("provider_error", f"Couldn't read your Discord profile ({type(e).__name__}).") from e
    if r.status_code != 200:
        raise OAuthFailed("provider_error", f"Couldn't read your Discord profile (HTTP {r.status_code}).")
    me = r.json()
    subject = _clip(me.get("id"), 64)
    if not subject:
        raise OAuthFailed("provider_error", "Discord sent a profile without an id.")
    email = _clip(me.get("email"), 254) if me.get("verified") else ""
    name = _clip(me.get("global_name")) or _clip(me.get("username")) or "Discord user"
    return Profile("discord", subject, name, email or None)


_jwks: tuple[float, KeySet] | None = None
_jwks_lock = threading.Lock()


async def _google_keys(http: httpx.AsyncClient, *, refresh: bool = False) -> KeySet:
    global _jwks
    with _jwks_lock:
        cached = _jwks
    if cached and not refresh and time.monotonic() - cached[0] < JWKS_TTL:
        return cached[1]
    try:
        r = await http.get(GOOGLE_JWKS)
        r.raise_for_status()
        keys = KeySet.import_key_set(r.json())
    except (httpx.HTTPError, ValueError, JoseError) as e:
        raise OAuthFailed("provider_error", f"Couldn't read Google's signing keys ({type(e).__name__}).") from e
    with _jwks_lock:
        _jwks = (time.monotonic(), keys)
    return keys


def verify_google_id_token(id_token: str, keys: KeySet, *, client_id: str, nonce: str) -> dict:
    """Signature (RS256 against Google's keys) + iss + aud + exp + nonce; returns the claims."""
    try:
        token = jwt.decode(id_token, keys, algorithms=["RS256"])
        jwt.JWTClaimsRegistry(
            leeway=60,
            iss={"essential": True, "values": GOOGLE_ISSUERS},
            aud={"essential": True, "value": client_id},
            sub={"essential": True},
            exp={"essential": True},
            nonce={"essential": True, "value": nonce},
        ).validate(token.claims)
    except (JoseError, ValueError) as e:
        raise OAuthFailed("id_token", f"Google's sign-in token didn't check out ({type(e).__name__}).") from e
    return token.claims


async def _google_profile(tokens: dict, creds: Credentials, pending: Pending, http: httpx.AsyncClient) -> Profile:
    id_token = tokens.get("id_token")
    if not id_token:
        raise OAuthFailed("provider_error", "Google sent no ID token.")
    keys = await _google_keys(http)
    try:
        claims = verify_google_id_token(id_token, keys, client_id=creds.client_id, nonce=pending.nonce)
    except OAuthFailed:
        # Google rotates keys: retry once with a fresh key set before refusing.
        keys = await _google_keys(http, refresh=True)
        claims = verify_google_id_token(id_token, keys, client_id=creds.client_id, nonce=pending.nonce)
    email = _clip(claims.get("email"), 254) if claims.get("email_verified") is True else ""
    name = _clip(claims.get("name")) or email or "Google user"
    return Profile("google", _clip(claims["sub"], 255), name, email or None)


async def complete(provider: str, code: str, pending: Pending, origin: str) -> Profile:
    """Exchange the code (with the PKCE verifier) and read the profile. Tokens are dropped."""
    spec = SPECS[provider]
    creds = credentials(provider)
    if creds is None:
        raise OAuthFailed("provider_unavailable", f"{PROVIDER_TITLES[provider]} sign-in isn't set up on this server.")
    async with _client() as http:
        tokens = await _exchange(spec, creds, code, pending, origin, http)
        if provider == "discord":
            return await _discord_profile(tokens, http)
        return await _google_profile(tokens, creds, pending, http)


def reset() -> None:
    """Forget pending logins and cached keys (tests)."""
    global _jwks
    with _pending_lock:
        _pending.clear()
    with _jwks_lock:
        _jwks = None
