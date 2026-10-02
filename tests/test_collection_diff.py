"""Phase 1 — direction-agnostic diff (generalized from decks.version_diff).

Pure in-memory: diff_collections over CollectionRow lists; no DB, no network
(the inventory-landing default is exercised in test_collection_apply.py).
"""

from __future__ import annotations

from magic_manager import collection_sync as cs


def _row(sid, finish, qty, *, set="c21", cn="1", name="X"):
    return cs.CollectionRow(qty=qty, finish=finish, scryfall_id=sid,
                            set=set, collector_number=cn, name=name)


def test_diff_added_removed_changed_unchanged():
    incoming = [
        _row("a", "nonfoil", 2, cn="1", name="Added"),      # not in landing → added
        _row("b", "nonfoil", 5, cn="2", name="Changed"),    # qty differs → changed
        _row("c", "foil", 1, cn="3", name="Same"),          # identical → unchanged
    ]
    landing = [
        _row("b", "nonfoil", 3, cn="2", name="Changed"),
        _row("c", "foil", 1, cn="3", name="Same"),
        _row("d", "nonfoil", 4, cn="4", name="Removed"),    # not in incoming → removed
    ]
    diff = cs.diff_collections(incoming, landing)
    assert {r["name"] for r in diff["added"]} == {"Added"}
    assert {r["name"] for r in diff["removed"]} == {"Removed"}
    assert len(diff["changed"]) == 1
    chg = diff["changed"][0]
    assert chg["name"] == "Changed"
    assert chg["qty_landing"] == 3 and chg["qty_incoming"] == 5
    assert diff["unchanged_count"] == 1


def test_diff_finish_is_part_of_the_key():
    # Same card, different finish = two distinct keys (not a "changed").
    incoming = [_row("a", "foil", 1)]
    landing = [_row("a", "nonfoil", 1)]
    diff = cs.diff_collections(incoming, landing)
    assert len(diff["added"]) == 1 and diff["added"][0]["finish"] == "foil"
    assert len(diff["removed"]) == 1 and diff["removed"][0]["finish"] == "nonfoil"
    assert not diff["changed"]


def test_diff_set_cn_key_mode_when_no_ids():
    # Rows without scryfall_id diff on (set, cn, finish).
    incoming = [cs.CollectionRow(qty=2, finish="nonfoil", set="c21", collector_number="263", name="SR")]
    landing = [cs.CollectionRow(qty=1, finish="nonfoil", set="c21", collector_number="263", name="SR")]
    diff = cs.diff_collections(incoming, landing, key="set_cn")
    assert len(diff["changed"]) == 1
    assert diff["changed"][0]["qty_landing"] == 1
    assert diff["changed"][0]["qty_incoming"] == 2


def test_diff_direction_symmetry():
    # Swapping incoming/landing swaps added<->removed (export is import reversed).
    a = [_row("a", "nonfoil", 1, name="OnlyA")]
    b = [_row("b", "nonfoil", 1, name="OnlyB")]
    fwd = cs.diff_collections(a, b)
    rev = cs.diff_collections(b, a)
    assert {r["name"] for r in fwd["added"]} == {"OnlyA"}
    assert {r["name"] for r in fwd["removed"]} == {"OnlyB"}
    assert {r["name"] for r in rev["added"]} == {"OnlyB"}
    assert {r["name"] for r in rev["removed"]} == {"OnlyA"}


def test_diff_aggregates_duplicate_rows():
    # Two CSV lines for the same printing+finish sum before diffing.
    incoming = [_row("a", "nonfoil", 1), _row("a", "nonfoil", 2)]
    diff = cs.diff_collections(incoming, [])
    assert len(diff["added"]) == 1
    assert diff["added"][0]["qty_incoming"] == 3


def test_diff_summary_line():
    diff = cs.diff_collections([_row("a", "nonfoil", 1)], [])
    assert cs.diff_summary_line(diff) == "1 added, 0 changed, 0 removed, 0 unchanged"
