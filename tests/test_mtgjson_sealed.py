"""Tests for mtgjson.sealed_products / sealed_product_decks (2026-08-31).

The lesson these pin: a product's component decks live in
``sealedProduct[].contents.deck``, and membership is INDEPENDENT of a deck's
``type`` field. The regression that motivated them: the Foundations Beginner
Box's 10 decks are typed ``"Jumpstart"`` in the DeckList, so filtering DeckList
by ``type`` never finds them — only ``sealedProduct`` does.

Offline: monkeypatch ``mtgjson.set_file`` + ``mtgjson.deck_list`` directly.
"""


# A minimal FDN-shaped set file: one Beginner Box SKU whose contents.deck names
# decks that (deliberately) carry type="Jumpstart" in the DeckList below.
_FDN_SEALED = [
    {
        "name": "Foundations Beginner Box",
        "category": "box_set",
        "subtype": "starter_deck",
        "cardCount": 200,
        "contents": {
            "deck": [
                {"name": "Cats", "set": "fdn"},
                {"name": "Elves", "set": "fdn"},
                {"name": "Goblins", "set": "fdn"},
            ],
            "other": [{"name": "2 Gameboard playmats"}],
        },
    },
    {
        "name": "Foundations Bundle",
        "category": "bundle",
        "subtype": "default",
        "contents": {"sealed": [{"name": "Play Booster", "count": 9}]},
    },
]

# DeckList entries — note type="Jumpstart" for the Beginner Box's decks.
_FDN_DECKLIST = [
    {"code": "FDN", "fileName": "Cats_FDN", "name": "Cats", "releaseDate": "2024-11-15", "type": "Jumpstart"},
    {"code": "FDN", "fileName": "Elves_FDN", "name": "Elves", "releaseDate": "2024-11-15", "type": "Jumpstart"},
    {"code": "FDN", "fileName": "Goblins_FDN", "name": "Goblins", "releaseDate": "2024-11-15", "type": "Jumpstart"},
    {"code": "FDN", "fileName": "StarterCollection_FDN", "name": "Starter Collection", "releaseDate": "2024-11-15", "type": "Box Set"},
]


def _patch(monkeypatch):
    from magic_manager import mtgjson
    monkeypatch.setattr(mtgjson, "set_file",
                        lambda code: {"sealedProduct": list(_FDN_SEALED)} if code.lower() == "fdn" else {})
    monkeypatch.setattr(mtgjson, "deck_list",
                        lambda *, set_code=None: [d for d in _FDN_DECKLIST
                                                  if set_code is None or d["code"] == set_code.upper()])


def test_sealed_products_lists_and_filters(monkeypatch):
    from magic_manager import mtgjson
    _patch(monkeypatch)

    allp = mtgjson.sealed_products("fdn")
    assert {p["name"] for p in allp} == {"Foundations Beginner Box", "Foundations Bundle"}

    # category filter (case-insensitive) narrows to the box set.
    boxes = mtgjson.sealed_products("fdn", category="Box_Set")
    assert [p["name"] for p in boxes] == ["Foundations Beginner Box"]

    # subtype filter too.
    starters = mtgjson.sealed_products("fdn", subtype="starter_deck")
    assert [p["name"] for p in starters] == ["Foundations Beginner Box"]

    # a set with no sealed data → [].
    assert mtgjson.sealed_products("zzz") == []


def test_sealed_product_decks_resolves_despite_type_mismatch(monkeypatch):
    """The core regression: the Beginner Box's decks are type='Jumpstart', but
    membership resolves via contents.deck, so we still get all three."""
    from magic_manager import mtgjson
    _patch(monkeypatch)

    decks = mtgjson.sealed_product_decks("fdn", "Foundations Beginner Box")
    assert [d["fileName"] for d in decks] == ["Cats_FDN", "Elves_FDN", "Goblins_FDN"]
    # Every resolved deck is typed Jumpstart — proving type != product membership.
    assert all(d["type"] == "Jumpstart" for d in decks)


def test_sealed_product_decks_substring_match(monkeypatch):
    from magic_manager import mtgjson
    _patch(monkeypatch)
    # A unique substring resolves without the exact SKU name.
    decks = mtgjson.sealed_product_decks("fdn", "beginner box")
    assert [d["fileName"] for d in decks] == ["Cats_FDN", "Elves_FDN", "Goblins_FDN"]


def test_sealed_product_decks_unknown_raises(monkeypatch):
    import pytest
    from magic_manager import mtgjson
    _patch(monkeypatch)
    with pytest.raises(LookupError):
        mtgjson.sealed_product_decks("fdn", "Nonexistent Product")


def test_sealed_product_decks_no_deck_contents(monkeypatch):
    """A product whose contents has no deck[] (e.g. the Bundle) returns []."""
    from magic_manager import mtgjson
    _patch(monkeypatch)
    assert mtgjson.sealed_product_decks("fdn", "Foundations Bundle") == []


# ---------- sealed_product_deck_refs — completeness reporting ----------

def test_deck_refs_full_resolution(monkeypatch):
    from magic_manager import mtgjson
    _patch(monkeypatch)
    r = mtgjson.sealed_product_deck_refs("fdn", "Foundations Beginner Box")
    assert [d["fileName"] for d in r["resolved"]] == ["Cats_FDN", "Elves_FDN", "Goblins_FDN"]
    assert r["unresolved"] == []
    assert r["has_deck_contents"] is True


def test_deck_refs_partial_resolution(monkeypatch):
    """A contents.deck ref with no matching DeckList entry is reported as
    unresolved, NOT silently dropped — the fix for the silent-partial finding."""
    from magic_manager import mtgjson
    # Beginner Box with a 4th component that isn't in the DeckList.
    sealed = [{
        "name": "Foundations Beginner Box",
        "category": "box_set",
        "contents": {"deck": [
            {"name": "Cats", "set": "fdn"},
            {"name": "Elves", "set": "fdn"},
            {"name": "Goblins", "set": "fdn"},
            {"name": "Phantom", "set": "fdn"},   # no DeckList entry
        ]},
    }]
    monkeypatch.setattr(mtgjson, "set_file",
                        lambda code: {"sealedProduct": sealed} if code.lower() == "fdn" else {})
    monkeypatch.setattr(mtgjson, "deck_list",
                        lambda *, set_code=None: [d for d in _FDN_DECKLIST
                                                  if set_code is None or d["code"] == set_code.upper()])
    r = mtgjson.sealed_product_deck_refs("fdn", "Foundations Beginner Box")
    assert [d["fileName"] for d in r["resolved"]] == ["Cats_FDN", "Elves_FDN", "Goblins_FDN"]
    assert [ref["name"] for ref in r["unresolved"]] == ["Phantom"]
    assert r["has_deck_contents"] is True


def test_deck_refs_deckless_vs_unresolved_distinguishable(monkeypatch):
    """The two empty-cases the CLI must tell apart: a deckless product has
    has_deck_contents=False; a fully-unresolved box has it True with resolved=[]."""
    from magic_manager import mtgjson
    _patch(monkeypatch)
    # Deckless: the Bundle (no contents.deck).
    bundle = mtgjson.sealed_product_deck_refs("fdn", "Foundations Bundle")
    assert bundle["has_deck_contents"] is False
    assert bundle["resolved"] == [] and bundle["unresolved"] == []

    # Fully-unresolved: contents.deck present, but the DeckList is empty.
    monkeypatch.setattr(mtgjson, "deck_list", lambda *, set_code=None: [])
    box = mtgjson.sealed_product_deck_refs("fdn", "Foundations Beginner Box")
    assert box["has_deck_contents"] is True
    assert box["resolved"] == []
    assert len(box["unresolved"]) == 3


# ---------- default_precon_state classifier (V11) ----------

def _patch_deck(monkeypatch, name, cards):
    """Stub mtgjson.deck to return a deck with `cards` mainBoard entries."""
    from magic_manager import mtgjson
    mb = [{"name": f"c{i}", "count": 1, "identifiers": {"scryfallId": f"s{i}"}}
          for i in range(cards)]
    monkeypatch.setattr(mtgjson, "deck", lambda fn: {"name": name, "mainBoard": mb})


def test_default_precon_state_pool_by_name(monkeypatch):
    from magic_manager import mtgjson
    # Small card count, but the name matches POOL_NAME_PATTERNS.
    _patch_deck(monkeypatch, "Starter Collection", cards=10)
    assert mtgjson.default_precon_state("StarterCollection_FDN") == "pool"


def test_default_precon_state_pool_by_card_count(monkeypatch):
    from magic_manager import mtgjson
    # Name doesn't match, but 387 cards > threshold → pool.
    _patch_deck(monkeypatch, "Some Big Thing", cards=387)
    assert mtgjson.default_precon_state("SomeBigThing_XYZ") == "pool"


def test_default_precon_state_built_default(monkeypatch):
    from magic_manager import mtgjson
    _patch_deck(monkeypatch, "Counter Blitz", cards=100)
    assert mtgjson.default_precon_state("CounterBlitz_FIC") == "built"


def test_default_precon_state_pool_via_sealedproduct(monkeypatch):
    """A Scene Box's component deck (small, plainly-named) is a pool because it's
    listed in a pool-named sealedProduct's contents.deck."""
    from magic_manager import mtgjson
    _patch_deck(monkeypatch, "The Black Sun Invasion", cards=6)
    monkeypatch.setattr(mtgjson, "sealed_products", lambda code, **k: [
        {"name": "Avatar The Last Airbender Scene Box The Black Sun Invasion",
         "contents": {"deck": [{"name": "The Black Sun Invasion", "set": "tla"}]}},
    ])
    assert mtgjson.default_precon_state("TheBlackSunInvasion_TLA") == "pool"


# ---------- V11 migration backfill ----------

def test_v11_backfill_maps_is_deconstructed(tmp_path, monkeypatch):
    """A pre-V11 deck row with is_deconstructed=1 backfills to precon_state
    'deconstructed'; 0 → 'built'."""
    import sqlite3
    from magic_manager import db
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(tmp_path / "mm.db"))
    # First connect creates the schema at CURRENT_VERSION (V11 already applied),
    # so the column exists; seed rows in each state and confirm the query buckets.
    with db.connect() as conn:
        now = db._utcnow_iso()
        for slug, state in (("a", "built"), ("b", "deconstructed"), ("c", "pool")):
            conn.execute(
                "INSERT INTO decks (slug, name, source_precon_file_name, precon_state, "
                "created_at, updated_at) VALUES (?, ?, 'FN_X', ?, ?, ?)",
                (slug, slug, state, now, now),
            )
    from magic_manager import decks
    assert decks.precon_unit_counts_for("FN_X") == (1, 1, 1)
