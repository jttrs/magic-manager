"""addcards engine + /api/ingest routes. Fully offline: seeded tmp DB, faked scryfall/mtgjson."""
from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from magic_manager import addcards, db, decks, ingest, mtgjson, parsers, scryfall
from magic_manager.web.app import create_app

SETS = [
    {"code": "tst", "name": "Test Set", "released_at": "2025-01-01"},
    {"code": "old", "name": "Old Set", "released_at": "2020-01-01"},
]


@pytest.fixture(autouse=True)
def _sets(monkeypatch):
    monkeypatch.setattr(scryfall, "all_sets", lambda: list(SETS))


@pytest.fixture
def cards(seed_cards, make_card):
    seed_cards([
        make_card(id="bolt-new", oracle_id="ob", name="Lightning Bolt", set="tst", collector_number="10",
                  released_at="2025-01-01"),
        make_card(id="bolt-old", oracle_id="ob", name="Lightning Bolt", set="old", collector_number="5",
                  released_at="2020-01-01", finishes=["nonfoil"]),
        make_card(id="bolt-promo", oracle_id="ob", name="Lightning Bolt", set="tst", collector_number="11p",
                  released_at="2025-06-01", promo_types=["prerelease"], promo=True),
        make_card(id="bolt2", oracle_id="o2", name="Bolt Strike", set="tst", collector_number="12"),
        make_card(id="fbolt", oracle_id="o3", name="Firebolt", set="tst", collector_number="13"),
        make_card(id="tok", oracle_id="o4", name="Bolt Token", set="tst", collector_number="14",
                  layout="token", type_line="Token Creature"),
        make_card(id="etch", oracle_id="o5", name="Etched Thing", set="tst", collector_number="15",
                  finishes=["etched"]),
    ])


def _own(sid, finish="nonfoil", qty=1):
    with db.connect() as conn:
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) VALUES (?,?,?,'2025-01-01')",
                     (sid, finish, qty))


# ---------- parsing ----------

def test_parse_formats_and_detection():
    r = parsers.parse_text("1 Lightning Bolt (TST) 10 *F*\n2x Counterspell\n3 Sol Ring [CMD] 5\n1 Opt [XYZ]\n1 Etch [ABC] 7 *E*")
    e = r.entries
    assert (e[0].set, e[0].collector_number, e[0].foil, e[0].line_no) == ("tst", "10", True, 1)
    assert (e[1].name, e[1].qty, e[1].set) == ("Counterspell", 2, None)
    assert (e[2].name, e[2].set, e[2].collector_number) == ("Sol Ring", "cmd", "5")
    assert (e[3].set, e[3].collector_number) == ("xyz", None)
    assert e[4].foil and e[4].collector_number == "7" and e[4].line_no == 5
    assert parsers.detect_paste_format("1 A (TST) 1") == "moxfield"
    assert parsers.detect_paste_format("# c\n1 A [TST] 1") == "tcgplayer"
    assert parsers.detect_paste_format("1 A") == "names"


# ---------- search ----------

def test_search_local_ranking(cards):
    out = addcards.search_printings("bolt")
    assert out["source"] == "local"
    ids = [p["scryfall_id"] for p in out["printings"]]
    assert ids == ["bolt2", "fbolt", "bolt-promo", "bolt-new", "bolt-old"]  # prefix, then contains by name, newest first
    exact = addcards.search_printings("Lightning Bolt")["printings"]
    assert [p["scryfall_id"] for p in exact] == ["bolt-promo", "bolt-new", "bolt-old"]
    assert "tok" not in ids
    assert out["printings"][1]["set_name"] == "Test Set"
    assert len(addcards.search_printings("bolt", limit=2)["printings"]) == 2


def test_search_owned_and_etched(cards):
    _own("etch", "foil", 2)
    p = addcards.search_printings("etched")["printings"][0]
    assert p["finishes"] == ["foil"] and p["owned"] == {"foil": 2}


def test_search_scryfall_fallback_upserts(tmp_db, make_card, monkeypatch):
    card = make_card(id="remote", name="Zzyzx Remote", set="tst", collector_number="9")
    seen = []
    monkeypatch.setattr(scryfall, "search", lambda q, **k: (seen.append(q), iter([card]))[1])
    out = addcards.search_printings("zzyzx")
    assert out["source"] == "scryfall" and [p["scryfall_id"] for p in out["printings"]] == ["remote"]
    assert seen == ["zzyzx unique:prints game:paper"]
    assert addcards.search_printings("zzyzx")["source"] == "local"


def test_search_scryfall_error_is_empty(tmp_db, monkeypatch):
    def boom(q, **k):
        raise scryfall.ScryfallError("404")
        yield
    monkeypatch.setattr(scryfall, "search", boom)
    assert addcards.search_printings("nothing")["printings"] == []


# ---------- resolve ----------

def _no_net(monkeypatch):
    def nope(*a, **k):
        raise AssertionError("network used")
    monkeypatch.setattr(scryfall, "collection", nope)
    monkeypatch.setattr(scryfall, "search", nope)


def test_resolve_exact_and_finish_switch(cards, monkeypatch):
    _no_net(monkeypatch)
    out = addcards.resolve_text("1 Lightning Bolt (OLD) 5 *F*\n2 Lightning Bolt (TST) 10")
    assert out["format"] == "moxfield"
    a, b = out["lines"]
    assert a["status"] == "exact" and a["chosen"] == "bolt-old" and a["finish"] == "nonfoil"
    assert "No foil printing" in a["note"]
    assert b["finish"] == "nonfoil" and b["qty"] == 2 and b["line"] == 2 and b["note"] is None


def test_resolve_ambiguous_owned_first_and_unresolved(cards, monkeypatch):
    def none_found(ids):
        return [], list(ids)
    monkeypatch.setattr(scryfall, "collection", none_found)
    monkeypatch.setattr(scryfall, "search", lambda *a, **k: iter([]))
    out = addcards.resolve_text("1 Lightning Bolt\n\n1 Nonexistent Card")
    amb, un = out["lines"]
    assert amb["status"] == "ambiguous"
    # standard non-promo newest first; promo last
    assert [c["scryfall_id"] for c in amb["candidates"]] == ["bolt-new", "bolt-old", "bolt-promo"]
    assert amb["chosen"] == "bolt-new"
    assert un["status"] == "unresolved" and un["chosen"] is None and "No card named" in un["note"]
    assert un["line"] == 3
    _own("bolt-old", "nonfoil", 3)
    amb2 = addcards.resolve_text("1 Lightning Bolt")["lines"][0]
    assert amb2["chosen"] == "bolt-old" and amb2["candidates"][0]["owned"] == {"nonfoil": 3}


def test_resolve_tcgplayer_set_only_and_mismatch(cards, monkeypatch):
    _no_net(monkeypatch)
    out = addcards.resolve_text("1 Lightning Bolt [OLD]\n1 Lightning Bolt [TST]\n1 Firebolt (TST) 10")
    assert out["format"] == "tcgplayer"
    one, many, mism = out["lines"]
    assert one["status"] == "exact" and one["chosen"] == "bolt-old"
    assert many["status"] == "ambiguous" and {c["set_code"] for c in many["candidates"]} == {"tst"}
    assert any("mismatch" in w for w in out["warnings"]) and mism["chosen"] == "bolt-new"


def test_resolve_fetches_missing_set_cn(tmp_db, make_card, monkeypatch):
    card = make_card(id="r1", name="Remote One", set="tst", collector_number="77")
    calls = []
    monkeypatch.setattr(scryfall, "collection", lambda ids: (calls.append(list(ids)), ([card], []))[1])
    out = addcards.resolve_text("1 Remote One (TST) 77", fmt="names")
    assert out["format"] == "names" and out["lines"][0]["chosen"] == "r1"
    assert calls == [[{"set": "tst", "collector_number": "77"}]]


def test_resolve_bad_line_warns(cards, monkeypatch):
    _no_net(monkeypatch)
    out = addcards.resolve_text("what is this\n1 Firebolt")
    assert len(out["lines"]) == 1 and any("unparseable" in w for w in out["warnings"])


# ---------- commit ----------

def test_commit_merges_one_event_and_reconciles(cards):
    out = addcards.commit(
        [("bolt-new", "nonfoil", 2), ("bolt-new", "nonfoil", 1), ("bolt-new", "foil", 1), ("fbolt", "nonfoil", 4)],
        source="paste", label="X",
    )
    assert out["copies"] == 8 and out["printings"] == 2
    assert out["summary"] == "+8 copies · 2 printings"
    with db.connect() as conn:
        inv = {(r[0], r[1]): r[2] for r in conn.execute("SELECT scryfall_id, finish, quantity FROM inventory")}
        ev = conn.execute("SELECT method, label FROM ingest_events").fetchall()
        assert ingest.reconcile_inventory_ledger(conn) == []
    assert inv == {("bolt-new", "nonfoil"): 3, ("bolt-new", "foil"): 1, ("fbolt", "nonfoil"): 4}
    assert [tuple(r) for r in ev] == [("import-block", "web:paste · X")]


def test_commit_search_method_and_validation(cards):
    addcards.commit([("fbolt", "nonfoil", 1)], source="search")
    with db.connect() as conn:
        assert conn.execute("SELECT method, label FROM ingest_events").fetchone()[:] == ("adhoc", "web:search")
    with pytest.raises(LookupError, match="nope"):
        addcards.commit([("nope", "nonfoil", 1)], source="search")
    with pytest.raises(LookupError):
        addcards.commit([("bolt-old", "foil", 1)], source="search")
    with pytest.raises(LookupError):
        addcards.commit([("etch", "nonfoil", 1)], source="search")
    addcards.commit([("etch", "foil", 1)], source="search")


# ---------- precons ----------

def test_precon_catalog_filter(tmp_db, monkeypatch):
    rows = [
        {"code": "BLC", "fileName": "A_BLC", "name": "Family Matters", "releaseDate": "2024-08-02", "type": "Commander Deck"},
        {"code": "NEO", "fileName": "B_NEO", "name": "Family Fun Collector's Edition", "releaseDate": "2022-02-01", "type": "Commander Deck"},
        {"code": "OLD", "fileName": "C_OLD", "name": "Older Deck", "releaseDate": "2010-01-01", "type": "Duel Deck"},
        {"code": "SPC", "fileName": "D_SPC", "name": "Some Sealed", "releaseDate": "2025-01-01", "type": "Theme Deck?"},
    ]
    monkeypatch.setattr(mtgjson, "deck_list", lambda **k: list(rows))
    monkeypatch.setattr(mtgjson, "default_precon_state", lambda fn, name=None, quick=False: "built")
    monkeypatch.setattr(decks, "precon_unit_counts", lambda: {"A_BLC": (2, 1)})
    allp = addcards.precon_catalog()
    assert [p["file_name"] for p in allp] == ["A_BLC", "C_OLD"]
    assert (allp[0]["owned_built"], allp[0]["owned_deconstructed"], allp[0]["set_code"]) == (2, 1, "blc")
    assert [p["file_name"] for p in addcards.precon_catalog("blc commander")] == ["A_BLC"]
    assert [p["file_name"] for p in addcards.precon_catalog("duel")] == ["C_OLD"]
    assert len(addcards.precon_catalog(limit=1)) == 1


# ---------- fetch deck ----------

class _FakeProc:
    def __init__(self, out, err, rc=0):
        self.stdout, self.stderr, self.returncode = io.StringIO(out), io.StringIO(err), rc

    def wait(self):
        return self.returncode


def test_fetch_deck_lines(cards, monkeypatch):
    payload = {"source": "x", "id": "1", "name": "My Deck", "cards": [
        {"qty": 2, "board": "main", "finish": "foil", "scryfall_id": "bolt-new", "set": None, "collector_number": None, "name": "Lightning Bolt"},
        {"qty": 1, "board": "commander", "finish": "nonfoil", "scryfall_id": None, "set": "tst", "collector_number": "13", "name": "Firebolt"},
        {"qty": 1, "board": "main", "finish": "nonfoil", "scryfall_id": None, "set": None, "collector_number": None, "name": "Bolt Strike"},
        {"qty": 1, "board": "maybe", "finish": "nonfoil", "scryfall_id": "fbolt", "name": "Firebolt"},
    ]}
    monkeypatch.setattr(addcards.subprocess, "Popen", lambda *a, **k: _FakeProc(json.dumps(payload), "fetching\nparsing\n"))
    msgs = []
    out = addcards.fetch_deck_lines("https://example.test/deck", progress=msgs.append)
    assert msgs == ["fetching", "parsing"]
    assert out["format"] == "deck" and out["deck_name"] == "My Deck"
    assert [(l["chosen"], l["finish"], l["section"], l["line"]) for l in out["lines"]] == [
        ("bolt-new", "foil", "main", 0), ("fbolt", "nonfoil", "commander", 0), ("bolt2", "nonfoil", "main", 0)]
    assert out["lines"][0]["raw"] == "2 Lightning Bolt"


def test_fetch_deck_failure(monkeypatch):
    monkeypatch.setattr(addcards.subprocess, "Popen", lambda *a, **k: _FakeProc("", "a\nboom\n", 1))
    with pytest.raises(RuntimeError, match="boom"):
        addcards.fetch_deck_lines("u")


# ---------- API ----------

@pytest.fixture
def client(tmp_db):
    with TestClient(create_app(serve_frontend=False)) as c:
        yield c


def test_api_search_resolve_commit(client, cards, monkeypatch):
    r = client.get("/api/ingest/search", params={"q": "firebolt"})
    assert r.status_code == 200 and r.json()["printings"][0]["scryfall_id"] == "fbolt"
    r = client.post("/api/ingest/resolve", json={"text": "1 Firebolt (TST) 13"})
    assert r.status_code == 200 and r.json()["lines"][0]["status"] == "exact"
    r = client.post("/api/ingest/commit", json={"items": [{"scryfall_id": "fbolt", "finish": "nonfoil", "qty": 2}], "source": "search"})
    assert r.status_code == 200 and r.json()["copies"] == 2
    r = client.post("/api/ingest/commit", json={"items": [{"scryfall_id": "ghost", "finish": "nonfoil", "qty": 1}], "source": "search"})
    assert r.status_code == 422
