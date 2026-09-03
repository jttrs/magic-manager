"""Tests for the Jumpstart buildable-set target math (2026-09-03).

Pins the two rules the shopping list depends on:
  - within a theme: MAX count per scryfall_id across the theme's versions,
  - across themes:  SUM of each theme's target.
Plus theme-name normalization. Pure-function tests — no DB/network needed
(build_target takes a plain {variant_name: {sid: count}} mapping).
"""

import sys
from pathlib import Path

# The script lives in scripts/, not the package — add it to the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from jumpstart_buildable import build_target, theme_of  # noqa: E402


def test_theme_of_strips_version_suffix():
    assert theme_of("Angels (1)") == "Angels"
    assert theme_of("Angels (12)") == "Angels"
    assert theme_of("Dinner") == "Dinner"                 # no suffix
    assert theme_of("Grave Robbers (3)") == "Grave Robbers"
    assert theme_of("Of the Coast (2)") == "Of the Coast"


def test_max_within_theme():
    """Two versions of one theme → per-sid MAX across versions."""
    boards = {
        "Angels (1)": {"a": 1, "shared": 1, "b": 2},
        "Angels (2)": {"c": 1, "shared": 1, "b": 1},
    }
    # single theme → target == its per-sid max
    assert build_target(boards) == {"a": 1, "b": 2, "c": 1, "shared": 1}


def test_sum_across_themes():
    """A card shared by 2 DISTINCT themes sums (both built at once)."""
    boards = {
        "Angels (1)": {"removal": 1, "angel_only": 1},
        "Elves (1)":  {"removal": 1, "elf_only": 1},
    }
    t = build_target(boards)
    assert t["removal"] == 2          # one per coexisting built theme
    assert t["angel_only"] == 1
    assert t["elf_only"] == 1


def test_combined_max_then_sum():
    """Max within each theme, then sum across themes."""
    boards = {
        # Angels: shared peaks at 2 (in v2)
        "Angels (1)": {"shared": 1},
        "Angels (2)": {"shared": 2},
        # Elves: shared peaks at 3
        "Elves (1)":  {"shared": 3},
    }
    # Angels contributes max(1,2)=2; Elves contributes 3; total 5.
    assert build_target(boards)["shared"] == 5


def test_single_version_theme_is_its_own_counts():
    boards = {"Dinner": {"x": 1, "y": 2}}
    assert build_target(boards) == {"x": 1, "y": 2}


def test_owned_subtraction_semantics():
    """missing = max(0, target - owned) — the caller's rule; verify the shape
    the script relies on holds for a hand example."""
    boards = {
        "Angels (1)": {"a": 1, "b": 2},
        "Elves (1)":  {"a": 1},           # a used by both themes → target 2
    }
    target = build_target(boards)
    assert target == {"a": 2, "b": 2}
    owned = {"a": 1, "b": 2}
    missing = {sid: target[sid] - owned.get(sid, 0)
               for sid in target if target[sid] - owned.get(sid, 0) > 0}
    assert missing == {"a": 1}            # own 1 of 2 a's; b fully covered
