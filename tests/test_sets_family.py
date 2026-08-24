"""Unit tests for the pure (non-network) helpers in magic_manager.sets.

Deliberately avoids sets.resolve() (hits scryfall.all_sets) — these tests
exercise is_excluded_variant(), the family-graph walkers, and the
ResolvedSet.filtered_codes() dataclass method directly, all confirmed by
running them before asserting.
"""

from __future__ import annotations

from magic_manager import sets


# ---------- is_excluded_variant ----------

def test_japanshowcase_promo_type_is_excluded():
    assert sets.is_excluded_variant({"promo_types": ["japanshowcase"], "border_color": "black"}) is True


def test_prerelease_promo_type_is_excluded():
    assert sets.is_excluded_variant({"promo_types": ["prerelease"], "border_color": "black"}) is True


def test_white_border_is_excluded():
    assert sets.is_excluded_variant({"promo_types": [], "border_color": "white"}) is True


def test_plain_card_is_not_excluded():
    assert sets.is_excluded_variant({"promo_types": [], "border_color": "black"}) is False


def test_boosterfun_promo_type_is_not_excluded():
    # boosterfun alone (no other excluded promo_types/border) is allowed —
    # only the specific set in EXCLUDED_PROMO_TYPES trips exclusion.
    assert sets.is_excluded_variant({"promo_types": ["boosterfun"], "border_color": "black"}) is False


# ---------- family-graph walkers ----------

def _fake_all_sets():
    return [
        {"code": "fin", "parent_set_code": None},
        {"code": "fca", "parent_set_code": "fin"},
        {"code": "fic", "parent_set_code": "fin"},
    ]


def test_descendants_of_returns_children():
    all_sets = _fake_all_sets()
    descendants = sets._descendants_of(all_sets, "fin")
    assert {s["code"] for s in descendants} == {"fca", "fic"}


def test_walk_to_parent_climbs_child_to_root():
    all_sets = _fake_all_sets()
    by_code = {s["code"]: s for s in all_sets}
    parent = sets._walk_to_parent(by_code, by_code["fca"])
    assert parent["code"] == "fin"


def test_walk_to_parent_on_root_is_noop():
    all_sets = _fake_all_sets()
    by_code = {s["code"]: s for s in all_sets}
    parent = sets._walk_to_parent(by_code, by_code["fin"])
    assert parent["code"] == "fin"


# ---------- ResolvedSet.filtered_codes ----------

def test_filtered_codes_includes_anchor_and_eternal_excludes_token():
    rs = sets.ResolvedSet(
        code="x",
        name="X",
        related=[
            {"code": "x", "set_type": "expansion"},
            {"code": "xc", "set_type": "eternal"},
            {"code": "xt", "set_type": "token"},
        ],
    )
    codes = rs.filtered_codes()
    assert "x" in codes
    assert "xc" in codes
    assert "xt" not in codes


def test_filtered_codes_include_kinds_pulls_in_token():
    rs = sets.ResolvedSet(
        code="x",
        name="X",
        related=[
            {"code": "x", "set_type": "expansion"},
            {"code": "xt", "set_type": "token"},
        ],
    )
    assert rs.filtered_codes(include_kinds={"token"}) == ["x", "xt"]
