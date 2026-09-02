"""Tests for add-precon's sealed-box resolution (2026-09-02).

`_resolve_precon_filenames` gained a deck-first, box-fallback form: when a
`name_query` matches no single physical precon, it tries
`mtgjson.sealed_product_decks` so a sealed box/bundle (Beginner Box, …) — which
has no decklist of its own — expands to its component decks. These pin:
  - a box name expands to all its component decks (even when those decks are a
    type excluded from `precon_variants`, e.g. Jumpstart),
  - a real single deck still wins (deck-first; box is only the fallback),
  - a matched-but-deckless product (pack-only Bundle) errors clearly,
  - a nonexistent name surfaces the original precon error, not a box error.

Offline: monkeypatch mtgjson.set_file + mtgjson.deck_list (+ deck for the
exact-fileName probe). Mirrors tests/test_mtgjson_sealed.py's fixture style.
"""

import pytest


# FDN-shaped: a Beginner Box whose 3 component decks are type="Jumpstart"
# (so precon_variants, which excludes Jumpstart, never surfaces them), a
# pack-only Bundle (no contents.deck), and one real Box Set precon.
_FDN_SEALED = [
    {
        "name": "Foundations Beginner Box",
        "category": "box_set",
        "contents": {
            "deck": [
                {"name": "Cats", "set": "fdn"},
                {"name": "Elves", "set": "fdn"},
                {"name": "Goblins", "set": "fdn"},
            ],
        },
    },
    {
        "name": "Foundations Bundle",
        "category": "bundle",
        "contents": {"sealed": [{"name": "Play Booster", "count": 9}]},
    },
]

_FDN_DECKLIST = [
    {"code": "FDN", "fileName": "Cats_FDN", "name": "Cats", "type": "Jumpstart"},
    {"code": "FDN", "fileName": "Elves_FDN", "name": "Elves", "type": "Jumpstart"},
    {"code": "FDN", "fileName": "Goblins_FDN", "name": "Goblins", "type": "Jumpstart"},
    {"code": "FDN", "fileName": "StarterCollection_FDN", "name": "Starter Collection", "type": "Box Set"},
]


def _patch(monkeypatch):
    from magic_manager import mtgjson
    monkeypatch.setattr(mtgjson, "set_file",
                        lambda code: {"sealedProduct": list(_FDN_SEALED)} if code.lower() == "fdn" else {})
    monkeypatch.setattr(mtgjson, "deck_list",
                        lambda *, set_code=None: [d for d in _FDN_DECKLIST
                                                  if set_code is None or d["code"] == set_code.upper()])

    # The exact-fileName probe calls deck(target); make it fail for our set-code
    # targets (they aren't fileNames) so resolution falls through as intended.
    def _fake_deck(fn):
        raise mtgjson.MtgJsonError(f"no such deck {fn!r}")
    monkeypatch.setattr(mtgjson, "deck", _fake_deck)


def test_beginner_box_expands_to_component_decks(monkeypatch):
    _patch(monkeypatch)
    from magic_manager.cli import _resolve_precon_filenames as R
    decks = R("fdn", "Foundations Beginner Box",
              want_all=False, only_type=None, include_collector=False)
    assert sorted(d["fileName"] for d in decks) == ["Cats_FDN", "Elves_FDN", "Goblins_FDN"]


def test_box_substring_name_resolves(monkeypatch):
    _patch(monkeypatch)
    from magic_manager.cli import _resolve_precon_filenames as R
    decks = R("fdn", "beginner box",
              want_all=False, only_type=None, include_collector=False)
    assert len(decks) == 3


def test_single_deck_wins_over_box_fallback(monkeypatch):
    """A real physical precon by name resolves deck-first; the box fallback
    never runs. 'Starter Collection' is a Box Set precon in the DeckList."""
    _patch(monkeypatch)
    from magic_manager.cli import _resolve_precon_filenames as R
    decks = R("fdn", "Starter Collection",
              want_all=False, only_type=None, include_collector=False)
    assert [d["fileName"] for d in decks] == ["StarterCollection_FDN"]


def test_pack_only_bundle_errors_clearly(monkeypatch):
    _patch(monkeypatch)
    from magic_manager.cli import _resolve_precon_filenames as R
    with pytest.raises(LookupError, match="no component decks to add"):
        R("fdn", "Foundations Bundle",
          want_all=False, only_type=None, include_collector=False)


def test_nonexistent_name_surfaces_precon_error(monkeypatch):
    """No deck AND no sealed product → the original precon LookupError (which
    lists candidate decks), not a sealed-box error."""
    _patch(monkeypatch)
    from magic_manager.cli import _resolve_precon_filenames as R
    with pytest.raises(LookupError, match="matched name"):
        R("fdn", "Totally Fake Nonsense",
          want_all=False, only_type=None, include_collector=False)
