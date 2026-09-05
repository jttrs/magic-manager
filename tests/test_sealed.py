"""Tests for sealed.py — recursive sealed-product valuation.

Offline: monkeypatch mtgjson.set_file / deck_list / deck, and seed local card
prices via MAGIC_MANAGER_DB where a real price join is exercised.
"""

import pytest

from magic_manager import sealed


# A tiny set with one booster type and two sealed products: a Booster Pack
# (contents.pack → EV) and a Booster Box (contents.sealed → 36 of that pack).
def _set_data():
    return {
        "code": "TST",
        "tcgplayerGroupId": 999,
        "cards": [
            {"uuid": "u-c", "name": "Common", "identifiers": {"scryfallId": "sid-c"}},
            {"uuid": "u-r", "name": "Rare", "identifiers": {"scryfallId": "sid-r"}},
        ],
        "booster": {
            "draft": {
                "boostersTotalWeight": 1,
                "boosters": [{"contents": {"common": 1, "rare": 1}, "weight": 1}],
                "sheets": {
                    "common": {"foil": False, "totalWeight": 1, "cards": {"u-c": 1}},
                    "rare": {"foil": False, "totalWeight": 1, "cards": {"u-r": 1}},
                },
            },
            "collector": {  # a SECOND type, richer, to prove code-selection
                "boostersTotalWeight": 1,
                "boosters": [{"contents": {"rare": 2}, "weight": 1}],
                "sheets": {
                    "rare": {"foil": False, "totalWeight": 1, "cards": {"u-r": 1}},
                },
            },
        },
        "sealedProduct": [
            {"name": "TST Booster Pack", "category": "booster_pack", "subtype": "draft",
             "uuid": "pack-uuid", "identifiers": {"tcgplayerProductId": "111"},
             "purchaseUrls": {"tcgplayer": "https://example/pack"},
             "contents": {"pack": [{"code": "draft", "set": "tst"}]}},
            {"name": "TST Collector Pack", "category": "booster_pack", "subtype": "collector",
             "uuid": "cpack-uuid", "identifiers": {"tcgplayerProductId": "112"},
             "contents": {"pack": [{"code": "collector", "set": "tst"}]}},
            {"name": "TST Booster Box", "category": "booster_box", "subtype": "draft",
             "uuid": "box-uuid", "identifiers": {"tcgplayerProductId": "222"},
             "purchaseUrls": {"tcgplayer": "https://example/box"},
             "contents": {"sealed": [{"name": "TST Booster Pack", "count": 36,
                                      "set": "tst", "uuid": "pack-uuid"}]}},
            {"name": "TST Clash Pack", "category": "multiple_decks", "subtype": "clash",
             "uuid": "clash-uuid", "identifiers": {},
             "contents": {"deck": [{"name": "Fate", "set": "tst"}],
                          "other": [{"name": "spindown die"}]}},
        ],
    }


_DECKLIST = [
    {"code": "TST", "fileName": "Fate_TST", "name": "Fate", "type": "Clash Pack"},
]


def _patch(monkeypatch, *, seed_prices=True, tmp_path=None):
    from magic_manager import mtgjson
    data = _set_data()
    monkeypatch.setattr(mtgjson, "set_file",
                        lambda code: data if code.lower() == "tst" else {})
    monkeypatch.setattr(mtgjson, "deck_list",
                        lambda *, set_code=None: [d for d in _DECKLIST
                                                  if set_code is None or d["code"] == set_code.upper()])
    monkeypatch.setattr(mtgjson, "deck",
                        lambda fn: {"mainBoard": [
                            {"name": "Rare", "count": 1, "identifiers": {"scryfallId": "sid-r"}},
                        ]} if fn == "Fate_TST" else {})
    if seed_prices and tmp_path is not None:
        monkeypatch.setenv("MAGIC_MANAGER_DB", str(tmp_path / "mm.db"))
        from magic_manager import db
        with db.connect() as conn:
            conn.executemany(
                "INSERT INTO cards (scryfall_id, name, set_code, collector_number, "
                "rarity, prices_usd, prices_usd_foil) VALUES (?,?,?,?,?,?,?)",
                [("sid-c", "Common", "tst", "1", "common", 0.25, 1.0),
                 ("sid-r", "Rare", "tst", "2", "rare", 4.0, 12.0)],
            )


def test_identify_product_substring(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path=tmp_path)
    p = sealed.identify_product("tst", "booster box")
    assert p["name"] == "TST Booster Box"


def test_identify_product_ambiguous_raises(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path=tmp_path)
    # "pack" matches Booster Pack, Collector Pack, and Clash Pack → ambiguous
    with pytest.raises(LookupError):
        sealed.identify_product("tst", "pack")


def test_pack_ev_intrinsic(monkeypatch, tmp_path):
    """A Booster Pack's intrinsic = draft booster EV = common($0.25) + rare($4) = $4.25."""
    _patch(monkeypatch, tmp_path=tmp_path)
    p = sealed.identify_product("tst", "TST Booster Pack")
    node = sealed.build_product_tree("tst", p)
    assert node.kind == "sealed"
    assert len(node.children) == 1
    pack = node.children[0]
    assert pack.kind == "pack" and pack.intrinsic_kind == "ev"
    assert pack.intrinsic_usd == pytest.approx(4.25)


def test_box_recurses_into_36_packs(monkeypatch, tmp_path):
    """Box → one child with count=36; intrinsic = 36 · pack_EV = 36·4.25 = $153."""
    _patch(monkeypatch, tmp_path=tmp_path)
    p = sealed.identify_product("tst", "TST Booster Box")
    node = sealed.build_product_tree("tst", p)
    assert len(node.children) == 1
    inner_pack = node.children[0]          # the resolved sub-product (sealed)
    assert inner_pack.count == 36
    assert node.intrinsic_usd == pytest.approx(36 * 4.25)
    t = sealed.aggregate(node)
    assert t.intrinsic == pytest.approx(153.0)


def test_pack_code_selects_booster_type(monkeypatch, tmp_path):
    """The Collector Pack references code='collector' → 2 rares = $8, NOT the
    draft EV of $4.25. Proves pack.code selects the right booster type."""
    _patch(monkeypatch, tmp_path=tmp_path)
    p = sealed.identify_product("tst", "TST Collector Pack")
    node = sealed.build_product_tree("tst", p)
    assert node.children[0].intrinsic_usd == pytest.approx(8.0)


def test_deck_contents_valued_and_other_ignored(monkeypatch, tmp_path):
    """Clash Pack: the deck (one Rare=$4) is valued; the spindown die (other) is
    NOT a node."""
    _patch(monkeypatch, tmp_path=tmp_path)
    p = sealed.identify_product("tst", "TST Clash Pack")
    node = sealed.build_product_tree("tst", p)
    kinds = [c.kind for c in node.children]
    assert kinds == ["deck"]              # 'other' produced no node
    assert node.children[0].intrinsic_usd == pytest.approx(4.0)


def test_market_whole_vs_parts(monkeypatch, tmp_path):
    """A stub provider prices box=$100 and pack=$3; aggregate reports whole=$100
    and parts=36·$3=$108."""
    _patch(monkeypatch, tmp_path=tmp_path)

    class StubProvider:
        name = "stub"
        def price(self, meta):
            return {"222": 100.0, "111": 3.0}.get(str(meta.get("tcgplayer_product_id")))

    p = sealed.identify_product("tst", "TST Booster Box")
    node = sealed.build_product_tree("tst", p, market_provider=StubProvider())
    t = sealed.aggregate(node)
    assert t.market_whole == pytest.approx(100.0)
    assert t.market_sum_of_parts == pytest.approx(108.0)


def test_null_provider_leaves_market_none(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path=tmp_path)
    p = sealed.identify_product("tst", "TST Booster Box")
    node = sealed.build_product_tree("tst", p)
    assert node.market_usd is None
    assert node.purchase_url == "https://example/box"


def test_unresolved_subproduct_diagnostic(monkeypatch, tmp_path):
    """A contents.sealed ref pointing at a nonexistent product is reported, not
    crashed."""
    _patch(monkeypatch, tmp_path=tmp_path)
    product = {"name": "Broken Box", "uuid": "bb", "contents": {
        "sealed": [{"name": "Ghost Pack", "count": 2, "set": "tst", "uuid": "nope"}]}}
    node = sealed.build_product_tree("tst", product)
    assert node.children == []
    assert any("unresolved sub-product" in d for d in node.diagnostics)


def test_cycle_guard(monkeypatch, tmp_path):
    """A product whose contents.sealed points back at itself terminates."""
    from magic_manager import mtgjson
    _patch(monkeypatch, tmp_path=tmp_path)
    selfref = {"name": "Ouroboros", "uuid": "self", "category": "box",
               "contents": {"sealed": [{"name": "Ouroboros", "count": 1,
                                        "set": "tst", "uuid": "self"}]}}
    monkeypatch.setattr(mtgjson, "sealed_products",
                        lambda code, **k: [selfref] if code.lower() == "tst" else [])
    node = sealed.build_product_tree("tst", selfref)
    # child resolves to itself, then the cycle guard fires on it.
    assert any("cycle detected" in d for c in node.children for d in c.diagnostics)


def test_variable_weighted_average(monkeypatch, tmp_path):
    """Two equally-weighted configs, each one deck worth $4 → weighted avg $4."""
    _patch(monkeypatch, tmp_path=tmp_path)
    product = {"name": "Toolkit", "uuid": "tk", "contents": {
        "variable": [{"configs": [
            {"deck": [{"name": "Fate", "set": "tst"}], "variable_config": [{"chance": 1, "weight": 1}]},
            {"deck": [{"name": "Fate", "set": "tst"}], "variable_config": [{"chance": 1, "weight": 1}]},
        ]}]}}
    node = sealed.build_product_tree("tst", product)
    var = node.children[0]
    assert var.kind == "variable"
    assert var.intrinsic_usd == pytest.approx(4.0)
    assert any("approximation" in d for d in var.diagnostics)
