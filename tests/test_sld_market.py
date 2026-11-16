"""Secret Lair in Market: drop list, bonus card, sld product cost, gap.

Offline: MTGJSON / valuation lookups are monkeypatched; card prices are seeded
into a tmp DB.
"""

from __future__ import annotations

import functools

import pytest
from fastapi.testclient import TestClient

from magic_manager import construct, market, mtgjson, scryfall, sealed, sld, sld_market, valuation
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


def test_sld_cost_is_the_guaranteed_cards_only_a_named_bonus_is_listed_not_counted(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    product = {"name": "Secret Lair Drop Garfield As Intended Foil",
               "contents": {"card": [{"set": "sld", "number": "7164", "identifiers": {"scryfallId": BONUS}, "foil": True}],
                            "deck": [{"name": "Garfield: As Intended Foil Edition", "set": "sld"}]}}
    monkeypatch.setattr(sld, "identify_drop", lambda name: {"name": "Garfield: As Intended", "release_date": "2026-06-16",
                                                            "file_names": ["GarfieldAsIntended_SLD"], "ids": [CARD]})
    seen = {}

    def fake_product(drop, edition, *, strict=False):
        seen["edition"] = (drop, edition, strict)
        return product
    monkeypatch.setattr(valuation, "sld_sealed_product", fake_product)
    monkeypatch.setattr(valuation, "sld_sealed_market", lambda name, edition, **k: (15.0, "tcgcsv"))
    monkeypatch.setattr(construct, "product_card_ids", lambda p: [BONUS])

    c = market.product_cost("sld", "sld", "garfield as intended", "foil")
    assert seen["edition"] == ("Garfield: As Intended", "foil", True)
    assert (c["kind"], c["name"], c["finish"], c["category"]) == ("sld", "Garfield: As Intended", "foil", "secret_lair")
    assert c["sealed_name"] == product["name"] and c["market"] == 15.0 and c["has_bonus"] is True
    assert c["known_exact"] == 16.0 and c["total_cards"] == 1          # the bonus is not in the total
    assert {ln["name"]: ln["bonus"] for ln in c["lines"]} == {"Counterspell": None, "Clone": "named"}
    assert sld_market.gap(c) == {"usd": -1.0, "pct": -6.2}


def test_sld_cost_lists_a_bonus_packs_candidates_as_possible(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    product = {"name": "Secret Lair Drop A Box of Rocks", "contents": {"pack": [{"code": "bonus-a-box-of-rocks", "set": "sld"}]}}
    monkeypatch.setattr(sld, "identify_drop", lambda name: {"name": "A Box of Rocks", "release_date": "2026-01-01",
                                                            "file_names": ["ABoxOfRocks_SLD"], "ids": [CARD]})
    monkeypatch.setattr(valuation, "sld_sealed_product", lambda *a, **k: product)
    monkeypatch.setattr(valuation, "sld_sealed_market", lambda name, edition, **k: (20.0, "tcgcsv"))
    monkeypatch.setattr(mtgjson, "set_file", lambda code: {"booster": {"bonus-a-box-of-rocks": {
        "sheets": {"bonus": {"cards": {"u-bonus": 1}}}}}})
    monkeypatch.setattr(mtgjson, "uuid_scryfall_ids", functools.cache(lambda code: {"u-bonus": BONUS}))
    c = market.product_cost("sld", "sld", "a box of rocks", "nonfoil")
    assert c["exact"] == 13.0 and c["booster_ev"] is None and c["has_bonus"] is True
    assert [(ln["name"], ln["bonus"]) for ln in c["lines"]] == [("Counterspell", None), ("Clone", "possible")]


def test_sld_cost_bonus_unknown_counts_nothing_extra(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    product = {"name": "Secret Lair Drop She-Ra", "contents": {"deck": [{"name": "She-Ra", "set": "sld"}],
                                                              "other": [{"name": "Bonus card unknown"}]}}
    monkeypatch.setattr(sld, "identify_drop", lambda name: {"name": "She-Ra", "release_date": "2026-09-29",
                                                            "file_names": ["SheRa_SLD"], "ids": [CARD]})
    monkeypatch.setattr(valuation, "sld_sealed_product", lambda *a, **k: product)
    monkeypatch.setattr(valuation, "sld_sealed_market", lambda name, edition, **k: (39.62, "tcgcsv"))
    c = market.product_cost("sld", "sld", "she-ra", "nonfoil")
    assert c["exact"] == 13.0 and c["has_bonus"] is True and [ln["bonus"] for ln in c["lines"]] == [None]


def test_sld_cost_without_sealed_product_falls_back_to_drop_cards(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    monkeypatch.setattr(sld, "identify_drop", lambda name: {"name": "Old Drop", "release_date": "2020-01-01",
                                                            "file_names": ["OldDrop_SLD"], "ids": [CARD]})
    monkeypatch.setattr(valuation, "sld_sealed_product", lambda *a, **k: None)
    monkeypatch.setattr(valuation, "sld_sealed_market", lambda name, edition, **k: (None, None))
    monkeypatch.setattr(valuation, "value_sealed_product", lambda *a, **k: pytest.fail("no sealed product to value"))
    c = market.product_cost("sld", "sld", "old drop", "nonfoil")
    assert c["sealed_name"] is None and c["market"] is None and c["exact"] == 13.0
    assert [ln["bonus"] for ln in c["lines"]] == [None] and c["has_bonus"] is False
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


def test_sld_cost_refreshes_the_drops_printings_and_reports_freshness(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    product = {"name": "X", "contents": {"card": [{"set": "sld", "number": "7164"}]}}
    monkeypatch.setattr(sld, "identify_drop", lambda name: {"name": "X", "release_date": "2026-11-12", "file_names": ["X_SLD"], "ids": [CARD]})
    monkeypatch.setattr(valuation, "sld_sealed_product", lambda *a, **k: product)
    monkeypatch.setattr(valuation, "sld_sealed_market", lambda name, edition, **k: (10.0, "tcgcsv"))
    monkeypatch.setattr(construct, "product_card_ids", lambda p: [BONUS])
    asked = []
    monkeypatch.setattr(market.sets, "refresh_printing_prices",
                        lambda ids: (asked.append(list(ids)), {"refreshed": 1, "prices_at": "2026-11-10T00:00:00+00:00", "preorder": True})[1])
    c = market.product_cost("sld", "sld", "x", "nonfoil")
    assert asked == [[BONUS], [CARD]]           # bonus printings refreshed too; freshness reported for the guaranteed cards
    assert c["prices_at"].startswith("2026-11-10") and c["preorder"] is True


def test_sld_cost_keeps_last_prices_when_scryfall_fails(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    monkeypatch.setattr(sld, "identify_drop", lambda name: {"name": "Y", "release_date": "2026-01-01", "file_names": ["Y_SLD"], "ids": [CARD]})
    monkeypatch.setattr(valuation, "sld_sealed_product", lambda *a, **k: None)
    monkeypatch.setattr(valuation, "sld_sealed_market", lambda name, edition, **k: (None, None))

    def boom(ids):
        raise scryfall.ScryfallError("HTTP 503")
    monkeypatch.setattr(market.sets, "refresh_printing_prices", boom)
    c = market.product_cost("sld", "sld", "y", "nonfoil")
    assert c["exact"] == 13.0 and c["prices_at"] is None and c["preorder"] is False
    assert any("couldn't refresh prices" in n for n in c["notes"])


def test_price_refresh_bypasses_the_wrapper_cache(monkeypatch):
    from magic_manager import util
    seen = {}

    class _Res:
        returncode, stdout, stderr = 0, '{"data": [], "not_found": []}', ""
    monkeypatch.setattr(util, "run_wrapper", lambda argv, **kw: (seen.setdefault("env", kw.get("env")), _Res())[1])
    scryfall.collection([{"id": "x"}], live=True)
    assert seen["env"]["SCRYFALL_CACHE_TTL"] == "0"


def _drop(monkeypatch, product, ids=None, name="Z"):
    monkeypatch.setattr(sld, "identify_drop", lambda n: {"name": name, "release_date": "2026-01-01",
                                                         "file_names": ["Z_SLD"], "ids": ids or [CARD]})
    monkeypatch.setattr(valuation, "sld_sealed_product", lambda *a, **k: product)
    monkeypatch.setattr(valuation, "sld_sealed_market", lambda n, edition, **k: (10.0, "tcgcsv"))


def test_floor_unpriced_counts_lines_without_a_floor_price(tmp_db, seed_cards, make_card, monkeypatch):
    seed_cards([make_card(id=CARD, oracle_id="o1", name="Counterspell", set="sld", collector_number="2664", prices={})])
    _drop(monkeypatch, None)
    c = market.product_cost("sld", "sld", "z", "nonfoil")
    assert c["floor_unpriced"] == 1 and c["known_floor"] is None and c["unpriced"] == 1


def test_foil_edition_priced_nonfoil_prices_bonus_lines_nonfoil_too(tmp_db, seed_cards, make_card, monkeypatch):
    seed_cards([
        make_card(id=CARD, oracle_id="o1", name="Counterspell", set="sld", collector_number="2664", prices={"usd": "13.00"}),
        make_card(id=BONUS, oracle_id="o2", name="Clone", set="sld", collector_number="7164", prices={"usd": "3.00"}),
    ])
    _drop(monkeypatch, {"name": "P", "contents": {"card": [{"set": "sld", "number": "7164"}]}})
    monkeypatch.setattr(construct, "product_card_ids", lambda p: [BONUS])
    c = market.product_cost("sld", "sld", "z", "foil")
    assert any("only priced nonfoil" in n for n in c["notes"])
    assert {ln["name"]: (ln["finish"], ln["unit_usd"]) for ln in c["lines"]} == {
        "Counterspell": ("nonfoil", 13.0), "Clone": ("nonfoil", 3.0)}


def test_possible_candidate_equal_to_a_named_id_is_listed_once_as_named(monkeypatch):
    product = {"contents": {"pack": [{"code": "bonus-z"}]}}
    monkeypatch.setattr(construct, "product_card_ids", lambda p: [BONUS])
    monkeypatch.setattr(mtgjson, "set_file", lambda code: {"booster": {"bonus-z": {"sheets": {"s": {"cards": {"u": 1}}}}}})
    monkeypatch.setattr(mtgjson, "uuid_scryfall_ids", functools.cache(lambda code: {"u": BONUS}))
    assert market._sld_bonus_ids(product) == ([BONUS], [], None)


def test_a_bonus_id_that_is_also_a_decklist_id_is_not_listed_as_bonus(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    _drop(monkeypatch, {"name": "P", "contents": {"card": [{"set": "sld", "number": "2664"}]}})
    monkeypatch.setattr(construct, "product_card_ids", lambda p: [CARD])
    c = market.product_cost("sld", "sld", "z", "nonfoil")
    assert [(ln["name"], ln["bonus"]) for ln in c["lines"]] == [("Counterspell", None)]


def test_unreadable_bonus_candidates_are_noted_not_swallowed(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    _drop(monkeypatch, {"name": "P", "contents": {"pack": [{"code": "bonus-z"}]}})

    def boom(code):
        raise mtgjson.MtgJsonError("HTTP 503")
    monkeypatch.setattr(mtgjson, "set_file", boom)
    c = market.product_cost("sld", "sld", "z", "nonfoil")
    assert any("couldn't read the bonus pack's candidates (HTTP 503)" in n for n in c["notes"])
    assert [ln["bonus"] for ln in c["lines"]] == [None]


def test_cost_lines_carry_the_exact_printings_image(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    _drop(monkeypatch, None)
    c = market.product_cost("sld", "sld", "z", "nonfoil")
    with market.db.connect() as conn:
        want = conn.execute("SELECT image_uri FROM cards WHERE scryfall_id=?", (CARD,)).fetchone()[0]
    assert c["lines"][0]["image_uri"] == want


def test_a_refresh_clears_that_products_memo_in_every_scope(tmp_db, seed_cards, make_card, monkeypatch):
    _seed(seed_cards, make_card)
    _drop(monkeypatch, None)
    other = ("someone-else", "sld", "sld", "z", "nonfoil")
    unrelated = ("someone-else", "sld", "sld", "other drop", "nonfoil")
    market._cost_memo[other] = (0.0, (), {})
    market._cost_memo[unrelated] = (0.0, (), {})
    monkeypatch.setattr(market.sets, "refresh_printing_prices",
                        lambda ids: {"refreshed": 1, "prices_at": None, "preorder": False})
    market.product_cost("sld", "sld", "z", "nonfoil")
    assert other not in market._cost_memo and unrelated in market._cost_memo
