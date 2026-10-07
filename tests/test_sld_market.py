"""Secret Lair in Market: drop list, bonus card, sld product cost, gap.

Offline: MTGJSON / valuation lookups are monkeypatched; card prices are seeded
into a tmp DB.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from magic_manager import construct, market, mtgjson, sealed, sld, sld_market, valuation
from magic_manager.web.app import create_app

CARD = "44444444-0000-0000-0000-000000000001"
BONUS = "44444444-0000-0000-0000-000000000002"


@pytest.fixture(autouse=True)
def _clear_memo():
    market._cost_memo.clear()
    mtgjson.uuid_scryfall_ids.cache_clear()
    yield
    market._cost_memo.clear()
    mtgjson.uuid_scryfall_ids.cache_clear()


def test_card_refs_resolve_mtgjson_uuid(monkeypatch):
    """sealedProduct card refs carry only uuid + set + number — bridge via the set file."""
    monkeypatch.setattr(mtgjson, "set_file", lambda code: {
        "cards": [{"uuid": "u-bonus", "identifiers": {"scryfallId": BONUS}}],
        "tokens": [{"uuid": "u-tok", "identifiers": {"scryfallId": "tok"}}],
    })
    product = {"contents": {"card": [
        {"name": "Clone", "number": "7164", "set": "sld", "uuid": "u-bonus", "foil": True},
        {"name": "Gone", "number": "1", "set": "sld", "uuid": "u-missing"},
    ]}}
    assert construct.product_card_ids(product) == [BONUS]
    raw = construct._needs_from_card_refs(product["contents"]["card"], "x")
    assert raw[0]["finish"] == "foil" and raw[0]["fb_cn"] == "7164"


def _seed(seed_cards, make_card):
    seed_cards([
        make_card(id=CARD, oracle_id="o1", name="Counterspell", set="sld", collector_number="2664",
                  prices={"usd": "13.00", "usd_foil": "16.00"}),
        make_card(id=BONUS, oracle_id="o2", name="Clone", set="sld", collector_number="7164",
                  prices={"usd": "3.00", "usd_foil": "3.50"}),
    ])


def test_sld_cost_includes_bonus_card_through_sealed_product(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    product = {"name": "Secret Lair Drop Garfield As Intended Foil",
               "contents": {"card": [{"set": "sld", "number": "7164", "identifiers": {"scryfallId": BONUS}, "foil": True}],
                            "deck": [{"name": "Garfield: As Intended Foil Edition", "set": "sld"}]}}
    monkeypatch.setattr(sld, "identify_drop", lambda name: {"name": "Garfield: As Intended", "release_date": "2026-06-16",
                                                            "file_names": ["GarfieldAsIntended_SLD"]})
    seen = {}

    def fake_product(drop, edition, *, strict=False):
        seen["edition"] = (drop, edition, strict)
        return product
    monkeypatch.setattr(valuation, "sld_sealed_product", fake_product)
    monkeypatch.setattr(sealed, "identify_product", lambda set_code, name: {**product, "category": "box_set"})
    needs = [construct.CardNeed(CARD, "foil", 1, "x", "Counterspell", "sld", "2664", 16.0),
             construct.CardNeed(BONUS, "foil", 1, "x", "Clone", "sld", "7164", 3.5)]
    monkeypatch.setattr(valuation, "value_sealed_product", lambda set_code, name, **kw: sealed.ProductValuation(
        label=name, kind="sealed", sealed_market=15.0, sealed_market_source="tcgcsv", intrinsic=19.5, card_needs=needs))

    c = market.product_cost("sld", "sld", "garfield as intended", "foil")
    assert seen["edition"] == ("Garfield: As Intended", "foil", True)
    assert (c["kind"], c["name"], c["finish"], c["category"]) == ("sld", "Garfield: As Intended", "foil", "secret_lair")
    assert c["sealed_name"] == product["name"] and c["market"] == 15.0
    assert c["known_exact"] == 19.5 and c["total_cards"] == 2
    bonus = {ln["name"]: ln["bonus"] for ln in c["lines"]}
    assert bonus == {"Counterspell": False, "Clone": True}
    assert sld_market.gap(c) == {"usd": -4.5, "pct": -23.1}


def test_sld_cost_without_sealed_product_falls_back_to_drop_cards(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    monkeypatch.setattr(sld, "identify_drop", lambda name: {"name": "Old Drop", "release_date": "2020-01-01",
                                                            "file_names": ["OldDrop_SLD"], "ids": [CARD]})
    monkeypatch.setattr(valuation, "sld_sealed_product", lambda *a, **k: None)
    monkeypatch.setattr(valuation, "sld_sealed_market", lambda name, edition, **k: (None, None))
    monkeypatch.setattr(valuation, "value_sealed_product", lambda *a, **k: pytest.fail("no sealed product to value"))
    c = market.product_cost("sld", "sld", "old drop", "nonfoil")
    assert c["sealed_name"] is None and c["market"] is None and c["exact"] == 13.0
    assert [ln["bonus"] for ln in c["lines"]] == [False]
    assert sld_market.gap(c) is None


def test_recent_lists_editions_with_tcgplayer_pages(monkeypatch):
    monkeypatch.setattr(sld, "recent_drops", lambda n: ([
        {"name": "Both", "release_date": "2026-09-01", "file_names": ["Both_SLD", "BothFoilEdition_SLD"]},
        {"name": "Foil Only Foil Edition", "release_date": "2026-08-01", "file_names": ["FoilOnlyFoilEdition_SLD"]},
    ], 99))
    products = {("Both", "nonfoil"): {"name": "SLD Both", "identifiers": {"tcgplayerProductId": "1"}},
                ("Both", "foil"): {"name": "SLD Both Foil", "identifiers": {}},
                ("Foil Only Foil Edition", "foil"): {"name": "SLD Foil Only Foil", "identifiers": {"tcgplayerProductId": "3"}}}
    monkeypatch.setattr(valuation, "sld_sealed_product", lambda name, edition, *, strict=False: products.get((name, edition)))
    out = sld_market.recent(2)
    assert out["total"] == 99
    both, foil_only = out["drops"]
    assert both["editions"] == [
        {"finish": "nonfoil", "sealed_name": "SLD Both", "tcgplayer_url": "https://www.tcgplayer.com/product/1"},
        {"finish": "foil", "sealed_name": "SLD Both Foil", "tcgplayer_url": None},
    ]
    assert [e["finish"] for e in foil_only["editions"]] == ["foil"]


def test_survey_skips_missing_editions_and_keeps_errors(monkeypatch):
    monkeypatch.setattr(sld_market, "recent", lambda limit: {"total": 2, "drops": [
        {"name": "A", "release_date": "x", "editions": [{"finish": "nonfoil"}]},
        {"name": "B", "release_date": "y", "editions": [{"finish": "nonfoil"}, {"finish": "foil"}]},
    ]})

    def fake_value(name, finish):
        if name == "B":
            raise LookupError("ambiguous")
        return {"market": 1.0}
    monkeypatch.setattr(sld_market, "value", fake_value)
    rows = sld_market.survey(5, "nonfoil")
    assert [(r["name"], r["error"]) for r in rows] == [("A", None), ("B", "ambiguous")]
    assert [r["name"] for r in sld_market.survey(5, "foil")] == ["B"]


def test_secret_lair_route(tmp_db, monkeypatch):
    monkeypatch.setattr(sld_market, "recent", lambda limit: {"total": 7, "drops": [
        {"name": "A", "release_date": "2026-01-01", "editions": [{"finish": "nonfoil", "sealed_name": None, "tcgplayer_url": None}]},
    ][:limit]})
    with TestClient(create_app(serve_frontend=False)) as c:
        r = c.get("/api/market/secret-lair", params={"limit": 5})
        assert r.status_code == 200 and r.json()["total"] == 7
        assert c.get("/api/market/secret-lair", params={"limit": 0}).status_code == 422
