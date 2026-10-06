"""Tests for market.py — the Market view's composition over the valuation engines.

Offline: a tmp DB with seeded cards for the deck-cost path; the sealed-product
valuation and MTGJSON calls are monkeypatched.
"""

from __future__ import annotations

import pytest

from magic_manager import decks, inventory, market, mtgjson, sealed, valuation

A = "33333333-0000-0000-0000-000000000001"   # the deck's printing (fic)
A_CHEAP = "33333333-0000-0000-0000-000000000002"  # same card, cheaper elsewhere
B = "33333333-0000-0000-0000-000000000003"
OA, OB = "bbbbbbbb-0000-0000-0000-000000000001", "bbbbbbbb-0000-0000-0000-000000000002"


@pytest.fixture
def deck(tmp_db, seed_cards, make_card):
    seed_cards([
        make_card(id=A, oracle_id=OA, name="Skullclamp", set="fic", collector_number="1",
                  prices={"usd": "5.00", "usd_foil": None}),
        make_card(id=A_CHEAP, oracle_id=OA, name="Skullclamp", set="msc", collector_number="9",
                  prices={"usd": "2.00", "usd_foil": None}),
        make_card(id=B, oracle_id=OB, name="Sol Ring", set="fic", collector_number="2",
                  prices={"usd": "1.00", "usd_foil": None}),
    ])
    decks.deck_create("counter-blitz", "Counter Blitz (FINAL FANTASY X)", precon_state="deconstructed",
                      source_precon_file_name="CounterBlitzFinalFantasyX_FIC")
    decks.deck_add_card("counter-blitz", A, "main", "nonfoil", 1)
    decks.deck_add_card("counter-blitz", B, "main", "nonfoil", 2)
    inventory.inventory_add(B, "nonfoil", 2)  # own the Sol Rings, free
    return "counter-blitz"


def test_deck_cost_three_ways_with_floor(deck, monkeypatch):
    monkeypatch.setattr(mtgjson, "sealed_products", lambda code: [
        {"name": "FIC Commander Deck Counter Blitz",
         "contents": {"deck": [{"name": "Counter Blitz (FINAL FANTASY X)", "set": "fic"}]}},
    ])
    seen = {}

    def fake_value(set_code, name, **kw):
        seen["args"] = (set_code, name)
        return sealed.ProductValuation(label=name, kind="sealed", sealed_market=40.0)
    monkeypatch.setattr(valuation, "value_sealed_product", fake_value)

    out = market.deck_cost(deck)
    assert seen["args"] == ("fic", "FIC Commander Deck Counter Blitz")
    assert out["sealed"] == 40.0 and out["sealed_product"] == "FIC Commander Deck Counter Blitz"
    assert out["scratch"] == 7.0              # 5 + 2·1
    assert out["with_collection"] == 5.0      # Sol Rings covered
    assert out["scratch_floor"] == 4.0        # Skullclamp at its 2.00 floor + 2·1
    assert out["with_collection_floor"] == 2.0
    clamp = next(line for line in out["lines"] if line["name"] == "Skullclamp")
    assert clamp["floor_usd"] == 2.0 and clamp["floor_set_code"] == "msc"
    ring = next(line for line in out["lines"] if line["name"] == "Sol Ring")
    assert (ring["need"], ring["free"], ring["buy"]) == (2, 2, 0)


def test_deck_cost_non_precon_has_no_sealed(deck, monkeypatch):
    from magic_manager import db
    with db.connect() as conn:
        conn.execute("UPDATE decks SET source_precon_file_name = NULL")
    monkeypatch.setattr(valuation, "value_sealed_product",
                        lambda *a, **k: pytest.fail("non-precon must not price a sealed product"))
    out = market.deck_cost(deck)
    assert out["sealed"] is None and out["sealed_product"] is None


def test_deck_cost_unknown_deck_raises(tmp_db):
    with pytest.raises(LookupError):
        market.deck_cost("nope")


def test_value_products_maps_columns_and_tolerates_errors(monkeypatch):
    def fake_value(set_code, name, **kw):
        if name == "Bad":
            raise LookupError("ambiguous")
        return sealed.ProductValuation(label=name, kind="sealed", sealed_market=100.0,
                                       sealed_market_source="tcgcsv", exact_singles=60.0,
                                       floor_singles=50.0, intrinsic=80.0, coverage=0.9)
    monkeypatch.setattr(valuation, "value_sealed_product", fake_value)
    ticks = []
    rows = market.value_products([("fin", "Bundle"), ("fin", "Bad")],
                                 progress=lambda i, n, name: ticks.append((i, n)))
    assert ticks == [(1, 2), (2, 2)]
    good, bad = rows
    assert good["sealed_market"] == 100.0 and good["contents_value"] == 80.0
    assert good["exact_singles"] == 60.0 and good["floor_singles"] == 50.0 and good["error"] is None
    assert bad["error"] == "ambiguous"


def test_family_products_spans_member_sets(monkeypatch):
    monkeypatch.setattr(market, "family_codes", lambda code: ("fin", "Final Fantasy", ["fic", "fin"]))

    def fake_products(code):
        if code == "fic":
            raise FileNotFoundError(code)
        return [{"name": "Play Booster Box", "category": "booster_box"},
                {"name": "Bundle", "category": "bundle"}]
    monkeypatch.setattr(mtgjson, "sealed_products", fake_products)
    out = market.family_products("fin")
    assert out["code"] == "fin"
    assert [p["name"] for p in out["products"]] == ["Play Booster Box", "Bundle"]
    assert {p["set_code"] for p in out["products"]} == {"fin"}


def test_product_cost_splits_known_cards_from_booster_ev(deck, monkeypatch):
    """A mixed container: known cards at exact + cheapest printing, plus pack EV."""
    from magic_manager import construct
    needs = [construct.CardNeed(A, "nonfoil", 1, "x", "Skullclamp", "fic", "1", 5.0),
             construct.CardNeed(B, "nonfoil", 2, "x", "Sol Ring", "fic", "2", 1.0)]
    monkeypatch.setattr(sealed, "identify_product", lambda set_code, name: {"name": "FIC Bundle", "category": "bundle"})
    monkeypatch.setattr(valuation, "value_sealed_product", lambda set_code, name, **kw: sealed.ProductValuation(
        label=name, kind="sealed", sealed_market=60.0, intrinsic=37.0, booster_ev=30.0, card_needs=needs))
    market._cost_memo.clear()
    c = market.product_cost("sealed", "fic", "bundle")
    assert (c["market"], c["contents"], c["booster_ev"]) == (60.0, 37.0, 30.0)
    assert (c["known_exact"], c["known_floor"]) == (7.0, 4.0)      # Skullclamp floors to $2 elsewhere
    assert (c["exact"], c["floor"]) == (37.0, 34.0)
    assert (c["total_cards"], c["unpriced"], c["category"]) == (3, 0, "bundle")
    clamp = {ln["name"]: ln for ln in c["lines"]}
    assert clamp["Skullclamp"]["floor_usd"] == 2.0 and clamp["Skullclamp"]["floor_set_code"] == "msc"
    assert clamp["Sol Ring"]["floor_usd"] == 1.0 and clamp["Sol Ring"]["free"] == 2
    monkeypatch.setattr(valuation, "value_sealed_product", lambda *a, **k: pytest.fail("memoized"))
    assert market.product_cost("sealed", "fic", "bundle") is c
    market._cost_memo.clear()


def test_product_cost_booster_only_has_no_known_cards(tmp_db, monkeypatch):
    monkeypatch.setattr(sealed, "identify_product", lambda set_code, name: {"name": "Play Booster Box", "category": "booster_box"})
    monkeypatch.setattr(valuation, "value_sealed_product", lambda set_code, name, **kw: sealed.ProductValuation(
        label=name, kind="sealed", sealed_market=140.0, intrinsic=120.0, booster_ev=120.0, booster_only=True))
    market._cost_memo.clear()
    c = market.product_cost("sealed", "fin", "play booster box")
    assert (c["known_exact"], c["known_floor"], c["exact"], c["floor"], c["lines"]) == (None, None, 120.0, 120.0, [])
    market._cost_memo.clear()
