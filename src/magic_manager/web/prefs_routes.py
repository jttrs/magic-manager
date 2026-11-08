"""'What counts' preference routes: open to every signed-in user (the auth gate binds them)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..api import collection_prefs as prefs_api

# No `write()` undo guard on purpose: preferences are kept out of undo, like consent.
router = APIRouter(prefix="/api/preferences/collection", tags=["preferences"])


@router.get("", response_model=prefs_api.PrefsOut)
def list_prefs():
    return prefs_api.listing()


@router.put("/{key}", response_model=prefs_api.PrefsOut)
def put_pref(key: str, body: prefs_api.PrefIn):
    try:
        return prefs_api.set_pref(key, body)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
