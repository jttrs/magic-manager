"""'What counts' preference routes: open to every signed-in user (the auth gate binds them)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..api import collection_prefs as prefs_api

# No `write()` undo guard on purpose: preferences are kept out of undo, like consent.
router = APIRouter(prefix="/api/preferences/collection", tags=["preferences"])


# Registered before "/{key}" so the fixed "families" path is never read as a preference key.
@router.get("/families", response_model=prefs_api.RuleFamiliesOut)
def list_rule_families():
    return prefs_api.rule_families()


@router.get("/families/{anchor}", response_model=prefs_api.FamilyRulesOut)
def get_family_rules(anchor: str):
    try:
        return prefs_api.family_rules(anchor)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.put("/families/{anchor}/rules/{rule_id}", response_model=prefs_api.FamilyRulesOut)
def put_family_rule(anchor: str, rule_id: str, body: prefs_api.FamilyRuleIn):
    try:
        return prefs_api.set_family_rule(anchor, rule_id, body)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


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
