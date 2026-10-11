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
            raise mtgjson.MtgJsonError("mtgjson.sh set fic exited 6: mtgjson.sh: HTTP 404 from https://x/FIC.json")
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


NEW_PRINT = "33333333-0000-0000-0000-0000000000ff"   # cheapest printing, set not synced locally


def test_live_floor_printing_resolves_in_buy_lines(deck, make_card, monkeypatch):
    """The live floor may pick a printing absent from `cards`; it must be
    persisted so the buy list (keyed by that id) doesn't silently drop it."""
    from magic_manager import collection_view, scryfall
    far = make_card(id=NEW_PRINT, oracle_id=OA, name="Skullclamp", set="zzz", collector_number="7",
                    prices={"usd": "0.50", "usd_foil": None})
    monkeypatch.setattr(scryfall, "search", lambda q, **k: [far])
    monkeypatch.setattr(valuation, "value_sealed_product", lambda *a, **k: pytest.fail("no sealed"))

    out = market.deck_cost(deck, with_sealed=False, live=True)
    clamp = next(line for line in out["lines"] if line["name"] == "Skullclamp")
    assert clamp["floor_scryfall_id"] == NEW_PRINT and out["live"] is True and out["live_error"] is None
    text = collection_view.buy_lines([(clamp["floor_scryfall_id"], "nonfoil", 1)], "tcgplayer")
    assert "Skullclamp" in text


def test_deck_cost_live_failure_falls_back_to_local(deck, monkeypatch):
    from magic_manager import scryfall

    def boom(q, **k):
        raise scryfall.ScryfallError("HTTP 503")
    monkeypatch.setattr(scryfall, "search", boom)
    out = market.deck_cost(deck, with_sealed=False, live=True)
    assert out["live"] is False and "503" in out["live_error"]
    assert out["scratch_floor"] == 4.0   # local floor (msc 2.00 + 2·1)


def test_family_products_outage_is_not_no_products(monkeypatch):
    """PR91-6: an MTGJSON outage must raise, not read as 'no sealed products'."""
    monkeypatch.setattr(market, "family_codes", lambda code: ("fin", "Final Fantasy", ["fin"]))

    def down(code):
        raise mtgjson.MtgJsonError("mtgjson.sh set fin exited 4: mtgjson.sh: curl failed")
    monkeypatch.setattr(mtgjson, "sealed_products", down)
    with pytest.raises(mtgjson.MtgJsonError):
        market.family_products("fin")


def test_value_products_carries_booster_ev_and_strict_reraises(monkeypatch):
    monkeypatch.setattr(valuation, "value_sealed_product", lambda set_code, name, **kw: sealed.ProductValuation(
        label=name, kind="sealed", exact_singles=40.0, floor_singles=30.0, booster_ev=25.0))
    assert market.value_products([("fin", "Bundle")])[0]["booster_ev"] == 25.0

    def boom(*a, **k):
        raise LookupError("no such product")
    monkeypatch.setattr(valuation, "value_sealed_product", boom)
    with pytest.raises(LookupError):
        market.value_products([("fin", "Nope")], strict=True)


# ---------- PR91-2: which sealed product IS this precon ----------

def _precon_with(monkeypatch, products):
    monkeypatch.setattr(mtgjson, "sealed_products", lambda code: products)
    return market._precon_product("counter-blitz")


def test_precon_product_matches_single_deck_product(deck, monkeypatch):
    cmd = {"name": "Commander Deck Counter Blitz", "category": "deck",
           "contents": {"deck": [{"name": "Counter Blitz (FINAL FANTASY X)"}], "sealed": [{"name": "Sample Pack"}]}}
    assert _precon_with(monkeypatch, [cmd]) == ("fic", "Commander Deck Counter Blitz")


def test_precon_product_skips_multi_deck_and_bundles(deck, monkeypatch):
    kit = {"name": "Starter Kit", "category": "multiple_decks",
           "contents": {"deck": [{"name": "Counter Blitz (FINAL FANTASY X)"}, {"name": "Other Deck"}]}}
    bundle = {"name": "Bundle", "category": "bundle",
              "contents": {"deck": [{"name": "Counter Blitz (FINAL FANTASY X)"}], "sealed": [{"name": "Play Booster", "count": 9}]}}
    assert _precon_with(monkeypatch, [kit, bundle]) is None


# ---------- PR91-1: the cheapest printing keeps a real finish ----------

FOIL_ONLY = "33333333-0000-0000-0000-0000000000f0"


def test_card_lines_foil_only_floor_keeps_foil(tmp_db, seed_cards, make_card):
    from magic_manager import construct
    seed_cards([make_card(id=FOIL_ONLY, oracle_id="bbbbbbbb-0000-0000-0000-0000000000f0", name="Foil Thing",
                          set="sld", collector_number="5", finishes=["foil"],
                          prices={"usd": None, "usd_foil": "12.00"})])
    rows = construct.net_against_loose([construct.CardNeed(FOIL_ONLY, "foil", 1, "x", "Foil Thing", "sld", "5", 12.0)])
    lines, need_floor, _ = market.card_lines(rows)
    (ln,) = lines
    assert (ln["floor_scryfall_id"], ln["floor_finish"], ln["floor_usd"]) == (FOIL_ONLY, "foil", 12.0)
    assert need_floor == 12.0


def test_card_lines_cheaper_nonfoil_floor_is_nonfoil(deck):
    from magic_manager import construct
    rows = construct.net_against_loose([construct.CardNeed(A, "foil", 1, "x", "Skullclamp", "fic", "1", 9.0)])
    (ln,), _, _ = market.card_lines(rows)
    assert (ln["floor_scryfall_id"], ln["floor_finish"], ln["floor_usd"]) == (A_CHEAP, "nonfoil", 2.0)


# ---------- PR91-3: unpriced cards never make a total look complete ----------

def test_deck_cost_reports_floor_coverage(deck, monkeypatch):
    from magic_manager import db
    with db.connect() as conn:
        conn.execute("UPDATE cards SET prices_usd = NULL, prices_usd_foil = NULL")
    out = market.deck_cost(deck, with_sealed=False)
    assert out["scratch"] is None and out["with_collection"] is None
    assert out["scratch_floor"] is None and out["with_collection_floor"] is None
    assert (out["unpriced"], out["floor_unpriced"], out["total_need"]) == (3, 3, 3)


def test_deck_cost_partial_floor_counts_unpriced(deck):
    from magic_manager import db
    with db.connect() as conn:
        conn.execute("UPDATE cards SET prices_usd = NULL WHERE scryfall_id = ?", (B,))
    out = market.deck_cost(deck, with_sealed=False)
    assert out["unpriced"] == 2 and out["floor_unpriced"] == 2   # Sol Ring has no price anywhere
    assert out["scratch"] == 5.0 and out["scratch_floor"] == 2.0


# ---------- PR91-6 / PR91-12: routes + the value_family job ----------

@pytest.fixture
def client(tmp_db):
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app
    with TestClient(create_app(serve_frontend=False)) as c:
        yield c


def test_value_route_maps_errors(client, monkeypatch):
    from magic_manager import scryfall

    def fake_value(set_code, name, **kw):
        if name == "Nope":
            raise LookupError("no product matches 'Nope'")
        if name == "Down":
            raise scryfall.ScryfallError("HTTP 503")
        return sealed.ProductValuation(label=name, kind="sealed", sealed_market=10.0)
    monkeypatch.setattr(valuation, "value_sealed_product", fake_value)
    ok = client.get("/api/market/value", params={"set": "fin", "name": "Bundle"})
    assert ok.status_code == 200 and ok.json()["sealed_market"] == 10.0
    assert client.get("/api/market/value", params={"set": "fin", "name": "Nope"}).status_code == 404
    assert client.get("/api/market/value", params={"set": "fin", "name": "Down"}).status_code == 502


def test_products_and_tree_routes_map_mtgjson_outage(client, monkeypatch):
    def down(*a, **k):
        raise mtgjson.MtgJsonError("curl failed")
    monkeypatch.setattr(market, "family_products", down)
    monkeypatch.setattr(market, "product_tree", down)
    assert client.get("/api/market/products", params={"code": "fin"}).status_code == 502
    assert client.get("/api/market/product-tree", params={"set": "fin", "name": "Bundle"}).status_code == 502


def test_value_family_job_values_every_product(monkeypatch):
    from magic_manager.api import market as market_api
    monkeypatch.setattr(market, "family_products", lambda code: {"code": "fin", "name": "Final Fantasy", "products": [
        {"set_code": "fin", "name": "Bundle"}, {"set_code": "fin", "name": "Bad"}]})

    def fake_value(set_code, name, **kw):
        if name == "Bad":
            raise RuntimeError("timeout")
        return sealed.ProductValuation(label=name, kind="sealed", sealed_market=50.0, intrinsic=60.0, booster_ev=40.0)
    monkeypatch.setattr(valuation, "value_sealed_product", fake_value)
    events = []
    res = market_api._run_value_family(market_api.ValueFamilyInput(code="fin"), events.append)
    assert res.summary == "Final Fantasy · 1 products valued · 1 failed"
    rows = res.artifacts[0].data
    assert [r["name"] for r in rows] == ["Bundle", "Bad"]
    assert rows[0]["booster_ev"] == 40.0 and rows[1]["error"] == "timeout"
    assert events[-1].done == events[-1].total == 2


def test_is_missing_file_only_matches_404():
    assert mtgjson.is_missing_file(mtgjson.MtgJsonError("mtgjson.sh: HTTP 404 from https://mtgjson.com/api/v5/ZZZ.json"))
    assert not mtgjson.is_missing_file(mtgjson.MtgJsonError("mtgjson.sh: HTTP 403 from https://mtgjson.com/api/v5/FIN.json"))
    assert not mtgjson.is_missing_file(mtgjson.MtgJsonError("mtgjson.sh: curl failed for https://x"))
    assert not mtgjson.is_missing_file(LookupError("HTTP 404 from"))


def test_product_cost_route_maps_outage(client, monkeypatch):
    from magic_manager import scryfall

    def down(*a, **k):
        raise scryfall.ScryfallError("HTTP 503")
    monkeypatch.setattr(market, "product_cost", down)
    r = client.get("/api/market/product-cost", params={"kind": "sealed", "set": "fin", "name": "Bundle"})
    assert r.status_code == 502


def test_deck_cost_all_free_unpriced_is_known_zero(deck):
    """Cards you already have loose cost $0 more, even when they have no price."""
    from magic_manager import db
    with db.connect() as conn:
        conn.execute("UPDATE cards SET prices_usd = NULL WHERE scryfall_id = ?", (B,))
    inventory.inventory_add(A, "nonfoil", 1)
    out = market.deck_cost(deck, with_sealed=False)
    assert out["with_collection"] == 0.0 and out["with_collection_floor"] == 0.0
    assert out["scratch"] == 5.0 and out["unpriced"] == 2
