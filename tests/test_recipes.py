"""Deck recipes (magic_manager.recipes) + /api/recipes, offline.

Catalog: two Jumpstart versions (one owned as a built deck), a Commander precon
that is read, one that isn't, a land pack (a pool type) and a 10-card product
(a pool once read). Plus an imported deck.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from magic_manager import db, decks, inventory, mtgjson, recipes, sets
from magic_manager.web.app import create_app

CATALOG = {
    "Cats1_JT": {"code": "JT", "fileName": "Cats1_JT", "name": "Cats (1)", "type": "Jumpstart", "releaseDate": "2025-01-01"},
    "Dogs_JT": {"code": "JT", "fileName": "Dogs_JT", "name": "Dogs", "type": "Jumpstart", "releaseDate": "2025-01-01"},
    "Boss_TST": {"code": "TST", "fileName": "Boss_TST", "name": "Boss Deck", "type": "Commander Deck", "releaseDate": "2025-06-01"},
    "Later_TST": {"code": "TST", "fileName": "Later_TST", "name": "Later Deck", "type": "Commander Deck", "releaseDate": "2025-07-01"},
    "Lands_TST": {"code": "TST", "fileName": "Lands_TST", "name": "Land Pack", "type": "Bundle Land Pack", "releaseDate": "2025-06-01"},
    "Tiny_TST": {"code": "TST", "fileName": "Tiny_TST", "name": "Tiny Box", "type": "Box Set", "releaseDate": "2025-06-01"},
    "Fancy_TST": {"code": "TST", "fileName": "Fancy_TST", "name": "Boss Collector's Edition", "type": "Commander Deck", "releaseDate": "2025-06-01"},
    "Draft_TST": {"code": "TST", "fileName": "Draft_TST", "name": "Some Draft Thing", "type": "Draft Booster", "releaseDate": "2025-06-01"},
}


@pytest.fixture
def world(tmp_db, seed_cards, make_card, make_precon_deck, monkeypatch):
    seed_cards([
        make_card(id="a", set="jt", collector_number="1", name="Alpha", color_identity=[], prices={"usd": "1.00", "usd_foil": "3.00"}),
        make_card(id="b", set="jt", collector_number="2", name="Bravo", color_identity=["W"], prices={"usd": "2.00"}),
        make_card(id="d", set="jt", collector_number="4", name="Delta", color_identity=["R"], prices={"usd": "0.50"}),
        make_card(id="k", set="tst", collector_number="1", name="King", type_line="Legendary Creature",
                  color_identity=["G"], prices={"usd": "4.00"}),
    ])
    files = {
        "Cats1_JT": make_precon_deck("Cats (1)", "Jumpstart", [
            {"sid": "a", "name": "Alpha", "set": "JT", "foil": True}, {"sid": "b", "name": "Bravo", "count": 19, "set": "JT"}]),
        "Dogs_JT": make_precon_deck("Dogs", "Jumpstart", [
            {"sid": "a", "name": "Alpha", "set": "JT"}, {"sid": "d", "name": "Delta", "count": 19, "set": "JT"}]),
        "Boss_TST": make_precon_deck("Boss Deck", "Commander Deck", [
            {"sid": "k", "name": "King", "set": "TST"}, {"sid": "a", "name": "Alpha", "count": 98, "set": "JT"},
            {"sid": "zz", "name": "Mystery", "set": "TST"}]),
        "Tiny_TST": make_precon_deck("Tiny Box", "Box Set", [{"sid": "a", "name": "Alpha", "count": 10, "set": "JT"}]),
    }
    monkeypatch.setattr(mtgjson, "_decklist_by_filename", lambda: CATALOG)
    monkeypatch.setattr(mtgjson, "cached_deck", lambda fn: files.get(fn))
    monkeypatch.setattr(mtgjson, "deck", lambda fn: files[fn])
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets", lambda: [
        {"code": "jt", "name": "Jump Test", "released_at": "2025-01-01"},
        {"code": "tst", "name": "Test Set", "released_at": "2025-06-01"}])

    inventory.inventory_add("a", "nonfoil", 3)
    inventory.inventory_add("d", "nonfoil", 17)
    with db.connect() as conn:
        decks.deck_create("pack:dogs-jt", "Dogs", source_precon_file_name="Dogs_JT", precon_state="built", conn=conn)
        decks.deck_create("imp", "My Import", source="moxfield", format="commander", conn=conn)
    decks.deck_add_card("pack:dogs-jt", "a", "main", "nonfoil", 1)
    decks.deck_add_card("pack:dogs-jt", "d", "main", "nonfoil", 19)
    decks.deck_add_card("imp", "k", "commander", "nonfoil", 1)
    decks.deck_assign_batch("pack:dogs-jt", [("a", "nonfoil", 1)])
    return files


def test_catalog_kinds_ownership_and_exclusions(world):
    rows = {r["key"]: r for r in recipes.catalog()}
    # Pools (land pack by type, a 10-card product once read), Collector's Editions
    # and non-precon product types are not recipes.
    assert set(rows) == {"pack:dogs-jt", "imp", "fn:Cats1_JT", "fn:Boss_TST", "fn:Later_TST"}
    dogs = rows["pack:dogs-jt"]
    assert (dogs["kind"], dogs["ownership"], dogs["built"], dogs["file_name"], dogs["read"]) == ("jumpstart", "built", 1, "Dogs_JT", True)
    assert rows["imp"]["kind"] == "import" and rows["imp"]["ownership"] == "built"
    cats = rows["fn:Cats1_JT"]
    assert (cats["kind"], cats["ownership"], cats["slug"], cats["deck_type"]) == ("jumpstart", "none", None, "Jumpstart")
    assert rows["fn:Boss_TST"]["kind"] == "precon" and rows["fn:Boss_TST"]["deck_type"] == "Commander"


def test_read_recipes_carry_value_art_colour_and_free_coverage(world):
    rows = {r["key"]: r for r in recipes.catalog()}
    cats = rows["fn:Cats1_JT"]
    # Alpha ships foil ($3) + 19 Bravo at $2; free: 2 Alpha (3 owned − 1 pledged), no Bravo.
    assert (cats["read"], cats["cards"], cats["value_usd"], cats["color"]) == (True, 20, 41.0, "W")
    assert (cats["have"], cats["short"], cats["status"]) == (1, 19, "far")
    assert cats["image_uri"]
    dogs = rows["pack:dogs-jt"]  # owned: needs from its deck_cards → 2 Alpha free (1 needed), 17 Delta of 19
    assert (dogs["have"], dogs["short"], dogs["status"], dogs["color"]) == (18, 2, "close", "R")


def test_unread_and_unsynced_recipes_stay_unread(world, monkeypatch):
    rows = {r["key"]: r for r in recipes.catalog()}
    later = rows["fn:Later_TST"]  # deck file not cached
    assert (later["read"], later["cards"], later["value_usd"], later["have"]) == (False, None, None, None)
    monkeypatch.setattr(sets, "unsynced_set_codes", lambda codes: [c for c in codes if c == "tst"])
    assert not {r["key"]: r for r in recipes.catalog()}["fn:Boss_TST"]["read"]  # a card set isn't synced


def test_owned_pool_hides_its_catalog_row(world):
    with db.connect() as conn:
        decks.deck_create("cats-pool", "Cats (1)", source_precon_file_name="Cats1_JT", precon_state="deconstructed", conn=conn)
        conn.execute("UPDATE decks SET kind = 'pool', kind_source = 'user' WHERE slug = 'cats-pool'")
    assert "fn:Cats1_JT" not in {r["key"] for r in recipes.catalog()}


def test_recipe_detail_and_unknown_cards(world):
    d = recipes.recipe("Boss_TST")
    assert d["ready"] and d["recipe"]["ownership"] == "none"
    assert [(c["printing"]["name"], c["board"], c["count"], c["free"]) for c in d["cards"]] == [
        ("King", "main", 1, 0), ("Alpha", "main", 98, 2)]
    assert d["unknown"] == ["Mystery"]
    assert recipes.recipe("Later_TST") == {"recipe": recipes.recipe("Later_TST")["recipe"], "ready": False, "cards": [], "unknown": []}
    with pytest.raises(LookupError):
        recipes.recipe("Lands_TST2")
    owned = recipes.recipe("Dogs_JT")["recipe"]
    assert (owned["ownership"], owned["slug"], owned["slugs"]) == ("built", "pack:dogs-jt", ["pack:dogs-jt"])


def test_ensure_read_fetches_and_raises_when_sets_stay_unsynced(world, monkeypatch):
    seen: list = []
    monkeypatch.setattr(sets, "ensure_priced", lambda codes, **k: seen.append(sorted(codes)) or {"missing": [], "stale": []})
    import magic_manager.front_cards as fc
    monkeypatch.setattr(fc, "sync_front_cards", lambda code: seen.append(code))
    assert recipes.ensure_read(["Cats1_JT", "Boss_TST"]) == 2
    assert seen == [["jt", "tst"], "jt"]
    monkeypatch.setattr(sets, "unsynced_set_codes", lambda codes: ["tst"])
    with pytest.raises(RuntimeError, match="TST"):
        recipes.ensure_read(["Boss_TST"])
    assert recipes.file_names_for_set("tst") == ["Boss_TST", "Later_TST", "Tiny_TST"]


def test_coverage_and_status():
    assert recipes.coverage({"a": 2, "b": 3}, {"a": 5, "b": 1}) == (3, 2)
    assert [recipes.status(n) for n in (0, 3, 4)] == ["build", "close", "far"]


def test_api_routes(world):
    client = TestClient(create_app())
    body = client.get("/api/recipes").json()
    assert body["close_short"] == recipes.CLOSE_SHORT
    assert {r["key"] for r in body["recipes"]} >= {"fn:Cats1_JT", "imp"}
    d = client.get("/api/recipes/Cats1_JT").json()
    assert d["ready"] and d["recipe"]["kind"] == "jumpstart" and len(d["cards"]) == 2
    assert client.get("/api/recipes/Nope").status_code == 404


def test_read_job_takes_names_or_a_set(world, monkeypatch):
    from magic_manager.api import decks as api
    seen: list = []
    monkeypatch.setattr(recipes, "ensure_read", lambda names, **k: seen.append(names) or len(names))
    res = api._run_read(api.ReadRecipesInput(file_names=["Cats1_JT"], set="tst"), lambda e: None)
    assert seen == [["Cats1_JT", "Boss_TST", "Later_TST", "Tiny_TST"]] and res.summary == "Read 4 deck recipes"
    with pytest.raises(ValueError):
        api._run_read(api.ReadRecipesInput(set="zzz"), lambda e: None)
