"""Tests for magic_manager.missing.variant_chase_printings / owned_oracle_ids
and magic_manager.card_diff.family_diff — the card-diff engine's three pools.

Offline: seeded tmp DB + faked all_sets ('tla' is configured with an empty
dupe-foil set so the preferred filter runs, matching test_functional_missing.py).
FIXTURE WARNING: make_card hardcodes ONE shared oracle_id — every test MUST
pass an explicit oracle_id= per distinct mechanical card.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def tla_family(monkeypatch):
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "tla", "parent_set_code": None,
                                  "name": "Avatar", "set_type": "expansion"}])


def _own(conn, sid, finish="nonfoil", qty=1):
    conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) "
                 "VALUES (?,?,?,'2025-01-01')", (sid, finish, qty))


def test_owned_oracle_ids_returns_exactly_seeded_owned(tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing, db
    seed_cards([
        make_card(id="owned1", oracle_id="o-owned", set="tla", collector_number="1",
                  rarity="rare", name="Owned"),
        make_card(id="notowned1", oracle_id="o-not-owned", set="tla", collector_number="2",
                  rarity="rare", name="NotOwned"),
    ])
    with db.connect() as conn:
        _own(conn, "owned1")
    assert missing.owned_oracle_ids({"tla"}) == {"o-owned"}


def test_variant_chase_is_printing_missing_intersect_owned_oracle(
        tmp_db, tla_family, seed_cards, make_card):
    """variant_chase_printings == missing_printings rows whose oracle_id is in
    owned_oracle_ids — verified by set identity against the two primitives."""
    from magic_manager import missing, db
    seed_cards([
        # Hero: base owned, borderless variant missing → variant-chase.
        make_card(id="hero-base", oracle_id="o-hero", set="tla", collector_number="5",
                  rarity="rare", name="Hero", prices={"usd": "1.00", "usd_foil": "2.00"}),
        make_card(id="hero-variant", oracle_id="o-hero", set="tla", collector_number="305",
                  rarity="rare", name="Hero", prices={"usd": "40.00", "usd_foil": "60.00"}),
        # Stranger: owned in zero printings → functional-missing, NOT variant-chase.
        make_card(id="stranger", oracle_id="o-stranger", set="tla", collector_number="6",
                  rarity="rare", name="Stranger", prices={"usd": "5.00", "usd_foil": None}),
    ])
    with db.connect() as conn:
        _own(conn, "hero-base")

    missing_rows = missing.missing_printings("tla")
    owned = missing.owned_oracle_ids({"tla"})
    expected = {r.scryfall_id for r in missing_rows
                if (r.card or {}).get("oracle_id") in owned}
    variant_rows = missing.variant_chase_printings("tla")
    actual = {r.scryfall_id for r in variant_rows}

    assert actual == expected
    assert actual == {"hero-variant"}  # the stranger (unowned oracle) is excluded


def test_variant_chase_equals_printing_missing_when_every_oracle_owned(
        tmp_db, tla_family, seed_cards, make_card):
    """Every missing printing's oracle IS owned elsewhere → variant_chase count
    == printing-missing count."""
    from magic_manager import missing, db
    seed_cards([
        make_card(id="a-base", oracle_id="o-a", set="tla", collector_number="7",
                  rarity="rare", name="A", prices={"usd": "1.00", "usd_foil": None}),
        make_card(id="a-variant", oracle_id="o-a", set="tla", collector_number="307",
                  rarity="rare", name="A", prices={"usd": "20.00", "usd_foil": None}),
        make_card(id="b-base", oracle_id="o-b", set="tla", collector_number="8",
                  rarity="rare", name="B", prices={"usd": "1.00", "usd_foil": None}),
        make_card(id="b-variant", oracle_id="o-b", set="tla", collector_number="308",
                  rarity="rare", name="B", prices={"usd": "25.00", "usd_foil": None}),
    ])
    with db.connect() as conn:
        _own(conn, "a-base")
        _own(conn, "b-base")

    missing_rows = missing.missing_printings("tla")
    variant_rows = missing.variant_chase_printings("tla", precomputed_missing=missing_rows)
    assert len(variant_rows) == len(missing_rows)
    assert {r.scryfall_id for r in variant_rows} == {r.scryfall_id for r in missing_rows}


def test_variant_chase_empty_when_no_oracle_owned(tmp_db, tla_family, seed_cards, make_card):
    """No cards owned at all → every oracle is unowned → variant_chase == 0."""
    from magic_manager import missing
    seed_cards([
        make_card(id="x", oracle_id="o-x", set="tla", collector_number="9",
                  rarity="rare", name="X", prices={"usd": "3.00", "usd_foil": None}),
        make_card(id="y", oracle_id="o-y", set="tla", collector_number="10",
                  rarity="rare", name="Y", prices={"usd": "4.00", "usd_foil": None}),
    ])
    missing_rows = missing.missing_printings("tla")
    assert len(missing_rows) > 0  # sanity: there IS something missing
    variant_rows = missing.variant_chase_printings("tla", precomputed_missing=missing_rows)
    assert variant_rows == []


def test_family_diff_pools_populated_and_counts_match(
        tmp_db, tla_family, seed_cards, make_card, monkeypatch):
    """family_diff assembles the three pools with counts matching the direct
    missing.py primitives. Pricing is local-first (sets.priced_map reads the
    seeded cards table directly, no network) — this test only asserts
    counts/rows, not $."""
    from magic_manager import missing, card_diff, db
    seed_cards([
        # Hero: base owned, variant missing → counts toward printing + variant-chase.
        make_card(id="hero-base", oracle_id="o-hero", set="tla", collector_number="5",
                  rarity="rare", name="Hero", prices={"usd": "1.00", "usd_foil": "2.00"}),
        make_card(id="hero-variant", oracle_id="o-hero", set="tla", collector_number="305",
                  rarity="rare", name="Hero", prices={"usd": "40.00", "usd_foil": "60.00"}),
        # Stranger: owned zero printings → counts toward printing + functional.
        make_card(id="stranger", oracle_id="o-stranger", set="tla", collector_number="6",
                  rarity="rare", name="Stranger", prices={"usd": "5.00", "usd_foil": None}),
    ])
    with db.connect() as conn:
        _own(conn, "hero-base")

    fd = card_diff.family_diff("tla")
    assert fd is not None
    assert fd.code == "tla"
    assert fd.owned_prints == 1
    assert fd.owned_qty == 1

    expected_missing = missing.missing_printings("tla")
    expected_functional = missing.functional_missing("tla", precomputed_missing=expected_missing)
    expected_variant = missing.variant_chase_printings("tla", precomputed_missing=expected_missing)

    assert fd.printing.count == len(expected_missing)
    assert fd.functional.count == expected_functional.n_cards
    assert fd.variant_chase.count == len(expected_variant)
    assert {r.scryfall_id for r in fd.printing.rows} == {r.scryfall_id for r in expected_missing}
    assert {r.scryfall_id for r in fd.variant_chase.rows} == {"hero-variant"}
    assert [c.oracle_id for c in fd.functional.rows] == ["o-stranger"]


def test_family_diff_none_for_unresolvable_code(tmp_db, tla_family):
    from magic_manager import card_diff
    assert card_diff.family_diff("not-a-real-set-code-xyz") is None
