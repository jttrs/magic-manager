"""Tests for the construct-value engine (magic_manager.construct).

Offline + deterministic via the shared conftest fixtures (tmp_db, seed_cards,
make_card, fake_mtgjson, make_precon_deck). The focus is the genuinely-new logic:

  - net_against_loose aggregates needs by (scryfall_id, finish) BEFORE netting,
    so a card shared by two sources nets loose copies ONCE (no double-spend),
  - buy_qty = max(0, need - loose),
  - "loose" is free_quantity (owned minus pledged), so pledged copies don't count,
  - summarize's three totals arithmetic,
  - expand_deck_file flattens a precon and prices via the local table.
"""

from __future__ import annotations

import pytest

from magic_manager import construct


# ---------- net_against_loose: aggregation + dedup ----------

def _need(sid, finish, qty, source, unit, name="C", set_code="tst", cn="1"):
    return construct.CardNeed(
        scryfall_id=sid, finish=finish, qty=qty, source=source,
        name=name, set_code=set_code, collector_number=cn, unit_usd=unit,
    )


def test_shared_card_across_sources_nets_loose_once(tmp_db, seed_cards, make_card):
    """Two decks each need 1 of a card; I own 2 loose. Aggregated need is 3,
    loose is subtracted once → buy 1 (NOT 3 - 2 - 2)."""
    sid = "11111111-0000-0000-0000-000000000001"
    seed_cards([make_card(id=sid, set="tst", collector_number="7",
                          prices={"usd": "0.50", "usd_foil": "1.00"})])
    from magic_manager import inventory
    inventory.inventory_add(sid, "nonfoil", 2)

    needs = [
        _need(sid, "nonfoil", 2, "Deck A", 0.50),
        _need(sid, "nonfoil", 1, "Deck B", 0.50),
    ]
    rows = construct.net_against_loose(needs)
    assert len(rows) == 1
    r = rows[0]
    assert r.need_qty == 3
    assert r.loose_qty == 2
    assert r.buy_qty == 1  # max(0, 3 - 2), netted once


def test_buy_qty_is_max_zero_need_minus_loose(tmp_db, seed_cards, make_card):
    """Own more than needed → buy 0, never negative."""
    sid = "11111111-0000-0000-0000-000000000002"
    seed_cards([make_card(id=sid, prices={"usd": "1.00", "usd_foil": "2.00"})])
    from magic_manager import inventory
    inventory.inventory_add(sid, "nonfoil", 5)

    rows = construct.net_against_loose([_need(sid, "nonfoil", 2, "D", 1.00)])
    assert rows[0].buy_qty == 0
    assert rows[0].loose_qty == 5


def test_finish_is_part_of_the_key(tmp_db, seed_cards, make_card):
    """foil and nonfoil of the same printing are distinct needs; owning nonfoil
    does not offset a foil need."""
    sid = "11111111-0000-0000-0000-000000000003"
    seed_cards([make_card(id=sid, prices={"usd": "1.00", "usd_foil": "3.00"})])
    from magic_manager import inventory
    inventory.inventory_add(sid, "nonfoil", 4)

    rows = construct.net_against_loose([
        _need(sid, "nonfoil", 1, "D", 1.00),
        _need(sid, "foil", 1, "D", 3.00),
    ])
    by_finish = {r.finish: r for r in rows}
    assert by_finish["nonfoil"].buy_qty == 0   # covered by loose
    assert by_finish["foil"].loose_qty == 0    # no foil owned
    assert by_finish["foil"].buy_qty == 1


def test_pledged_copies_are_not_loose(tmp_db, seed_cards, make_card):
    """A copy pledged to a built deck is NOT available; free_quantity excludes
    it, so with-collection must still buy it."""
    from magic_manager import decks, inventory
    sid = "11111111-0000-0000-0000-000000000004"
    seed_cards([make_card(id=sid, set="tst", collector_number="9",
                          prices={"usd": "2.00", "usd_foil": "4.00"})])
    inventory.inventory_add(sid, "nonfoil", 2)
    # Pledge both copies to a built deck.
    decks.deck_create("pledged-deck", "Pledged Deck")
    decks.deck_add_card("pledged-deck", sid, "main", "nonfoil", 2)
    decks.deck_assign_batch("pledged-deck", [(sid, "nonfoil", 2)])

    rows = construct.net_against_loose([_need(sid, "nonfoil", 2, "D", 2.00)])
    assert rows[0].loose_qty == 0   # owned 2, pledged 2 → free 0
    assert rows[0].buy_qty == 2


# ---------- summarize: three totals ----------

def test_summarize_three_totals(tmp_db, seed_cards, make_card):
    sid_a = "22222222-0000-0000-0000-000000000001"
    sid_b = "22222222-0000-0000-0000-000000000002"
    seed_cards([
        make_card(id=sid_a, set="tst", collector_number="1",
                  prices={"usd": "10.00", "usd_foil": "20.00"}),
        make_card(id=sid_b, set="tst", collector_number="2",
                  prices={"usd": "1.00", "usd_foil": "2.00"}),
    ])
    from magic_manager import inventory
    inventory.inventory_add(sid_b, "nonfoil", 3)  # own the cheap one

    needs = [
        _need(sid_a, "nonfoil", 1, "D", 10.00, name="Pricey", cn="1"),
        _need(sid_b, "nonfoil", 2, "D", 1.00, name="Cheap", cn="2"),
    ]
    rows = construct.net_against_loose(needs)
    s = construct.summarize(rows, sealed_market=25.00)
    assert s["sealed"] == 25.00
    assert s["scratch"] == 12.00           # 10 + 2*1
    assert s["with_collection"] == 10.00   # only the pricey one, cheap covered
    assert s["coverage"] == 1.0
    assert s["n_unpriced"] == 0
    # sorted by unit value desc: pricey first
    assert rows[0].name == "Pricey"


def test_unpriced_card_drags_coverage(tmp_db, seed_cards, make_card):
    """A printing not in the local cards table is unpriced: counted in need,
    contributes $0, surfaced via coverage + n_unpriced."""
    sid_priced = "33333333-0000-0000-0000-000000000001"
    seed_cards([make_card(id=sid_priced, prices={"usd": "5.00", "usd_foil": "9.00"})])
    needs = [
        _need(sid_priced, "nonfoil", 1, "D", 5.00),
        _need("deadbeef-0000-0000-0000-000000000000", "nonfoil", 1, "D", None),
    ]
    rows = construct.net_against_loose(needs)
    s = construct.summarize(rows, sealed_market=None)
    assert s["scratch"] == 5.00
    assert s["n_unpriced"] == 1
    assert s["coverage"] == pytest.approx(0.5)
    assert s["sealed"] is None


# ---------- expand_deck_file: flatten + price ----------

def test_expand_deck_file_flattens_and_prices(tmp_db, seed_cards, make_card,
                                               fake_mtgjson, make_precon_deck):
    sid1 = "44444444-0000-0000-0000-000000000001"
    sid2 = "44444444-0000-0000-0000-000000000002"
    seed_cards([
        make_card(id=sid1, name="Alpha", set="tst", collector_number="10",
                  prices={"usd": "3.00", "usd_foil": "6.00"}),
        make_card(id=sid2, name="Beta", set="tst", collector_number="11",
                  prices={"usd": "0.25", "usd_foil": "0.50"}),
    ])
    deck = make_precon_deck("Test Precon", "Starter Kit", [
        {"sid": sid1, "name": "Alpha", "count": 1, "set": "TST", "cn": "10"},
        {"sid": sid2, "name": "Beta", "count": 4, "set": "TST", "cn": "11"},
    ])
    fake_mtgjson(deck=deck)

    exp = construct.expand_deck_file("TestPrecon_TST")
    assert exp.label == "Test Precon"
    assert exp.sealed_market is None  # a decklist has no sealed price
    rows = construct.net_against_loose(exp.needs)
    s = construct.summarize(rows, exp.sealed_market)
    assert s["scratch"] == pytest.approx(3.00 + 4 * 0.25)  # 4.00
    assert s["with_collection"] == pytest.approx(4.00)     # own nothing
    # table carries set + collector number from the local cards row
    top = rows[0]
    assert (top.name, top.set_code, top.collector_number) == ("Alpha", "tst", "10")


def test_expand_deck_file_unknown_raises(tmp_db, fake_mtgjson):
    fake_mtgjson(deck={})  # empty → treated as missing
    with pytest.raises(LookupError):
        construct.expand_deck_file("DoesNotExist_XXX")
