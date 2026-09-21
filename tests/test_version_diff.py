"""Tests for decks.version_diff — comparing two SCD-2 snapshots of a deck.

Keyed on (scryfall_id, board, finish): a count change is "changed"; moving the
same card to a different board is a remove (old board) + add (new board),
since the key includes board.
"""

from __future__ import annotations


def test_version_diff_added_removed_changed_unchanged(tmp_db, seed_cards, make_card):
    from magic_manager import decks
    seed_cards([
        make_card(id="a1", set="tst", collector_number="1", name="Alpha"),
        make_card(id="a2", set="tst", collector_number="2", name="Bravo"),
        make_card(id="a3", set="tst", collector_number="3", name="Charlie"),
        make_card(id="a4", set="tst", collector_number="4", name="Delta"),
    ])
    decks.deck_create("difftest", "Diff Test")
    # v1: a1 x2 (main), a2 x1 (main), a3 x1 (side)
    decks.deck_add_card("difftest", "a1", "main", "nonfoil", 2)
    decks.deck_add_card("difftest", "a2", "main", "nonfoil", 1)
    decks.deck_add_card("difftest", "a3", "side", "nonfoil", 1)

    decks.new_draft_from_current("difftest")
    # v2: bump a1 to 3x (changed), remove a2 (removed), keep a3 unchanged,
    # add a4 (added), and move a3... wait a3 stays on side unchanged; test
    # board-move separately below with a4.
    decks.deck_set_card("difftest", "a1", "main", "nonfoil", 3)
    decks.deck_remove_card("difftest", "a2", "main", "nonfoil")
    decks.deck_add_card("difftest", "a4", "main", "nonfoil", 1)

    diff = decks.version_diff("difftest", 1, 2)

    added_sids = {r["scryfall_id"] for r in diff["added"]}
    removed_sids = {r["scryfall_id"] for r in diff["removed"]}
    changed_sids = {r["scryfall_id"] for r in diff["changed"]}

    assert added_sids == {"a4"}
    assert removed_sids == {"a2"}
    assert changed_sids == {"a1"}
    # a3 (side, unchanged) is the one unchanged row.
    assert diff["unchanged_count"] == 1

    changed_a1 = next(r for r in diff["changed"] if r["scryfall_id"] == "a1")
    assert changed_a1["count_a"] == 2
    assert changed_a1["count_b"] == 3
    assert changed_a1["board"] == "main"
    assert changed_a1["finish"] == "nonfoil"
    assert changed_a1["name"] == "Alpha"

    added_a4 = next(r for r in diff["added"] if r["scryfall_id"] == "a4")
    assert added_a4["count"] == 1
    assert added_a4["name"] == "Delta"

    removed_a2 = next(r for r in diff["removed"] if r["scryfall_id"] == "a2")
    assert removed_a2["count"] == 1
    assert removed_a2["name"] == "Bravo"


def test_version_diff_board_move_is_remove_plus_add(tmp_db, seed_cards, make_card):
    """The same card moved main -> side is a removed (main) + added (side)
    pair, because the diff key includes board."""
    from magic_manager import decks
    seed_cards([make_card(id="m1", set="tst", collector_number="1", name="Mover")])
    decks.deck_create("movetest", "Move Test")
    decks.deck_add_card("movetest", "m1", "main", "nonfoil", 1)

    decks.new_draft_from_current("movetest")
    decks.deck_remove_card("movetest", "m1", "main", "nonfoil")
    decks.deck_add_card("movetest", "m1", "side", "nonfoil", 1)

    diff = decks.version_diff("movetest", 1, 2)
    assert diff["changed"] == []
    assert diff["unchanged_count"] == 0

    removed = diff["removed"]
    added = diff["added"]
    assert len(removed) == 1 and removed[0]["board"] == "main"
    assert len(added) == 1 and added[0]["board"] == "side"
    assert removed[0]["scryfall_id"] == "m1"
    assert added[0]["scryfall_id"] == "m1"
