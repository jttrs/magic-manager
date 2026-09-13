"""Tests for scripts/sealed_value_batch.py — the multi-product batch valuer.

Offline: monkeypatch the `valuation.*` producers the batch script routes to, so
no network/DB is needed. Verifies routing (sealed vs SLD), the 4-column render
with per-cell deltas, the booster-only EV labeling, and error rows.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Load the script as a module (it lives in scripts/, not the package). Register
# it in sys.modules BEFORE exec so its @dataclass can resolve cls.__module__.
_spec = importlib.util.spec_from_file_location(
    "sealed_value_batch", ROOT / "scripts" / "sealed_value_batch.py")
svb = importlib.util.module_from_spec(_spec)
sys.modules["sealed_value_batch"] = svb
_spec.loader.exec_module(svb)

from magic_manager import sealed  # noqa: E402


def _pv(**kw):
    """A ProductValuation with sensible defaults for rendering tests."""
    base = dict(label="X", kind="sealed", listing=None, sealed_market=None,
                exact_singles=None, floor_singles=None)
    base.update(kw)
    return sealed.ProductValuation(**base)


# ---------- routing + producer delegation ----------

def test_value_sealed_delegates_to_valuation(monkeypatch):
    from magic_manager import valuation
    captured = {}
    def fake(code, substr, **kw):
        captured.update(code=code, substr=substr, **kw)
        return _pv(label="AFR Display", kind="sealed", listing=kw.get("listing"),
                   sealed_market=399.95, exact_singles=470.51, floor_singles=375.53)
    monkeypatch.setattr(valuation, "value_sealed_product", fake)
    row = svb._value_sealed({"set_code": "afc", "product": "Display", "asking_price": 434.99},
                            "chain", {})
    assert row.kind == "sealed"
    assert row.valuation.sealed_market == 399.95 and row.valuation.listing == 434.99
    assert captured["code"] == "afc" and captured["listing"] == 434.99


def test_value_sealed_unresolved_is_error_row(monkeypatch):
    from magic_manager import valuation
    def boom(code, substr, **kw):
        raise LookupError("no product matching 'zzz'")
    monkeypatch.setattr(valuation, "value_sealed_product", boom)
    row = svb._value_sealed({"set_code": "afc", "product": "zzz"}, "chain", {})
    assert row.kind == "error" and "no product matching" in row.note


def test_value_sld_delegates_and_edition_hint(monkeypatch):
    from magic_manager import valuation
    captured = {}
    def fake(substr, **kw):
        captured.update(substr=substr, **kw)
        return _pv(label="Far Out, Man", kind="sld", listing=kw.get("listing"),
                   sealed_market=45.87, exact_singles=61.44, floor_singles=23.45,
                   finish="foil" if kw.get("edition") == "foil" else "nonfoil")
    monkeypatch.setattr(valuation, "value_sld_drop", fake)
    row = svb._value_sld({"set_code": "sld", "drop": "Far Out", "asking_price": 45.0,
                          "edition": "Rainbow Foil"}, "chain", {})
    assert row.kind == "sld"
    assert captured["edition"] == "foil"        # "Rainbow Foil" → foil edition hint
    assert row.valuation.sealed_market == 45.87


def test_value_item_routes_sld_vs_sealed(monkeypatch):
    from magic_manager import valuation
    monkeypatch.setattr(valuation, "value_sld_drop",
                        lambda s, **k: _pv(label="D", kind="sld"))
    monkeypatch.setattr(valuation, "value_sealed_product",
                        lambda c, s, **k: _pv(label="P", kind="sealed"))
    assert svb.value_item({"set_code": "sld", "drop": "D"}, "chain", {}).kind == "sld"
    assert svb.value_item({"set_code": "afc", "product": "P"}, "chain", {}).kind == "sealed"


# ---------- 4-column render with per-cell deltas ----------

def test_render_four_columns_with_deltas():
    rows = [
        svb.BatchRow("Good Deal", "sealed", _pv(
            label="Good Deal", listing=700.0, sealed_market=800.0,
            exact_singles=650.0, floor_singles=500.0)),
        svb.BatchRow("Overpay", "sealed", _pv(
            label="Overpay", listing=435.0, sealed_market=400.0,
            exact_singles=470.0, floor_singles=375.0)),
    ]
    out = "\n".join(svb._render(rows))
    # header carries Finish + the 4 value columns
    assert "Finish" in out and "Listing" in out and "Sealed mkt" in out
    assert "Exact singles" in out and "Floor singles" in out
    # per-cell deltas: sealed_market − listing
    assert "$800.00 (+$100.00)" in out   # 800 - 700
    assert "$400.00 (-$35.00)" in out    # 400 - 435


def test_render_name_hyperlinks_to_url():
    rows = [svb.BatchRow("Far Out, Man", "sld", _pv(
        label="Far Out, Man", kind="sld", listing=60.0, sealed_market=75.0,
        exact_singles=79.43, floor_singles=28.23, finish="foil"),
        url="https://store.example/far-out-man")]
    out = "\n".join(svb._render(rows))
    assert "[Far Out, Man](https://store.example/far-out-man)" in out
    assert "| foil |" in out              # finish explicit per row


def test_render_no_url_leaves_bare_label():
    rows = [svb.BatchRow("Bare", "sld", _pv(label="Bare", kind="sld",
            listing=10.0, sealed_market=12.0, exact_singles=8.0, floor_singles=5.0))]
    out = "\n".join(svb._render(rows))
    assert "Bare" in out and "](" not in out   # no link syntax when no url


def test_render_listing_none_shows_bare_values():
    rows = [svb.BatchRow("No Listing", "sld", _pv(
        label="No Listing", kind="sld", listing=None,
        sealed_market=45.87, exact_singles=61.44, floor_singles=23.45))]
    out = "\n".join(svb._render(rows))
    assert "$45.87" in out and "(+" not in out and "(-" not in out   # no delta w/o listing


def test_render_booster_only_labels_ev():
    rows = [svb.BatchRow("Booster Box", "sealed", _pv(
        label="Booster Box", listing=300.0, sealed_market=350.0,
        exact_singles=88.4, floor_singles=88.4, booster_only=True))]
    out = "\n".join(svb._render(rows))
    assert "EV" in out            # cols 3/4 tagged EV for a pure-booster product


def test_render_error_row_no_crash():
    rows = [svb.BatchRow("Bad", "error", None, note="no product matching")]
    out = "\n".join(svb._render(rows))
    assert "Bad" in out and "—" in out
