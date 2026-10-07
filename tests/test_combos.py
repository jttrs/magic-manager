"""combos: Commander Spellbook combos a deck contains / is one card away from,
and the combos one card is part of — joined to ownership and cheapest price."""
from __future__ import annotations

import pytest

from magic_manager import brackets, combos, commander_spellbook, deck_edit, decks, inventory

CMD, SCEPTER, REVERSAL, SIDE = (f"00000000-0000-0000-0000-00000000000{x}" for x in "1234")
LATTICE = "00000000-0000-0000-0000-000000000005"
OID = {n: f"aaaaaaaa-0000-0000-0000-00000000000{i}" for i, n in enumerate(
    ["Thrasios", "Isochron Scepter", "Dramatic Reversal", "Sideboard Card", "Mycosynth Lattice"], 1)}
VANDAL = "aaaaaaaa-0000-0000-0000-000000000099"     # not in the local catalog


def _card(name, oid=None, **extra):
    return {"name": name, "oracleId": oid or OID.get(name), "imageUriFrontArtCrop": f"https://img/{name}.jpg", **extra}


def _variant(vid, names, *, popularity=10, produces=("Infinite mana",), requires=()):
    return {
        "id": vid, "identity": "U", "popularity": popularity, "description": "Do it.\nRepeat.",
        "easyPrerequisites": "All on the battlefield.", "notablePrerequisites": "", "manaNeeded": "{2}",
        "uses": [{"card": c if isinstance(c, dict) else _card(c), "quantity": 1} for c in names],
        "produces": [{"feature": {"name": p}} for p in produces],
        "requires": [{"template": {"name": r}} for r in requires],
    }


@pytest.fixture
def deck(seed_cards, make_card):
    seed_cards([make_card(id=s, oracle_id=OID[n], name=n, collector_number=str(i), prices={"usd": "2.50"})
                for i, (s, n) in enumerate([(CMD, "Thrasios"), (SCEPTER, "Isochron Scepter"),
                                            (REVERSAL, "Dramatic Reversal"), (SIDE, "Sideboard Card"),
                                            (LATTICE, "Mycosynth Lattice")], 1)])
    slug = deck_edit.create_deck("Combo Brew", commander=CMD)
    decks.deck_add_card(slug, SCEPTER, "main", "either", 1)
    decks.deck_add_card(slug, REVERSAL, "main", "either", 1)
    decks.deck_add_card(slug, SIDE, "side", "either", 1)
    inventory.inventory_add(LATTICE, "nonfoil", 2)
    return slug


RESPONSE = {"results": {
    "identity": "U",
    "included": [_variant("1-2", ["Dramatic Reversal", "Isochron Scepter"], popularity=100)],
    "almostIncluded": [
        _variant("2-5", ["Isochron Scepter", "Mycosynth Lattice"], popularity=5),
        _variant("3-5", ["Dramatic Reversal", "Mycosynth Lattice"], popularity=7, requires=("A sac outlet",)),
        _variant("4-9", ["Isochron Scepter", _card("Vandalblast", VANDAL)], popularity=50),
    ],
    "almostIncludedByAddingColors": [_variant("9-9", ["Thrasios", "Vandalblast"])],
}}


def test_deck_combos_splits_included_and_one_card_away_joined_to_ownership(deck, fake_spellbook):
    state = fake_spellbook(find_my_combos=RESPONSE)
    r = combos.deck_combos(deck)

    (_, commander, main), = state["calls"]
    assert commander == ["Thrasios"] and sorted(main) == ["Dramatic Reversal", "Isochron Scepter"]   # sideboard ignored
    assert r.available and r.identity == "U" and r.off_color == 1
    (inc,) = r.included
    assert all(p.in_deck for p in inc.pieces) and inc.missing is None
    assert inc.url == "https://commanderspellbook.com/combo/1-2/"
    assert (inc.produces, inc.prerequisites, inc.mana_needed) == (["Infinite mana"], "All on the battlefield.", "{2}")

    assert [c.id for c in r.almost] == ["4-9", "3-5", "2-5"]                      # most popular first
    assert r.almost[1].requires == ["A sac outlet"]
    assert [(m.piece.name, m.combos, m.popularity) for m in r.missing_cards] == [
        ("Mycosynth Lattice", ["3-5", "2-5"], 12), ("Vandalblast", ["4-9"], 50)]  # most combos first
    lattice = r.missing_cards[0].piece
    assert (lattice.in_deck, lattice.facts.owned, lattice.facts.free, lattice.facts.lowest_usd) == (False, 2, 2, 2.5)
    vandal = r.missing_cards[1].piece
    assert vandal.facts.owned == 0 and vandal.image_uri == "https://img/Vandalblast.jpg"


def test_unsaved_draft_rows_and_empty_deck(deck, fake_spellbook):
    state = fake_spellbook(find_my_combos=RESPONSE)
    r = combos.combos_for_rows([(SCEPTER, "main", 1), (REVERSAL, "maybe", 1)])
    assert state["calls"][-1][2] == ["Isochron Scepter"] and r.available
    assert combos.combos_for_rows([(SIDE, "side", 1)]).included == []           # nothing to ask about
    assert len(state["calls"]) == 1


def test_spellbook_outage_degrades_to_unavailable(deck, fake_spellbook):
    fake_spellbook(find_my_combos=commander_spellbook.CommanderSpellbookError("HTTP 503"))
    r = combos.deck_combos(deck)
    assert not r.available and "HTTP 503" in r.error and r.almost == []


def test_unknown_deck_raises_lookup_error(deck, fake_spellbook):
    with pytest.raises(LookupError):
        combos.deck_combos("nope")


def test_card_combos_marks_owned_pieces(deck, fake_spellbook):
    state = fake_spellbook(variants={"results": [_variant("2-5", ["Isochron Scepter", "Mycosynth Lattice"])]})
    r = combos.card_combos("Isochron Scepter", limit=5)
    assert state["calls"] == [("variants", 'card="Isochron Scepter"', 5)]
    (c,) = r.combos
    assert [(p.name, p.facts.owned) for p in c.pieces] == [("Isochron Scepter", 0), ("Mycosynth Lattice", 2)]


def test_request_body_uses_card_objects_sorted_and_deduped():
    body = commander_spellbook._decklist_body(commander=["B"], main=["Z", "A", "Z"])
    assert body == {"commanders": [{"card": "B", "quantity": 1}],
                    "main": [{"card": "A", "quantity": 1}, {"card": "Z", "quantity": 1}]}


def test_brackets_reads_included_from_the_live_response_shape():
    assert [c["id"] for c in brackets._extract_combos(RESPONSE)] == ["1-2"]


def test_api_routes(deck, fake_spellbook):
    from fastapi.testclient import TestClient

    from magic_manager.web.app import create_app

    fake_spellbook(find_my_combos=RESPONSE, variants={"results": RESPONSE["results"]["included"]})
    with TestClient(create_app(serve_frontend=False)) as client:
        r = client.get(f"/api/decks/{deck}/combos").json()
        assert [m["piece"]["name"] for m in r["missing_cards"]] == ["Mycosynth Lattice", "Vandalblast"]
        assert r["missing_cards"][0]["piece"]["facts"]["free"] == 2
        assert r["missing_cards"][0]["piece"]["printing"]["scryfall_id"] == LATTICE   # your copy, ready to add
        assert r["missing_cards"][1]["piece"]["printing"] is None                     # not in the local catalog
        assert client.get("/api/decks/nope/combos").status_code == 404
        d = client.post("/api/combos/draft", json={"cards": [
            {"scryfall_id": SCEPTER, "board": "main", "finish": "either", "count": 1}]}).json()
        assert d["available"] and len(d["included"]) == 1
        c = client.get("/api/combos/card", params={"name": "Isochron Scepter"}).json()
        assert c["combos"][0]["pieces"][0]["name"] == "Dramatic Reversal"
