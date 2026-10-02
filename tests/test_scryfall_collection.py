"""scryfall.collection error-tolerant bisection + resolve_identifiers indexing.

Both moved into the shared scryfall seam (from collection_sync) so every caller
— deck import, collection sync, EV, price checks — gets 400-tolerance. These
patch scryfall._run (the single HTTP shell-out) so the real bisection in
scryfall.collection runs.
"""

from __future__ import annotations

import json

import pytest

from magic_manager import scryfall


def _run_raising_on(bad_set):
    """A fake _run that 400s any page containing a {'set': bad_set} identifier,
    else echoes each identifier back as a found card keyed by its 'set'."""
    def fake_run(args, stdin=None):
        idents = json.loads(stdin)["identifiers"]
        if any(i.get("set") == bad_set for i in idents):
            raise scryfall.ScryfallError("HTTP 400: bad set code")
        return {"data": [{"id": i["set"], "set": i["set"], "collector_number": "1",
                          "name": i["set"]} for i in idents],
                "not_found": []}
    return fake_run


def test_collection_bisects_to_quarantine_bad_identifier(monkeypatch):
    monkeypatch.setattr(scryfall, "_run", _run_raising_on("bad"))
    idents = [{"set": "a"}, {"set": "b"}, {"set": "bad"}, {"set": "d"}]
    found, not_found = scryfall.collection(idents)
    # The 3 good ones resolve; the malformed one is isolated into not_found.
    assert {c["id"] for c in found} == {"a", "b", "d"}
    assert not_found == [{"set": "bad"}]


def test_collection_all_bad_degrades_to_all_not_found(monkeypatch):
    # Every identifier malformed → each isolated, none found, no raise.
    def fake_run(args, stdin=None):
        raise scryfall.ScryfallError("400")
    monkeypatch.setattr(scryfall, "_run", fake_run)
    idents = [{"set": "x"}, {"set": "y"}]
    found, not_found = scryfall.collection(idents)
    assert found == []
    assert not_found == [{"set": "x"}, {"set": "y"}]


def test_collection_clean_batch_no_bisection(monkeypatch):
    calls = {"n": 0}
    def fake_run(args, stdin=None):
        calls["n"] += 1
        idents = json.loads(stdin)["identifiers"]
        return {"data": [{"id": i["id"]} for i in idents], "not_found": []}
    monkeypatch.setattr(scryfall, "_run", fake_run)
    found, not_found = scryfall.collection([{"id": "a"}, {"id": "b"}])
    assert {c["id"] for c in found} == {"a", "b"}
    assert calls["n"] == 1  # single page, no bisection


def test_resolve_identifiers_builds_indexes(monkeypatch):
    monkeypatch.setattr(scryfall, "_run", lambda args, stdin=None: {
        "data": [{"id": "sid1", "set": "fin", "collector_number": "233", "name": "Lightning"},
                 {"id": "sid2", "set": "pw25", "collector_number": "16", "name": "Yuna // Back"}],
        "not_found": [],
    })
    by_sid, by_setcn, by_name, warnings = scryfall.resolve_identifiers(
        [{"id": "sid1"}], [{"set": "pw25", "collector_number": "16"}]
    )
    assert by_sid["sid1"]["name"] == "Lightning"
    assert by_setcn[("fin", "233")]["id"] == "sid1"
    # by_name indexes full name AND the DFC front face.
    assert by_name["yuna // back"]["id"] == "sid2"
    assert by_name["yuna"]["id"] == "sid2"
    assert warnings == []


def test_resolve_identifiers_folds_not_found_into_warnings(monkeypatch):
    monkeypatch.setattr(scryfall, "_run", lambda args, stdin=None: {
        "data": [], "not_found": [{"id": "ghost"}],
    })
    by_sid, by_setcn, by_name, warnings = scryfall.resolve_identifiers([{"id": "ghost"}], [])
    assert by_sid == {} and len(warnings) == 1 and "ghost" in warnings[0]
