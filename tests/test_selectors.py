"""Unit tests for the selector DSL — parsing, cn-sort ordering, and the
unconfigured-family guard. Pure where possible; the one materialize test uses
a seeded tmp DB + faked all_sets so it stays offline."""

from __future__ import annotations

import pytest

from magic_manager import selectors
from magic_manager.selectors import _cn_sort_key, SelectorParseError


# ---------- collector-number sort key ----------

def test_cn_sort_key_numeric_ordering():
    assert _cn_sort_key("2") < _cn_sort_key("10")   # numeric, not lexicographic
    assert _cn_sort_key("1858") < _cn_sort_key("1859")


def test_cn_sort_key_suffix_ordering():
    # bare number sorts before its lettered variant; variants sort alphabetically
    assert _cn_sort_key("1858") < _cn_sort_key("1858a")
    assert _cn_sort_key("1858a") < _cn_sort_key("1859")


def test_cn_sort_key_shape():
    assert _cn_sort_key("99b") == (99, "b")
    assert _cn_sort_key("1") == (1, "")


# ---------- parse-time errors ----------

def test_empty_selector_raises():
    with pytest.raises(SelectorParseError):
        selectors.materialize("")


def test_unconfigured_family_preferred_raises(tmp_db, seed_cards, make_card, monkeypatch):
    """`treatment=preferred` on a family with no FAMILY_DUPE_FOIL_PROMO_TYPES
    entry must raise SelectorParseError (the guard that protected EOE before it
    was configured), NOT silently return everything.

    Note: the guard is row-driven — it fires while filtering rows, so the
    family must have at least one seeded card for the error to surface.
    """
    import magic_manager.scryfall as scry
    # 'zzz' is a nonsense anchor that will never be in FAMILY_DUPE_FOIL_PROMO_TYPES
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "zzz", "parent_set_code": None,
                                  "name": "Zzz", "set_type": "expansion"}])
    seed_cards([make_card(id="z1", set="zzz", collector_number="1", rarity="rare")])
    with pytest.raises(SelectorParseError):
        selectors.materialize("set:zzz+related missing treatment=preferred")


# ---------- materialize against a seeded DB ----------

def test_materialize_owned_filters_to_inventory(tmp_db, seed_cards, make_card, monkeypatch):
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "tla", "parent_set_code": None,
                                  "name": "Avatar", "set_type": "expansion"}])
    seed_cards([
        make_card(id="a1", set="tla", collector_number="5", rarity="rare"),
        make_card(id="a2", set="tla", collector_number="6", rarity="rare"),
    ])
    from magic_manager import db
    with db.connect() as conn:
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) "
                     "VALUES ('a1','nonfoil',2,'2025-01-01')")
    owned = selectors.materialize("set:tla+related owned")
    sids = {r.scryfall_id for r in owned}
    assert sids == {"a1"}  # only the card actually in inventory
