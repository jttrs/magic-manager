"""Regression tests for the import-precon atomicity + sync bug (2026-08-24).

Bug: `import_precon` ran deck_create / deck_add_card / inventory_add in SEPARATE
transactions and never synced the family first. On an unsynced family the
deck_cards insert hit a FK violation AFTER the deck row had already committed —
leaving an orphan empty deck that made the retry fail with "slug already exists".

These tests are written to FAIL on the pre-fix code and PASS after Phase 1.
"""

import pytest


def _deck_count(db):
    with db.connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM decks").fetchone()[0]


def test_import_precon_autosyncs_unsynced_family(tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """Happy path: family not synced → import syncs it, then populates deck+inventory."""
    from magic_manager import decks, db

    # The precon references two cards; the family is NOT pre-seeded.
    sids = ["ncc-sid-1", "ncc-sid-2"]
    deck = make_precon_deck(
        "Bedecked Brokers", "Commander Deck",
        [{"sid": sids[0], "name": "A", "set": "ncc", "cn": "1", "count": 1, "board": "commander"},
         {"sid": sids[1], "name": "B", "set": "ncc", "cn": "2", "count": 99, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    # sync() will pull these via scryfall.search — this is the auto-sync the fix adds.
    fake_scryfall(search=[
        make_card(id=sids[0], set="ncc", collector_number="1", name="A"),
        make_card(id=sids[1], set="ncc", collector_number="2", name="B"),
    ])

    result = decks.import_precon("BedeckedBrokers_NCC")

    assert result["effective_slugs"] == ["bedecked-brokers"]
    assert result["deck_card_qty"] == 100
    # cards got synced as a side effect
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM cards WHERE set_code='ncc'").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0] == 2


def test_import_precon_no_orphan_on_failure(tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """If a card genuinely can't be resolved (sync yields nothing for it), the
    import must fail atomically — NO orphan deck row left behind."""
    from magic_manager import decks

    deck = make_precon_deck(
        "Cabaretti Cacophony", "Commander Deck",
        [{"sid": "missing-sid-X", "name": "Ghost", "set": "ncc", "cn": "9", "count": 1, "board": "commander"}],
    )
    fake_mtgjson(deck=deck)
    # sync returns NOTHING for this family → the referenced sid never lands in cards
    # → deck_cards insert must FK-fail → whole import must roll back.
    fake_scryfall(search=[])

    with pytest.raises(Exception):
        decks.import_precon("CabarettiCacophony_NCC")

    from magic_manager import db
    assert _deck_count(db) == 0, "orphan deck shell left behind after failed import"


def test_import_precon_retry_after_failure_succeeds(tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """After a failed import leaves no orphan, a corrected retry must succeed
    (the exact recovery that required manual `deck delete` before the fix)."""
    from magic_manager import decks, db

    deck = make_precon_deck(
        "Maestros Massacre", "Commander Deck",
        [{"sid": "mm-sid-1", "name": "Boss", "set": "ncc", "cn": "3", "count": 1, "board": "commander"}],
    )
    fake_mtgjson(deck=deck)

    # First attempt: sync yields nothing → fails.
    fake_scryfall(search=[])
    with pytest.raises(Exception):
        decks.import_precon("MaestrosMassacre_NCC")
    assert _deck_count(db) == 0

    # Retry: now the card resolves → clean success, no "slug already exists".
    fake_scryfall(search=[make_card(id="mm-sid-1", set="ncc", collector_number="3", name="Boss")])
    result = decks.import_precon("MaestrosMassacre_NCC")
    assert result["effective_slugs"] == ["maestros-massacre"]
    assert _deck_count(db) == 1
