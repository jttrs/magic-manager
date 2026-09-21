"""Unit tests for magic_manager.legality.validate — pure, offline, no DB.

Card dicts are hand-built in the shape decks._materialize_for_checks produces:
scryfall_id, oracle_id, name, board, finish, count, type_line, color_identity
(list), oracle_text, keywords (list), legalities (dict|None).
"""

from __future__ import annotations

import json

from magic_manager import legality


def _card(name, board, count=1, *, type_line="Creature — Test",
          color_identity=None, oracle_text="", keywords=None,
          legalities=None, finish="nonfoil", scryfall_id=None, oracle_id=None):
    return {
        "scryfall_id": scryfall_id or f"sid-{name}",
        "oracle_id": oracle_id or f"oid-{name}",
        "name": name,
        "board": board,
        "finish": finish,
        "count": count,
        "type_line": type_line,
        "color_identity": color_identity if color_identity is not None else [],
        "oracle_text": oracle_text,
        "keywords": keywords or [],
        "legalities": legalities if legalities is not None else {"commander": "legal"},
    }


def _commander_card(name="Legal Commander", **kw):
    kw.setdefault("type_line", "Legendary Creature — Test")
    kw.setdefault("color_identity", ["G"])
    return _card(name, "commander", **kw)


def _legal_100_deck():
    """A minimal legal commander deck: 1 commander + 99 singleton main cards,
    all within the commander's (green) identity."""
    cards = [_commander_card()]
    for i in range(99):
        cards.append(_card(
            f"Card {i}", "main",
            type_line="Creature — Test",
            color_identity=["G"],
        ))
    return cards


def test_commander_legal_deck():
    report = legality.validate(_legal_100_deck(), format="commander")
    assert report.legal is True
    assert report.violations == [] or all(v.severity != "error" for v in report.violations)


def test_commander_wrong_size():
    cards = [_commander_card()] + [
        _card(f"Card {i}", "main", color_identity=["G"]) for i in range(50)
    ]
    report = legality.validate(cards, format="commander")
    assert report.legal is False
    codes = {v.code for v in report.violations if v.severity == "error"}
    assert "deck_size" in codes


def test_commander_off_color_identity():
    cards = _legal_100_deck()
    # Swap one card to a color outside the commander's green identity.
    cards[1]["color_identity"] = ["R"]
    cards[1]["name"] = "Red Intruder"
    report = legality.validate(cards, format="commander")
    assert report.legal is False
    ci_violation = next(v for v in report.violations if v.code == "color_identity")
    assert "Red Intruder" in ci_violation.cards


def test_commander_singleton_violation():
    cards = _legal_100_deck()
    # Duplicate an existing non-basic name so it's a 2x.
    dupe_name = cards[1]["name"]
    cards[2]["name"] = dupe_name
    report = legality.validate(cards, format="commander")
    assert report.legal is False
    singleton_violation = next(v for v in report.violations if v.code == "singleton")
    assert dupe_name in singleton_violation.cards


def test_commander_banned_card():
    cards = _legal_100_deck()
    cards[1]["legalities"] = {"commander": "banned"}
    banned_name = cards[1]["name"]
    report = legality.validate(cards, format="commander")
    assert report.legal is False
    banned_violation = next(v for v in report.violations if v.code == "banned")
    assert banned_name in banned_violation.cards


def test_commander_no_commander():
    cards = [
        _card(f"Card {i}", "main", color_identity=["G"]) for i in range(100)
    ]
    report = legality.validate(cards, format="commander")
    assert report.legal is False
    codes = {v.code for v in report.violations if v.severity == "error"}
    assert "commander_eligibility" in codes


def test_commander_ineligible_commander():
    cards = [
        _card("Not A Commander", "commander", type_line="Sorcery", color_identity=["G"]),
    ] + [_card(f"Card {i}", "main", color_identity=["G"]) for i in range(99)]
    report = legality.validate(cards, format="commander")
    assert report.legal is False
    codes = {v.code for v in report.violations if v.severity == "error"}
    assert "commander_eligibility" in codes


def test_basic_lands_exempt_from_singleton():
    cards = [_commander_card()]
    for _ in range(10):
        cards.append(_card(
            "Forest", "main", type_line="Basic Land — Forest", color_identity=[],
        ))
    for i in range(89):
        cards.append(_card(f"Card {i}", "main", color_identity=["G"]))
    report = legality.validate(cards, format="commander")
    codes = {v.code for v in report.violations if v.severity == "error"}
    assert "singleton" not in codes


def test_sixty_card_main_under_min():
    cards = [_card(f"Card {i}", "main") for i in range(50)]
    report = legality.validate(cards, format="standard")
    assert report.legal is False
    assert any(v.code == "deck_size" for v in report.violations if v.severity == "error")


def test_sixty_card_copy_limit():
    cards = [_card("Overplayed", "main", count=5)]
    cards += [_card(f"Filler {i}", "main") for i in range(59)]
    report = legality.validate(cards, format="standard")
    assert report.legal is False
    copies_violation = next(v for v in report.violations if v.code == "copies")
    assert "Overplayed" in copies_violation.cards


def test_sixty_card_side_too_big():
    cards = [_card(f"Main {i}", "main") for i in range(60)]
    cards += [_card(f"Side {i}", "side") for i in range(16)]
    report = legality.validate(cards, format="standard")
    assert report.legal is False
    assert any(
        v.code == "deck_size" and "sideboard" in v.message
        for v in report.violations if v.severity == "error"
    )


def test_vintage_restricted_over_one():
    cards = [_card("Black Lotus", "main", count=2, legalities={"vintage": "restricted"})]
    cards += [_card(f"Filler {i}", "main") for i in range(59)]
    report = legality.validate(cards, format="vintage")
    assert report.legal is False
    restricted_violation = next(v for v in report.violations if v.code == "restricted")
    assert "Black Lotus" in restricted_violation.cards


def test_vintage_restricted_at_one_is_legal():
    cards = [_card("Black Lotus", "main", count=1, legalities={"vintage": "restricted"})]
    cards += [_card(f"Filler {i}", "main") for i in range(59)]
    report = legality.validate(cards, format="vintage")
    assert report.legal is True


def test_pauper_not_legal_is_banned_coded():
    cards = [_card("Rare Bomb", "main", legalities={"pauper": "not_legal"})]
    cards += [_card(f"Filler {i}", "main") for i in range(59)]
    report = legality.validate(cards, format="pauper")
    assert report.legal is False
    banned_violation = next(
        v for v in report.violations if v.code == "banned" and v.severity == "error"
    )
    assert "Rare Bomb" in banned_violation.cards


def test_unknown_format_is_legal_with_info():
    cards = [_card("Whatever", "main")]
    report = legality.validate(cards, format="cube")
    assert report.legal is True
    unknown_violation = next(v for v in report.violations if v.code == "unknown_format")
    assert unknown_violation.severity == "info"


def test_missing_legalities_is_stale_data_info():
    cards = _legal_100_deck()
    cards[1]["legalities"] = None
    report = legality.validate(cards, format="commander")
    stale = next(v for v in report.violations if v.code == "stale_data")
    assert stale.severity == "info"


def test_to_json_from_json_round_trip():
    report = legality.validate(_legal_100_deck(), format="commander")
    d = report.to_json()
    rebuilt = legality.LegalityReport.from_json(d)
    assert rebuilt.format == report.format
    assert rebuilt.legal == report.legal
    assert rebuilt.checked_count == report.checked_count
    assert [v.code for v in rebuilt.violations] == [v.code for v in report.violations]
    # Confirm it's genuinely JSON-serializable (round trips through json module too).
    d2 = json.loads(json.dumps(d))
    assert legality.LegalityReport.from_json(d2).legal == report.legal
