"""Tests for the earmark deal-review valuation dispatch (2026-09-12).

Regression guard for the "earmark bugging out" bug: Secret Lair earmarks were
valued through the sealedProduct TREE engine (like any other product), which for
an SLD drop is dominated by a shared `dnd-50th-anniversary` booster `variable`
config — so `aggregate()` returned an IDENTICAL intrinsic for every distinct
drop (e.g. both Beholder I and II reported $283.36). The fix routes `sld` earmarks
through `valuation.value_sld_drop` (the drop's own printings), matching every
other sealed-value tool. These pin that dispatch WITHOUT the network: the sealed
tree path must never be hit for an SLD earmark, and the stored sealedProduct name
(with its `Secret Lair x` scaffold + finish marker) must be stripped to a drop
substring for the SLD resolver.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import review_earmarks  # noqa: E402
from magic_manager import sealed, valuation  # noqa: E402


def _boom(*a, **k):  # any call to the sealed tree engine is a bug for SLD
    raise AssertionError("SLD earmark must NOT touch the sealed tree engine")


def test_sld_earmark_routes_to_sld_engine(monkeypatch):
    # Guard: the sealed tree path is a hard error for an SLD earmark.
    monkeypatch.setattr(sealed, "identify_product", _boom)
    monkeypatch.setattr(sealed, "build_product_tree", _boom)

    captured = {}

    def fake_value_sld_drop(substr, *, market, edition):
        captured["substr"] = substr
        captured["edition"] = edition
        return sealed.ProductValuation(
            label="Beholder I", kind="sld", listing=None,
            sealed_market=47.58, sealed_market_source="tcgcsv",
            exact_singles=40.35, floor_singles=12.0, finish="foil")

    monkeypatch.setattr(valuation, "value_sld_drop", fake_value_sld_drop)

    out = review_earmarks._value_product(
        "sld",
        "Secret Lair Drop Secret Lair x Dungeons and Dragons "
        "Death is in the Eyes of the Beholder I Rainbow Foil",
        market_provider=None, edition="foil", market_name="tcgcsv")

    # market ← sealed_market, intrinsic ← exact_singles (NOT the booster-EV tree).
    assert out == {"market": 47.58, "intrinsic": 40.35, "error": None}
    # Name stripped to a drop substring (scaffold + finish marker removed).
    assert captured["substr"] == "dungeons and dragons death is in the eyes of the beholder i"
    # Finish comes from the stored subtype (unified resolver), passed through.
    assert captured["edition"] == "foil"


def test_sld_earmark_lookup_error_is_soft(monkeypatch):
    # A drop that can't be resolved degrades to a blank row + error string,
    # never aborting the whole review run.
    monkeypatch.setattr(sealed, "identify_product", _boom)

    def raise_lookup(*a, **k):
        raise LookupError("no Secret Lair drop matching 'whatever'")

    monkeypatch.setattr(valuation, "value_sld_drop", raise_lookup)
    out = review_earmarks._value_product("sld", "Whatever Foil",
                                         market_provider=None, market_name="tcgcsv")
    assert out["market"] is None and out["intrinsic"] is None
    assert "no Secret Lair drop" in out["error"]


def test_edition_falls_back_to_name_sniff_when_no_subtype(monkeypatch):
    # Pre-unification rows have no subtype; the finish is sniffed from the stored
    # (sealedProduct) name so old earmarks still price the right finish.
    monkeypatch.setattr(sealed, "identify_product", _boom)
    captured = {}

    def fake(substr, *, market, edition):
        captured["edition"] = edition
        return sealed.ProductValuation(label="x", kind="sld", listing=None,
                                       sealed_market=1.0, exact_singles=2.0)

    monkeypatch.setattr(valuation, "value_sld_drop", fake)
    review_earmarks._value_product("sld", "Some Drop Non-Foil Edition",
                                   market_provider=None, edition=None,
                                   market_name="tcgcsv")
    assert captured["edition"] == "nonfoil"
    review_earmarks._value_product("sld", "Some Drop Rainbow Foil",
                                   market_provider=None, edition=None,
                                   market_name="tcgcsv")
    assert captured["edition"] == "foil"
