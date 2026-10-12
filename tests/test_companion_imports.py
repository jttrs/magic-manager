"""Browser-companion imports: private Archidekt decks and Moxfield collections /
binders — reader goldens → strict server models → engines, plus the collection
import's preview/apply semantics (owner, 2026-10-11: add or replace chosen per
import; printings the read doesn't list are never touched; etched = foil;
proxies and digital copies skipped; ONE ``collection-import`` ingest event; the
ledger still reconciles). Goldens are written by
``web/e2e/companion-import-readers.spec.ts`` in real Chromium. Fully offline.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from magic_manager import collection_sync, config, db, decksource, ingest, scraper_health, scryfall
from magic_manager.api import collection_import as ci
from magic_manager.api import companion as companion_api

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "companion"


def _golden(name: str) -> dict:
    return json.loads((FIX / name).read_text())


# ---------- Archidekt ----------

def test_archidekt_reader_output_becomes_the_same_payload_as_the_api_import():
    out = _golden("archidekt-deck.expected.json")
    req = companion_api.DeckFromBrowserIn(source="archidekt", deck=out["deck"])
    payload = decksource.payload_from_archidekt(req.deck.model_dump(), req.deck.id)
    assert (payload["source"], payload["id"], payload["name"]) == ("archidekt", "13106730", "Revival Trance - Final Fantasy Commander")
    by = {c["name"]: c for c in payload["cards"]}
    assert by["Terra, Herald of Hope"]["board"] == "commander"
    assert by["Demolition Field"]["finish"] == "foil"
    assert by["Angel of the Ruins"]["board"] == "maybe"
    assert all(c["scryfall_id"] and c["set"] and c["collector_number"] for c in payload["cards"])


def test_archidekt_deck_model_is_strict_and_must_match_its_source():
    deck = _golden("archidekt-deck.expected.json")["deck"]
    with pytest.raises(ValueError):
        companion_api.DeckFromBrowserIn(source="archidekt", deck={**deck, "userIp": "1.2.3.4"})
    with pytest.raises(ValueError):
        companion_api.DeckFromBrowserIn(source="moxfield", deck=deck)
    with pytest.raises(ValueError):
        companion_api.DeckFromBrowserIn(source="archidekt", deck=_golden("moxfield-deck.expected.json")["deck"])


def test_payload_from_archidekt_is_what_the_server_import_builds():
    api_shape = {"id": 5, "name": "D", "owner": {"username": "me"},
                 "cards": [{"quantity": 2, "modifier": "Etched", "categories": ["Commander"],
                            "card": {"uid": "u", "collectorNumber": "7", "edition": {"editioncode": "abc"}, "oracleCard": {"name": "N"}}}]}
    p = decksource.payload_from_archidekt(api_shape)
    assert (p["id"], p["author"]) == ("5", "me")
    assert p["cards"] == decksource.parse_archidekt(api_shape)


# ---------- Moxfield collection: reader golden → model ----------

def test_collection_reader_output_is_exactly_what_the_server_accepts():
    c = _golden("moxfield-collection.expected.json")["collection"]
    req = ci.CollectionReadIn(source="moxfield", scope="collection", id=c["id"], name=c["name"], lines=c["lines"])
    assert len(req.lines) == 20
    with pytest.raises(ValueError):
        ci.CollectionReadIn(source="moxfield", scope="collection", lines=[{**c["lines"][0], "condition": "nearMint"}])
    with pytest.raises(ValueError):
        ci.CollectionReadIn(source="moxfield", scope="collection", lines=c["lines"], token="x")
    b = _golden("moxfield-binder.expected.json")["collection"]
    breq = ci.CollectionReadIn(source="moxfield", scope="binder", id=b["id"], name=b["name"], lines=b["lines"])
    assert ci.label_for(breq) == "web:moxfield binder · Trade Box 1"


def test_a_whole_real_sized_collection_fits_every_layer():
    """The read is capped at the same 60,000 printings in the reader, the app and the server, and
    the bridge forwards which collection read was asked for (it once dropped ``what``/``binder``,
    so "Read my collection" failed as request.invalid for everyone)."""
    reader = (ROOT / "extension/src/readers/moxfield-collection.js").read_text()
    app = (ROOT / "web/src/core/companion.ts").read_text()
    bridge = (ROOT / "extension/src/bridge.js").read_text()
    assert ci.MAX_LINES == 60_000 and "MAX_LINES = 60000" in reader and "lines: z.array(collectionLine).max(60_000)" in app
    assert "what: typeof p.what === 'string'" in bridge and "binder: typeof p.binder === 'string'" in bridge
    line = {"quantity": 1, "finish": "nonfoil", "scryfall_id": "0000579f-7b35-4ed3-b44c-db2a538066fe", "set": "fin", "cn": "1", "name": "X"}
    assert len(ci.CollectionReadIn(source="moxfield", scope="collection", lines=[line] * ci.MAX_LINES).lines) == ci.MAX_LINES
    with pytest.raises(ValueError):
        ci.CollectionReadIn(source="moxfield", scope="collection", lines=[line] * (ci.MAX_LINES + 1))


def test_worker_never_reports_size_or_a_crash_as_a_bad_request():
    bg = (ROOT / "extension/src/background.js").read_text()
    assert "fail('reader.crashed'" in bg and "fail('request.too_large'" in bg
    assert "detail: 'too large'" not in bg and "MAX_PAYLOAD_BYTES" not in bg   # every size check is maxPayload(kind)
    assert "packed(pending.kind, data)" in bg                                    # the watched second read too
    assert "storage.session.set({ pending: { ...now, stage: 'send', data" not in bg   # held packed, not as objects


def test_rows_from_lines_merges_etched_and_skips_proxies_and_digital():
    read = collection_sync.rows_from_lines(_golden("moxfield-collection.expected.json")["collection"]["lines"])
    assert read.skipped == {"proxy": 1, "digital": 1}
    assert {r.finish for r in read.rows} == {"nonfoil", "foil"}
    assert len(read.rows) == 18


# ---------- preview / apply ----------

SID = ["00000000-0000-4000-8000-00000000000%d" % i for i in range(1, 6)]


@pytest.fixture
def owned(tmp_db, seed_cards, make_card):
    seed_cards([make_card(id=s, oracle_id=f"o{i}", set="tst", collector_number=str(i), name=f"Card {i}") for i, s in enumerate(SID, 1)])
    from magic_manager import inventory
    inventory.inventory_add(SID[0], "nonfoil", 3)
    inventory.inventory_add(SID[1], "foil", 1)
    inventory.inventory_add(SID[4], "nonfoil", 7)      # owned, not in the read: never touched


def _lines():
    return [
        {"quantity": 5, "finish": "nonfoil", "scryfall_id": SID[0], "set": "tst", "cn": "1", "name": "Card 1"},
        {"quantity": 1, "finish": "etched", "scryfall_id": SID[1], "set": "tst", "cn": "2", "name": "Card 2"},
        {"quantity": 2, "finish": "nonfoil", "scryfall_id": SID[2], "set": "tst", "cn": "3", "name": "Card 3"},
        {"quantity": 4, "finish": "nonfoil", "scryfall_id": SID[3], "set": "tst", "cn": "4", "name": "Card 4", "proxy": True},
    ]


def _qty(sid, finish="nonfoil"):
    with db.connect() as conn:
        r = conn.execute("SELECT quantity FROM inventory WHERE scryfall_id=? AND finish=?", (sid, finish)).fetchone()
    return r[0] if r else 0


def _no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("known printings resolve locally")
    monkeypatch.setattr(scryfall, "resolve_identifiers", boom)


def test_preview_compares_current_with_incoming_and_writes_nothing(owned, monkeypatch):
    _no_network(monkeypatch)
    p = collection_sync.preview_lines(_lines())
    rows = {(r["scryfall_id"], r["finish"]): (r["current"], r["incoming"]) for r in p["rows"]}
    assert rows == {(SID[0], "nonfoil"): (3, 5), (SID[1], "foil"): (1, 1), (SID[2], "nonfoil"): (0, 2)}
    assert p["skipped"] == {"proxy": 4, "digital": 0}
    assert p["not_in_read"] == 1 and p["already_imported_at"] is None
    assert (_qty(SID[0]), _qty(SID[2])) == (3, 0)


def test_replace_sets_listed_printings_and_leaves_the_rest(owned, monkeypatch):
    _no_network(monkeypatch)
    out = collection_sync.apply_lines(_lines(), mode="replace", label="web:moxfield collection")
    assert (_qty(SID[0]), _qty(SID[1], "foil"), _qty(SID[2]), _qty(SID[3]), _qty(SID[4])) == (5, 1, 2, 0, 7)
    assert (out["added"], out["updated"]) == (1, 1)
    with db.connect() as conn:
        ev = conn.execute("SELECT method, label, mode FROM ingest_events WHERE ingest_id=?", (out["ingest_id"],)).fetchone()
        assert tuple(ev) == ("collection-import", "web:moxfield collection", "replace")
        assert ingest.reconcile_inventory_ledger(conn) == []
    again = collection_sync.apply_lines(_lines(), mode="replace", label="x")     # idempotent, allowed
    assert (again["added"], again["updated"]) == (0, 0) and _qty(SID[0]) == 5


def test_add_sums_and_refuses_the_same_read_twice(owned, monkeypatch):
    _no_network(monkeypatch)
    collection_sync.apply_lines(_lines(), mode="add", label="web:moxfield binder · New")
    assert (_qty(SID[0]), _qty(SID[1], "foil"), _qty(SID[2]), _qty(SID[4])) == (8, 2, 2, 7)
    assert collection_sync.preview_lines(_lines())["already_imported_at"]
    with pytest.raises(collection_sync.AlreadyImported):
        collection_sync.apply_lines(_lines(), mode="add", label="again")
    collection_sync.apply_lines(_lines(), mode="add", label="again", force=True)
    assert _qty(SID[0]) == 13
    with db.connect() as conn:
        assert ingest.reconcile_inventory_ledger(conn) == []


def test_replace_refuses_to_go_below_built_deck_copies(owned, monkeypatch):
    _no_network(monkeypatch)
    from magic_manager import decks
    d = decks.deck_create("built", "Built")
    with db.connect() as conn:
        conn.execute("INSERT INTO deck_assignments (deck_id, scryfall_id, finish, count, assigned_at) "
                     "VALUES (?, ?, 'nonfoil', 6, '2026-01-01')", (d.deck_id, SID[0]))
        conn.commit()
    p = collection_sync.preview_lines(_lines())
    assert {r["scryfall_id"]: r["pledged"] for r in p["rows"]}[SID[0]] == 6
    with pytest.raises(collection_sync.BelowPledged) as e:
        collection_sync.apply_lines(_lines(), mode="replace", label="x")
    assert e.value.rows == [{"scryfall_id": SID[0], "finish": "nonfoil", "incoming": 5, "pledged": 6}]
    assert _qty(SID[0]) == 3 and _qty(SID[2]) == 0          # all-or-nothing: nothing written
    collection_sync.apply_lines(_lines(), mode="add", label="y")   # adding never lowers anything
    assert _qty(SID[0]) == 8


def test_any_real_collector_number_is_accepted():
    ci.CollectionReadIn(source="moxfield", scope="collection",
                        lines=[{"quantity": 1, "finish": "nonfoil", "set": "sld", "cn": "633Φ", "name": "X"}])
    with pytest.raises(ValueError):
        ci.CollectionReadIn(source="moxfield", scope="collection",
                            lines=[{"quantity": 1, "finish": "nonfoil", "set": "sld", "cn": "<b>1", "name": "X"}])


def test_unknown_printings_resolve_through_scryfall_and_unresolvable_are_reported(owned, monkeypatch, make_card):
    new = "00000000-0000-4000-8000-000000000009"
    card = make_card(id=new, oracle_id="o9", set="tst", collector_number="9", name="Card 9")
    monkeypatch.setattr(scryfall, "resolve_identifiers", lambda ids, setcn: ({new: card}, {("tst", "9"): card}, {}, []))
    p = collection_sync.preview_lines([
        {"quantity": 1, "finish": "nonfoil", "scryfall_id": new, "set": "tst", "cn": "9", "name": "Card 9"},
        {"quantity": 1, "finish": "nonfoil", "scryfall_id": "00000000-0000-4000-8000-0000000000ff", "name": "Gone"},
    ])
    assert [r["scryfall_id"] for r in p["rows"]] == [new]
    assert [n["name"] for n in p["not_found"]] == ["Gone"]


# ---------- routes ----------

@pytest.fixture
def client(owned, tmp_path, monkeypatch):
    import shutil
    monkeypatch.setenv("MAGIC_MANAGER_CONFIG_DIR", str(tmp_path))
    (tmp_path / "features.toml").write_text("[features]\ncompanion = false\n")
    for f in (Path(__file__).resolve().parents[1] / "config").glob("*.toml"):
        if f.name != "features.toml":
            shutil.copy(f, tmp_path / f.name)
    monkeypatch.delenv("MM_FEATURES", raising=False)
    monkeypatch.setenv("MM_SCRAPER_HEALTH", str(tmp_path / "health.json"))
    _no_network(monkeypatch)
    config._cached_toml.cache_clear()
    from magic_manager.web.app import create_app
    yield TestClient(create_app(serve_frontend=False))
    config._cached_toml.cache_clear()


def test_collection_import_routes(client, monkeypatch):
    body = {"source": "moxfield", "scope": "binder", "id": "LbwVB1hSiU2THiRQeR2QlQ", "name": "Trade Box 1", "lines": _lines()}
    assert client.post("/api/collection/import/preview", json=body).status_code == 403
    monkeypatch.setenv("MM_FEATURES", "companion")
    p = client.post("/api/collection/import/preview", json=body)
    assert p.status_code == 200, p.text
    assert p.json()["label"] == "web:moxfield binder · Trade Box 1" and len(p.json()["rows"]) == 3
    assert client.post("/api/collection/import/preview", json={**body, "cookie": "x"}).status_code == 422
    a = client.post("/api/collection/import/apply", json={**body, "mode": "add"})
    assert a.status_code == 200 and a.json()["added"] == 1
    assert client.post("/api/collection/import/apply", json={**body, "mode": "add"}).status_code == 409
    assert client.post("/api/collection/import/apply", json={**body, "mode": "replace"}).status_code == 200
    only_proxies = {**body, "lines": [_lines()[3]]}
    r = client.post("/api/collection/import/preview", json=only_proxies)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "collection.empty"
    assert client.post("/api/collection/import/apply", json={**body, "mode": "replace"},
                       headers={"sec-fetch-site": "cross-site"}).status_code == 403
    low = {**body, "lines": [{**_lines()[0], "quantity": 1}]}
    from magic_manager import decks
    d = decks.deck_create("built", "Built")
    with db.connect() as conn:
        conn.execute("INSERT INTO deck_assignments (deck_id, scryfall_id, finish, count, assigned_at) "
                     "VALUES (?, ?, 'nonfoil', 2, '2026-01-01')", (d.deck_id, SID[0]))
        conn.commit()
    r = client.post("/api/collection/import/apply", json={**low, "mode": "replace"})
    assert r.status_code == 409 and r.json()["detail"]["below_pledged"][0]["pledged"] == 2
    assert {h.scraper.key: h.status for h in scraper_health.health()}["companion-collection/moxfield"] == "ok"


def test_archidekt_deck_from_browser_route(client, monkeypatch, seed_cards, make_card):
    monkeypatch.setenv("MM_FEATURES", "companion")
    deck = _golden("archidekt-deck.expected.json")["deck"]
    seed_cards([make_card(id=c["card"]["uid"], oracle_id=c["card"]["uid"], set=c["card"]["edition"]["editioncode"],
                          collector_number=c["card"]["collectorNumber"], name=c["card"]["oracleCard"]["name"]) for c in deck["cards"]])
    r = client.post("/api/ingest/deck-from-browser", json={"source": "archidekt", "deck": deck})
    assert r.status_code == 200, r.text
    assert r.json()["deck"]["source"] == "archidekt" and r.json()["deck_name"] == deck["name"]


# ---------- scraper health ----------

def test_new_readers_are_registered_and_reportable():
    keys = scraper_health.by_key()
    assert keys["companion-deck/archidekt"].canary == "browser"
    assert keys["companion-collection/moxfield"].canary == "browser"
    assert scraper_health.reported_key("archidekt.changed") == "companion-deck/archidekt"
    assert scraper_health.reported_key("moxfield.collection_changed") == "companion-collection/moxfield"
