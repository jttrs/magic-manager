"""``deck_compose_plan`` / ``deck_assign_from_composition`` net what the deck
already holds (top-up), and ``mm audit deck-inventory`` reports built decks
short of their recipe."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from magic_manager import db, decks, inventory

runner = CliRunner()


def _pledged(slug, sid, finish):
    with db.connect() as c:
        r = c.execute(
            "SELECT da.count FROM deck_assignments da JOIN decks d ON d.deck_id = da.deck_id "
            "WHERE d.slug=? AND da.scryfall_id=? AND da.finish=?", (slug, sid, finish)).fetchone()
        return r["count"] if r else 0


@pytest.fixture
def deck(seed_cards, make_card):
    seed_cards([make_card(id="x", name="Xx", collector_number="1"),
                make_card(id="y", name="Yy", collector_number="2")])
    inventory.inventory_add("x", "nonfoil", 2)
    decks.deck_create("d", "D", precon_state="deconstructed")
    decks.deck_add_card("d", "x", "main", "nonfoil", 2)
    return "d"


def _row(plan, sid, finish):
    return next(r for r in plan["rows"] if (r["scryfall_id"], r["finish"]) == (sid, finish))


def test_plan_nets_existing_pledges(deck):
    decks.deck_assign_batch(deck, [("x", "nonfoil", 1)])
    plan = decks.deck_compose_plan(deck)
    row = _row(plan, "x", "nonfoil")
    assert (row["need"], row["pledged"], row["remaining"], row["free"]) == (2, 1, 1, 1)
    assert plan["shortfalls"] == []


def test_assign_from_composition_tops_up_then_is_a_noop(deck):
    decks.deck_assign_batch(deck, [("x", "nonfoil", 1)])
    res = decks.deck_assign_from_composition(deck)
    assert (res["assigned_rows"], res["assigned_qty"]) == (1, 1)
    assert _pledged(deck, "x", "nonfoil") == 2
    again = decks.deck_assign_from_composition(deck)      # must not raise
    assert (again["assigned_rows"], again["assigned_qty"], again["shortfalls"]) == (0, 0, [])
    assert again["either_choices"] == []
    assert _pledged(deck, "x", "nonfoil") == 2


def test_real_shortfall_still_reported(deck):
    inventory.inventory_remove("x", "nonfoil", 1)
    decks.deck_assign_batch(deck, [("x", "nonfoil", 1)])
    plan = decks.deck_compose_plan(deck)
    assert [(s["remaining"], s["free"]) for s in plan["shortfalls"]] == [(1, 0)]


def test_either_prefers_finish_already_pledged(seed_cards, make_card):
    seed_cards([make_card(id="f", name="Ff", collector_number="3")])
    inventory.inventory_add("f", "foil", 1)
    inventory.inventory_add("f", "nonfoil", 1)
    decks.deck_create("e", "E", precon_state="deconstructed")
    decks.deck_add_card("e", "f", "main", "either", 1)
    decks.deck_assign_batch("e", [("f", "foil", 1)])
    plan = decks.deck_compose_plan("e")
    assert plan["either_choices"] == [{"scryfall_id": "f", "chose_finish": "foil", "reason": "already-pledged"}]
    row = _row(plan, "f", "foil")
    assert (row["pledged"], row["remaining"]) == (1, 0)
    assert decks.deck_assign_from_composition("e")["assigned_qty"] == 0
    assert _pledged("e", "f", "nonfoil") == 0


def test_dry_run_cli_lines(deck):
    from magic_manager.cli import app
    decks.deck_assign_batch(deck, [("x", "nonfoil", 1)])
    inventory.inventory_remove("x", "nonfoil", 1)       # owned 1, pledged 1 → the missing copy has no free card
    res = runner.invoke(app, ["deck", "compose", deck, "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "# already pledged to this deck: 1 of 2 card-qty" in res.stdout
    assert "/nonfoil: need 1 (recipe 2, pledged 1), free 0" in res.stdout


def test_audit_reports_built_decks_short_of_recipe(deck):
    from magic_manager.cli import app, _built_decks_short
    decks.deck_assign_batch(deck, [("x", "nonfoil", 1)])    # marks it built, 1 of 2 pledged
    assert _built_decks_short() == [
        {"slug": deck, "need": 2, "pledged": 1, "short": 1, "coverable": 1}]
    res = runner.invoke(app, ["audit", "deck-inventory"])
    assert res.exit_code == 0, res.output                    # report-only: exit code unchanged
    assert "Built decks short of their recipe: 1" in res.stdout
    assert "pledged 1 of 2; free inventory covers 1 of the 1 missing" in res.stdout
    assert f"uv run mm deck compose {deck}" in res.stdout
    decks.deck_assign_from_composition(deck)
    assert _built_decks_short() == []
