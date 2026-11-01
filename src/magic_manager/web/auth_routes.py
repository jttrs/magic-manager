"""Hosted sign-in: auth routes + the gate every ``/api/`` request passes (``MM_MODE=hosted``).

Local mode installs nothing — no login, and the auth routes don't exist (404).

The gate (deny by default):

* Every non-GET ``/api/`` request must carry ``Origin`` == ``MM_PUBLIC_ORIGIN``
  (on top of the app-wide ``Sec-Fetch-Site`` guard) → else 403 ``auth.origin``.
* Every ``/api/`` route outside :data:`PUBLIC_ROUTES` needs a live session of a user
  allowed in (admins only while profiles are closed) → else 401 ``auth.required``.
* ``/api/admin/*`` (the Admin page) additionally needs an admin → else 403 ``auth.admin_only``.
* A write with a session needs ``X-CSRF-Token`` == the session's token (from
  ``GET /api/auth/me``; constant-time compare) → else 403 ``auth.csrf``; writes are
  limited per session → 429 ``auth.rate_limited``.
* Sign-in start + callback are limited per client IP; their failures redirect to
  ``/?auth_error=<code>`` for the sign-in screen.

Refusals use the app's error body ``{detail, code, request_id}``.
"""
from __future__ import annotations

import asyncio
import hmac
import logging
from dataclasses import replace
from typing import Annotated

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from urllib.parse import urlencode

from .. import analytics, auth, db, userfiles
from .. import layout as _layout
from ..api import auth as auth_api
from ..auth import oauth, ratelimit, store
from . import account_routes, admin_routes

log = logging.getLogger("magic_manager.web.auth")

# Exact paths reachable without a session (route templates for the {provider} ones).
PUBLIC_ROUTES = frozenset({
    "/api/features",
    "/api/auth/me",
    "/api/auth/logout",
    "/api/auth/login/{provider}",
    "/api/auth/callback/{provider}",
})
_PUBLIC_PREFIXES = ("/api/auth/login/", "/api/auth/callback/")
_SAFE = ("GET", "HEAD", "OPTIONS")

LOGIN_PER_MINUTE = 10
WRITES_PER_MINUTE = 120
login_limiter = ratelimit.Limiter(LOGIN_PER_MINUTE)
write_limiter = ratelimit.Limiter(WRITES_PER_MINUTE)


def cookie_name() -> str:
    # __Host- = Secure, Path=/, no Domain: the browser won't let a sibling host set it.
    return "__Host-mm_session" if auth.secure_cookies() else "mm_session"


def state_cookie_name() -> str:
    return "__Host-mm_oauth" if auth.secure_cookies() else "mm_oauth"


def _is_public(path: str) -> bool:
    return path in PUBLIC_ROUTES or path.startswith(_PUBLIC_PREFIXES)


def _refuse(request: Request, status: int, code: str, detail: str) -> JSONResponse:
    request.state.error_code = code
    return JSONResponse(status_code=status, content={
        "detail": detail, "code": code, "request_id": getattr(request.state, "request_id", None)})


def allowed(session: store.Session | None) -> store.Session | None:
    """The session if its user may use this server right now (profiles rail: admins only while closed)."""
    if session is None or session.user.disabled:
        return None
    if not auth.may_sign_in(session.user.is_admin):
        return None
    return session


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_cookie(resp: Response, name: str, value: str, max_age: int) -> None:
    resp.set_cookie(name, value, max_age=max_age, path="/", httponly=True,
                    secure=auth.secure_cookies(), samesite="lax")


def _clear_cookie(resp: Response, name: str) -> None:
    resp.delete_cookie(name, path="/", httponly=True, secure=auth.secure_cookies(), samesite="lax")


def _fail(code: str, *, clear_state: bool = True) -> RedirectResponse:
    resp = RedirectResponse("/?" + urlencode({"auth_error": code}), status_code=303)
    if clear_state:
        _clear_cookie(resp, state_cookie_name())
    return resp


class _RedactQuery(logging.Filter):
    """Hosted: keep invite codes, OAuth codes and state out of the access log."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str) and "?" in args[2]:
            record.args = (*args[:2], args[2].split("?", 1)[0] + "?…", *args[3:])
        return True


_redactor = _RedactQuery()

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=auth_api.MeOut)
def auth_me(request: Request):
    return auth_api.me(getattr(request.state, "session", None))


@router.post("/logout", status_code=204)
def auth_logout(request: Request):
    store.end_session(request.cookies.get(cookie_name()))
    resp = Response(status_code=204)
    _clear_cookie(resp, cookie_name())
    return resp


@router.get("/login/{provider}", include_in_schema=False)
def auth_login(request: Request, provider: str,
               invite: Annotated[str | None, Query(max_length=128)] = None,
               next: Annotated[str | None, Query(max_length=512)] = None):  # noqa: A002 — the public param name
    if provider not in oauth.SPECS:
        return _fail("provider_unavailable")
    if not login_limiter.take(_client_ip(request)):
        return _fail("rate_limited")
    if invite:
        try:
            is_admin = store.invite_is_admin(invite)
        except store.InviteInvalid:
            return _fail("invite_invalid")
        if not auth.may_sign_in(is_admin):
            return _fail("profiles_soon")
    try:
        state, url = oauth.begin(provider, request.app.state.public_origin, invite=invite or None, next_path=next)
    except oauth.OAuthFailed as e:
        return _fail(e.code)
    resp = RedirectResponse(url, status_code=303)
    # Binds the callback to THIS browser (login CSRF): the callback's state must match.
    _set_cookie(resp, state_cookie_name(), state, int(oauth.PENDING_TTL))
    return resp


@router.get("/callback/{provider}", include_in_schema=False)
async def auth_callback(request: Request, provider: str,
                        code: Annotated[str | None, Query(max_length=2048)] = None,
                        state: Annotated[str | None, Query(max_length=256)] = None,
                        error: Annotated[str | None, Query(max_length=256)] = None):
    if provider not in oauth.SPECS:
        return _fail("provider_unavailable")
    if not login_limiter.take(_client_ip(request)):
        return _fail("rate_limited")
    cookie_state = request.cookies.get(state_cookie_name())
    if not state or not cookie_state or not _same(state, cookie_state):
        return _fail("state")
    try:
        pending = oauth.take_pending(state, provider)
    except oauth.OAuthFailed as e:
        return _fail(e.code)
    if error or not code:
        return _fail("denied")
    origin = request.app.state.public_origin
    try:
        profile = await oauth.complete(provider, code, pending, origin)
    except oauth.OAuthFailed as e:
        log.warning("sign-in with %s failed: %s", provider, e.code)
        return _fail(e.code)
    return await asyncio.to_thread(_finish, request, profile, pending)


def _same(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def _finish(request: Request, profile: oauth.Profile, pending: oauth.Pending) -> Response:
    user = store.user_for_identity(profile.provider, profile.subject)
    if user is None:
        if not pending.invite:
            return _fail("not_invited")
        try:
            if not auth.may_sign_in(store.invite_is_admin(pending.invite)):
                return _fail("profiles_soon")
            user = store.redeem_invite(pending.invite, profile.provider, profile.subject,
                                       profile.display_name, profile.email)
        except store.InviteInvalid:
            return _fail("invite_invalid")
    if user.disabled:
        return _fail("disabled")
    if not auth.may_sign_in(user.is_admin):
        return _fail("profiles_soon")
    store.update_profile(user.id, profile.display_name, profile.email)
    try:
        userfiles.ensure(db.data_dir(), user.id)  # first sign-in: an empty collection file; else migrate it
    except Exception:  # noqa: BLE001 — never sign in to a missing/unmigrated file
        log.exception("could not prepare the collection file of user %s", user.id)
        return _fail("profile_unavailable")
    new = store.create_session(user.id, replaces=request.cookies.get(cookie_name()))
    resp = RedirectResponse(pending.next_path, status_code=303)
    _set_cookie(resp, cookie_name(), new.token, int(store.SESSION_ABSOLUTE.total_seconds()))
    _clear_cookie(resp, state_cookie_name())
    log.info("signed in user %s with %s", user.id, profile.provider)
    return resp


def install(app: FastAPI) -> None:
    """Hosted mode: check config, add the routes and the gate. Local mode: nothing."""
    if not auth.hosted():
        return
    app.state.public_origin = auth.check_hosted()
    app.include_router(router)
    app.include_router(admin_routes.router)
    app.include_router(account_routes.delete_router)
    logging.getLogger("uvicorn.access").addFilter(_redactor)

    @app.middleware("http")
    async def auth_gate(request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/"):
            resp = await call_next(request)
            # The SPA can carry ?invite=<code>: never leak it to another site in a Referer.
            resp.headers.setdefault("Referrer-Policy", "same-origin")
            return resp
        write = request.method not in _SAFE
        if write and request.headers.get("origin") != app.state.public_origin:
            return _refuse(request, 403, "auth.origin", "Writes are accepted only from this app's own pages.")
        token = request.cookies.get(cookie_name())
        session = allowed(await asyncio.to_thread(store.session_for, token)) if token else None
        request.state.session = session
        if session is not None:
            request.state.user_id = session.user.id
        if not _is_public(path) and session is None:
            return _refuse(request, 401, "auth.required", "Sign in to use this.")
        if write and session is not None:
            if not store.csrf_matches(session, request.headers.get("x-csrf-token")):
                return _refuse(request, 403, "auth.csrf", "This page is out of date — reload it and try again.")
            if not write_limiter.take(session.token_hash):
                return _refuse(request, 429, "auth.rate_limited", "Too many changes at once — wait a minute and try again.")
        if session is not None and not userfiles.path_for(db.data_dir(), session.user.id).exists():
            # A session minted before its file existed (e.g. before step 5): create it now.
            try:
                await asyncio.to_thread(userfiles.ensure, db.data_dir(), session.user.id)
            except Exception:  # noqa: BLE001 — never serve a request without the user's own file
                log.exception("could not prepare the collection file of user %s", session.user.id)
                return _refuse(request, 503, "auth.profile_unavailable",
                               "Your collection couldn’t be opened on this server. Try again in a moment.")
        # Server events in this request (and delete-my-data) key on the signed-in user,
        # and every connection in it opens ONLY that user's file (no session → none:
        # db.connect fails closed). Never from client input.
        bound = analytics.bind(replace(analytics.current(), user_id=session.user.id)) if session else None
        user_token = _layout.bind_user(session.user.id) if session else None
        try:
            resp = await call_next(request)
        finally:
            if user_token is not None:
                _layout.reset_user(user_token)
            if bound is not None:
                analytics.reset(bound)
        resp.headers.setdefault("Cache-Control", "no-store")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp
