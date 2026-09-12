"""Tests for scripts/sealed_value_batch.py — the multi-product batch valuer.

Offline: monkeypatch the engine calls the batch script routes to (sealed.* and
sld.*) so no network/DB is needed. Verifies routing, deal-delta math, error
rows, and the asking-column toggle. The script is imported as a module.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Load the script as a module (it lives in scripts/, not the package). Register
# it in sys.modules BEFORE exec so its @dataclass can resolve cls.__module__.
_spec = importlib.util.spec_from_file_location(
    "sealed_value_batch", ROOT / "scripts" / "sealed_value_batch.py")
svb = importlib.util.module_from_spec(_spec)
sys.modules["sealed_value_batch"] = svb
_spec.loader.exec_module(svb)


class _FakeTotals:
    def __init__(self, whole, intrinsic, coverage=1.0):
        self.market_whole = whole
        self.market_sum_of_parts = None
        self.intrinsic = intrinsic
        self.coverage = coverage
        self.diagnostics = []


def _patch_sealed(monkeypatch, *, market, intrinsic, coverage=1.0, name="AFR Display"):
    from magic_manager import sealed, sets
    monkeypatch.setattr(sealed, "identify_product",
                        lambda code, substr: {"name": name, "uuid": "u"})
    monkeypatch.setattr(sealed, "build_product_tree",
                        lambda *a, **k: type("N", (), {"name": name})())
    monkeypatch.setattr(sealed, "referenced_set_codes", lambda node: {"afc"})
    monkeypatch.setattr(sealed, "aggregate",
                        lambda node: _FakeTotals(market, intrinsic, coverage))
    monkeypatch.setattr(sealed, "make_market_provider", lambda mode: object())
    monkeypatch.setattr(sets, "ensure_priced", lambda *a, **k: {})


def test_value_sealed_row(monkeypatch):
    _patch_sealed(monkeypatch, market=399.95, intrinsic=470.51, name="AFR Display")
    from magic_manager import sealed
    row = svb._value_sealed({"set_code": "afc", "product": "Display", "asking_price": 434.99},
                            sealed.make_market_provider("null"))
    assert row.kind == "sealed"
    assert row.market == 399.95 and row.intrinsic == 470.51
    assert row.asking == 434.99
    assert row.note == ""            # full coverage → no note


def test_value_sealed_low_coverage_note(monkeypatch):
    _patch_sealed(monkeypatch, market=800.0, intrinsic=678.78, coverage=0.98, name="CLB")
    from magic_manager import sealed
    row = svb._value_sealed({"set_code": "clb", "product": "Set of 4"},
                            sealed.make_market_provider("null"))
    assert "coverage 98%" in row.note


def test_value_sealed_unresolved_is_error_row(monkeypatch):
    from magic_manager import sealed
    def boom(code, substr):
        raise LookupError("no product matching 'zzz'")
    monkeypatch.setattr(sealed, "identify_product", boom)
    monkeypatch.setattr(sealed, "make_market_provider", lambda mode: object())
    row = svb._value_sealed({"set_code": "afc", "product": "zzz"},
                            sealed.make_market_provider("null"))
    assert row.kind == "error" and "no product matching" in row.note


def test_value_sld_row(monkeypatch):
    from magic_manager import sld
    monkeypatch.setattr(sld, "identify_drop", lambda s: {"name": "Spinner Rack"})
    monkeypatch.setattr(sld, "value_drop", lambda drop, **k: type("V", (), {
        "name": "Spinner Rack", "nonfoil_total": 37.37, "nf_floor_total": 4.38})())
    row = svb._value_sld({"set_code": "sld", "drop": "Spinner", "asking_price": 29.99})
    assert row.kind == "sld"
    assert row.market == 37.37 and row.intrinsic == 4.38   # own-nonfoil / nonfoil-floor


def test_value_item_routes_sld_vs_sealed(monkeypatch):
    from magic_manager import sld
    monkeypatch.setattr(sld, "identify_drop", lambda s: {"name": "D"})
    monkeypatch.setattr(sld, "value_drop", lambda drop, **k: type("V", (), {
        "name": "D", "nonfoil_total": 1.0, "nf_floor_total": 0.5})())
    r = svb.value_item({"set_code": "sld", "drop": "D"}, object())
    assert r.kind == "sld"


def test_render_deal_delta_and_asking_toggle():
    rows = [
        svb.BatchRow("Good Deal", "sealed", asking=700.0, market=800.0, intrinsic=650.0),
        svb.BatchRow("Overpay", "sealed", asking=435.0, market=400.0, intrinsic=470.0),
    ]
    out = "\n".join(svb._render(rows, show_asking=True))
    assert "Deal Δ" in out
    assert "$100.00" in out    # 800 - 700
    assert "$-35.00" in out    # 400 - 435
    # Without asking, the deal column is gone.
    out2 = "\n".join(svb._render(rows, show_asking=False))
    assert "Deal Δ" not in out2 and "Asking" not in out2


def test_error_row_renders_without_crashing():
    rows = [svb.BatchRow("Bad", "error", asking=None, market=None, intrinsic=None,
                         note="no product matching")]
    out = "\n".join(svb._render(rows, show_asking=False))
    assert "error" in out
