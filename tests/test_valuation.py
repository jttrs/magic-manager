"""Tests for valuation.py — the unified 4-column producers.

Offline: monkeypatch the engine functions the producers orchestrate
(sealed.*, construct.*, sld.*, mtgjson.*, sets.ensure_priced) so no network/DB
runs. Verifies the 4-column mapping, the booster-only branch, the sealed floor
pass, the SLD sealed-market resolver (incl. edition selection + provider
fallthrough), and finish handling.
"""

import pytest

from magic_manager import sealed, valuation


# ---------- helpers ----------

class _Totals:
    def __init__(self, whole, intrinsic, coverage=1.0):
        self.market_whole = whole
        self.market_sum_of_parts = None
        self.intrinsic = intrinsic
        self.coverage = coverage
        self.diagnostics = []


class _Need:
    def __init__(self, sid, finish, qty, unit):
        self.scryfall_id = sid
        self.finish = finish
        self.qty = qty
        self.unit_usd = unit


class _NetRow:
    def __init__(self, sid, finish, need_qty, unit):
        self.scryfall_id = sid
        self.finish = finish
        self.need_qty = need_qty
        self.unit_usd = unit


class _Exp:
    def __init__(self, needs, packs_skipped=None):
        self.needs = needs
        self.packs_skipped = packs_skipped or []
        self.sealed_market = None
        self.diagnostics = []


class _Provider:
    """Prices by tcgplayer_product_id from a dict; records last_source."""
    name = "stub"
    def __init__(self, by_pid):
        self.by_pid = by_pid
        self.last_source = None
    def price(self, meta):
        v = self.by_pid.get(meta.get("tcgplayer_product_id"))
        self.last_source = "stub" if v is not None else None
        return v


# ---------- value_sealed_product ----------

def _patch_sealed(monkeypatch, *, market_whole, needs, packs=None, intrinsic=0.0,
                  oracle_map=None, floors=None):
    from magic_manager import construct, sets
    monkeypatch.setattr(sealed, "identify_product", lambda c, s: {"name": "AFR Display", "uuid": "u"})
    monkeypatch.setattr(sealed, "build_product_tree",
                        lambda *a, **k: type("N", (), {"name": "AFR Display"})())
    monkeypatch.setattr(sealed, "referenced_set_codes", lambda node: {"afc"})
    monkeypatch.setattr(sealed, "aggregate", lambda node: _Totals(market_whole, intrinsic))
    monkeypatch.setattr(sealed, "make_market_provider", lambda mode: _Provider({}))
    monkeypatch.setattr(sets, "ensure_priced", lambda *a, **k: {})
    monkeypatch.setattr(construct, "expand_sealed", lambda *a, **k: _Exp(needs, packs))
    monkeypatch.setattr(construct, "net_against_loose",
                        lambda ns: [_NetRow(n.scryfall_id, n.finish, n.qty, n.unit_usd) for n in ns])
    # floor pass: map scryfall_id → oracle_id, then oracle_id → (nf, foil) floors
    monkeypatch.setattr(valuation, "_oracle_ids_for", lambda sids: (oracle_map or {}))
    from magic_manager import sld
    monkeypatch.setattr(sld, "card_floors_many", lambda oids: (floors or {}))


def test_value_sealed_product_four_columns(monkeypatch):
    needs = [_Need("s1", "nonfoil", 1, 10.0), _Need("s2", "nonfoil", 2, 5.0)]  # exact = 10 + 2*5 = 20
    _patch_sealed(monkeypatch, market_whole=399.95, needs=needs,
                  oracle_map={"s1": "o1", "s2": "o2"},
                  floors={"o1": (7.0, None), "o2": (3.0, None)})  # floor = 7 + 2*3 = 13
    pv = valuation.value_sealed_product("afc", "Display", listing=434.99, market="stub")
    assert pv.kind == "sealed"
    assert pv.listing == 434.99
    assert pv.sealed_market == 399.95
    assert pv.exact_singles == pytest.approx(20.0)
    assert pv.floor_singles == pytest.approx(13.0)
    assert not pv.booster_only


def test_value_sealed_product_booster_only(monkeypatch):
    # No fixed needs + a skipped random pack → booster_only, EV from intrinsic.
    _patch_sealed(monkeypatch, market_whole=95.0, needs=[], packs=["M15 draft booster"],
                  intrinsic=88.4)
    pv = valuation.value_sealed_product("m15", "booster box", listing=100.0, market="stub")
    assert pv.booster_only
    assert pv.exact_singles == pytest.approx(88.4) and pv.floor_singles == pytest.approx(88.4)
    assert "booster" in pv.note.lower()


def test_value_sealed_product_foil_floor(monkeypatch):
    needs = [_Need("s1", "foil", 1, 12.0)]
    _patch_sealed(monkeypatch, market_whole=50.0, needs=needs,
                  oracle_map={"s1": "o1"}, floors={"o1": (2.0, 9.0)})  # foil floor = 9
    pv = valuation.value_sealed_product("x", "y", listing=None, market="stub")
    assert pv.floor_singles == pytest.approx(9.0)   # used foil floor for a foil need


# ---------- sld_sealed_market ----------

def _patch_sld_market(monkeypatch, products, provider):
    from magic_manager import mtgjson
    monkeypatch.setattr(mtgjson, "sealed_products", lambda code: products)
    monkeypatch.setattr(mtgjson, "set_file", lambda code: {"tcgplayerGroupId": 2576})
    monkeypatch.setattr(sealed, "_market_meta",
                        lambda p, sd: {"tcgplayer_product_id": (p.get("identifiers") or {}).get("tcgplayerProductId")})
    monkeypatch.setattr(sealed, "make_market_provider", lambda mode: provider)


def test_sld_sealed_market_punctuation_and_base(monkeypatch):
    # drop name has a comma; product name doesn't — must still match. Base edition.
    products = [
        {"name": "Secret Lair Drop Far Out Man",
         "identifiers": {"tcgplayerProductId": 258487}},
        {"name": "Secret Lair Drop Far Out Man Foil Edition",
         "identifiers": {"tcgplayerProductId": 258488}},
    ]
    _patch_sld_market(monkeypatch, products, _Provider({258487: 45.87, 258488: 79.97}))
    price, source = valuation.sld_sealed_market("Far Out, Man", "auto", market="stub")
    assert price == 45.87 and source == "stub"       # base (non-foil) picked


def test_sld_sealed_market_foil_edition(monkeypatch):
    products = [
        {"name": "Secret Lair Drop Far Out Man", "identifiers": {"tcgplayerProductId": 258487}},
        {"name": "Secret Lair Drop Far Out Man Foil Edition", "identifiers": {"tcgplayerProductId": 258488}},
    ]
    _patch_sld_market(monkeypatch, products, _Provider({258487: 45.87, 258488: 79.97}))
    price, _ = valuation.sld_sealed_market("Far Out, Man", "foil", market="stub")
    assert price == 79.97                            # foil edition picked


def test_sld_sealed_market_no_match_returns_none(monkeypatch):
    _patch_sld_market(monkeypatch, [{"name": "Secret Lair Drop Something Else",
                                     "identifiers": {"tcgplayerProductId": 1}}],
                      _Provider({1: 5.0}))
    price, source = valuation.sld_sealed_market("Far Out, Man", "auto", market="stub")
    assert price is None and source is None


# ---------- value_sld_drop ----------

def test_value_sld_drop_maps_columns(monkeypatch):
    from magic_manager import sld
    monkeypatch.setattr(sld, "identify_drop", lambda s: {"name": "Far Out, Man"})
    monkeypatch.setattr(sld, "value_drop", lambda drop, **k: type("V", (), {
        "name": "Far Out, Man", "nonfoil_total": 61.44, "foil_total": 79.43,
        "nf_floor_total": 23.45, "foil_floor_total": 28.23})())
    monkeypatch.setattr(valuation, "sld_sealed_market", lambda name, ed, **k: (45.87, "tcgcsv"))
    # nonfoil (auto)
    pv = valuation.value_sld_drop("far out", listing=45.0, market="stub", edition="auto")
    assert pv.kind == "sld" and pv.finish == "nonfoil"
    assert pv.sealed_market == 45.87 and pv.exact_singles == 61.44 and pv.floor_singles == 23.45
    # foil edition → uses foil totals
    pv2 = valuation.value_sld_drop("far out", listing=45.0, market="stub", edition="foil")
    assert pv2.finish == "foil"
    assert pv2.exact_singles == 79.43 and pv2.floor_singles == 28.23


# ---------- regression: the real-name matching bugs behind blank cells ----------

def test_sld_sealed_market_marvels_storm_x_scaffold_apostrophe(monkeypatch):
    # Drop "Marvel's Storm" vs product "… Secret Lair x Marvels Storm": the x
    # scaffold + apostrophe broke the old whole-string match.
    products = [
        {"name": "Secret Lair Drop Secret Lair x Marvels Storm",
         "identifiers": {"tcgplayerProductId": 111}},
        {"name": "Secret Lair Drop Secret Lair x Marvels Storm Rainbow Foil",
         "identifiers": {"tcgplayerProductId": 112}},
    ]
    _patch_sld_market(monkeypatch, products, _Provider({111: 90.0, 112: 96.98}))
    assert valuation.sld_sealed_market("Marvel's Storm", "foil", market="stub")[0] == 96.98
    assert valuation.sld_sealed_market("Marvel's Storm", "auto", market="stub")[0] == 90.0


def test_sld_sealed_market_beholder_amp_and(monkeypatch):
    # "Dungeons & Dragons" (drop) vs "Dungeons and Dragons" (product).
    products = [
        {"name": "Secret Lair Drop Secret Lair x Dungeons and Dragons Death is in the Eyes of the Beholder I",
         "identifiers": {"tcgplayerProductId": 201}},
        {"name": "Secret Lair Drop Secret Lair x Dungeons and Dragons Death is in the Eyes of the Beholder I Rainbow Foil",
         "identifiers": {"tcgplayerProductId": 202}},
    ]
    _patch_sld_market(monkeypatch, products, _Provider({201: 49.99, 202: 55.0}))
    price, _ = valuation.sld_sealed_market(
        "Dungeons & Dragons: Death is in the Eyes of the Beholder I", "foil", market="stub")
    assert price == 55.0


def test_value_sld_drop_foil_fallback_to_nonfoil(monkeypatch):
    # Foil edition, but the cards are only priced nonfoil (usd_foil null → foil
    # totals are 0). Must fall back to the nonfoil sum, not blank it.
    from magic_manager import sld
    monkeypatch.setattr(sld, "identify_drop", lambda s: {"name": "Featuring: Julie Bell"})
    monkeypatch.setattr(sld, "value_drop", lambda drop, **k: type("V", (), {
        "name": "Featuring: Julie Bell", "nonfoil_total": 59.65, "foil_total": 0.0,
        "nf_floor_total": 41.16, "foil_floor_total": 0.0})())
    monkeypatch.setattr(valuation, "sld_sealed_market", lambda name, ed, **k: (44.99, "stub"))
    pv = valuation.value_sld_drop("julie bell", market="stub", edition="foil")
    assert pv.exact_singles == 59.65          # fell back to nonfoil, not $0/blank
    assert pv.floor_singles == 41.16
    assert pv.finish == "nonfoil"             # reflects what was actually used
    assert any("nonfoil" in d for d in pv.diagnostics)   # transparency diagnostic
