"""Tests for the conn= transaction-threading seam added in the atomicity fix.

Guarantees: (1) CRUD fns enlisted in a caller's open transaction that then
raises leave NOTHING persisted (rollback); (2) the conn=None standalone path
still commits (behavior parity for existing callers)."""

from __future__ import annotations

import pytest


def test_conn_threaded_writes_rollback_on_outer_failure(tmp_db, seed_cards, make_card):
    """deck_create + deck_add_card + inventory_add sharing one connection that
    then raises → the whole unit rolls back (no orphan deck, no inventory)."""
    from magic_manager import db, decks, inventory
    seed_cards([make_card(id="c1", set="tst", collector_number="1", finishes=["nonfoil"])])

    with pytest.raises(RuntimeError):
        with db.connect() as conn:
            decks.deck_create("rollme", "Roll Me", conn=conn)
            decks.deck_add_card("rollme", "c1", "main", "nonfoil", 1, conn=conn)
            inventory.inventory_add("c1", "nonfoil", 3, conn=conn)
            raise RuntimeError("boom before commit")

    # Nothing survived the rollback.
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM decks").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM deck_cards").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0] == 0


def test_conn_threaded_writes_commit_on_success(tmp_db, seed_cards, make_card):
    """Same writes on a shared connection that exits cleanly → all persist once."""
    from magic_manager import db, decks, inventory
    seed_cards([make_card(id="c2", set="tst", collector_number="2", finishes=["nonfoil"])])

    with db.connect() as conn:
        decks.deck_create("keepme", "Keep Me", conn=conn)
        decks.deck_add_card("keepme", "c2", "main", "nonfoil", 1, conn=conn)
        inventory.inventory_add("c2", "nonfoil", 3, conn=conn)

    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM decks").fetchone()[0] == 1
        assert conn.execute("SELECT quantity FROM inventory WHERE scryfall_id='c2'").fetchone()[0] == 3


def test_conn_none_standalone_commits(tmp_db, seed_cards, make_card):
    """conn=None (the existing-caller path) commits independently — parity."""
    from magic_manager import db, decks, inventory
    seed_cards([make_card(id="c3", set="tst", collector_number="3", finishes=["nonfoil"])])

    decks.deck_create("solo", "Solo")
    decks.deck_add_card("solo", "c3", "main", "nonfoil", 2)
    inventory.inventory_add("c3", "nonfoil", 5)

    assert decks.deck_get("solo") is not None
    with db.connect() as conn:
        assert conn.execute("SELECT quantity FROM inventory WHERE scryfall_id='c3'").fetchone()[0] == 5
