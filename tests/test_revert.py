"""ingest.revert_event (V35): revert one import with a compensating event."""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from magic_manager import db, deck_edit, decks, ingest, inventory, provenance

A = "00000000-0000-0000-0000-00000000000a"
B = "00000000-0000-0000-0000-00000000000b"


@pytest.fixture
def cards(seed_cards, make_card, fake_scryfall):
    fake_scryfall(all_sets=[{"code": "fin", "name": "Final Fantasy"}])
    seed_cards([
        make_card(id=A, name="Alpha", set="fin", collector_number="1", prices={"usd": "1.50", "usd_foil": "4.00"}),
        make_card(id=B, oracle_id="bbbbbbbb-0000-0000-0000-0000000000bb", name="Beta", set="fin",
                  collector_number="2", prices={"usd": "0.25", "usd_foil": None}),
    ])


def _import(lines, method="import-block", label="web:deck · Goblins", mode=None):
    with ingest.open_ingest_event(method, label=label, mode=mode) as rec:
        for sid, fin, q in lines:
            inventory.inventory_add(sid, fin, q, conn=rec.conn, ingest_id=rec.ingest_id, method=method)
    return rec.ingest_id


def _owned():
    with db.connect() as c:
        return {(r[0], r[1]): r[2] for r in c.execute("SELECT scryfall_id, finish, quantity FROM inventory")}


def _reconciles():
    with db.connect() as c:
        return ingest.reconcile_inventory_ledger(c) == []


def _deck_for(iid, slug="goblins"):
    payload = {"source": "archidekt", "id": "42", "name": "Goblins", "author": None,
               "cards": [{"qty": 1, "name": "Alpha", "scryfall_id": A, "board": "main", "finish": "nonfoil"}]}
    r = deck_edit.import_payload(payload, ingest_id=iid)
    assert r["created"]
    if r["not_found"]:                      # offline: the fake Scryfall can't resolve it
        decks.deck_add_card(r["slug"], A, "main", "nonfoil", 1)
    return r["slug"]


def test_happy_path_compensates_and_keeps_history(cards):
    before = _import([(A, "nonfoil", 1)], method="adhoc", label="web:search")
    iid = _import([(A, "nonfoil", 2), (B, "nonfoil", 3)])
    plan = ingest.revert_event(iid)                     # dry run writes nothing
    assert plan.ok and (plan.copies_removed, plan.copies_restored) == (5, 0)
    assert _owned() == {(A, "nonfoil"): 3, (B, "nonfoil"): 3}

    done = ingest.revert_event(iid, dry_run=False)
    assert _owned() == {(A, "nonfoil"): 1}
    assert _reconciles()
    with db.connect() as c:
        ev = c.execute("SELECT method, label, reverts_ingest_id FROM ingest_events WHERE ingest_id = ?",
                       (done.revert_ingest_id,)).fetchone()
        assert tuple(ev) == ("revert", f"revert:{iid} · web:deck · Goblins", iid)
        assert c.execute("SELECT COUNT(*) FROM inventory_events WHERE ingest_id = ?", (iid,)).fetchone()[0] == 2

    h = {e.ingest_id: e for e in provenance.history().entries}
    assert (h[iid].reverted_by, h[iid].revertible, h[iid].held) == (done.revert_ingest_id, False, 0)
    assert h[before].held == 1 and h[before].revertible             # earlier copies stay with their import
    r = h[done.revert_ingest_id]
    assert (r.kind, r.reverts, r.revertible, r.detail) == ("revert", iid, False, "Added a deck's cards · Goblins")


def test_deletes_the_deck_the_import_saved(cards):
    iid = _import([(A, "nonfoil", 1)])
    slug = _deck_for(iid)
    plan = ingest.revert_event(iid)
    assert [d.slug for d in plan.decks] == [slug]
    ingest.revert_event(iid, dry_run=False)
    assert decks.deck_get(slug) is None


def test_deck_link_only_for_a_fresh_web_deck_import(cards):
    other = _import([(A, "nonfoil", 1)], method="adhoc", label="web:search")
    payload = {"source": "archidekt", "id": "7", "name": "X", "author": None,
               "cards": [{"qty": 1, "name": "Alpha", "scryfall_id": A, "board": "main", "finish": "nonfoil"}]}
    slug = deck_edit.import_payload(payload, ingest_id=other)["slug"]
    with db.connect() as c:
        assert c.execute("SELECT created_by_ingest_id FROM decks WHERE slug = ?", (slug,)).fetchone()[0] is None


def test_built_deck_blocks(cards):
    iid = _import([(A, "nonfoil", 1)])
    slug = _deck_for(iid)
    deck_edit.build(slug)
    plan = ingest.revert_event(iid)
    assert plan.refusal_code == "deck_in_use"
    with pytest.raises(ingest.RevertRefused):
        ingest.revert_event(iid, dry_run=False)
    assert _owned() == {(A, "nonfoil"): 1}


def test_pledged_copies_block_all_or_nothing(cards):
    iid = _import([(A, "nonfoil", 2), (B, "nonfoil", 1)])
    decks.deck_create("other", "Other")
    decks.deck_add_card("other", A, "main", "nonfoil", 1)
    deck_edit.build("other")
    plan = ingest.revert_event(iid)
    assert plan.refusal_code == "lines_blocked"
    [blocked] = plan.blocked
    assert (blocked.scryfall_id, blocked.blocker, blocked.pledged_to) == (A, "pledged", ["Other"])
    with pytest.raises(ingest.RevertRefused):
        ingest.revert_event(iid, dry_run=False)
    assert _owned() == {(A, "nonfoil"): 2, (B, "nonfoil"): 1}       # nothing partial
    with db.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM ingest_events WHERE method = 'revert'").fetchone()[0] == 0


def test_removed_copies_block(cards):
    iid = _import([(A, "nonfoil", 2)])
    inventory.inventory_remove(A, "nonfoil", 1)
    plan = ingest.revert_event(iid)
    assert plan.refusal_code == "lines_blocked"
    assert (plan.lines[0].blocker, plan.lines[0].held) == ("removed", 1)


def test_reverting_a_removal_puts_copies_back(cards):
    _import([(A, "nonfoil", 2)], method="adhoc", label=None)
    with ingest.open_ingest_event("adhoc") as rec:
        inventory.inventory_remove(A, "nonfoil", 1, conn=rec.conn, ingest_id=rec.ingest_id)
    plan = ingest.revert_event(rec.ingest_id, dry_run=False)
    assert plan.copies_restored == 1 and _owned() == {(A, "nonfoil"): 2} and _reconciles()


def test_double_revert_and_revert_of_revert_refused(cards):
    iid = _import([(A, "nonfoil", 1)])
    done = ingest.revert_event(iid, dry_run=False)
    assert ingest.revert_event(iid).refusal_code == "already_reverted"
    assert ingest.revert_event(done.revert_ingest_id).refusal_code == "not_revertible"
    with pytest.raises(ingest.RevertRefused):
        ingest.revert_event(iid, dry_run=False)
    with db.connect() as c, pytest.raises(sqlite3.IntegrityError):        # one revert per event, by schema
        ingest.create_event(c, "revert", reverts_ingest_id=iid)


@pytest.mark.parametrize("method,mode,label", [
    ("precon", None, "precon:Goblins_FIN"),
    ("purchase", "purchase", "purchase:manapool:1"),
    ("checklist", "replace", "set:fin"),
    ("checklist", "additive", "jumpstart:fin"),
])
def test_wrong_kind_refused(cards, method, mode, label):
    iid = _import([(A, "nonfoil", 1)], method=method, label=label, mode=mode)
    plan = ingest.revert_event(iid)
    assert plan.refusal_code == "not_revertible" and plan.refusal


def test_additive_set_checklist_and_collection_import_revert(cards):
    a = _import([(A, "nonfoil", 1)], method="checklist", label="set:fin", mode="additive")
    b = _import([(B, "nonfoil", 1)], method="collection-import", label="web:file Moxfield · x.csv", mode="add")
    assert ingest.revert_event(a).ok and ingest.revert_event(b).ok


def test_unknown_event(cards):
    with pytest.raises(LookupError):
        ingest.revert_event(999)


def test_v35_migration_from_v34(tmp_path, monkeypatch, make_card):
    f = tmp_path / "v34.db"
    raw = sqlite3.connect(str(f))
    raw.executescript(db.MIGRATIONS[0])
    for i in range(1, 34):
        raw.executescript(db.MIGRATIONS[i])
    db.upsert_card(raw, make_card(id="a"))
    raw.execute("INSERT INTO schema_version (version) VALUES (34)")
    raw.execute("INSERT INTO ingest_events (ingest_id, at, method, label) VALUES (7, '2026-01-01', 'adhoc', 'x')")
    raw.execute("INSERT INTO inventory_events (ingest_id, scryfall_id, finish, delta, at) VALUES (7, 'a', 'nonfoil', 1, '2026-01-01')")
    raw.execute("INSERT INTO decks (slug, name, created_at, updated_at) VALUES ('d', 'D', '2026', '2026')")
    raw.commit()
    raw.close()
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(f))
    with db.connect() as conn:
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == db.CURRENT_VERSION
        assert tuple(conn.execute("SELECT ingest_id, method, label, reverts_ingest_id FROM ingest_events").fetchone()) == (7, "adhoc", "x", None)
        assert conn.execute("SELECT created_by_ingest_id FROM decks").fetchone()[0] is None
        ingest.create_event(conn, "revert", reverts_ingest_id=7)
        assert conn.execute("PRAGMA foreign_key_check(inventory_events)").fetchall() == []


# ---------- API ----------

@pytest.fixture
def client(cards):
    from magic_manager.web.app import create_app
    with TestClient(create_app(serve_frontend=False)) as c:
        yield c


def test_api_plan_and_revert(client):
    iid = _import([(A, "nonfoil", 2)])
    _deck_for(iid)
    r = client.get(f"/api/history/{iid}/revert")
    assert r.status_code == 200
    p = r.json()
    assert p["ok"] and p["copies_removed"] == 2 and p["decks"][0]["name"] == "Goblins"
    assert p["lines"][0]["printing"]["name"] == "Alpha"
    entry = next(e for e in client.get("/api/history").json()["entries"] if e["ingest_id"] == iid)
    assert entry["revertible"] is True
    r = client.post(f"/api/history/{iid}/revert")
    assert r.status_code == 200, r.text
    assert r.json()["summary"] == "Reverted: removed 2 copies, deleted 1 decklist"
    r = client.post(f"/api/history/{iid}/revert")
    assert r.status_code == 409
    body = r.json()
    assert body["detail"]["plan"]["reason"] == "already_reverted"
    assert client.get("/api/history/999/revert").status_code == 404


def test_api_blocked_409_lists_lines(client):
    iid = _import([(A, "nonfoil", 1)])
    inventory.inventory_remove(A, "nonfoil", 1)
    r = client.post(f"/api/history/{iid}/revert")
    assert r.status_code == 409
    plan = r.json()["detail"]["plan"]
    assert plan["reason"] == "lines_blocked" and plan["lines"][0]["blocker"] == "removed"
