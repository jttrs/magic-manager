"""Unit tests for magic_manager.brackets.suggest — pure-ish, offline (the
optional spellbook client is injected; passing None keeps it fully offline).

Card dicts are hand-built in the shape decks._materialize_for_checks produces:
scryfall_id, oracle_id, name, board, count, type_line, oracle_text,
game_changer (int 0/1), legalities.
"""

from __future__ import annotations

import json

import pytest

from magic_manager import brackets


def _card(name, board, count=1, *, game_changer=0, legalities=None,
          type_line="Creature — Test", oracle_text="",
          scryfall_id=None, oracle_id=None):
    return {
        "scryfall_id": scryfall_id or f"sid-{name}",
        "oracle_id": oracle_id or f"oid-{name}",
        "name": name,
        "board": board,
        "count": count,
        "type_line": type_line,
        "oracle_text": oracle_text,
        "game_changer": game_changer,
        "legalities": legalities if legalities is not None else {"commander": "legal"},
    }


def _commander_deck(extra_main=None):
    cards = [_card("My Commander", "commander", type_line="Legendary Creature — Test")]
    cards += (extra_main or [])
    return cards


def test_no_commander_board_returns_none_bracket():
    cards = [_card(f"Card {i}", "main") for i in range(10)]
    detail = brackets.suggest(cards)
    assert detail.suggested_bracket is None


def test_no_risk_factors_floor_is_2():
    cards = _commander_deck([_card(f"Card {i}", "main") for i in range(99)])
    detail = brackets.suggest(cards)
    assert detail.suggested_bracket == 2
    assert detail.game_changer_count == 0


def test_one_to_three_game_changers_floor_is_3():
    main = [_card(f"GC {i}", "main", game_changer=1) for i in range(2)]
    main += [_card(f"Filler {i}", "main") for i in range(97)]
    cards = _commander_deck(main)
    detail = brackets.suggest(cards)
    assert detail.suggested_bracket == 3
    assert detail.game_changer_count == 2


def test_more_than_three_game_changers_floor_is_4():
    main = [_card(f"GC {i}", "main", game_changer=1) for i in range(4)]
    main += [_card(f"Filler {i}", "main") for i in range(95)]
    cards = _commander_deck(main)
    detail = brackets.suggest(cards)
    assert detail.suggested_bracket == 4
    assert detail.game_changer_count == 4


def test_mass_land_denial_floors_at_least_4():
    main = [_card("Armageddon", "main")]
    main += [_card(f"Filler {i}", "main") for i in range(98)]
    cards = _commander_deck(main)
    detail = brackets.suggest(cards)
    assert detail.suggested_bracket >= 4
    assert "Armageddon" in detail.mass_land_denial


def test_spellbook_two_card_combo_bumps_to_4(fake_spellbook):
    from magic_manager import commander_spellbook
    fake_spellbook(find_my_combos={
        "results": [{"uses": [{"card": "A"}, {"card": "B"}]}],
    })
    main = [_card(f"Filler {i}", "main") for i in range(99)]
    cards = _commander_deck(main)
    detail = brackets.suggest(cards, spellbook=commander_spellbook)
    assert detail.spellbook_available is True
    assert detail.two_card_combos == 1
    assert detail.suggested_bracket == 4


def test_spellbook_failure_degrades_gracefully(fake_spellbook):
    from magic_manager import commander_spellbook
    fake_spellbook(find_my_combos=RuntimeError("network down"))
    main = [_card(f"Filler {i}", "main") for i in range(99)]
    cards = _commander_deck(main)
    detail = brackets.suggest(cards, spellbook=commander_spellbook)
    assert detail.spellbook_available is False
    assert detail.combos == []
    # No crash, and the floor still resolves (no risk factors -> 2).
    assert detail.suggested_bracket == 2


def test_no_network_when_spellbook_is_none():
    """spellbook=None must never touch the commander_spellbook wrapper."""
    main = [_card(f"Filler {i}", "main") for i in range(99)]
    cards = _commander_deck(main)
    detail = brackets.suggest(cards, spellbook=None)
    assert detail.spellbook_available is False
    assert detail.combos == []
    assert detail.suggested_bracket == 2


def test_to_json_from_json_round_trip():
    main = [_card(f"Filler {i}", "main") for i in range(99)]
    cards = _commander_deck(main)
    detail = brackets.suggest(cards)
    d = detail.to_json()
    rebuilt = brackets.BracketDetail.from_json(d)
    assert rebuilt.suggested_bracket == detail.suggested_bracket
    assert rebuilt.game_changer_count == detail.game_changer_count
    assert rebuilt.rationale == detail.rationale
    # Genuinely JSON-serializable.
    d2 = json.loads(json.dumps(d))
    assert brackets.BracketDetail.from_json(d2).suggested_bracket == detail.suggested_bracket
