"""Request telemetry: request ids, coded errors and server-side analytics events.

* Every ``/api`` response carries ``X-Request-ID``; error bodies carry it too
  (``{"detail", "code", "request_id"}``) so a user-visible error can be traced in
  the server log and in the analytics store (``mm analytics trace <ref>``).
* Errors get a specific ``code``: the engine exception behind an HTTPException
  (``StaleCounts`` → ``stale_counts``), ``request_validation``, or ``http_<status>``.
  Unhandled exceptions become a 500 that names the exception — never a bare
  "Internal Server Error".
* Hosted, an error's ``detail`` never carries raw engine text: a SQLite / OS /
  subprocess error, or any message showing a filesystem path, SQL text or a
  wrapper's stderr, becomes a plain message for its status (:func:`public_detail`);
  the full text stays in the server log under the same ``request_id``.
* The client's in-memory session id arrives as ``X-MM-Session`` (a UUID, else
  ignored) and links server events to that browser session.
* After the response, :func:`analytics.record_response` records ``api.error`` or a
  catalog route-trigger event — off the event loop, never failing the request.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import subprocess
import uuid

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import analytics, mtgjson, owner_machine
from ..analytics import catalog, consent

log = logging.getLogger("magic_manager.web")


def _state(scope) -> dict:
    return scope.setdefault("state", {})


def error_code(exc: StarletteHTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict) and isinstance(detail.get("code"), str):
        explicit = catalog.check_value(catalog.Prop("code", "code"), detail["code"], ())
        if explicit:
            return explicit
    cause = exc.__cause__
    if cause is not None:
        return catalog.to_code(type(cause).__name__)
    return "not_found" if exc.status_code == 404 else f"http_{exc.status_code}"


# Text that must never reach a hosted user: an absolute filesystem path, SQLite
# text, a wrapper script's exit/stderr, a traceback.
_LEAKY = re.compile(
    r"(?<![\w:/.])/(?:[\w.~-]+/)+[\w.~-]*"            # /Users/…/x, /data/users/…, /var/folders/…
    r"|\bsqlite3?\b|SQLITE_|no such (?:table|column)|constraint failed|database is locked"
    r"|\.sh\b|\bexited \d+|Traceback|File \"",
    re.I)
# Exceptions whose text is never shown hosted, whatever it says.
_RAW_CAUSES: tuple[type[BaseException], ...] = (sqlite3.Error, OSError, subprocess.SubprocessError)

_PLAIN_BY_STATUS = {
    502: "An outside service didn’t answer as expected — try again in a moment.",
    503: "That isn’t available right now — try again in a moment.",
}
PLAIN_DEFAULT = "This couldn’t be done — the details are in the server log."


def leaky(text: str) -> bool:
    return bool(_LEAKY.search(text))


def public_detail(detail, cause: BaseException | None, status: int):
    """Hosted: ``detail`` with raw engine text replaced by a plain message (the code
    and request id still identify it). Local mode keeps every detail."""
    if consent.mode() != "hosted":
        return detail
    plain = _PLAIN_BY_STATUS.get(status, PLAIN_DEFAULT)
    if isinstance(cause, _RAW_CAUSES):
        return {**detail, "message": plain} if isinstance(detail, dict) and "message" in detail else plain
    return _scrub(detail, plain)


def _scrub(value, plain: str):
    if isinstance(value, str):
        return plain if leaky(value) else value
    if isinstance(value, dict):
        return {k: _scrub(v, plain) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v, plain) for v in value]
    return value


class TelemetryMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/"):
            return await self.app(scope, receive, send)
        rid = uuid.uuid4().hex
        headers = dict(scope.get("headers") or [])
        sid = analytics.session_id_or_none(headers.get(b"x-mm-session", b"").decode("latin-1"))
        state = _state(scope)
        state["request_id"] = rid
        ctx = analytics.Context(request_id=rid, session_id=sid)
        token = analytics.bind(ctx)
        sent = {"started": False, "status": 500}

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                sent["started"], sent["status"] = True, message["status"]
                message["headers"] = [*message.get("headers", []), (b"x-request-id", rid.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception as e:  # noqa: BLE001 — a coded 500 instead of a bare one
            code = catalog.to_code(type(e).__name__)
            state["error_code"] = code
            log.exception("%s %s → 500 %s ref=%s", scope.get("method"), scope.get("path"), code, rid)
            if sent["started"]:
                raise
            sent["status"] = 500
            # Hosted: the message can carry SQL/paths — keep it in the server log only.
            msg = f"Unexpected server error — {type(e).__name__}"
            if consent.mode() != "hosted":
                msg += f": {e}"
            body = json.dumps({"detail": msg, "code": code, "request_id": rid}).encode()
            await send({"type": "http.response.start", "status": 500,
                        "headers": [(b"content-type", b"application/json"), (b"x-request-id", rid.encode())]})
            await send({"type": "http.response.body", "body": body})
        finally:
            analytics.reset(token)
        status = sent["status"]
        if state.get("user_id"):  # set by the hosted auth gate
            ctx = analytics.Context(request_id=rid, session_id=sid, user_id=state["user_id"])
        route = getattr(scope.get("route"), "name", None)
        code = state.get("error_code")
        if 400 <= status < 500:
            log.warning("%s %s → %s %s ref=%s", scope.get("method"), scope.get("path"), status, code, rid)
        try:
            if route and (status >= 400 or catalog.load().triggers_for(route)):
                await asyncio.to_thread(analytics.record_response, route, scope.get("method", "GET"), status, code, ctx=ctx)
        except Exception as e:  # noqa: BLE001 — analytics never fails a request
            log.warning("analytics skipped for %s: %s: %s", route, type(e).__name__, e)


def install(app: FastAPI) -> None:
    app.add_middleware(TelemetryMiddleware)

    @app.exception_handler(StarletteHTTPException)
    async def coded_http_error(request: Request, exc: StarletteHTTPException):
        code = error_code(exc)
        request.state.error_code = code
        if exc.status_code in (204, 304):
            return Response(status_code=exc.status_code, headers=exc.headers)
        if exc.__cause__ is not None and consent.mode() == "hosted":
            log.warning("%s %s → %s %s ref=%s: %s: %s", request.method, request.url.path, exc.status_code, code,
                        getattr(request.state, "request_id", None), type(exc.__cause__).__name__, exc.__cause__)
        detail = public_detail(exc.detail, exc.__cause__, exc.status_code)
        return JSONResponse({"detail": detail, "code": code,
                             "request_id": getattr(request.state, "request_id", None)},
                            status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(owner_machine.AdminOnly)
    async def admin_only(request: Request, exc: owner_machine.AdminOnly):
        # A path on the owner's machine/logins, asked for by a non-admin (hosted): fail closed.
        request.state.error_code = owner_machine.CODE
        return JSONResponse({"detail": str(exc), "code": owner_machine.CODE,
                             "request_id": getattr(request.state, "request_id", None)}, status_code=403)

    @app.exception_handler(mtgjson.BadIdentifier)
    async def bad_identifier(request: Request, exc: mtgjson.BadIdentifier):
        # A set code / deck file name that isn't one reached the engine (the API types refuse most first).
        request.state.error_code = mtgjson.BadIdentifier.error_code
        return JSONResponse({"detail": str(exc), "code": mtgjson.BadIdentifier.error_code,
                             "request_id": getattr(request.state, "request_id", None)}, status_code=422)

    @app.exception_handler(RequestValidationError)
    async def coded_validation_error(request: Request, exc: RequestValidationError):
        request.state.error_code = "request_validation"
        return JSONResponse({"detail": jsonable_encoder(exc.errors()), "code": "request_validation",
                             "request_id": getattr(request.state, "request_id", None)}, status_code=422)
