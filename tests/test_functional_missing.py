"""Tests for magic_manager.missing.functional_missing — the "functional
completeness" metric (own ≥1 printing of every mechanically-unique card).

Offline: seeded tmp DB + faked all_sets ('tla' is configured with an empty
dupe-foil set so the preferred filter runs). FIXTURE WARNING: make_card hardcodes
ONE shared oracle_id — every test MUST pass an explicit oracle_id= per distinct
mechanical card, or all seeded cards collapse to one oracle and assertions are
meaningless.
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


def test_functional_excludes_card_whose_base_owned_but_variant_missing(
        tmp_db, tla_family, seed_cards, make_card):
    """The load-bearing distinction: a variant is in missing_printings (unowned
    printing) yet the oracle is functionally owned (base owned) → NOT functional-
    missing."""
    from magic_manager import missing, db
    seed_cards([
        make_card(id="base", oracle_id="o-hero", set="tla", collector_number="5",
                  rarity="rare", name="Hero", prices={"usd": "1.00", "usd_foil": "2.00"}),
        make_card(id="variant", oracle_id="o-hero", set="tla", collector_number="305",
                  rarity="rare", name="Hero", prices={"usd": "40.00", "usd_foil": "60.00"}),
    ])
    with db.connect() as conn:
        _own(conn, "base")  # own the base printing
    # the variant IS in printing-missing…
    assert "variant" in {r.scryfall_id for r in missing.missing_printings("tla")}
    # …but the oracle is functionally owned → functional_missing is empty.
    fm = missing.functional_missing("tla")
    assert fm.n_cards == 0


def test_functional_includes_card_owned_in_zero_printings(
        tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing
    seed_cards([make_card(id="u1", oracle_id="o-un", set="tla", collector_number="6",
                          rarity="rare", name="Unowned", prices={"usd": "5.00", "usd_foil": None})])
    fm = missing.functional_missing("tla")
    assert fm.n_cards == 1
    assert fm.cards[0].oracle_id == "o-un"


def test_functional_picks_cheapest_finish(tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing
    seed_cards([make_card(id="c1", oracle_id="o-c", set="tla", collector_number="7",
                          rarity="rare", name="Cheap Foil", prices={"usd": "10.00", "usd_foil": "3.00"})])
    fm = missing.functional_missing("tla")
    assert fm.cards[0].family_usd == 3.0
    assert fm.cards[0].family_finish == "foil"


def test_functional_nonfoil_preferred_on_tie(tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing
    seed_cards([make_card(id="t1", oracle_id="o-t", set="tla", collector_number="8",
                          rarity="rare", name="Tie", prices={"usd": "5.00", "usd_foil": "5.00"})])
    assert missing.functional_missing("tla").cards[0].family_finish == "nonfoil"


def test_functional_cheapest_across_multiple_family_printings(
        tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing
    seed_cards([
        make_card(id="a", oracle_id="o-multi", set="tla", collector_number="9",
                  rarity="rare", name="Multi", prices={"usd": "12.00", "usd_foil": None}),
        make_card(id="b", oracle_id="o-multi", set="tla", collector_number="309",
                  rarity="rare", name="Multi", prices={"usd": "4.00", "usd_foil": None}),
    ])
    fm = missing.functional_missing("tla")
    assert fm.n_cards == 1
    assert fm.cards[0].family_usd == 4.0
    assert fm.cards[0].family_cn == "309"


def test_functional_family_scope_and_anywhere_floor(
        tmp_db, tla_family, seed_cards, make_card):
    """In-family floor ignores an out-of-family cheaper printing; anywhere_floor_fn
    surfaces it separately."""
    from magic_manager import missing
    seed_cards([make_card(id="fam", oracle_id="o-scope", set="tla", collector_number="10",
                          rarity="rare", name="Scoped", prices={"usd": "8.00", "usd_foil": None})])
    fm = missing.functional_missing(
        "tla", anywhere_floor_fn=lambda oid: (1.0, "nonfoil") if oid == "o-scope" else None)
    c = fm.cards[0]
    assert c.family_usd == 8.0           # in-family floor
    assert c.anywhere_usd == 1.0          # cheaper elsewhere
    assert fm.family_total_usd == 8.0
    assert fm.anywhere_total_usd == 1.0


def test_functional_summary_totals(tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing
    seed_cards([
        make_card(id="s1", oracle_id="o-1", set="tla", collector_number="11",
                  rarity="rare", name="A", prices={"usd": "3.00", "usd_foil": None}),
        make_card(id="s2", oracle_id="o-2", set="tla", collector_number="12",
                  rarity="rare", name="B", prices={"usd": "5.00", "usd_foil": None}),
    ])
    fm = missing.functional_missing("tla")
    assert fm.n_cards == 2
    assert fm.family_total_usd == 8.0
    # no anywhere_floor_fn → anywhere falls back to family price
    assert fm.anywhere_total_usd == 8.0


def test_functional_unpriced_card_counted_zero(tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing
    seed_cards([make_card(id="np", oracle_id="o-np", set="tla", collector_number="13",
                          rarity="rare", name="Unpriced", prices={"usd": None, "usd_foil": None})])
    fm = missing.functional_missing("tla")
    assert fm.n_cards == 1               # counted…
    assert fm.family_total_usd == 0.0     # …at $0


def test_card_dict_includes_oracle_id(tmp_db, tla_family, seed_cards, make_card):
    """Regression guard for the selectors plumbing change."""
    from magic_manager import selectors
    seed_cards([make_card(id="od", oracle_id="o-dict", set="tla", collector_number="14",
                          rarity="rare", name="OracleDict")])
    rows = selectors.materialize("set:tla")
    assert rows and rows[0].card.get("oracle_id") == "o-dict"
