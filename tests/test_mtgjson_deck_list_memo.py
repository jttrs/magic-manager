"""mtgjson.deck_list() is memoized in-process, keyed on the wrapper's on-disk
DeckList.json — offline: the wrapper call is stubbed, the cache dir is tmp."""
from __future__ import annotations

import os

from magic_manager import mtgjson

ROWS = [
    {"code": "FIC", "fileName": "A_FIC", "name": "A", "type": "Commander Deck"},
    {"code": "FDN", "fileName": "B_FDN", "name": "B", "type": "Jumpstart"},
]


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("MTGJSON_CACHE_DIR", str(tmp_path))
    calls = []

    def fake_run_json(args):
        calls.append(args)
        (tmp_path / "DeckList.json").write_text("{}")   # what the wrapper does on a fetch
        return {"data": [dict(r) for r in ROWS]}

    monkeypatch.setattr(mtgjson, "_run_json", fake_run_json)
    return calls


def test_deck_list_reuses_one_read(tmp_path, monkeypatch):
    calls = _setup(tmp_path, monkeypatch)
    assert [r["fileName"] for r in mtgjson.deck_list()] == ["A_FIC", "B_FDN"]
    assert [r["fileName"] for r in mtgjson.deck_list(set_code="fic")] == ["A_FIC"]
    assert mtgjson.jumpstart_variants("FDN")[0]["fileName"] == "B_FDN"
    assert len(calls) == 1


def test_deck_list_returns_a_fresh_list(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    mtgjson.deck_list().clear()
    assert len(mtgjson.deck_list()) == 2


def test_deck_list_rereads_when_the_disk_copy_changes(tmp_path, monkeypatch):
    calls = _setup(tmp_path, monkeypatch)
    mtgjson.deck_list()
    p = tmp_path / "DeckList.json"
    st = p.stat()
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))  # re-downloaded
    mtgjson.deck_list()
    assert len(calls) == 2
    p.unlink()                                                         # refreshed (deleted)
    mtgjson.deck_list()
    assert len(calls) == 3


def test_deck_list_rereads_after_the_ttl(tmp_path, monkeypatch):
    calls = _setup(tmp_path, monkeypatch)
    now = [1000.0]
    monkeypatch.setattr(mtgjson.time, "monotonic", lambda: now[0])
    mtgjson.deck_list()
    now[0] += mtgjson._DECK_LIST_TTL_S - 1
    mtgjson.deck_list()
    assert len(calls) == 1
    now[0] += 2
    mtgjson.deck_list()
    assert len(calls) == 2


def test_refresh_drops_the_memo(tmp_path, monkeypatch):
    calls = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(mtgjson, "_run", lambda args: "")
    mtgjson.deck_list()
    mtgjson.refresh("DeckList.json")
    mtgjson.deck_list()
    assert len(calls) == 2
