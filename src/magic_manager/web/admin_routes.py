"""Admin routes (``/api/admin/*``) — hosted only, installed with the auth gate.

The gate already requires a live session + Origin + CSRF on writes; every route
here additionally requires that session's user to be an admin (checked server-side
per request from ``auth.db``, never from client input) → else 403 ``auth.admin_only``.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request

from .. import owner_machine
from ..api import admin as admin_api
from ..auth import admin as admin_engine

_UID = Path(pattern=r"^[a-z0-9]{16}$")
_FLAG = Path(pattern=r"^[a-z][a-z0-9_]{0,63}$")


def require_admin(request: Request) -> str:
    session = getattr(request.state, "session", None)
    if session is None or not session.user.is_admin or session.user.disabled:
        raise owner_machine.AdminOnly("Only an admin can use this.")
    return session.user.id


Admin = Annotated[str, Depends(require_admin)]

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _call(fn, *args):
    try:
        return fn(*args)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except admin_engine.SelfLockout as e:
        raise HTTPException(409, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except PermissionError as e:  # profiles closed: member invites can't be minted
        raise HTTPException(403, str(e)) from e


@router.get("/users", response_model=admin_api.AdminUsersOut)
def admin_users():
    return admin_api.users()


@router.post("/invites", response_model=admin_api.InviteOut, status_code=201)
def admin_invite(body: admin_api.InviteIn, actor: Admin):
    return _call(admin_api.invite, body, actor)


@router.post("/users/{user_id}/sign-out", response_model=admin_api.SignOutOut)
def admin_sign_out(user_id: Annotated[str, _UID]):
    return _call(admin_api.sign_out, user_id)


@router.post("/users/{user_id}/disable", response_model=admin_api.AdminUserOut)
def admin_disable(user_id: Annotated[str, _UID], actor: Admin):
    return _call(admin_api.disable, user_id, actor)


@router.post("/users/{user_id}/enable", response_model=admin_api.AdminUserOut)
def admin_enable(user_id: Annotated[str, _UID]):
    return _call(admin_api.enable, user_id)


@router.put("/users/{user_id}/flags/{flag}", response_model=admin_api.AdminUserOut)
def admin_set_flag(user_id: Annotated[str, _UID], flag: Annotated[str, _FLAG], body: admin_api.FlagIn, actor: Admin):
    return _call(admin_api.set_flag, user_id, flag, body, actor)
