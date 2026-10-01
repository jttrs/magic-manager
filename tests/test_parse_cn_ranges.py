"""Tests for parsers.parse_cn_ranges — the deterministic CN-range spec parser
(the bulk-add agentic step, made scriptable for the web app). Pure/offline."""

from __future__ import annotations

import pytest

from magic_manager import parsers


def _pairs(spec):
    return [(c.collector_number, c.finish) for c in parsers.parse_cn_ranges(spec)]


def test_inclusive_range_default_nonfoil():
    assert _pairs("1858-1860") == [
        ("1858", "nonfoil"), ("1859", "nonfoil"), ("1860", "nonfoil")]


def test_segment_finish_token():
    assert _pairs("1858-1859 foil") == [("1858", "foil"), ("1859", "foil")]


def test_singletons():
    assert _pairs("246, 380, 451") == [
        ("246", "nonfoil"), ("380", "nonfoil"), ("451", "nonfoil")]


def test_mixed_per_segment_finish():
    assert _pairs("1858-1859 nonfoil, 7001 foil") == [
        ("1858", "nonfoil"), ("1859", "nonfoil"), ("7001", "foil")]


def test_both_finishes_plus_foil():
    assert _pairs("1858-1859 +foil") == [
        ("1858", "nonfoil"), ("1858", "foil"),
        ("1859", "nonfoil"), ("1859", "foil")]


def test_empty_spec_is_empty_list():
    assert parsers.parse_cn_ranges("") == []
    assert parsers.parse_cn_ranges("   ") == []


def test_inverted_range_raises():
    with pytest.raises(ValueError, match="inverted"):
        parsers.parse_cn_ranges("5-3")


def test_unparseable_segment_raises():
    with pytest.raises(ValueError, match="unparseable"):
        parsers.parse_cn_ranges("1858a-1860")  # letter-suffix CNs aren't range-expandable
    with pytest.raises(ValueError):
        parsers.parse_cn_ranges("garbage")


def test_whitespace_tolerant():
    assert _pairs("  1858 - 1859 ,  7001  foil ") == [
        ("1858", "nonfoil"), ("1859", "nonfoil"), ("7001", "foil")]
