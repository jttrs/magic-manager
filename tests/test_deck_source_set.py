"""Tests for the precon→set hard link (SCHEMA_V6 decks.source_set_code)."""

from __future__ import annotations


def test_migration_adds_source_set_code_column(tmp_db):
    from magic_manager import db
    with db.connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(decks)").fetchall()}
    assert "source_set_code" in cols


def test_import_precon_records_source_set(tmp_db, fake_scryfall, fake_mtgjson,
                                          make_card, make_precon_deck):
    from magic_manager import decks, db
    deck = make_precon_deck(
        "Bedecked Brokers", "Commander Deck",
        [{"sid": "b1", "name": "Cmdr", "set": "ncc", "cn": "1", "count": 1, "board": "commander"}],
    )
    # MTGJSON deck dict must carry the source set code
    deck["code"] = "NCC"
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[make_card(id="b1", set="ncc", collector_number="1", name="Cmdr")])

    decks.import_precon("BedeckedBrokers_NCC")
    with db.connect() as conn:
        row = conn.execute(
            "SELECT source_set_code FROM decks WHERE slug='bedecked-brokers'"
        ).fetchone()
    assert row["source_set_code"] == "ncc"


def test_deck_create_defaults_null_source(tmp_db):
    from magic_manager import decks, db
    decks.deck_create("handmade", "Handmade Deck")
    with db.connect() as conn:
        row = conn.execute(
            "SELECT source_set_code FROM decks WHERE slug='handmade'"
        ).fetchone()
    assert row["source_set_code"] is None


def test_backfill_sets_dominant_set(tmp_db, seed_cards, make_card):
    from magic_manager import decks, db
    seed_cards([
        make_card(id="d1", set="ncc", collector_number="1"),
        make_card(id="d2", set="ncc", collector_number="2"),
        make_card(id="d3", set="snc", collector_number="3"),  # minority set
    ])
    # a NULL-source deck with 2 ncc + 1 snc → dominant is ncc
    decks.deck_create("legacy-deck", "Legacy")
    decks.deck_add_card("legacy-deck", "d1", "main", "nonfoil", 1)
    decks.deck_add_card("legacy-deck", "d2", "main", "nonfoil", 1)
    decks.deck_add_card("legacy-deck", "d3", "main", "nonfoil", 1)

    n = decks.backfill_source_set_codes()
    assert n == 1
    with db.connect() as conn:
        row = conn.execute(
            "SELECT source_set_code FROM decks WHERE slug='legacy-deck'"
        ).fetchone()
    assert row["source_set_code"] == "ncc"

    # idempotent: second run touches nothing
    assert decks.backfill_source_set_codes() == 0
