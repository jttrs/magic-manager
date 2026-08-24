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
