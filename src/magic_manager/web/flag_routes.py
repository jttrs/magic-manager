"""Feature-flag picker routes: local = always allowed (your own machine); hosted = admins."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import auth
from ..api import flags as flags_api
from . import admin_routes


def require_flag_admin(request: Request) -> str | None:
    if not auth.hosted():
        return None
    return admin_routes.require_admin(request)


Actor = Annotated[str | None, Depends(require_flag_admin)]

router = APIRouter(prefix="/api/flags", tags=["flags"], dependencies=[Depends(require_flag_admin)])


@router.get("", response_model=flags_api.FlagsOut)
def list_flags(user_id: Actor):
    return flags_api.listing(user_id)


@router.put("/{flag}", response_model=flags_api.FlagRowOut)
def put_flag(body: flags_api.FlagIn, user_id: Actor, flag: Annotated[str, admin_routes._FLAG]):
    try:
        return flags_api.set_flag(flag, body, user_id)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
