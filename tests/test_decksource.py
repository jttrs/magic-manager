"""Offline tests for the multi-source deck importer (decksource.py).

Covers, with no network (scryfall.collection is monkeypatched via fake_scryfall):
  - source_of / deck_id_from_url URL classification + id extraction
  - parse_moxfield / parse_archidekt / parse_mtggoldfish shape → normalized cards
    (board mapping, finish mapping, scryfall_id vs set+cn resolution keys)
  - import_deck end-to-end: resolve → create deck → write deck_cards rows
"""

from __future__ import annotations

import pytest

from magic_manager import decksource


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,src,deck_id", [
    ("https://www.moxfield.com/decks/AbC123xyz", "moxfield", "AbC123xyz"),
    ("https://moxfield.com/decks/AbC123xyz/whatever", "moxfield", "AbC123xyz"),
    ("https://archidekt.com/decks/9876543-my-cool-deck", "archidekt", "9876543"),
    ("https://www.archidekt.com/decks/12345", "archidekt", "12345"),
    ("https://www.mtggoldfish.com/deck/6543210", "mtggoldfish", "6543210"),
])
def test_source_and_id(url, src, deck_id):
    assert decksource.source_of(url) == src
    assert decksource.deck_id_from_url(url) == deck_id


def test_source_of_rejects_unknown():
    with pytest.raises(ValueError):
        decksource.source_of("https://example.com/decks/1")


# ---------------------------------------------------------------------------
# Per-source parsers → normalized cards
# ---------------------------------------------------------------------------

def test_parse_moxfield_boards_and_finishes():
    data = {
        "name": "Mox Test",
        "boards": {
            "mainboard": {"cards": {
                "e1": {"quantity": 3, "card": {"scryfall_id": "sid-main", "set": "tst", "cn": "1", "name": "Main Card"}},
            }},
            "commanders": {"cards": {
                "e2": {"quantity": 1, "card": {"scryfall_id": "sid-cmd", "set": "tst", "cn": "2", "name": "Cmdr"}},
            }},
            "sideboard": {"cards": {
                "e3": {"quantity": 2, "isFoil": True, "card": {"scryfall_id": "sid-side", "set": "tst", "cn": "3", "name": "Side"}},
            }},
            "companions": {"cards": {
                "e4": {"quantity": 1, "card": {"scryfall_id": "sid-comp", "set": "tst", "cn": "4", "name": "Comp"}},
            }},
            "maybeboard": {"cards": {
                "e5": {"quantity": 1, "card": {"finish": "etched", "scryfall_id": "sid-maybe", "set": "tst", "cn": "5", "name": "Maybe"}},
            }},
            "tokens": {"cards": {
                "e6": {"quantity": 1, "card": {"scryfall_id": "sid-tok", "set": "ttst", "cn": "1", "name": "Token"}},
            }},
            # a board name we don't map should be skipped, not guessed
            "unknownBucket": {"cards": {
                "e7": {"quantity": 9, "card": {"scryfall_id": "sid-x", "set": "tst", "cn": "9"}},
            }},
        },
    }
    cards = decksource.parse_moxfield(data)
    by_board = {c["board"]: c for c in cards}
    assert set(by_board) == {"main", "commander", "side", "companion", "maybe", "token"}
    assert by_board["main"]["qty"] == 3
    assert by_board["main"]["scryfall_id"] == "sid-main"
    assert by_board["side"]["finish"] == "foil"          # isFoil
    assert by_board["maybe"]["finish"] == "foil"          # finish=etched
    assert by_board["main"]["finish"] == "nonfoil"
    assert all(c["scryfall_id"] != "sid-x" for c in cards)  # unknown board skipped


def test_parse_archidekt_categories_and_modifier():
    data = {
        "name": "Arch Test",
        "cards": [
            {"quantity": 1, "modifier": "Normal", "categories": ["Commander"],
             "card": {"uid": "sid-cmd", "collectorNumber": "10",
                      "edition": {"editioncode": "tst"}, "oracleCard": {"name": "General"}}},
            {"quantity": 2, "modifier": "Foil", "categories": ["Sideboard"],
             "card": {"uid": "sid-side", "collectorNumber": "11",
                      "edition": {"editioncode": "tst"}, "oracleCard": {"name": "SB Card"}}},
            {"quantity": 1, "modifier": "Normal", "categories": ["Maybeboard"],
             "card": {"uid": "sid-maybe", "collectorNumber": "12",
                      "edition": {"editioncode": "tst"}, "oracleCard": {"name": "Maybe"}}},
            {"quantity": 4, "modifier": "Normal", "categories": ["Ramp"],
             "card": {"uid": "sid-ramp", "collectorNumber": "13",
                      "edition": {"editioncode": "tst"}, "oracleCard": {"name": "Ramp Card"}}},
        ],
    }
    cards = decksource.parse_archidekt(data)
    by_board = {c["board"]: c for c in cards}
    assert by_board["commander"]["scryfall_id"] == "sid-cmd"
    assert by_board["side"]["finish"] == "foil"
    assert by_board["maybe"]["board"] == "maybe"
    # A non-reserved category → mainboard, but the category string is preserved.
    assert by_board["main"]["qty"] == 4
    assert by_board["main"]["category"] == "Ramp"


def test_parse_mtggoldfish_delegates_to_parse_text():
    text = "\n".join([
        "1 Sol Ring (tst) 1",
        "3 Forest (tst) 2 *F*",
        "",
        "Sideboard:",
        "1 Naturalize (tst) 3",
    ])
    cards = decksource.parse_mtggoldfish(text)
    main = [c for c in cards if c["board"] == "main"]
    side = [c for c in cards if c["board"] == "side"]
    assert {c["name"] for c in main} == {"Sol Ring", "Forest"}
    assert any(c["finish"] == "foil" and c["name"] == "Forest" for c in main)
    assert side and side[0]["name"] == "Naturalize"
    # MTGGoldfish text has no scryfall_id — resolution falls back to set+cn.
    assert all(c["scryfall_id"] is None and c["set"] == "tst" for c in cards)


# ---------------------------------------------------------------------------
# import_deck: resolve → create → write deck_cards
# ---------------------------------------------------------------------------

def test_import_deck_end_to_end(tmp_db, fake_scryfall, make_card):
    found = [
        make_card(id="sid-cmd", set="tst", collector_number="10", name="General"),
        make_card(id="sid-main", set="tst", collector_number="1", name="Main Card"),
    ]
    fake_scryfall(collection_found=found)

    cards = [
        {"qty": 1, "board": "commander", "finish": "nonfoil", "scryfall_id": "sid-cmd",
         "set": "tst", "collector_number": "10", "name": "General", "category": None},
        {"qty": 3, "board": "main", "finish": "foil", "scryfall_id": "sid-main",
         "set": "tst", "collector_number": "1", "name": "Main Card", "category": None},
    ]
    res = decksource.import_deck(cards, slug="my-deck", name="My Deck")
    assert res["created"] is True
    assert res["added"] == 2
    assert res["updated"] == 0
    assert res["not_found"] == []

    from magic_manager import decks as decks_mod
    rows = decks_mod.deck_show("my-deck")
    got = {(r.scryfall_id, r.board, r.finish, r.count) for r in rows}
    assert got == {
        ("sid-cmd", "commander", "nonfoil", 1),
        ("sid-main", "main", "foil", 3),
    }


def test_import_deck_appends_and_reports_unresolved(tmp_db, fake_scryfall, make_card):
    fake_scryfall(collection_found=[make_card(id="sid-main", set="tst", collector_number="1", name="Main Card")])
    base = [{"qty": 1, "board": "main", "finish": "nonfoil", "scryfall_id": "sid-main",
             "set": "tst", "collector_number": "1", "name": "Main Card", "category": None}]
    decksource.import_deck(base, slug="d", name="D")

    # Re-import: same card sums (updated), plus one that Scryfall can't resolve.
    fake_scryfall(collection_found=[make_card(id="sid-main", set="tst", collector_number="1", name="Main Card")])
    more = base + [{"qty": 1, "board": "main", "finish": "nonfoil", "scryfall_id": "sid-missing",
                    "set": "zzz", "collector_number": "999", "name": "Ghost", "category": None}]
    res = decksource.import_deck(more, slug="d")
    assert res["created"] is False
    assert res["updated"] == 1
    assert len(res["not_found"]) == 1
    assert res["not_found"][0]["name"] == "Ghost"

    from magic_manager import decks as decks_mod
    rows = decks_mod.deck_show("d")
    assert {(r.scryfall_id, r.count) for r in rows} == {("sid-main", 2)}


def test_import_deck_resolves_name_only(tmp_db, fake_scryfall, make_card):
    """MTGGoldfish downloads are frequently name-only (no set/cn); those must
    still resolve, via the name fallback tier."""
    fake_scryfall(collection_found=[
        make_card(id="sid-bolt", set="lea", collector_number="161", name="Lightning Bolt"),
    ])
    cards = [{"qty": 4, "board": "main", "finish": "nonfoil", "scryfall_id": None,
              "set": None, "collector_number": None, "name": "Lightning Bolt", "category": None}]
    res = decksource.import_deck(cards, slug="burn", name="Burn")
    assert res["added"] == 1 and res["not_found"] == []

    from magic_manager import decks as decks_mod
    rows = decks_mod.deck_show("burn")
    assert {(r.scryfall_id, r.count) for r in rows} == {("sid-bolt", 4)}
