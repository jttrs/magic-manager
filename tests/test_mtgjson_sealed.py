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
