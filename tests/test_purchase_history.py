"""provenance.history: the purchase-history timeline read off the V19 ledger."""
from __future__ import annotations

import pytest

from magic_manager import db, decks, ingest, inventory, provenance

A = "00000000-0000-0000-0000-00000000000a"
B = "00000000-0000-0000-0000-00000000000b"


@pytest.fixture
def seeded(seed_cards, make_card, fake_scryfall):
    fake_scryfall(all_sets=[{"code": "fin", "name": "Final Fantasy"}])
    seed_cards([
        make_card(id=A, name="Alpha", set="fin", collector_number="1", prices={"usd": "1.50", "usd_foil": "4.00"}),
        make_card(id=B, oracle_id="bbbbbbbb-0000-0000-0000-0000000000bb", name="Beta", set="fin",
                  collector_number="2", prices={"usd": "0.25", "usd_foil": None}),
    ])


def _event(method, label=None, source_path=None, status="success", *, rows_added=0, rows_updated=0):
    with db.connect() as conn:
        iid = ingest.create_event(conn, method, label=label, source_path=source_path)
        conn.execute("UPDATE ingest_events SET status = ?, rows_added = ?, rows_updated = ? WHERE ingest_id = ?",
                     (status, rows_added, rows_updated, iid))
        conn.commit()
    return iid


def _by_id(h):
    return {e.ingest_id: e for e in h.entries}


def test_entries_classify_title_and_value(seeded):
    decks.deck_create("goblins", "Goblins", source_precon_file_name="Goblins_FIN", kind="deck")
    decks.deck_create("camp", "Camp Comrades", source_precon_file_name="CampComrades_FIN",
                      precon_state="deconstructed", kind="pool")
    legacy = _event("checklist", "set:fin", "checklists/final-fantasy-add-checklist.xlsx", rows_added=213)
    jump = _event("precon", "jumpstart:fin", "checklists/fin-jumpstart-checklist.xlsx", rows_added=3)
    recon = _event("checklist", "backfill:checklist", status="backfill")
    unknown = _event("unattributed-backfill", "backfill:unattributed", status="backfill")
    inventory.inventory_add(A, "nonfoil", 4, ingest_id=recon)
    inventory.inventory_add(B, "nonfoil", 2, ingest_id=unknown)
    precon = _event("precon", "precon:Goblins_FIN", "Goblins_FIN")
    inventory.inventory_add(A, "foil", 1, ingest_id=precon)
    inventory.inventory_add(B, "nonfoil", 2, ingest_id=precon)
    pool = _event("precon", "trueup:CampComrades_FIN")
    with db.connect() as conn:                     # a trueup move: copies leave the unknown bucket
        ingest.record_delta(conn, unknown, B, "nonfoil", -2)
        ingest.record_delta(conn, pool, B, "nonfoil", 2)
        conn.commit()
    search = _event("adhoc", "web:search · birthday")
    inventory.inventory_add(A, "nonfoil", 1, ingest_id=search)
    move = _event("deck-assign", "deck-assigned:goblins", "deck:goblins", rows_added=2)
    failed = _event("precon", "precon:Nope_FIN", status="failed")

    h = provenance.history()
    got = _by_id(h)
    assert failed not in got
    assert [e.ingest_id for e in h.entries] == sorted(got, reverse=True)          # newest first

    e = got[precon]
    assert (e.kind, e.title, e.product, e.set_code, e.deck_slug, e.dated) == ("deck", "Goblins", "Goblins_FIN", "fin", "goblins", "acquired")
    assert (e.copies_in, e.held, e.printings, e.value_usd) == (3, 3, 2, 4.50)     # 1 foil A @4 + 2 B @0.25
    e = got[pool]
    assert (e.kind, e.title, e.dated, e.deck_slug, e.held) == ("pool", "Camp Comrades", "identified", None, 2)
    e = got[unknown]
    assert (e.kind, e.title, e.dated, e.copies_in, e.copies_out, e.held, e.value_usd) == (
        "unknown", "Provenance unknown", "reconstructed", 2, 2, 0, 0.0)
    e = got[recon]
    assert (e.kind, e.title, e.held, e.value_usd) == ("checklist", "Checklists before the ledger", 4, 6.0)
    e = got[legacy]
    assert (e.kind, e.title, e.detail, e.ledgered, e.lines) == (
        "checklist", "Checklist · Final Fantasy", "final-fantasy-add-checklist.xlsx", False, 213)
    assert (got[jump].kind, got[jump].title, got[jump].product) == ("checklist", "Jumpstart packs · Final Fantasy", None)
    e = got[search]
    assert (e.kind, e.title, e.detail, e.value_usd) == ("singles", "Added from search", "birthday", 1.5)
    e = got[move]
    assert (e.kind, e.title, e.deck_slug, e.ledgered, e.lines, e.held) == ("move", "Built Goblins", "goblins", True, 2, 0)


def test_event_lines_and_unknown(seeded):
    iid = _event("precon", "precon:Goblins_FIN", "Goblins_FIN")
    inventory.inventory_add(B, "nonfoil", 3, ingest_id=iid)
    inventory.inventory_add(A, "foil", 1, ingest_id=iid)
    inventory.inventory_remove(B, "nonfoil", 1)                     # a separate (adhoc) event
    entry, lines = provenance.history_event(iid)
    assert entry.held == 4
    assert [(ln.scryfall_id, ln.finish, ln.copies_in, ln.held, ln.unit_usd) for ln in lines] == [
        (A, "foil", 1, 1, 4.0), (B, "nonfoil", 3, 3, 0.25)]           # most valuable held first
    with pytest.raises(LookupError):
        provenance.history_event(99999)


def test_history_api_and_routes(seeded):
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app

    iid = _event("precon", "precon:Goblins_FIN", "Goblins_FIN")
    inventory.inventory_add(A, "nonfoil", 2, ingest_id=iid)
    c = TestClient(create_app(serve_frontend=False))
    r = c.get("/api/history")
    assert r.status_code == 200
    body = r.json()
    assert body["entries"][0]["title"] == "Goblins (FIN)" and body["entries"][0]["value_usd"] == 3.0
    r = c.get(f"/api/history/{iid}")
    assert r.status_code == 200
    (line,) = r.json()["lines"]
    assert (line["printing"]["name"], line["finish"], line["held"]) == ("Alpha", "nonfoil", 2)
    assert c.get("/api/history/99999").status_code == 404
