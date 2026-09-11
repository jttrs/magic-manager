"""Tests for decks.construct_precon_from_loose — register a precon as a tracked
`built` deck and pledge ALREADY-OWNED loose inventory to it, WITHOUT adding the
cards to inventory (no double-count).

Offline: tmp DB + fake_scryfall (drives the auto-sync inside import_precon) +
fake_mtgjson (the canned precon). The load-bearing guarantee is #3: inventory
quantity is invariant across a construct (only deck_assignments grows).
"""

from __future__ import annotations

import pytest


def _inv_snapshot(db):
    with db.connect() as conn:
        return {
            (r["scryfall_id"], r["finish"]): r["quantity"]
            for r in conn.execute(
                "SELECT scryfall_id, finish, quantity FROM inventory"
            ).fetchall()
        }


def _assignments(db):
    with db.connect() as conn:
        return {
            (r["scryfall_id"], r["finish"]): r["count"]
            for r in conn.execute(
                "SELECT scryfall_id, finish, count FROM deck_assignments"
            ).fetchall()
        }


def _deck_rows_for(db, file_name):
    with db.connect() as conn:
        return conn.execute(
            "SELECT slug, precon_state FROM decks WHERE source_precon_file_name = ?",
            (file_name,),
        ).fetchall()


def _seed_two_card_precon(fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """A 2-card precon (A commander ×1, B main ×2), both from set 'tst'.

    Seeds the two cards into the `cards` table up front (so loose inventory can
    be added before import_precon runs) AND primes the scryfall/mtgjson fakes.
    """
    from magic_manager import db
    sids = ["cfl-sid-a", "cfl-sid-b"]
    cards = [
        make_card(id=sids[0], set="tst", collector_number="1", name="A"),
        make_card(id=sids[1], set="tst", collector_number="2", name="B"),
    ]
    with db.connect() as conn:
        db.upsert_cards(conn, cards)
    deck = make_precon_deck(
        "Loose Kit", "Starter Kit",
        [{"sid": sids[0], "name": "A", "set": "tst", "cn": "1", "count": 1, "board": "commander"},
         {"sid": sids[1], "name": "B", "set": "tst", "cn": "2", "count": 2, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=cards)
    return sids


def test_full_coverage_pledges_all_without_touching_inventory(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    from magic_manager import decks, inventory, db
    sids = _seed_two_card_precon(fake_scryfall, fake_mtgjson, make_card, make_precon_deck)
    # Own the full recipe loose (A×1, B×2 nonfoil).
    with db.connect() as conn:
        inventory.inventory_add(sids[0], "nonfoil", 1, conn=conn)
        inventory.inventory_add(sids[1], "nonfoil", 2, conn=conn)

    res = decks.construct_precon_from_loose("LooseKit_TST")

    assert res["fully_covered"] is True
    assert res["created_recipe"] is True and res["reused_existing"] is False
    assert res["assigned_qty"] == res["recipe_card_qty"] == 3
    rows = _deck_rows_for(db, "LooseKit_TST")
    assert len(rows) == 1 and rows[0]["precon_state"] == "built"
    # inventory qty unchanged; assignments now hold the pledged copies.
    assert _inv_snapshot(db) == {(sids[0], "nonfoil"): 1, (sids[1], "nonfoil"): 2}
    assert _assignments(db) == {(sids[0], "nonfoil"): 1, (sids[1], "nonfoil"): 2}


def test_partial_coverage_refuses_without_flag_then_pledges_with_it(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    from magic_manager import decks, inventory, db
    sids = _seed_two_card_precon(fake_scryfall, fake_mtgjson, make_card, make_precon_deck)
    # Own only A (1 of the 2 distinct cards).
    with db.connect() as conn:
        inventory.inventory_add(sids[0], "nonfoil", 1, conn=conn)

    with pytest.raises(decks.AssignmentOverflow):
        decks.construct_precon_from_loose("LooseKit_TST")
    # Recipe row was created (built, 0 pledged); nothing pledged on refusal.
    rows = _deck_rows_for(db, "LooseKit_TST")
    assert len(rows) == 1 and rows[0]["precon_state"] == "built"
    assert _assignments(db) == {}

    # Retry with allow_shortfall → pledges the covered card, lists the short one.
    res = decks.construct_precon_from_loose("LooseKit_TST", allow_shortfall=True)
    assert res["reused_existing"] is True and res["created_recipe"] is False
    assert res["fully_covered"] is False
    assert _assignments(db) == {(sids[0], "nonfoil"): 1}
    short_sids = {s["scryfall_id"] for s in res["shortfalls"]}
    assert sids[1] in short_sids


def test_no_inventory_double_count(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """Load-bearing: inventory quantity is byte-for-byte invariant; only the
    free slice shrinks (proving a pledge happened)."""
    from magic_manager import decks, inventory, db
    sids = _seed_two_card_precon(fake_scryfall, fake_mtgjson, make_card, make_precon_deck)
    with db.connect() as conn:
        inventory.inventory_add(sids[0], "nonfoil", 1, conn=conn)
        inventory.inventory_add(sids[1], "nonfoil", 2, conn=conn)

    before = _inv_snapshot(db)
    free_b_before = inventory.free_quantity(sids[1], "nonfoil")

    decks.construct_precon_from_loose("LooseKit_TST")

    assert _inv_snapshot(db) == before, "inventory quantity must not change"
    assert inventory.free_quantity(sids[1], "nonfoil") == free_b_before - 2


def test_rerun_reuses_recipe_and_does_not_double_pledge(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    from magic_manager import decks, inventory, db
    sids = _seed_two_card_precon(fake_scryfall, fake_mtgjson, make_card, make_precon_deck)
    with db.connect() as conn:
        inventory.inventory_add(sids[0], "nonfoil", 1, conn=conn)
        inventory.inventory_add(sids[1], "nonfoil", 2, conn=conn)

    decks.construct_precon_from_loose("LooseKit_TST")
    first = _assignments(db)
    res2 = decks.construct_precon_from_loose("LooseKit_TST")

    assert res2["reused_existing"] is True and res2["created_recipe"] is False
    assert len(_deck_rows_for(db, "LooseKit_TST")) == 1, "no -2 clone on re-run"
    assert _assignments(db) == first, "recipe cap prevents re-pledge"


def test_new_copy_creates_second_row(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    from magic_manager import decks, inventory, db
    sids = _seed_two_card_precon(fake_scryfall, fake_mtgjson, make_card, make_precon_deck)
    # Own enough for TWO copies so the second can also pledge.
    with db.connect() as conn:
        inventory.inventory_add(sids[0], "nonfoil", 2, conn=conn)
        inventory.inventory_add(sids[1], "nonfoil", 4, conn=conn)

    decks.construct_precon_from_loose("LooseKit_TST")
    res2 = decks.construct_precon_from_loose(
        "LooseKit_TST", new_copy=True, slug="loose-kit-2")

    assert res2["created_recipe"] is True and res2["reused_existing"] is False
    rows = _deck_rows_for(db, "LooseKit_TST")
    assert len(rows) == 2
    assert {r["slug"] for r in rows} == {"loose-kit", "loose-kit-2"}


def test_dry_run_writes_no_assignments(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    from magic_manager import decks, inventory, db
    sids = _seed_two_card_precon(fake_scryfall, fake_mtgjson, make_card, make_precon_deck)
    with db.connect() as conn:
        inventory.inventory_add(sids[0], "nonfoil", 1, conn=conn)
        inventory.inventory_add(sids[1], "nonfoil", 2, conn=conn)

    res = decks.construct_precon_from_loose("LooseKit_TST", dry_run=True)

    assert res["assigned_rows"] == 0
    assert _assignments(db) == {}, "dry-run must not pledge"
    # The recipe row is created (a built deck with 0 pledged), which is fine.
    assert len(_deck_rows_for(db, "LooseKit_TST")) == 1
