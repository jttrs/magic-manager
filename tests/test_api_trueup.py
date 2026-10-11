"""api.trueup — the product-coverage jobs. trueup.plan is stubbed: these pin the
adapter (output mapping, the reviewed-list guard before any write)."""
from __future__ import annotations

import pytest

from magic_manager import trueup
from magic_manager.api import trueup as api

P = {"fileName": "Box_HOB", "name": "Crack the Plates", "type": "Box Set", "code": "HOB",
     "release_date": "2026-08-14", "recipe_qty": 6, "usd": 37.37}


def _result(ready, conflicts=(), **kw):
    return {"ready": list(ready), "conflicts": list(conflicts), "contested_cards": [],
            "sld_complete": [], "sld_partial": [], **kw}


def test_scan_maps_products_and_conflict_winners(monkeypatch):
    lost = {**P, "fileName": "Other_HOB", "name": "Other", "lost": [{"lost_to": ["Crack the Plates"]}, {"lost_to": ["Crack the Plates", "Z"]}]}
    seen = {}
    monkeypatch.setattr(trueup, "plan", lambda **kw: seen.update(kw) or _result([P], [lost]))
    res = api._run_scan(api.ScanInput(refute=["Nope_X"], picks=["Other_HOB"]), lambda e: None)
    out = res.artifacts[0].data
    assert seen["refute"] == {"Nope_X"} and seen["picks"] == ["Other_HOB"]
    assert out["ready"][0]["usd"] == 37.37
    assert out["conflicts"][0]["lost_to"] == ["Crack the Plates", "Z"]
    assert res.summary == "1 products your cards complete · 1 lost a shared card"


def test_apply_refuses_when_the_reviewed_list_changed(monkeypatch):
    calls = []
    monkeypatch.setattr(trueup, "plan", lambda **kw: calls.append(kw) or _result([]))
    with pytest.raises(ValueError, match="changed since the scan"):
        api._run_apply(api.ApplyInput(expect=["Box_HOB"]), lambda e: None)
    assert len(calls) == 1 and not calls[0].get("apply")


def test_apply_records_only_the_reviewed_products(monkeypatch):
    calls = []

    def fake(**kw):
        calls.append(kw)
        return _result([P], applied=kw.get("apply", False), registered=1, reattributed=6)
    monkeypatch.setattr(trueup, "plan", fake)
    res = api._run_apply(api.ApplyInput(expect=["Box_HOB"]), lambda e: None)
    assert [c["only"] for c in calls] == [{"Box_HOB"}, {"Box_HOB"}]
    assert calls[1]["apply"] is True
    assert res.summary == "Recorded 1 products · 6 cards now traced to them"


def test_scan_reports_unreadable_lists(monkeypatch):
    unread = [{"ref": "set:hob", "name": "HOB products", "error": "offline"}]
    monkeypatch.setattr(trueup, "plan", lambda **kw: _result([], unread=unread))
    res = api._run_scan(api.ScanInput(), lambda e: None)
    assert res.artifacts[0].data["unread"] == unread
    assert res.summary == "0 products your cards complete · 1 lists could not be read"


def test_apply_names_unreadable_lists_instead_of_blaming_a_change(monkeypatch):
    calls = []
    unread = [{"ref": "Box_HOB", "name": "Crack the Plates", "error": "mtgjson down"}]
    monkeypatch.setattr(trueup, "plan", lambda **kw: calls.append(kw) or _result([], unread=unread))
    with pytest.raises(ValueError, match="Couldn’t read the product lists again \\(Crack the Plates\\)"):
        api._run_apply(api.ApplyInput(expect=["Box_HOB"]), lambda e: None)
    assert len(calls) == 1 and not calls[0].get("apply")


def test_apply_keeps_pick_order(monkeypatch):
    calls = []
    monkeypatch.setattr(trueup, "plan", lambda **kw: calls.append(kw) or _result([P], registered=1))
    api._run_apply(api.ApplyInput(expect=["Box_HOB"], picks=["B", "A"]), lambda e: None)
    assert [c["picks"] for c in calls] == [["B", "A"], ["B", "A"]]
