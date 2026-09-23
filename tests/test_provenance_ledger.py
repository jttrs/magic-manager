"""Provenance ledger (V19) — every inventory write path emits a ledger event,
and inventory.quantity stays == SUM(inventory_events.delta).

Offline suite: uses the tmp_db + seed_cards + fake_mtgjson fixtures from
conftest. Each test drives one write path and asserts (a) a matching
ingest_events row of the right method and (b) the reconciliation invariant.
"""

from __future__ import annotations

import pytest


def _ledger_sum(conn, sid, finish):
    row = conn.execute(
        "SELECT COALESCE(SUM(delta), 0) AS s FROM inventory_events "
        "WHERE scryfall_id = ? AND finish = ?",
        (sid, finish),
    ).fetchone()
    return row["s"]


def _inv_qty(conn, sid, finish):
    row = conn.execute(
        "SELECT quantity FROM inventory WHERE scryfall_id = ? AND finish = ?",
        (sid, finish),
    ).fetchone()
    return row["quantity"] if row else 0


def _methods(conn):
    return [r["method"] for r in conn.execute(
        "SELECT method FROM ingest_events ORDER BY ingest_id")]


# ---------- per-path coverage ----------

def test_inventory_add_emits_adhoc_event(tmp_db, seed_cards, make_card):
    from magic_manager import db, inventory as inv

    sid = "11111111-0000-0000-0000-000000000001"
    seed_cards([make_card(id=sid, set="tst", collector_number="1")])

    inv.inventory_add(sid, "nonfoil", 3)

    with db.connect() as conn:
        assert _methods(conn) == ["adhoc"]
        assert _inv_qty(conn, sid, "nonfoil") == 3
        assert _ledger_sum(conn, sid, "nonfoil") == 3


def test_inventory_add_merge_records_signed_delta(tmp_db, seed_cards, make_card):
    from magic_manager import db, inventory as inv

    sid = "11111111-0000-0000-0000-000000000002"
    seed_cards([make_card(id=sid, set="tst", collector_number="2")])

    inv.inventory_add(sid, "nonfoil", 2)          # +2
    inv.inventory_add(sid, "nonfoil", 5, replace=True)   # replace 2 -> 5 == +3

    with db.connect() as conn:
        # two adhoc events, deltas +2 then +3, cache == 5 == sum
        assert _methods(conn) == ["adhoc", "adhoc"]
        assert _inv_qty(conn, sid, "nonfoil") == 5
        assert _ledger_sum(conn, sid, "nonfoil") == 5


def test_inventory_remove_records_negative_delta(tmp_db, seed_cards, make_card):
    from magic_manager import db, inventory as inv

    sid = "11111111-0000-0000-0000-000000000003"
    seed_cards([make_card(id=sid, set="tst", collector_number="3")])

    inv.inventory_add(sid, "foil", 4)
    inv.inventory_remove(sid, "foil", qty=1)   # -1 -> 3
    inv.inventory_remove(sid, "foil")          # delete remaining 3 -> 0

    with db.connect() as conn:
        assert _inv_qty(conn, sid, "foil") == 0
        assert _ledger_sum(conn, sid, "foil") == 0  # +4 -1 -3


def test_inventory_set_records_signed_delta(tmp_db, seed_cards, make_card):
    from magic_manager import db, inventory as inv

    sid = "11111111-0000-0000-0000-000000000004"
    seed_cards([make_card(id=sid, set="tst", collector_number="4")])

    inv.inventory_set(sid, "nonfoil", 3)   # +3 (intake method default)
    inv.inventory_set(sid, "nonfoil", 1)   # -2
    inv.inventory_set(sid, "nonfoil", 0)   # -1 -> deleted

    with db.connect() as conn:
        assert set(_methods(conn)) == {"intake"}
        assert _inv_qty(conn, sid, "nonfoil") == 0
        assert _ledger_sum(conn, sid, "nonfoil") == 0


def test_import_precon_emits_one_precon_event(tmp_db, seed_cards, make_card, fake_mtgjson, fake_scryfall):
    from magic_manager import db, decks

    a = "22222222-0000-0000-0000-000000000001"
    b = "22222222-0000-0000-0000-000000000002"
    seed_cards([
        make_card(id=a, set="tst", collector_number="10", name="Card A"),
        make_card(id=b, set="tst", collector_number="11", name="Card B"),
    ])
    fake_scryfall()  # sync is a no-op; cards already seeded
    fake_mtgjson(deck={
        "name": "Test Precon",
        "code": "tst",
        "type": "Commander Deck",
        "commander": [{"count": 1, "isFoil": False, "setCode": "tst",
                       "identifiers": {"scryfallId": a}}],
        "mainBoard": [{"count": 2, "isFoil": False, "setCode": "tst",
                       "identifiers": {"scryfallId": b}}],
    })

    decks.import_precon("TestPrecon_TST", slug="test-precon")

    with db.connect() as conn:
        methods = _methods(conn)
        assert methods.count("precon") == 1, methods
        # commander a: +1, mainboard b: +2 — both attributed to the one event
        assert _inv_qty(conn, a, "nonfoil") == 1
        assert _inv_qty(conn, b, "nonfoil") == 2
        assert _ledger_sum(conn, a, "nonfoil") == 1
        assert _ledger_sum(conn, b, "nonfoil") == 2
        # exactly one ingest event, and every inventory_events row points at it
        ev = conn.execute("SELECT ingest_id FROM ingest_events "
                          "WHERE method='precon'").fetchone()["ingest_id"]
        rows = conn.execute("SELECT DISTINCT ingest_id FROM inventory_events").fetchall()
        assert [r["ingest_id"] for r in rows] == [ev]


# ---------- reconciliation invariant ----------

def test_reconcile_empty_after_mixed_ops(tmp_db, seed_cards, make_card):
    from magic_manager import db, inventory as inv, ingest

    ids = [f"33333333-0000-0000-0000-00000000000{i}" for i in range(1, 4)]
    seed_cards([make_card(id=s, set="tst", collector_number=str(20 + i))
                for i, s in enumerate(ids)])

    inv.inventory_add(ids[0], "nonfoil", 4)
    inv.inventory_add(ids[1], "foil", 2)
    inv.inventory_remove(ids[0], "nonfoil", qty=1)
    inv.inventory_set(ids[2], "nonfoil", 3)

    with db.connect() as conn:
        drift = ingest.reconcile_inventory_ledger(conn)
        assert drift == [], drift


def test_rebuild_from_ledger_is_noop_when_consistent(tmp_db, seed_cards, make_card):
    from magic_manager import db, inventory as inv, ingest

    sid = "44444444-0000-0000-0000-000000000001"
    seed_cards([make_card(id=sid, set="tst", collector_number="30")])
    inv.inventory_add(sid, "nonfoil", 5)
    inv.inventory_remove(sid, "nonfoil", qty=2)

    with db.connect() as conn:
        before = {(r["scryfall_id"], r["finish"]): r["quantity"]
                  for r in conn.execute("SELECT * FROM inventory")}
        result = ingest.rebuild_inventory_from_ledger(conn)
        after = {(r["scryfall_id"], r["finish"]): r["quantity"]
                 for r in conn.execute("SELECT * FROM inventory")}

    assert result["drift_before"] == 0
    assert before == after == {(sid, "nonfoil"): 3}


def test_rebuild_repairs_injected_drift(tmp_db, seed_cards, make_card):
    from magic_manager import db, inventory as inv, ingest

    sid = "44444444-0000-0000-0000-000000000002"
    seed_cards([make_card(id=sid, set="tst", collector_number="31")])
    inv.inventory_add(sid, "nonfoil", 6)

    # Corrupt the cache directly (simulating a pre-ledger drift), NOT the ledger.
    with db.connect() as conn:
        conn.execute("UPDATE inventory SET quantity = 99 WHERE scryfall_id = ?", (sid,))

    with db.connect() as conn:
        drift = ingest.reconcile_inventory_ledger(conn)
        assert len(drift) == 1
        result = ingest.rebuild_inventory_from_ledger(conn)
        assert result["drift_before"] == 1
        assert ingest.reconcile_inventory_ledger(conn) == []
        assert _inv_qty(conn, sid, "nonfoil") == 6  # restored to ledger truth


# ---------- find_events_by_sha ----------

def test_open_event_discards_noop(tmp_db):
    """An ingest event that records no deltas is deleted on exit (no dangling
    dimension rows from e.g. a batch where every card failed to resolve)."""
    from magic_manager import db, ingest

    with ingest.open_ingest_event("adhoc", label="empty batch"):
        pass  # record nothing

    with db.connect() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM ingest_events").fetchone()["n"]
        assert n == 0


def test_find_events_by_sha_roundtrip(tmp_db):
    from magic_manager import db, ingest

    with db.connect() as conn:
        eid = ingest.create_event(conn, "checklist", label="set:tst",
                                  source_sha256="deadbeef", mode="additive")
    with db.connect() as conn:
        found = ingest.find_events_by_sha(conn, "deadbeef")
        assert len(found) == 1
        assert found[0]["id"] == eid
        assert found[0]["method"] == "checklist"
        assert ingest.find_events_by_sha(conn, "nope") == []
