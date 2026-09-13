"""Unit tests for magic_manager.util — the consolidated shared helpers."""

from __future__ import annotations

from magic_manager import util


def test_cn_sort_key_numeric_then_suffix():
    assert util.cn_sort_key("2") < util.cn_sort_key("10")
    assert util.cn_sort_key("1858") < util.cn_sort_key("1858a") < util.cn_sort_key("1859")


def test_cn_sort_key_non_numeric_sorts_first():
    # non-numeric / empty → (0, cn); numeric → (int, suffix)
    assert util.cn_sort_key("abc") == (0, "abc")
    assert util.cn_sort_key("") == (0, "")
    assert util.cn_sort_key(None) == (0, "")
    assert util.cn_sort_key("") < util.cn_sort_key("1")


def test_cn_sort_key_matches_selectors_alias():
    # selectors._cn_sort_key is a thin alias — must agree everywhere.
    from magic_manager.selectors import _cn_sort_key
    for cn in ["1", "10", "1858a", "99b", "N1"]:
        assert _cn_sort_key(cn) == util.cn_sort_key(cn)


def test_fmt_usd():
    assert util.fmt_usd(1.0) == "$1.00"
    assert util.fmt_usd(12.5) == "$12.50"
    assert util.fmt_usd(None) == "—"


def test_fmt_delta_cell():
    f = util.fmt_delta_cell
    # sign convention is listing − value (negative = listing below that measure)
    # value None → em dash regardless of listing
    assert f(None, 10.0) == "—"
    assert f(None, None) == "—"
    # listing None → bare value, no delta
    assert f(45.87, None) == "$45.87"
    # sealed mkt $75, listing $60 → listing is $15 BELOW market (a discount)
    assert f(75.0, 60.0) == "$75.00 (-$15.00)"
    # value below listing → positive (listing above that measure / premium)
    assert f(399.95, 434.99) == "$399.95 (+$35.04)"
    # exactly equal → +$0.00
    assert f(50.0, 50.0) == "$50.00 (+$0.00)"
    # delta rounds to cents
    assert f(10.25, 12.50) == "$10.25 (+$2.25)"


def test_delta_of_sign():
    assert util.delta_of(75.0, 60.0) == -15.0     # listing below value → negative
    assert util.delta_of(60.0, 75.0) == 15.0      # listing above value → positive
    assert util.delta_of(None, 60.0) is None
    assert util.delta_of(75.0, None) is None


# ---------- format_color_identity ----------

def test_color_identity_card_rule_collapses_multicolor():
    f = util.format_color_identity
    assert f([], collapse_multicolor=True) == "C"          # colorless
    assert f(["W"], collapse_multicolor=True) == "W"        # mono
    assert f(["R", "W"], collapse_multicolor=True) == "M"   # multicolor → M
    assert f(["W", "U", "B", "R", "G"], collapse_multicolor=True) == "M"


def test_color_identity_deck_rule_actual_letters_wubrg_order():
    f = util.format_color_identity
    assert f([], collapse_multicolor=False) == "C"
    assert f(["W"], collapse_multicolor=False) == "W"
    # order-independent input → canonical WUBRG order out
    assert f(["G", "W"], collapse_multicolor=False) == "WG"
    assert f(["R", "B", "U"], collapse_multicolor=False) == "UBR"
    assert f(["G", "R", "B", "U", "W"], collapse_multicolor=False) == "WUBRG"


def test_color_identity_accepts_json_string_and_filters_junk():
    f = util.format_color_identity
    assert f('["B","G"]', collapse_multicolor=False) == "BG"
    assert f('[]', collapse_multicolor=True) == "C"
    assert f("not json", collapse_multicolor=False) == "C"   # bad JSON → colorless
    # non-WUBRG tokens (e.g. a stray 'P'/'C') are filtered out
    assert f(["W", "P", "C"], collapse_multicolor=False) == "W"
