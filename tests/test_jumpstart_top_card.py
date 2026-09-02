"""Tests for the Jumpstart checklist top-card columns (2026-09-02).

`_rollup_deck_prices` now also returns the single most expensive GAMEPLAY card
in a pack + its price, at the card's SHIPPED finish (same price basis as
usd_total). These pin: the max picks the right card/finish, foil-shipped cards
rank on their foil price, and an all-unpriced pack yields (None, None).

Offline: seed the cards table (rollup reads prices from it directly), build an
MTGJSON-shaped deck dict via make_precon_deck.
"""


def test_rollup_top_card_picks_priciest_gameplay_card(tmp_db, seed_cards, make_card, make_precon_deck):
    from magic_manager import sets as sets_mod

    seed_cards([
        make_card(id="s-cheap", name="Bulk Common", collector_number="1",
                  prices={"usd": "0.10", "usd_foil": "0.20"}),
        make_card(id="s-mid", name="Midrange Rare", collector_number="2",
                  prices={"usd": "3.00", "usd_foil": "5.00"}),
        make_card(id="s-chase", name="Chase Mythic", collector_number="3",
                  prices={"usd": "25.00", "usd_foil": "40.00"}),
    ])
    deck = make_precon_deck("Demo", "Jumpstart", [
        {"sid": "s-cheap", "name": "Bulk Common", "count": 10, "board": "mainBoard"},
        {"sid": "s-mid", "name": "Midrange Rare", "count": 1, "board": "mainBoard"},
        {"sid": "s-chase", "name": "Chase Mythic", "count": 1, "board": "mainBoard"},
    ])

    total_count, usd_total, top_card, top_card_usd = sets_mod._rollup_deck_prices(deck)
    assert total_count == 12
    assert top_card == "Chase Mythic"
    assert top_card_usd == 25.00        # nonfoil (shipped nonfoil), unit price not ×count
    # usd_total = 10*0.10 + 1*3.00 + 1*25.00 = 29.00
    assert usd_total == 29.00


def test_rollup_top_card_uses_shipped_foil_price(tmp_db, seed_cards, make_card, make_precon_deck):
    """A foil-shipped card ranks on its FOIL price — so a card that's cheaper
    nonfoil than another can still win as the top card when shipped foil."""
    from magic_manager import sets as sets_mod

    seed_cards([
        make_card(id="s-nonfoil-hi", name="Nonfoil Twenty", collector_number="1",
                  prices={"usd": "20.00", "usd_foil": "22.00"}),
        make_card(id="s-foil-hi", name="Foil Fifty", collector_number="2",
                  prices={"usd": "5.00", "usd_foil": "50.00"}),
    ])
    deck = make_precon_deck("Demo", "Jumpstart", [
        {"sid": "s-nonfoil-hi", "name": "Nonfoil Twenty", "count": 1, "board": "mainBoard"},
        {"sid": "s-foil-hi", "name": "Foil Fifty", "count": 1, "foil": True, "board": "mainBoard"},
    ])

    _tc, _usd, top_card, top_card_usd = sets_mod._rollup_deck_prices(deck)
    assert top_card == "Foil Fifty"      # 50.00 foil > 20.00 nonfoil
    assert top_card_usd == 50.00


def test_rollup_top_card_none_when_unpriced(tmp_db, seed_cards, make_card, make_precon_deck):
    from magic_manager import sets as sets_mod

    seed_cards([
        make_card(id="s-np", name="No Price", collector_number="1",
                  prices={"usd": None, "usd_foil": None}),
    ])
    deck = make_precon_deck("Demo", "Jumpstart", [
        {"sid": "s-np", "name": "No Price", "count": 3, "board": "mainBoard"},
    ])
    total_count, usd_total, top_card, top_card_usd = sets_mod._rollup_deck_prices(deck)
    assert total_count == 3           # count still tallies unpriced cards
    assert usd_total is None
    assert top_card is None and top_card_usd is None
