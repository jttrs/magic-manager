"""Account routes (§25.1 H10): ``GET /api/account/export`` (both modes) and, hosted
only, ``POST /api/account/delete`` (installed with the auth gate).

Whose account is ALWAYS the signed-in user from the server session (the gate binds
it; nothing here reads a user id from the request). The export streams a zip built
in memory — no temp file. Deleting needs, in order: a fresh sign-in (the session was
made ≤ ``store.REAUTH_WINDOW`` ago, else 403 ``auth.reauth_required``), the typed
confirmation (422 ``account.confirm``), not being the last admin (409
``auth.last_admin``); their queued and running jobs are cancelled first (a job
still running after :data:`JOB_STOP_WAIT` → 409 ``account.jobs_running``). The gate already enforced Origin + CSRF + the write limit.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .. import account, undo
from .. import layout as _layout
from ..api import account as account_api
from ..auth import ratelimit, store
from . import sitecheck
from .runtime import JobsBusy

log = logging.getLogger("magic_manager.web.account")

EXPORTS_PER_MINUTE = 6
JOB_STOP_WAIT = 15.0  # seconds a delete waits for the user's cancelled jobs to stop
export_limiter = ratelimit.Limiter(EXPORTS_PER_MINUTE)

router = APIRouter(prefix="/api/account", tags=["account"])
delete_router = APIRouter(prefix="/api/account", tags=["account"])


def _refused(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, detail={"code": code, "message": message})


@router.get("/export", response_class=StreamingResponse,
            responses={200: {"content": {"application/zip": {}}, "description": "Your data as a zip."}})
def account_export(request: Request):
    # Only from this app's own pages (or a typed URL): another site can't make your
    # browser fetch it.
    if (site := sitecheck.cross_site(request)) is not None:
        raise _refused(403, sitecheck.CODE, sitecheck.message(site))
    if not export_limiter.take(_layout.bound_user() or "local"):
        raise _refused(429, "auth.rate_limited", "Too many downloads at once — wait a minute and try again.")
    try:
        out = account_api.export()
    except account.ExportFailed as e:
        raise _refused(500, "account.export_failed", f"Your data couldn’t be packed: {e}") from e
    return StreamingResponse(out.chunks(), media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="{out.filename}"',
        "Content-Length": str(len(out.data)),
        "Cache-Control": "no-store",
    })


@delete_router.post("/delete", response_model=account_api.DeleteOut)
def account_delete(body: account_api.DeleteIn, request: Request):
    session = getattr(request.state, "session", None)
    if session is None:  # the gate refuses first; never act without a session
        raise _refused(401, "auth.required", "Sign in to use this.")
    uid = session.user.id
    if not session.fresh():
        minutes = int(store.REAUTH_WINDOW.total_seconds() // 60)
        raise _refused(403, "auth.reauth_required",
                       f"Sign in again to confirm it’s you, then delete your account within {minutes} minutes.")
    if not account_api.confirmed(body.confirm):
        raise _refused(422, "account.confirm", f"Type “{account.DELETE_CONFIRMATION}” to confirm.")
    try:
        account.check_not_last_admin(uid)  # early, friendly; delete re-checks in its transaction
        # Their queued jobs never start; running ones stop at the next progress tick.
        # A job still running after the wait refuses the delete below (JobsBusy).
        jobs = request.app.state.jobs
        if jobs.cancel_user(uid):
            jobs.wait_idle(uid, JOB_STOP_WAIT)
        with jobs.closing_user(uid), request.app.state.undo_guards.current().restoring():
            out = account_api.delete(uid)
    except account.LastAdmin as e:
        raise _refused(409, account.LAST_ADMIN, str(e)) from e
    except JobsBusy as e:
        raise _refused(409, "account.jobs_running", f"Wait for “{e.title}” to finish, then delete your account.") from e
    except undo.UndoError as e:
        raise _refused(409, "account.jobs_running", str(e)) from e
    except Exception:  # noqa: BLE001 — a step after sign-in was turned off failed: say so, coded
        log.exception("deleting the account of user %s did not finish", uid)
        resp = JSONResponse(status_code=500, content={
            "detail": {"code": "account.delete_incomplete",
                       "message": "Deleting your account didn’t finish. Your sign-in may already be turned off — "
                                  "ask the admin to finish it (they run `mm auth delete-user`)."},
            "code": "account.delete_incomplete", "request_id": getattr(request.state, "request_id", None)})
        request.state.error_code = "account.delete_incomplete"
        return _signed_out(resp)
    return _signed_out(JSONResponse(out.model_dump()))


def _signed_out(resp: JSONResponse) -> JSONResponse:
    from .auth_routes import _clear_cookie, cookie_name
    _clear_cookie(resp, cookie_name())
    return resp
