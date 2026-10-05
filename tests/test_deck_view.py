"""deck_view engine + /api/decks (offline)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from magic_manager import deck_view, decks, inventory, mtgjson
from magic_manager.web.app import create_app

SETS = [
    {"code": "tst", "name": "Test Set", "released_at": "2025-01-01"},
    {"code": "old", "name": "Old Set", "released_at": "2020-05-05"},
]
DECKLIST = {"pre.json": {"code": "TST", "fileName": "pre.json", "name": "Pre", "releaseDate": "2025-03-03", "type": "Commander Deck"}}


@pytest.fixture
def world(tmp_db, seed_cards, make_card, fake_scryfall, monkeypatch):
    fake_scryfall(all_sets=SETS)
    monkeypatch.setattr(mtgjson, "_decklist_by_filename", lambda: DECKLIST)
    seed_cards([
        make_card(id="cmdr", name="Boss", collector_number="1", cmc=4.0, type_line="Legendary Creature",
                  color_identity=["G", "U"], prices={"usd": "1.00", "usd_foil": "5.00"}),
        make_card(id="bolt", name="Bolt", collector_number="2", cmc=1.0, prices={"usd": "2.00", "usd_foil": "10.00"}),
        make_card(id="elf", name="Elf", collector_number="3", cmc=1.0, prices={"usd": "0.50", "usd_foil": None}),
        make_card(id="tok", name="Goblin Token", collector_number="4", cmc=0.0, layout="token",
                  prices={"usd": "9.00"}),
    ])
    with __import__("magic_manager.db", fromlist=["x"]).connect() as c:
        c.execute("UPDATE cards SET is_token = 1 WHERE scryfall_id = 'tok'")
    return None


def _deck(slug, cards, **kw):
    decks.deck_create(slug, kw.pop("name", slug), **kw)
    for sid, board, finish, n in cards:
        decks.deck_add_card(slug, sid, board, finish, n)


def test_summaries_fields(world):
    _deck("pre", [("cmdr", "commander", "nonfoil", 1), ("bolt", "main", "foil", 2), ("elf", "main", "either", 4),
                  ("tok", "token", "nonfoil", 3)],
          name="Pre", format="commander", source_precon_file_name="pre.json")
    _deck("imp", [("elf", "main", "nonfoil", 1)], source="moxfield", source_set_code="OLD", author="me")
    _deck("cus", [])
    by = {d["slug"]: d for d in deck_view.deck_summaries()}
    p = by["pre"]
    assert (p["origin"], p["source"], p["set_code"], p["set_name"], p["released"]) == (
        "precon", "Commander Deck", "tst", "Test Set", "2025-03-03")
    assert p["cards"] == 7  # tokens excluded
    assert p["value_usd"] == round(1 + 2 * 10 + 4 * 0.5, 2)  # foil price; 'either' nonfoil
    assert p["image_uri"] is not None
    i = by["imp"]
    assert (i["origin"], i["source"], i["set_code"], i["released"], i["author"]) == ("import", "moxfield", "old", "2020-05-05", "me")
    c = by["cus"]
    assert (c["origin"], c["source"], c["set_code"], c["set_name"], c["released"], c["cards"], c["pledged_pct"]) == (
        "custom", None, None, None, None, 0, 0)
    order = [d["slug"] for d in deck_view.deck_summaries()]
    assert order == ["pre", "imp", "cus"]


def test_image_prefers_commander_and_pledged_pct(world):
    _deck("a", [("cmdr", "commander", "nonfoil", 1), ("bolt", "main", "nonfoil", 3)])
    _deck("b", [("bolt", "main", "nonfoil", 1), ("elf", "main", "nonfoil", 1)])
    with __import__("magic_manager.db", fromlist=["x"]).connect() as c:
        c.execute("UPDATE cards SET image_uri = 'img-' || scryfall_id")
    inventory.inventory_add("bolt", "nonfoil", 3)
    inventory.inventory_add("elf", "nonfoil", 1)
    decks.deck_assign_batch("a", [("bolt", "nonfoil", 2)])
    by = {d["slug"]: d for d in deck_view.deck_summaries()}
    assert by["a"]["image_uri"] == "img-cmdr"
    assert by["b"]["image_uri"] == "img-bolt"  # priciest
    assert by["a"]["pledged_pct"] == 50.0


def test_detail_ordering_pledged_and_free(world):
    _deck("a", [("bolt", "main", "nonfoil", 2), ("cmdr", "commander", "nonfoil", 1), ("elf", "main", "nonfoil", 1),
                ("tok", "token", "nonfoil", 1)])
    _deck("b", [("bolt", "main", "nonfoil", 1)])
    inventory.inventory_add("bolt", "nonfoil", 4)
    decks.deck_assign_batch("a", [("bolt", "nonfoil", 2)])
    decks.deck_assign_batch("b", [("bolt", "nonfoil", 1)])
    d = deck_view.deck_detail("a")
    assert d["deck"]["slug"] == "a"
    assert [c["printing"]["scryfall_id"] for c in d["cards"]] == ["cmdr", "bolt", "elf", "tok"]
    cmdr = d["cards"][0]
    assert cmdr["color_identity"] == ["G", "U"] and cmdr["type_line"] == "Legendary Creature" and cmdr["cmc"] == 4.0
    bolt = d["cards"][1]
    assert bolt["pledged_here"] == 2 and bolt["free"] == 1 and bolt["printing"]["owned"] == {"nonfoil": 4}
    assert {"set_code", "treatment", "finishes", "price_usd"} <= set(bolt["printing"])
    assert deck_view.deck_detail("b")["cards"][0]["pledged_here"] == 1


def test_unknown_slug(world):
    with pytest.raises(LookupError):
        deck_view.deck_detail("nope")


def test_api(world):
    _deck("a", [("cmdr", "commander", "nonfoil", 1)])
    with TestClient(create_app(serve_frontend=False)) as client:
        r = client.get("/api/decks")
        assert r.status_code == 200 and r.json()[0]["slug"] == "a"
        r = client.get("/api/decks/a")
        assert r.status_code == 200 and r.json()["cards"][0]["printing"]["scryfall_id"] == "cmdr"
        assert client.get("/api/decks/zzz").status_code == 404


def test_deck_type_prefers_format_then_product_type():
    from magic_manager.deck_view import deck_type
    assert deck_type("commander", "Commander Deck") == "Commander"
    assert deck_type("Pauper", None) == "Pauper"
    assert deck_type("standard_brawl", None) == "Brawl"
    assert deck_type("paupercommander", None) == "Pauper Commander"
    assert deck_type(None, "Jumpstart") == "Jumpstart"
    assert deck_type(None, "Starter Kit") == "Starter / intro"
    assert deck_type(None, "Enemy Deck") == "Archenemy"
    assert deck_type(None, None) == "Other"
    assert deck_type("canlander", None) == "Canlander"
