"""Shared pytest fixtures for the magic-manager suite.

The whole suite is offline + deterministic:
  - `tmp_db` points the app at a throwaway SQLite file via the MAGIC_MANAGER_DB
    env seam (db.py:34-44); schema auto-creates on first connect().
  - `fake_scryfall` / `fake_mtgjson` monkeypatch the semantic network boundaries
    (scryfall.search/collection/all_sets, mtgjson.deck) so no bash wrapper or
    HTTP is ever touched.
  - `make_card` builds raw-Scryfall-API-shaped dicts (the shape db.upsert_card /
    scryfall.search return), so seeding goes through the real projection code.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


# ---------- throwaway DB ----------

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Redirect the entire app DB to a temp file for one test.

    Mirrors scripts/rehearse_migration.py: set MAGIC_MANAGER_DB, let the schema
    build itself on first connect(). Any module reading db_path()/db_dir() at
    call time (not import time) picks this up.
    """
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(db_file))
    # Import after env is set so nothing caches the old path.
    from magic_manager import db
    with db.connect():  # force schema creation
        pass
    return db_file


# ---------- card fixtures (raw Scryfall API shape) ----------

def _make_card(**overrides) -> dict:
    """A raw-Scryfall-API-shaped card dict (what scryfall.search yields and
    db.upsert_card consumes). Override any field per test."""
    card = {
        "id": overrides.pop("id", "00000000-0000-0000-0000-000000000001"),
        "oracle_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "name": "Test Card",
        "set": "tst",
        "collector_number": "1",
        "rarity": "rare",
        "mana_cost": "{1}{G}",
        "cmc": 2.0,
        "type_line": "Creature — Test",
        "colors": ["G"],
        "color_identity": ["G"],
        "prices": {"usd": "1.00", "usd_foil": "2.00"},
        "released_at": "2025-01-01",
        "image_uris": {"normal": "https://example.test/x.jpg"},
        "scryfall_uri": "https://scryfall.com/card/tst/1/test-card",
        "promo": False,
        "layout": "normal",
        "frame_effects": [],
        "finishes": ["nonfoil", "foil"],
        "oracle_text": "",
        "flavor_name": None,
        "promo_types": [],
        "border_color": "black",
        "full_art": False,
        "security_stamp": None,
    }
    card.update(overrides)
    return card


@pytest.fixture
def make_card():
    """Factory fixture: `make_card(name=..., set=..., promo_types=[...])`."""
    return _make_card


@pytest.fixture
def seed_cards(tmp_db):
    """Insert given raw-API card dicts into the tmp DB's cards table.

    Usage: `seed_cards([make_card(id="x", set="ncc", collector_number="5")])`.
    Returns the count inserted.
    """
    from magic_manager import db

    def _seed(cards: list[dict]) -> int:
        with db.connect() as conn:
            return db.upsert_cards(conn, cards)

    return _seed


# ---------- network fakes ----------

@pytest.fixture
def fake_scryfall(monkeypatch):
    """Stub scryfall.search/collection/all_sets with in-memory data.

    Call the returned `configure(...)` to set what the fakes return:
      configure(search=[card,...], collection_found=[card,...], all_sets=[set,...])
    search() is what sets.sync() iterates, so this drives sync in tests.
    """
    from magic_manager import scryfall

    state = {"search": [], "collection_found": [], "collection_not_found": [], "all_sets": []}

    def configure(*, search=None, collection_found=None, collection_not_found=None, all_sets=None):
        if search is not None:
            state["search"] = search
        if collection_found is not None:
            state["collection_found"] = collection_found
        if collection_not_found is not None:
            state["collection_not_found"] = collection_not_found
        if all_sets is not None:
            state["all_sets"] = all_sets

    monkeypatch.setattr(scryfall, "search", lambda *a, **k: iter(list(state["search"])))
    monkeypatch.setattr(
        scryfall, "collection",
        lambda ids: (list(state["collection_found"]), list(state["collection_not_found"])),
    )
    monkeypatch.setattr(scryfall, "all_sets", lambda: list(state["all_sets"]))
    return configure


@pytest.fixture
def fake_mtgjson(monkeypatch):
    """Stub mtgjson.deck to return a canned precon deck dict.

    Call configure(deck={...}) with an MTGJSON-shaped deck (commander/mainBoard
    lists of entries carrying identifiers.scryfallId).
    """
    from magic_manager import mtgjson

    state = {"deck": {}}

    def configure(*, deck=None):
        if deck is not None:
            state["deck"] = deck

    monkeypatch.setattr(mtgjson, "deck", lambda file_name: dict(state["deck"]))
    return configure


def _make_precon_deck(name: str, deck_type: str, entries: list[dict]) -> dict:
    """Build an MTGJSON-shaped deck dict. Each entry: {sid, name, count, board, foil}."""
    boards: dict[str, list] = {}
    for e in entries:
        board_key = e.get("board", "mainBoard")
        boards.setdefault(board_key, []).append({
            "name": e.get("name", "Card"),
            "count": e.get("count", 1),
            "isFoil": e.get("foil", False),
            "setCode": e.get("set", "TST"),
            "number": e.get("cn", "1"),
            "identifiers": {"scryfallId": e["sid"]},
        })
    return {"name": name, "type": deck_type, **boards}


@pytest.fixture
def make_precon_deck():
    """Factory fixture: build an MTGJSON-shaped deck dict for fake_mtgjson."""
    return _make_precon_deck
