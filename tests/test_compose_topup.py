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
    assert plan["either_choices"] == [{"scryfall_id": "f", "chose_finish": "foil", "reason": "shared-rule"}]
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
    from magic_manager import audit
    from magic_manager.cli import app
    decks.deck_assign_batch(deck, [("x", "nonfoil", 1)])    # marks it built, 1 of 2 pledged
    assert audit.built_decks_short() == [
        {"slug": deck, "need": 2, "pledged": 1, "short": 1, "coverable": 1}]
    res = runner.invoke(app, ["audit", "deck-inventory"])
    assert res.exit_code == 0, res.output                    # report-only: exit code unchanged
    assert "Built decks short of their recipe: 1" in res.stdout
    assert "pledged 1 of 2; free inventory covers 1 of the 1 missing" in res.stdout
    assert f"uv run mm deck compose {deck}" in res.stdout
    decks.deck_assign_from_composition(deck)
    assert audit.built_decks_short() == []


# ---------- 'either' slots resolve through the shared rule (decks.resolve_needs) ----------

def _either_deck(seed_cards, make_card, slug, sid, *, count, nonfoil=0, foil=0):
    seed_cards([make_card(id=sid, name=sid.upper() * 2, collector_number=str(sum(map(ord, sid))))])
    if nonfoil:
        inventory.inventory_add(sid, "nonfoil", nonfoil)
    if foil:
        inventory.inventory_add(sid, "foil", foil)
    decks.deck_create(slug, slug.upper(), precon_state="deconstructed")
    decks.deck_add_card(slug, sid, "main", "either", count)


def test_either_pledged_across_both_finishes_is_complete(seed_cards, make_card):
    from magic_manager import audit
    _either_deck(seed_cards, make_card, "s", "sp", count=2, nonfoil=3, foil=1)
    decks.deck_assign_batch("s", [("sp", "nonfoil", 1), ("sp", "foil", 1)])
    plan = decks.deck_compose_plan("s")
    assert plan["shortfalls"] == []
    assert {(r["finish"], r["need"], r["pledged"], r["remaining"]) for r in plan["rows"]} == {
        ("nonfoil", 1, 1, 0), ("foil", 1, 1, 0)}
    assert plan["either_choices"] == [{"scryfall_id": "sp", "chose_finish": "split", "reason": "shared-rule"}]
    res = decks.deck_assign_from_composition("s")           # must not raise AssignmentOverflow
    assert (res["assigned_rows"], res["assigned_qty"]) == (0, 0)
    assert "s" not in [d["slug"] for d in audit.built_decks_short()]
    assert decks.compose_summary(plan) == {"need": 2, "pledged": 2, "short": 0, "coverable": 0}


def test_either_partly_pledged_in_secondary_finish_tops_up(seed_cards, make_card):
    _either_deck(seed_cards, make_card, "h", "hp", count=2, nonfoil=3, foil=1)
    decks.deck_assign_batch("h", [("hp", "foil", 1)])
    plan = decks.deck_compose_plan("h")
    assert plan["shortfalls"] == []
    assert plan["either_choices"][0]["chose_finish"] == "split"
    res = decks.deck_assign_from_composition("h")           # must not raise
    assert (res["assigned_rows"], res["assigned_qty"]) == (1, 1)
    assert (_pledged("h", "hp", "nonfoil"), _pledged("h", "hp", "foil")) == (1, 1)
    assert decks.deck_assign_from_composition("h")["assigned_qty"] == 0


def test_either_primary_finish_already_pledged(seed_cards, make_card):
    _either_deck(seed_cards, make_card, "p", "pp", count=1, nonfoil=1, foil=1)
    decks.deck_assign_batch("p", [("pp", "nonfoil", 1)])
    plan = decks.deck_compose_plan("p")
    assert plan["either_choices"] == [{"scryfall_id": "pp", "chose_finish": "nonfoil", "reason": "shared-rule"}]
    assert [(r["finish"], r["remaining"]) for r in plan["rows"]] == [("nonfoil", 0)]
    assert decks.deck_assign_from_composition("p")["assigned_qty"] == 0
    assert _pledged("p", "pp", "foil") == 0


def test_foil_first_order(seed_cards, make_card):
    _either_deck(seed_cards, make_card, "o", "op", count=2, nonfoil=1, foil=1)
    assert decks.deck_compose_plan("o")["either_choices"][0]["chose_finish"] == "split"
    _either_deck(seed_cards, make_card, "q", "qp", count=1, nonfoil=1, foil=1)
    # One 'either' copy, both finishes free → the first finish in order wins.
    nonfoil = decks.deck_compose_plan("q")
    foil = decks.deck_compose_plan("q", foil_first=True)
    assert nonfoil["either_choices"] == [{"scryfall_id": "qp", "chose_finish": "nonfoil", "reason": "shared-rule"}]
    assert foil["either_choices"] == [{"scryfall_id": "qp", "chose_finish": "foil", "reason": "shared-rule"}]
    assert [r["finish"] for r in foil["rows"]] == ["foil"]
    res = decks.deck_assign_from_composition("q", foil_first=True)
    assert (_pledged("q", "qp", "foil"), _pledged("q", "qp", "nonfoil"), res["assigned_qty"]) == (1, 0, 1)
    # Two copies, one of each finish free → split regardless of order, no shortfall.
    assert decks.deck_compose_plan("o", foil_first=True)["shortfalls"] == []


def test_exact_and_either_rows_of_one_printing(seed_cards, make_card):
    seed_cards([make_card(id="xp", name="Xp", collector_number="8")])
    inventory.inventory_add("xp", "nonfoil", 1)
    inventory.inventory_add("xp", "foil", 1)
    decks.deck_create("m", "M", precon_state="deconstructed")
    decks.deck_add_card("m", "xp", "main", "either", 1)     # the 'either' row comes first
    decks.deck_add_card("m", "xp", "main", "nonfoil", 1)
    plan = decks.deck_compose_plan("m")
    assert plan["shortfalls"] == []
    assert {(r["finish"], r["need"]) for r in plan["rows"]} == {("nonfoil", 1), ("foil", 1)}
    assert plan["either_choices"] == [{"scryfall_id": "xp", "chose_finish": "foil", "reason": "shared-rule"}]
    assert decks.deck_assign_from_composition("m")["assigned_qty"] == 2
    again = decks.deck_compose_plan("m")
    assert [r["remaining"] for r in again["rows"]] == [0, 0]
    assert decks.deck_assign_from_composition("m")["assigned_qty"] == 0


def test_compose_summary_math(deck):
    inventory.inventory_add("y", "nonfoil", 1)
    decks.deck_add_card(deck, "y", "main", "nonfoil", 3)    # y: need 3, only 1 owned
    decks.deck_assign_batch(deck, [("x", "nonfoil", 1)])
    assert decks.compose_summary(decks.deck_compose_plan(deck)) == {
        "need": 5, "pledged": 1, "short": 4, "coverable": 2}
