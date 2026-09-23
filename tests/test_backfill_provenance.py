"""V19 historical backfill — reconstruct the ledger from ground truth so that
SUM(inventory_events.delta) == inventory EXACTLY, with the honest remainder in
the unattributed bucket.

Offline: seeds inventory + a precon-sourced deck, stubs mtgjson.deck, runs the
backfill's core, and asserts exact reconciliation + correct bucket split.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _load_backfill():
    """Import scripts/backfill_provenance.py as a module."""
    import importlib.util
    path = ROOT / "scripts" / "backfill_provenance.py"
    spec = importlib.util.spec_from_file_location("backfill_provenance", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_backfill_splits_precon_vs_unattributed(tmp_db, seed_cards, make_card,
                                                fake_mtgjson, monkeypatch):
    from magic_manager import db, inventory as inv, decks, ingest

    a = "55555555-0000-0000-0000-000000000001"  # precon card
    b = "55555555-0000-0000-0000-000000000002"  # precon card
    c = "55555555-0000-0000-0000-000000000003"  # loose (unattributed) card
    seed_cards([
        make_card(id=a, set="tst", collector_number="1", name="Precon A"),
        make_card(id=b, set="tst", collector_number="2", name="Precon B"),
        make_card(id=c, set="tst", collector_number="3", name="Loose C"),
    ])

    # Precon decklist: a×1 (commander) + b×2 (main).
    fake_mtgjson(deck={
        "name": "Test Precon", "code": "tst", "type": "Commander Deck",
        "commander": [{"count": 1, "isFoil": False, "setCode": "tst",
                       "identifiers": {"scryfallId": a}}],
        "mainBoard": [{"count": 2, "isFoil": False, "setCode": "tst",
                       "identifiers": {"scryfallId": b}}],
    })

    # Create a precon-sourced deck row WITHOUT going through import_precon's
    # inventory writes — we want a "pre-ledger" state to reconstruct. Insert the
    # deck row directly, then seed inventory to what a real import would leave:
    # a=1, b=2 (from the precon) PLUS c=4 loose (booster pulls, unattributable).
    with db.connect() as conn:
        decks.deck_create("test-precon", "Test Precon",
                          source_precon_file_name="TestPrecon_TST",
                          precon_state="built", conn=conn)

    # Seed inventory directly (bypassing the ledger) to simulate a pre-V19 DB.
    with db.connect() as conn:
        for sid, fin, q in ((a, "nonfoil", 1), (b, "nonfoil", 2), (c, "nonfoil", 4)):
            conn.execute(
                "INSERT INTO inventory (scryfall_id, finish, quantity, acquired_at) "
                "VALUES (?, ?, ?, '2021-01-01T00:00:00+00:00')", (sid, fin, q))

    # Ledger is empty at this point; run the backfill core.
    bf = _load_backfill()
    rc = bf.run(force=False, dry_run=False)
    assert rc == 0

    with db.connect() as conn:
        # Exact reconciliation: no drift.
        assert ingest.reconcile_inventory_ledger(conn) == []

        # Precon event attributed a(1) + b(2) = 3 copies.
        precon = conn.execute(
            "SELECT ingest_id FROM ingest_events WHERE label='backfill:precon'"
        ).fetchone()
        precon_sum = conn.execute(
            "SELECT COALESCE(SUM(delta),0) AS s FROM inventory_events WHERE ingest_id=?",
            (precon["ingest_id"],),
        ).fetchone()["s"]
        assert precon_sum == 3

        # Unattributed bucket holds the loose c(4).
        unattr = conn.execute(
            "SELECT ingest_id FROM ingest_events WHERE method='unattributed-backfill'"
        ).fetchone()
        unattr_sum = conn.execute(
            "SELECT COALESCE(SUM(delta),0) AS s FROM inventory_events WHERE ingest_id=?",
            (unattr["ingest_id"],),
        ).fetchone()["s"]
        assert unattr_sum == 4


def test_backfill_refuses_double_run_without_force(tmp_db, seed_cards, make_card,
                                                   fake_mtgjson):
    from magic_manager import db

    sid = "66666666-0000-0000-0000-000000000001"
    seed_cards([make_card(id=sid, set="tst", collector_number="1")])
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO inventory (scryfall_id, finish, quantity, acquired_at) "
            "VALUES (?, 'nonfoil', 2, '2021-01-01T00:00:00+00:00')", (sid,))
    fake_mtgjson(deck={})

    bf = _load_backfill()
    assert bf.run(force=False, dry_run=False) == 0     # first run OK
    assert bf.run(force=False, dry_run=False) == 2     # refuses (already populated)
    assert bf.run(force=True, dry_run=False) == 0      # --force clears + rebuilds

    with db.connect() as conn:
        from magic_manager import ingest
        assert ingest.reconcile_inventory_ledger(conn) == []
