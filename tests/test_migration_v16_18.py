"""Migration correctness for V16 (cards.legalities/keywords/game_changer),
V17 (deck_versions + decks.current_version_id) and V18 (deck_cards
re-homed onto deck_version_id).

Builds a pre-V16 DB by hand (raw sqlite3, applying MIGRATIONS[:15] — i.e.
V1..V15 — directly, mirroring db._ensure_schema's own bootstrap loop), seeds a
deck with the OLD deck_cards shape (deck_id column, no deck_versions table
yet), stamps schema_version=15, then opens it via db.connect() — which
triggers the V16/V17/V18 migrations (and the V17 python hook) in one pass.
"""

from __future__ import annotations

import sqlite3


def _build_pre_v16_db(db_file, db_mod) -> None:
    """Apply MIGRATIONS[0..14] (V1..V15) to a fresh sqlite file, seed one deck
    with 2 deck_cards rows in the OLD (deck_id-keyed) shape, and stamp
    schema_version=15."""
    raw = sqlite3.connect(str(db_file))
    try:
        raw.executescript(db_mod.MIGRATIONS[0])  # V1 (idempotent CREATE)
        for i in range(1, 15):  # V2..V15 (indices 1..14)
            raw.executescript(db_mod.MIGRATIONS[i])
        raw.execute("INSERT INTO schema_version (version) VALUES (15)")

        # Seed two cards (pre-V16: no legalities/keywords/game_changer data).
        raw.execute(
            "INSERT INTO cards (scryfall_id, oracle_id, name, set_code, "
            "collector_number, rarity) VALUES "
            "('pre1', 'o-pre1', 'Pre Card One', 'tst', '1', 'rare')"
        )
        raw.execute(
            "INSERT INTO cards (scryfall_id, oracle_id, name, set_code, "
            "collector_number, rarity) VALUES "
            "('pre2', 'o-pre2', 'Pre Card Two', 'tst', '2', 'common')"
        )

        # Seed a deck (pre-V17: no deck_versions, no current_version_id).
        raw.execute(
            "INSERT INTO decks (slug, name, created_at, updated_at) VALUES "
            "('legacy-deck', 'Legacy Deck', '2020-01-01T00:00:00+00:00', "
            "'2020-01-01T00:00:00+00:00')"
        )
        deck_id = raw.execute(
            "SELECT deck_id FROM decks WHERE slug='legacy-deck'"
        ).fetchone()[0]

        # Seed deck_cards in the OLD shape (deck_id column, not deck_version_id).
        raw.execute(
            "INSERT INTO deck_cards (deck_id, scryfall_id, board, finish, count) "
            "VALUES (?, 'pre1', 'main', 'nonfoil', 2)",
            (deck_id,),
        )
        raw.execute(
            "INSERT INTO deck_cards (deck_id, scryfall_id, board, finish, count) "
            "VALUES (?, 'pre2', 'main', 'nonfoil', 3)",
            (deck_id,),
        )
        raw.commit()
    finally:
        raw.close()


def test_migration_v16_to_v18(tmp_path, monkeypatch):
    from magic_manager import db as db_mod

    db_file = tmp_path / "premigrate.db"
    _build_pre_v16_db(db_file, db_mod)

    monkeypatch.setenv("MAGIC_MANAGER_DB", str(db_file))
    with db_mod.connect():  # triggers V16/V17/V18 + the V17 python hook
        pass

    with db_mod.connect() as conn:
        version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
        assert version == 18

        # V16: cards has the new columns.
        card_cols = {r["name"] for r in conn.execute("PRAGMA table_info(cards)").fetchall()}
        assert {"legalities", "keywords", "game_changer"} <= card_cols

        # V17: every deck got a v1 current version, and it's 'tuned' (existing
        # decks are settled lists per the V17 hook, not fresh brews).
        deck_row = conn.execute(
            "SELECT deck_id, current_version_id FROM decks WHERE slug='legacy-deck'"
        ).fetchone()
        assert deck_row["current_version_id"] is not None
        version_row = conn.execute(
            "SELECT version_number, status, is_current FROM deck_versions "
            "WHERE deck_version_id = ?",
            (deck_row["current_version_id"],),
        ).fetchone()
        assert version_row["version_number"] == 1
        assert version_row["status"] == "tuned"
        assert version_row["is_current"] == 1

        # V18: deck_cards is version-scoped now (deck_id column gone).
        deck_cards_cols = {
            r["name"] for r in conn.execute("PRAGMA table_info(deck_cards)").fetchall()
        }
        assert "deck_version_id" in deck_cards_cols
        assert "deck_id" not in deck_cards_cols

        # Counts preserved, re-homed onto the v1 version.
        rows = conn.execute(
            "SELECT scryfall_id, count FROM deck_cards WHERE deck_version_id = ? "
            "ORDER BY scryfall_id",
            (deck_row["current_version_id"],),
        ).fetchall()
        assert [(r["scryfall_id"], r["count"]) for r in rows] == [
            ("pre1", 2), ("pre2", 3),
        ]

        # No dangling FK references anywhere in the migrated DB.
        fk_problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert fk_problems == []
