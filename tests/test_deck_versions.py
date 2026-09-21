"""Tests for deck SCD-2 versioning (V17/V18): deck_create's auto-v1,
create_version/new_draft_from_current, the exactly-one-current invariant,
finalize's warn-only legality/bracket write, set_status, and version_list.

Offline: tmp_db + seed_cards/make_card (no network needed for these paths —
finalize's Commander Spellbook lookup is skipped via use_spellbook=False).
"""

from __future__ import annotations


def test_deck_create_auto_creates_v1(tmp_db):
    from magic_manager import decks, db
    deck = decks.deck_create("brewtest", "Brew Test")
    assert deck.current_version_id is not None

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM deck_versions WHERE deck_id = ?", (deck.deck_id,)
        ).fetchall()
    assert len(rows) == 1
    v1 = rows[0]
    assert v1["version_number"] == 1
    assert v1["status"] == "brew"
    assert v1["is_current"] == 1
    assert v1["effective_to"] is None
    assert v1["deck_version_id"] == deck.current_version_id


def test_create_version_bumps_and_retires_prior(tmp_db):
    from magic_manager import decks, db
    deck = decks.deck_create("bumptest", "Bump Test")
    v1_id = deck.current_version_id

    v2 = decks.create_version("bumptest", status="brew", change_reason="tweak")
    assert v2.version_number == 2
    assert v2.is_current == 1

    with db.connect() as conn:
        row = conn.execute(
            "SELECT current_version_id FROM decks WHERE slug='bumptest'"
        ).fetchone()
        assert row["current_version_id"] == v2.deck_version_id

        v1_row = conn.execute(
            "SELECT is_current, effective_to FROM deck_versions WHERE deck_version_id = ?",
            (v1_id,),
        ).fetchone()
        assert v1_row["is_current"] == 0
        assert v1_row["effective_to"] is not None


def test_exactly_one_current_invariant(tmp_db):
    from magic_manager import decks, db
    decks.deck_create("invarianttest", "Invariant Test")
    for _ in range(4):
        decks.create_version("invarianttest", status="brew")

    with db.connect() as conn:
        deck_id = conn.execute(
            "SELECT deck_id FROM decks WHERE slug='invarianttest'"
        ).fetchone()["deck_id"]
        n_current = conn.execute(
            "SELECT COUNT(*) FROM deck_versions WHERE deck_id = ? AND is_current = 1",
            (deck_id,),
        ).fetchone()[0]
    assert n_current == 1

    versions = decks.version_list("invarianttest")
    assert len(versions) == 5  # v1 (auto) + 4 created


def test_new_draft_from_current_clones_cards(tmp_db, seed_cards, make_card):
    from magic_manager import decks
    seed_cards([
        make_card(id="d1", set="tst", collector_number="1"),
        make_card(id="d2", set="tst", collector_number="2"),
    ])
    decks.deck_create("clonetest", "Clone Test")
    decks.deck_add_card("clonetest", "d1", "main", "nonfoil", 2)
    decks.deck_add_card("clonetest", "d2", "main", "nonfoil", 3)

    v2 = decks.new_draft_from_current("clonetest", change_reason="tuning pass")
    assert v2.version_number == 2
    assert v2.status == "brew"

    rows = decks.deck_show("clonetest")
    sids = {r.scryfall_id: r.count for r in rows}
    assert sids == {"d1": 2, "d2": 3}


def test_editing_new_version_does_not_mutate_prior_snapshot(tmp_db, seed_cards, make_card):
    from magic_manager import decks
    seed_cards([
        make_card(id="e1", set="tst", collector_number="1"),
        make_card(id="e2", set="tst", collector_number="2"),
    ])
    decks.deck_create("snaptest", "Snapshot Test")
    decks.deck_add_card("snaptest", "e1", "main", "nonfoil", 1)
    v1 = decks.version_get("snaptest", 1)

    decks.new_draft_from_current("snaptest")
    # Mutate the new current version (v2): add a card, remove the original.
    decks.deck_add_card("snaptest", "e2", "main", "nonfoil", 4)
    decks.deck_remove_card("snaptest", "e1", "main", "nonfoil")

    # v1's snapshot is untouched.
    v1_rows = decks.deck_show("snaptest", version_id=v1.deck_version_id)
    v1_sids = {r.scryfall_id: r.count for r in v1_rows}
    assert v1_sids == {"e1": 1}

    # Current (v2) reflects the edits.
    current_rows = decks.deck_show("snaptest")
    current_sids = {r.scryfall_id: r.count for r in current_rows}
    assert current_sids == {"e2": 4}


def test_finalize_warn_only_on_illegal_deck(tmp_db, seed_cards, make_card):
    """A deliberately-illegal small commander deck (wrong size, no commander)
    still finalizes successfully — finalize never raises."""
    from magic_manager import decks
    seed_cards([make_card(id="f1", set="tst", collector_number="1")])
    decks.deck_create("illegaltest", "Illegal Test", format="commander")
    decks.deck_add_card("illegaltest", "f1", "main", "nonfoil", 1)

    result = decks.finalize("illegaltest", use_spellbook=False)
    assert result["status"] == "tuned"
    assert result["legality"]["legal"] is False

    v = decks.version_get("illegaltest", 1)
    assert v.status == "tuned"
    assert v.legality_report is not None


def test_finalize_populates_legality_report(tmp_db, seed_cards, make_card):
    from magic_manager import decks
    seed_cards([make_card(id="g1", set="tst", collector_number="1")])
    decks.deck_create("populatetest", "Populate Test", format="commander")
    decks.deck_add_card("populatetest", "g1", "main", "nonfoil", 1)

    result = decks.finalize("populatetest", use_spellbook=False)
    assert result["slug"] == "populatetest"
    assert result["version_number"] == 1
    assert result["format"] == "commander"
    assert isinstance(result["legality"], dict)

    v = decks.version_get("populatetest", 1)
    import json
    report = json.loads(v.legality_report)
    assert report["format"] == "commander"


def test_set_status_flips_without_validation(tmp_db):
    from magic_manager import decks
    decks.deck_create("statustest", "Status Test")
    v = decks.set_status("statustest", "tuned")
    assert v.status == "tuned"
    # No legality report written — set_status has no validation side effects.
    assert v.legality_report is None


def test_version_list_oldest_first(tmp_db):
    from magic_manager import decks
    decks.deck_create("orderedtest", "Ordered Test")
    decks.create_version("orderedtest", status="brew")
    decks.create_version("orderedtest", status="tuned")

    versions = decks.version_list("orderedtest")
    numbers = [v.version_number for v in versions]
    assert numbers == [1, 2, 3]
