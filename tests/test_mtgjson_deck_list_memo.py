"""mtgjson.deck_list() is memoized in-process, keyed on the wrapper's on-disk
DeckList.json, and a cached copy is read from disk without spawning the
wrapper — offline: the wrapper call is stubbed, the cache dir is tmp."""
from __future__ import annotations

import json
import os

from magic_manager import mtgjson

ROWS = [
    {"code": "FIC", "fileName": "A_FIC", "name": "A", "type": "Commander Deck"},
    {"code": "FDN", "fileName": "B_FDN", "name": "B", "type": "Jumpstart"},
]


def _write(tmp_path, rows):
    (tmp_path / "DeckList.json").write_text(json.dumps({"data": rows}))


def _names():
    return [r["fileName"] for r in mtgjson.deck_list()]


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("MTGJSON_CACHE_DIR", str(tmp_path))
    calls = []

    def fake_run_json(args):
        calls.append(args)
        _write(tmp_path, ROWS)                           # what the wrapper does on a fetch
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
    _write(tmp_path, ROWS[:1])                                         # re-downloaded
    assert _names() == ["A_FIC"]
    assert len(calls) == 1                                             # read from disk
    (tmp_path / "DeckList.json").unlink()                              # refreshed (deleted)
    assert _names() == ["A_FIC", "B_FDN"]
    assert len(calls) == 2                                             # the wrapper fetches it


def test_cached_deck_list_is_read_without_the_wrapper(tmp_path, monkeypatch):
    calls = _setup(tmp_path, monkeypatch)
    _write(tmp_path, ROWS)
    assert _names() == ["A_FIC", "B_FDN"]
    assert calls == []


def test_unreadable_cached_deck_list_goes_through_the_wrapper(tmp_path, monkeypatch):
    calls = _setup(tmp_path, monkeypatch)
    (tmp_path / "DeckList.json").write_text("")                        # the wrapper re-fetches an empty file
    assert _names() == ["A_FIC", "B_FDN"]
    assert len(calls) == 1


def test_deck_list_rereads_after_the_ttl(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    now = [1000.0]
    monkeypatch.setattr(mtgjson.time, "monotonic", lambda: now[0])
    mtgjson.deck_list()
    p = tmp_path / "DeckList.json"
    st = p.stat()
    p.write_text(p.read_text().replace("A_FIC", "C_FIC"))              # same size, stamp restored
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    now[0] += mtgjson._DECK_LIST_TTL_S - 1
    assert _names() == ["A_FIC", "B_FDN"]                              # memo
    now[0] += 2
    assert _names() == ["C_FIC", "B_FDN"]                              # re-read


def test_refresh_drops_the_memo(tmp_path, monkeypatch):
    calls = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(mtgjson, "_run", lambda args: (tmp_path / "DeckList.json").unlink())
    mtgjson.deck_list()
    mtgjson.refresh("DeckList.json")
    mtgjson.deck_list()
    assert len(calls) == 2
