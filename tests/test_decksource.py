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
    # ManaBox base64url ids — must survive intact, incl. embedded '-'/'_'.
    ("https://manabox.app/decks/nkZ_o0BVT5WjZ5kSq6XlzA", "manabox", "nkZ_o0BVT5WjZ5kSq6XlzA"),
    ("https://manabox.app/decks/AZsqTaLVf-Ghvr1Fv8_OSg", "manabox", "AZsqTaLVf-Ghvr1Fv8_OSg"),
    # Scryfall — the @user segment precedes 'decks'; the uuid (with '-') survives.
    ("https://scryfall.com/@fakeality/decks/438f7793-6d9d-49c3-bcfb-92ea42e00141",
     "scryfall", "438f7793-6d9d-49c3-bcfb-92ea42e00141"),
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

def test_author_extractors():
    assert decksource.author_moxfield({"createdByUser": {"userName": "alice"}}) == "alice"
    assert decksource.author_archidekt({"owner": {"username": "bob"}}) == "bob"
    assert decksource.author_moxfield({}) is None
    assert decksource.author_archidekt({}) is None


def test_parse_moxfield_boards_and_finishes():
    data = {
        "name": "Mox Test",
        "createdByUser": {"userName": "alice"},
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
    res = decksource.import_deck(cards, slug="my-deck", name="My Deck", author="alice")
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
    # author is stamped on the deck row at creation
    assert decks_mod.deck_get("my-deck").author == "alice"


def test_import_deck_appends_and_reports_unresolved(tmp_db, fake_scryfall, make_card):
    fake_scryfall(collection_found=[make_card(id="sid-main", set="tst", collector_number="1", name="Main Card")])
    base = [{"qty": 1, "board": "main", "finish": "nonfoil", "scryfall_id": "sid-main",
             "set": "tst", "collector_number": "1", "name": "Main Card", "category": None}]
    decksource.import_deck(base, slug="d", name="D", author="alice")

    # Re-import: same card sums (updated), plus one that Scryfall can't resolve.
    fake_scryfall(collection_found=[make_card(id="sid-main", set="tst", collector_number="1", name="Main Card")])
    more = base + [{"qty": 1, "board": "main", "finish": "nonfoil", "scryfall_id": "sid-missing",
                    "set": "zzz", "collector_number": "999", "name": "Ghost", "category": None}]
    res = decksource.import_deck(more, slug="d", author="someone-else")
    assert res["created"] is False
    assert res["updated"] == 1
    assert len(res["not_found"]) == 1
    assert res["not_found"][0]["name"] == "Ghost"

    from magic_manager import decks as decks_mod
    rows = decks_mod.deck_show("d")
    assert {(r.scryfall_id, r.count) for r in rows} == {("sid-main", 2)}
    # re-import must NOT overwrite the author stamped at creation
    assert decks_mod.deck_get("d").author == "alice"


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


# ---------------------------------------------------------------------------
# ManaBox — SSR page with embedded (HTML-escaped) Astro hydration payload
# ---------------------------------------------------------------------------

# Minimal fixture mirroring the real page shape: HTML-escaped (&quot;) payload
# with "key":[0,val] tuples, one card per "internalId". A deck-metadata preamble
# (deck name/format, NO internalId) precedes the cards. Covers: commander
# (boardCategory 0), a Foil main, a Normal main, and a card with a set-prefixed
# collector number (plst "The List" style "JUD-77").
_MANABOX_HTML = (
    "<html><head><title>OUT, AM I?</title></head><body>"
    '<script>{"id":[0,"abc"],"name":[0,"OUT, AM I?"],"format":[0,"Commander"],'
    '"cards":[1,['
    '[0,{"internalId":[0,0],"collectorNumber":[0,"23"],"name":[0,"Green Goblin, Nemesis"],'
    '"quantity":[0,1],"boardCategory":[0,0],"variant":[0,"Normal"],"setId":[0,"spe"]}],'
    '[0,{"internalId":[0,1],"collectorNumber":[0,"351"],"name":[0,"Anger"],'
    '"quantity":[0,2],"boardCategory":[0,3],"variant":[0,"Foil"],"setId":[0,"mh3"]}],'
    '[0,{"internalId":[0,2],"collectorNumber":[0,"JUD-77"],"name":[0,"Lightning Greaves"],'
    '"quantity":[0,1],"boardCategory":[0,3],"variant":[0,"Normal"],"setId":[0,"plst"]}]'
    "]]}</script></body></html>"
).replace('"', "&quot;").replace("&quot;<", '"<').replace(">&quot;", '">')


def test_parse_manabox_shape():
    cards = decksource.parse_manabox(_MANABOX_HTML)
    # Keyed by name for order-independent assertions.
    by_name = {c["name"]: c for c in cards}
    assert set(by_name) == {"Green Goblin, Nemesis", "Anger", "Lightning Greaves"}

    cmd = by_name["Green Goblin, Nemesis"]
    assert cmd["board"] == "commander" and cmd["qty"] == 1
    assert cmd["set"] == "spe" and cmd["collector_number"] == "23"
    assert cmd["finish"] == "nonfoil"

    foil = by_name["Anger"]
    assert foil["board"] == "main" and foil["qty"] == 2
    assert foil["set"] == "mh3" and foil["collector_number"] == "351"
    assert foil["finish"] == "foil"  # variant "Foil" → foil

    listed = by_name["Lightning Greaves"]
    assert listed["set"] == "plst" and listed["collector_number"] == "JUD-77"
    assert listed["board"] == "main" and listed["finish"] == "nonfoil"


def test_parse_manabox_etched_is_foil():
    # Swap the (escaped) Foil variant for Etched — both must map to foil.
    html_text = _MANABOX_HTML.replace(
        "&quot;variant&quot;:[0,&quot;Foil&quot;]",
        "&quot;variant&quot;:[0,&quot;Etched&quot;]",
    )
    assert "Etched" in html_text  # guard: the swap actually landed
    cards = decksource.parse_manabox(html_text)
    anger = next(c for c in cards if c["name"] == "Anger")
    assert anger["finish"] == "foil"  # Etched also maps to foil


def test_deck_name_manabox():
    assert decksource.deck_name_manabox(_MANABOX_HTML) == "OUT, AM I?"
    assert decksource.deck_name_manabox("<html><body>no title</body></html>") is None


def test_import_deck_manabox_end_to_end(tmp_db, fake_scryfall, make_card):
    """ManaBox parse → set+CN resolution → deck_cards, with foil preserved."""
    fake_scryfall(collection_found=[
        make_card(id="sid-ggn", set="spe", collector_number="23", name="Green Goblin, Nemesis"),
        make_card(id="sid-anger", set="mh3", collector_number="351", name="Anger"),
        make_card(id="sid-greaves", set="plst", collector_number="JUD-77", name="Lightning Greaves"),
    ])
    cards = decksource.parse_manabox(_MANABOX_HTML)
    res = decksource.import_deck(cards, slug="mb-deck", name=decksource.deck_name_manabox(_MANABOX_HTML))
    assert res["created"] is True and res["added"] == 3 and res["not_found"] == []

    from magic_manager import decks as decks_mod
    got = {(r.scryfall_id, r.board, r.finish, r.count) for r in decks_mod.deck_show("mb-deck")}
    assert got == {
        ("sid-ggn", "commander", "nonfoil", 1),
        ("sid-anger", "main", "foil", 2),
        ("sid-greaves", "main", "nonfoil", 1),
    }
    assert decks_mod.deck_get("mb-deck").name == "OUT, AM I?"


# ---------------------------------------------------------------------------
# Scryfall — /decks/{id}/export/json payload
# ---------------------------------------------------------------------------

def _sf_entry(*, count, found, finish=None, sid=None, set_code=None, cn=None, name=None):
    """A minimal Scryfall deck_entry; card_digest is None for placeholder rows."""
    digest = None
    if found:
        digest = {"object": "card_digest", "id": sid, "name": name,
                  "set": set_code, "collector_number": cn}
    return {"object": "deck_entry", "count": count, "found": found,
            "finish": finish, "card_digest": digest}


# Mirrors a real export: commander (+ a placeholder), a land, a FOIL nonland, and
# an "outside" (considering) row that must be dropped entirely.
_SCRYFALL_DECK = {
    "object": "deck",
    "name": "Patron of the Orochi Stax EDH",
    "format": "commander",
    "entries": {
        "commanders": [
            _sf_entry(count=1, found=True, sid="sid-patron", set_code="bok",
                      cn="138", name="Patron of the Orochi"),
            _sf_entry(count=1, found=False),  # placeholder — skipped
        ],
        "lands": [
            _sf_entry(count=1, found=True, sid="sid-cradle", set_code="usg",
                      cn="321", name="Gaea's Cradle"),
        ],
        "nonlands": [
            _sf_entry(count=1, found=True, finish="foil", sid="sid-monolith",
                      set_code="ulg", cn="126", name="Grim Monolith"),
        ],
        "outside": [
            _sf_entry(count=1, found=True, sid="sid-outside", set_code="xxx",
                      cn="1", name="Considering This"),
        ],
    },
}


def test_parse_scryfall_shape():
    cards = decksource.parse_scryfall(_SCRYFALL_DECK)
    by_name = {c["name"]: c for c in cards}
    # "outside" dropped; placeholder dropped → exactly the 3 real in-deck cards.
    assert set(by_name) == {"Patron of the Orochi", "Gaea's Cradle", "Grim Monolith"}

    cmd = by_name["Patron of the Orochi"]
    assert cmd["board"] == "commander" and cmd["scryfall_id"] == "sid-patron"
    assert cmd["set"] == "bok" and cmd["collector_number"] == "138"

    assert by_name["Gaea's Cradle"]["board"] == "main"           # lands → main
    monolith = by_name["Grim Monolith"]
    assert monolith["board"] == "main"                            # nonlands → main
    assert monolith["finish"] == "foil"                          # finish "foil" → foil


def test_deck_name_scryfall():
    assert decksource.deck_name_scryfall(_SCRYFALL_DECK) == "Patron of the Orochi Stax EDH"
    assert decksource.deck_name_scryfall({}) is None


# ---------------------------------------------------------------------------
# Re-pull dedup (V25) — refuse without force, replace with force
# ---------------------------------------------------------------------------

def _one_card(sid, name, *, set_code="tst", cn="1", qty=1, board="main"):
    return {"qty": qty, "board": board, "finish": "nonfoil", "scryfall_id": sid,
            "set": set_code, "collector_number": cn, "name": name, "category": None}


def test_import_deck_dedup_refuses_second_pull(tmp_db, fake_scryfall, make_card):
    fake_scryfall(collection_found=[make_card(id="sid-a", set="tst", collector_number="1", name="Card A")])
    cards = [_one_card("sid-a", "Card A")]
    first = decksource.import_deck(cards, slug="d1", name="D1",
                                   source="moxfield", source_deck_id="ABC")
    assert first["created"] is True and first["added"] == 1

    # Second pull of the SAME (source, id) — even under a different slug — refused.
    fake_scryfall(collection_found=[make_card(id="sid-a", set="tst", collector_number="1", name="Card A")])
    dup = decksource.import_deck(cards, slug="d1-again", name="Dup",
                                 source="moxfield", source_deck_id="ABC")
    assert dup == {"duplicate": True, "existing_slug": "d1",
                   "source": "moxfield", "source_deck_id": "ABC"}

    from magic_manager import decks as decks_mod
    # Nothing written: original unchanged (count still 1), no second deck created.
    assert {(r.scryfall_id, r.count) for r in decks_mod.deck_show("d1")} == {("sid-a", 1)}
    assert decks_mod.deck_get("d1-again") is None


def test_import_deck_force_replaces_not_sums(tmp_db, fake_scryfall, make_card):
    fake_scryfall(collection_found=[
        make_card(id="sid-a", set="tst", collector_number="1", name="Card A"),
        make_card(id="sid-b", set="tst", collector_number="2", name="Card B"),
    ])
    decksource.import_deck([_one_card("sid-a", "Card A"), _one_card("sid-b", "Card B")],
                           slug="d2", name="D2", source="archidekt", source_deck_id="99")

    # Forced re-pull with a CHANGED list: A's count up to 3, B dropped, C added.
    fake_scryfall(collection_found=[
        make_card(id="sid-a", set="tst", collector_number="1", name="Card A"),
        make_card(id="sid-c", set="tst", collector_number="3", name="Card C"),
    ])
    res = decksource.import_deck(
        [_one_card("sid-a", "Card A", qty=3), _one_card("sid-c", "Card C", set_code="tst", cn="3")],
        slug="ignored-slug", name="ignored", source="archidekt", source_deck_id="99", force=True)
    assert res.get("replaced") is True and res["slug"] == "d2"  # targets the matched deck

    from magic_manager import decks as decks_mod
    got = {(r.scryfall_id, r.count) for r in decks_mod.deck_show("d2")}
    # REPLACE, not sum: A is 3 (not 1+3=4), B is gone, C present.
    assert got == {("sid-a", 3), ("sid-c", 1)}


def test_import_deck_no_source_still_appends(tmp_db, fake_scryfall, make_card):
    """A hand-fed import with no source keys keeps the create-or-append behavior."""
    fake_scryfall(collection_found=[make_card(id="sid-a", set="tst", collector_number="1", name="Card A")])
    decksource.import_deck([_one_card("sid-a", "Card A")], slug="d3", name="D3")
    fake_scryfall(collection_found=[make_card(id="sid-a", set="tst", collector_number="1", name="Card A")])
    res = decksource.import_deck([_one_card("sid-a", "Card A")], slug="d3")  # no source → append
    assert res.get("duplicate") is None and res["updated"] == 1

    from magic_manager import decks as decks_mod
    assert {(r.scryfall_id, r.count) for r in decks_mod.deck_show("d3")} == {("sid-a", 2)}


def test_import_deck_bad_identifier_does_not_sink_batch(tmp_db, monkeypatch, make_card):
    """A deck with one malformed identifier (bad set code → Scryfall HTTP 400)
    must still import the good cards — decksource inherits the 400-bisection now
    that it lives in the shared scryfall.collection seam. Patch _run so the real
    bisection runs."""
    import json as _json
    from magic_manager import scryfall
    good = make_card(id="sid-good", set="tst", collector_number="1", name="Good")

    def fake_run(args, stdin=None):
        idents = _json.loads(stdin)["identifiers"]
        if any(i.get("set") == "bogus" for i in idents):
            raise scryfall.ScryfallError("HTTP 400: bad set code")  # whole-page 400
        data = [good for i in idents if i.get("set") == "tst" or i.get("id") == "sid-good"]
        return {"data": data, "not_found": [i for i in idents
                                            if i.get("set") not in ("tst", None) and not i.get("id")]}

    monkeypatch.setattr(scryfall, "_run", fake_run)
    cards = [
        _one_card("sid-good", "Good", set_code="tst", cn="1"),
        {"qty": 1, "board": "main", "finish": "nonfoil", "scryfall_id": None,
         "set": "bogus", "collector_number": "9", "name": "Bad", "category": None},
    ]
    res = decksource.import_deck(cards, slug="bad-batch", name="BB")  # must NOT raise
    assert res["added"] == 1
    assert len(res["not_found"]) == 1 and res["not_found"][0]["name"] == "Bad"
