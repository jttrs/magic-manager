import pytest

from magic_manager import card_earmarks as ce, db, decks, inventory, scryfall
from magic_manager.deck_edit import DraftCard

LEADER, ANGEL, BOLT, BANNED, SOL, SOL2 = (f"00000000-0000-0000-0000-00000000000{i}" for i in range(1, 7))


def _oid(n):
    return f"aaaaaaaa-0000-0000-0000-00000000000{n}"


@pytest.fixture
def cards(seed_cards, make_card, monkeypatch):
    legal = {"commander": "legal", "modern": "legal"}
    seed_cards([
        make_card(id=LEADER, oracle_id=_oid(1), name="Squall", color_identity=["W", "B"], type_line="Legendary Creature — Human", legalities=legal),
        make_card(id=ANGEL, oracle_id=_oid(2), name="Angel", collector_number="2", color_identity=["W"], legalities=legal),
        make_card(id=BOLT, oracle_id=_oid(3), name="Bolt", collector_number="3", color_identity=["R"], legalities=legal),
        make_card(id=BANNED, oracle_id=_oid(4), name="Bad Card", collector_number="4", color_identity=[], legalities={"commander": "banned", "modern": "not_legal"}),
        make_card(id=SOL, oracle_id=_oid(5), name="Sol", collector_number="5", color_identity=[], legalities=legal, finishes=["nonfoil"]),
        make_card(id=SOL2, oracle_id=_oid(5), name="Sol", set="alt", collector_number="9", color_identity=[], legalities=legal),
    ])
    monkeypatch.setattr(scryfall, "collection", lambda ids: ([], list(ids)))
    decks.deck_create("squall", "Squall", format="commander")
    decks.deck_create("other", "Other")


def test_save_upserts_by_card_and_validates(cards):
    a = ce.save(SOL, printing=SOL2, finish="foil", reason="collect", note="  alt art  ")
    assert (a.oracle_id, a.name, a.scryfall_id, a.finish, a.reason, a.note) == (_oid(5), "Sol", SOL2, "foil", "collect", "alt art")
    b = ce.save("sol", reason="deck", deck="squall")           # by name; same card → replaced, not duplicated
    assert (b.scryfall_id, b.finish, b.reason, b.deck_slug, b.note) == (None, None, "deck", "squall", None)
    assert b.earmarked_at == a.earmarked_at
    assert [e.oracle_id for e in ce.listing()] == [_oid(5)]
    with pytest.raises(ValueError, match="no foil"):
        ce.save(SOL, printing=SOL, finish="foil")
    with pytest.raises(ValueError, match="not 'Sol'"):
        ce.save(SOL, printing=ANGEL)
    with pytest.raises(ValueError, match="needs a preferred printing"):
        ce.save(SOL, finish="foil")
    with pytest.raises(ValueError, match="reason"):
        ce.save(SOL, reason="maybe")
    with pytest.raises(LookupError, match="no deck"):
        ce.save(SOL, deck="nope")
    assert ce.remove(_oid(5)) and not ce.remove(_oid(5))


def test_listing_filters_marks_and_deck_delete_clears_pointer(cards):
    ce.save(ANGEL, reason="deck", deck="squall")
    ce.save(BOLT, reason="collect")
    assert [e.name for e in ce.listing(reason="collect")] == ["Bolt"]
    assert [e.name for e in ce.listing(deck="squall")] == ["Angel"]
    assert ce.marks([_oid(2), _oid(4), None]) == {_oid(2)}
    decks.deck_delete("squall")
    assert ce.listing(reason="deck")[0].deck_slug is None


def test_entries_use_preferred_else_your_most_free_printing(cards):
    inventory.inventory_add(SOL2, "nonfoil", 2)
    ce.save(SOL)
    (e,) = ce.entries(ce.listing())
    assert (e["printing"]["scryfall_id"], e["owned"], e["free"]) == (SOL2, 2, 2)
    ce.save(SOL, printing=SOL)
    assert ce.entries(ce.listing())[0]["printing"]["scryfall_id"] == SOL


def test_for_deck_filters_on_format_and_commander_colours(cards):
    ce.save(ANGEL, reason="deck", deck="squall")
    for c in (BOLT, BANNED, SOL):
        ce.save(c)
    draft = [DraftCard(LEADER, "commander", "nonfoil", 1), DraftCard(SOL, "main", "either", 1)]
    r = ce.for_deck("squall", draft)
    assert (r["format"], r["commander_colors"]) == ("commander", ["W", "B"])
    assert [e["earmark"]["name"] for e in r["for_deck"]] == ["Angel"]
    assert [(e["earmark"]["name"], e["in_deck"]) for e in r["legal"]] == [("Sol", True)]
    hidden = {e["earmark"]["name"]: [b["code"] for b in e["reasons"]] for e in r["hidden"]}
    assert hidden == {"Bolt": ["colour_identity"], "Bad Card": ["banned"]}
    assert r["rule"] == "Legal in Commander · within white, black"
    assert r["hidden"][0]["reasons"][0]["message"] in {"Outside the commander’s colors (white, black)", "Banned in Commander"}

    # A card pointed at this deck stays listed there, with its blockers attached.
    ce.save(BOLT, reason="deck", deck="squall")
    r = ce.for_deck("squall", draft)
    (pinned,) = [e for e in r["for_deck"] if e["earmark"]["name"] == "Bolt"]
    assert [b["code"] for b in pinned["reasons"]] == ["colour_identity"]
    assert "Bolt" not in {e["earmark"]["name"] for e in r["hidden"]}

    # No commander yet → colours aren't filtered; a deck with no format and no commander isn't filtered at all.
    open_ = ce.for_deck("squall", [])
    assert {e["earmark"]["name"] for e in open_["hidden"]} == {"Bad Card"}
    assert open_["rule"] == "Legal in Commander · no commander yet, so colors aren’t checked"
    free = ce.for_deck("other", [])
    assert free["format"] is None and not free["hidden"] and free["rule"] == "No format set, so nothing is filtered"
    with pytest.raises(LookupError):
        ce.for_deck("nope", [])


def test_partner_commanders_union_their_colours(cards, seed_cards, make_card):
    seed_cards([make_card(id="00000000-0000-0000-0000-000000000009", oracle_id=_oid(9), name="Partner",
                          collector_number="99", color_identity=["R"], type_line="Legendary Creature — Elf",
                          legalities={"commander": "legal"})])
    ce.save(BOLT)
    draft = [DraftCard(LEADER, "commander", "nonfoil", 1), DraftCard("00000000-0000-0000-0000-000000000009", "commander", "nonfoil", 1)]
    r = ce.for_deck("squall", draft)
    assert r["commander_colors"] == ["W", "B", "R"]
    assert [e["earmark"]["name"] for e in r["legal"]] == ["Bolt"]


def test_blockers_rule():
    codes = lambda *a: [b["code"] for b in ce.blockers(*a)]
    f = {"ci": ["R"], "legalities": {"modern": "not_legal", "commander": "restricted"}}
    assert ce.blockers("modern", None, f) == [{"code": "not_legal", "message": "Not legal in Modern"}]
    assert codes("commander", {"R", "G"}, f) == []
    assert codes("cube", None, f) == []                           # a format Scryfall doesn't rule on
    assert codes("commander", set(), {"ci": [], "legalities": None}) == ["no_legality"]
    assert codes(None, None, None) == ["not_in_catalog"]


def test_earmarks_are_in_undo(cards):
    from magic_manager import layout, undo
    assert "card_earmarks" in layout.USER_TABLES
    assert any("card_earmarks" in ts for _, ts in undo.DETAIL_GROUPS)
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM card_earmarks").fetchone()[0] == 0


def test_api_routes(cards):
    from fastapi.testclient import TestClient

    from magic_manager.web.app import create_app

    c = TestClient(create_app(serve_frontend=False))
    r = c.put("/api/earmarks/cards", json={"card": ANGEL, "reason": "deck", "deck": "squall", "note": "lifelink"})
    assert r.status_code == 200 and r.json()["deck_slug"] == "squall"
    assert c.put("/api/earmarks/cards", json={"card": ANGEL, "reason": "nope"}).status_code == 422
    assert c.put("/api/earmarks/cards", json={"card": ANGEL, "deck": "missing"}).status_code == 404
    assert c.put("/api/earmarks/cards", json={"card": ANGEL, "extra": 1}).status_code == 422
    (e,) = c.get("/api/earmarks/cards").json()
    assert (e["earmark"]["name"], e["printing"]["scryfall_id"]) == ("Angel", ANGEL)
    assert c.get("/api/earmarks/cards", params={"reason": "collect"}).json() == []
    d = c.post("/api/decks/squall/earmarked", json={"cards": [{"scryfall_id": LEADER, "board": "commander", "finish": "nonfoil", "count": 1}]}).json()
    assert [x["earmark"]["name"] for x in d["for_deck"]] == ["Angel"] and d["commander_colors"] == ["W", "B"]
    assert c.post("/api/decks/nope/earmarked", json={"cards": []}).status_code == 404
    assert c.delete(f"/api/earmarks/cards/{_oid(2)}").json() == {"removed": True}
    assert c.get("/api/earmarks/cards").json() == []


def test_collection_cards_carry_the_earmark(cards, monkeypatch):
    from magic_manager import collection_view
    from magic_manager.api import collection as collection_api

    class _FC:
        summary = type("S", (), {})()
    fc = _FC()
    fc.summary.__dict__.update(code="tst", name="Test", printings=2, owned_printings=0, owned_copies=0,
                               owned_usd=0.0, missing_printings=2, missing_usd=0.0, sets=[])

    def _card(sid, oid):
        return collection_view.CollectionCard(
            scryfall_id=sid, oracle_id=oid, name="x", family="tst", set_code="tst", collector_number="1",
            rarity="rare", type_line=None, cmc=None, color_identity=[], released_at=None, finishes=["nonfoil"],
            owned={}, pledged={}, price_usd=None, price_usd_foil=None, image_uri=None, scryfall_uri=None,
            treatment="", standard_frame=True, is_bulk=False, is_chase=False, is_token=False)
    fc.cards = [_card(SOL, _oid(5)), _card(SOL2, _oid(5)), _card(BOLT, _oid(3))]
    monkeypatch.setattr(collection_view, "family_cards", lambda code: fc)
    ce.save("Sol")
    out = collection_api.family_view(["tst"])
    assert {c.scryfall_id: c.earmarked for c in out.cards} == {SOL: True, SOL2: True, BOLT: False}


def test_cli_add_ls_rm(cards):
    from typer.testing import CliRunner

    from magic_manager.cli import app

    run = CliRunner().invoke
    r = run(app, ["earmark", "card", "add", "Bad Card", "--set", "tst", "--cn", "4"])      # no finish preference
    assert r.exit_code == 0, r.output
    assert run(app, ["earmark", "card", "add", "Sol", "--set", "tst", "--cn", "5"]).exit_code == 0   # nonfoil-only printing
    assert run(app, ["earmark", "card", "add", "Sol", "--foil"]).exit_code == 2                     # a finish needs a printing
    r = run(app, ["earmark", "card", "add", "Sol", "--set", "alt", "--cn", "9", "--foil", "--reason", "collect", "--note", "shiny"])
    assert r.exit_code == 0 and "Earmarked Sol (collect)" in r.output
    assert run(app, ["earmark", "card", "add", "Sol", "--set", "alt"]).exit_code == 2
    assert run(app, ["earmark", "card", "add", "Nothing Like It"]).exit_code == 2
    out = run(app, ["earmark", "card", "ls"]).output
    assert "Sol" in out and "ALT #9" in out and "shiny" in out
    import json
    rows = json.loads(run(app, ["earmark", "card", "ls", "--json"]).output)
    assert {e["earmark"]["name"]: e["earmark"]["finish"] for e in rows} == {"Sol": "foil", "Bad Card": None}
    assert "Removed." in run(app, ["earmark", "card", "rm", "Sol"]).output
    run(app, ["earmark", "card", "rm", "Bad Card"])
    assert "(no earmarked cards)" in run(app, ["earmark", "card", "ls"]).output


def _at_v36(path):
    import sqlite3
    con = sqlite3.connect(path)
    con.execute("DROP TABLE IF EXISTS card_earmarks")
    con.execute("UPDATE schema_version SET version = 36")
    con.commit()
    con.close()


def test_v37_migration_single_and_split(tmp_path, monkeypatch):
    import shutil
    import sqlite3

    from magic_manager import layout

    fresh = tmp_path / "fresh.db"
    with db.connect(fresh):
        pass
    single = tmp_path / "single" / "magic_manager.db"
    single.parent.mkdir()
    shutil.copy(fresh, single)
    _at_v36(single)
    with db.connect(single) as conn:                       # the single layout runs V37 on connect
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == db.CURRENT_VERSION
        assert conn.execute("SELECT COUNT(*) FROM card_earmarks").fetchone()[0] == 0

    data = tmp_path / "data"
    (data / "users").mkdir(parents=True)
    catalog, user = data / "catalog.db", data / "users" / "owner.db"
    for dst, keep in ((catalog, layout.CATALOG_TABLES), (user, set(layout.USER_TABLES) - {"card_earmarks"})):
        shutil.copy(fresh, dst)
        con = sqlite3.connect(dst)
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            if t not in keep and t not in layout.INFRA_TABLES:
                con.execute(f"DROP TABLE {t}")
        con.commit()
        con.close()
        _at_v36(dst)
    assert db.MIGRATION_TARGETS[37] == "user"
    assert db.migrate_split_file(catalog, "catalog") == []           # nothing for the catalog
    assert db.migrate_split_file(user, "user") == [37]
    with sqlite3.connect(user) as u:
        assert u.execute("SELECT COUNT(*) FROM card_earmarks").fetchone()[0] == 0
    with sqlite3.connect(catalog) as c:
        assert not c.execute("SELECT 1 FROM sqlite_master WHERE name = 'card_earmarks'").fetchone()
