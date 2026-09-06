"""Tests for manapool.py — the sealed-product Mana Pool market provider.

Offline: monkeypatch ``manapool._run`` so no subprocess/network runs. The fake
branches on the queried uuid (``args[-1]``): the probe uuid returns an empty
data set, real uuids return canned /products/sealed rows.
"""

import pytest

from magic_manager import manapool, sealed


# A canned /products/sealed row (cents), liquid: has both market + low + sales.
_LIQUID = {
    "url": "https://manapool.com/sealed/blb/play-booster-box",
    "product_type": "mtg_sealed", "set_code": "BLB",
    "name": "Bloomburrow Play Booster Box", "tcgplayer_product_id": 111,
    "low_price": 18500, "price_market": 18888, "available_quantity": 112,
    "recent_sales": [{"price": 19000, "quantity": 1},
                     {"price": 21000, "quantity": 1},
                     {"price": 20000, "quantity": 1}],
}
# A scarce row: no market price populated, only a floor, no sales.
_FLOOR_ONLY = {
    "set_code": "CLB", "name": "CLB Set of 4", "tcgplayer_product_id": 222,
    "low_price": 80000, "price_market": 0, "available_quantity": 4,
    "recent_sales": [],
}
# An illiquid row: nothing priced at all.
_ZERO = {
    "set_code": "XXX", "name": "Nothing", "low_price": 0, "price_market": 0,
    "available_quantity": 0, "recent_sales": [],
}


def _fake_run(rows_by_uuid):
    """Build a _run replacement returning {"data":[row]} for known uuids,
    {"data":[]} for the probe / unknown uuids."""
    def fake(args):
        uuid = args[-1]
        row = rows_by_uuid.get(uuid)
        return {"meta": {"as_of": "t"}, "data": [row] if row else []}
    return fake


# ---------- price() : deterministic market figure ----------

def test_price_prefers_market_over_low(monkeypatch):
    monkeypatch.setattr(manapool, "_run", _fake_run({"u-liquid": _LIQUID}))
    p = manapool.ManapoolMarketProvider()
    # price_market 18888c preferred over low 18500c → $188.88
    assert p.price({"uuid": "u-liquid"}) == pytest.approx(188.88)


def test_price_falls_back_to_low_when_no_market(monkeypatch):
    monkeypatch.setattr(manapool, "_run", _fake_run({"u-floor": _FLOOR_ONLY}))
    p = manapool.ManapoolMarketProvider()
    # price_market 0 → falls back to low 80000c → $800.00
    assert p.price({"uuid": "u-floor"}) == pytest.approx(800.00)


def test_price_none_on_illiquid_all_zero(monkeypatch):
    monkeypatch.setattr(manapool, "_run", _fake_run({"u-zero": _ZERO}))
    p = manapool.ManapoolMarketProvider()
    assert p.price({"uuid": "u-zero"}) is None


def test_price_none_on_empty_data(monkeypatch):
    monkeypatch.setattr(manapool, "_run", _fake_run({}))  # every uuid → empty
    p = manapool.ManapoolMarketProvider()
    assert p.price({"uuid": "u-missing"}) is None


def test_price_none_without_uuid(monkeypatch):
    monkeypatch.setattr(manapool, "_run", _fake_run({"u-liquid": _LIQUID}))
    p = manapool.ManapoolMarketProvider()
    assert p.price({"name": "no uuid here"}) is None


# ---------- full() : advisory snapshot + recent-sales median ----------

def test_full_recent_sales_median(monkeypatch):
    monkeypatch.setattr(manapool, "_run", _fake_run({"u-liquid": _LIQUID}))
    p = manapool.ManapoolMarketProvider()
    snap = p.full({"uuid": "u-liquid"})
    assert snap is not None
    assert snap.market == pytest.approx(188.88)
    assert snap.low == pytest.approx(185.00)
    assert snap.n_available == 112
    # median of [190, 210, 200] = 200.00
    assert snap.recent_sales_median == pytest.approx(200.00)
    assert snap.n_sales == 3
    assert "sold-median $200.00 (n=3)" in snap.as_display()


def test_full_no_sales_median_none(monkeypatch):
    monkeypatch.setattr(manapool, "_run", _fake_run({"u-floor": _FLOOR_ONLY}))
    p = manapool.ManapoolMarketProvider()
    snap = p.full({"uuid": "u-floor"})
    assert snap.recent_sales_median is None and snap.n_sales == 0
    # floor shown, no sold-median clause
    assert "$800.00" in snap.as_display() and "sold-median" not in snap.as_display()


def test_memoized_per_uuid(monkeypatch):
    calls = {"n": 0}
    def counting(args):
        if args[-1] == "u-liquid":
            calls["n"] += 1
            return {"data": [_LIQUID]}
        return {"data": []}
    monkeypatch.setattr(manapool, "_run", counting)
    p = manapool.ManapoolMarketProvider()   # 1 call for the probe (uuid != u-liquid)
    p.price({"uuid": "u-liquid"})
    p.price({"uuid": "u-liquid"})
    p.full({"uuid": "u-liquid"})
    assert calls["n"] == 1   # only the first u-liquid lookup hit _run


# ---------- unconfigured → dropped by the seam ----------

def test_unconfigured_dropped_by_build_providers(monkeypatch):
    def raises(args):
        raise manapool.ManapoolUnconfigured("MANAPOOL_* not set")
    monkeypatch.setattr(manapool, "_run", raises)
    # _build_providers must catch the construction error and drop the provider.
    assert sealed._build_providers(["manapool"]) == []
    # make_market_provider("manapool") → no providers → NullMarketProvider
    prov = sealed.make_market_provider("manapool")
    assert isinstance(prov, sealed.NullMarketProvider)
