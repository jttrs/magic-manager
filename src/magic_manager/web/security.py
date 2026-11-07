"""Hosted-mode hardening for every response and request (§25.4 step 10).

* :class:`SecurityHeaders` — on EVERY response (SPA, assets, API, errors):
  ``Content-Security-Policy`` (:func:`content_security_policy`), ``X-Content-Type-Options``,
  ``X-Frame-Options``, ``Referrer-Policy`` and, when the public origin is https,
  ``Strict-Transport-Security``. No ``'unsafe-inline'`` and no ``'unsafe-eval'``: the
  one runtime ``<style>`` (Radix dialogs' scroll lock) carries a per-response nonce —
  the SPA page gets ``<meta name="csp-nonce">`` (:func:`render_index`) and
  ``web/src/app/csp.ts`` hands it to the style injector.
* :func:`client_ip` — the client address the rate limiters key on. Behind Tailscale
  Serve or Cloudflare Tunnel every TCP peer is 127.0.0.1, so the proxy's header is
  trusted — but ONLY when ``MM_TRUSTED_PROXY`` names that proxy and the peer is
  loopback. Unset = trust no header (uvicorn's own proxy-header rewrite is off too:
  ``mm serve`` passes ``proxy_headers=False``).
* :data:`live_limiter` / :func:`live_fetch` — a per-user limit on read routes that
  fetch live third-party data (EDHREC, Scryfall, MTGJSON, Commander Spellbook).

Local mode installs none of it (no login, one person on their own machine).
"""
from __future__ import annotations

import html
import ipaddress
import os
import secrets

from fastapi import HTTPException, Request

from .. import auth
from .. import layout as _layout
from ..auth import ratelimit

# Card art, card backs and mana symbols load from Scryfall's CDN (cards./backs./svgs.scryfall.io).
IMAGE_HOSTS = ("https://*.scryfall.io",)

CSP_DIRECTIVES: tuple[tuple[str, str], ...] = (
    ("default-src", "'self'"),
    ("script-src", "'self'"),
    ("style-src", "'self'"),
    ("img-src", " ".join(("'self'", "data:", *IMAGE_HOSTS))),
    ("font-src", "'self'"),
    ("connect-src", "'self'"),
    ("worker-src", "'self'"),
    ("manifest-src", "'self'"),
    ("frame-ancestors", "'none'"),
    ("base-uri", "'none'"),
    ("form-action", "'self'"),
    ("object-src", "'none'"),
)

HSTS = "max-age=31536000"
NONCE_META = "csp-nonce"
NONCE_STATE = "csp_nonce"


def new_nonce() -> str:
    return secrets.token_urlsafe(18)


def content_security_policy(style_nonce: str | None = None) -> str:
    """The hosted policy; ``style_nonce`` (the SPA page only) admits the runtime
    ``<style>`` elements that carry it."""
    return "; ".join(
        f"{k} {v} 'nonce-{style_nonce}'" if k == "style-src" and style_nonce else f"{k} {v}"
        for k, v in CSP_DIRECTIVES)


def render_index(page: str, nonce: str) -> str:
    """The SPA's index.html with this response's style nonce in a meta tag."""
    meta = f'<meta name="{NONCE_META}" content="{html.escape(nonce)}" />'
    return page.replace("<head>", f"<head>\n    {meta}", 1)


def response_headers(public_origin: str | None, style_nonce: str | None = None) -> list[tuple[bytes, bytes]]:
    out = [
        (b"content-security-policy", content_security_policy(style_nonce).encode()),
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"same-origin"),
    ]
    if public_origin and public_origin.startswith("https://"):
        out.append((b"strict-transport-security", HSTS.encode()))
    return out


class SecurityHeaders:
    """ASGI middleware: the hardening headers on every HTTP response (replacing any
    the app set, so a route can't weaken them). A response whose request stored a
    style nonce (``request.state.csp_nonce``: the SPA page) gets it in its policy."""

    def __init__(self, app, public_origin: str | None) -> None:
        self.app = app
        self.public_origin = public_origin
        self.headers = response_headers(public_origin)
        self._names = {k for k, _ in self.headers}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                nonce = (scope.get("state") or {}).get(NONCE_STATE)
                headers = response_headers(self.public_origin, nonce) if nonce else self.headers
                kept = [(k, v) for k, v in message.get("headers", []) if k.lower() not in self._names]
                message["headers"] = [*kept, *headers]
            await send(message)

        await self.app(scope, receive, send_with_headers)


# ---------- the client address behind a trusted proxy ----------

PROXY_HEADERS = {"cloudflare": "cf-connecting-ip", "tailscale": "x-forwarded-for"}


class ProxyConfigError(auth.HostedConfigError):
    """``MM_TRUSTED_PROXY`` names no proxy this app knows."""


def trusted_proxy() -> str | None:
    """``MM_TRUSTED_PROXY``: ``tailscale`` | ``cloudflare`` | unset (trust no header)."""
    raw = (os.environ.get("MM_TRUSTED_PROXY") or "").strip().lower()
    if not raw:
        return None
    if raw not in PROXY_HEADERS:
        raise ProxyConfigError(f"MM_TRUSTED_PROXY must be one of {', '.join(sorted(PROXY_HEADERS))} or unset (got {raw!r})")
    return raw


def _ip(text: str) -> str | None:
    try:
        return str(ipaddress.ip_address(text.strip()))
    except ValueError:
        return None


def _loopback(host: str | None) -> bool:
    try:
        return bool(host) and ipaddress.ip_address(host).is_loopback  # type: ignore[arg-type]
    except ValueError:
        return False


def client_ip(request: Request) -> str:
    """The real client address: the TCP peer, unless the peer is loopback AND
    ``MM_TRUSTED_PROXY`` names the proxy in front — then that proxy's header
    (Cloudflare: ``CF-Connecting-IP``; Tailscale Serve: the LAST
    ``X-Forwarded-For`` hop, the one the proxy appended). Anything malformed
    falls back to the peer."""
    peer = request.client.host if request.client else None
    proxy = trusted_proxy()
    if proxy and _loopback(peer):
        raw = request.headers.get(PROXY_HEADERS[proxy]) or ""
        candidate = raw.split(",")[-1] if proxy == "tailscale" else raw
        if (ip := _ip(candidate)) is not None:
            return ip
    return peer or "unknown"


# ---------- live third-party reads, per user ----------

LIVE_PER_MINUTE = 120
live_limiter = ratelimit.Limiter(LIVE_PER_MINUTE)
LIVE_CODE = "auth.rate_limited"


def live_fetch(request: Request) -> None:
    """Dependency for read routes that may fetch live third-party data: hosted,
    each user gets :data:`LIVE_PER_MINUTE` per minute (429 ``auth.rate_limited``).
    Local mode: no limit."""
    if not auth.hosted():
        return
    key = _layout.bound_user() or client_ip(request)
    if not live_limiter.take(key):
        raise HTTPException(429, {"code": LIVE_CODE,
                                  "message": "Too many live look-ups at once — wait a minute and try again."})
