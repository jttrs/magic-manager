"""EDHREC rankings in Explore: offline ranking identity, cached read-or-sync,
the collection join, and the web read + job."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from magic_manager import db, edhrec, explore, inventory, sets
from magic_manager.web.app import create_app

KRENKO, MAGDA = "00000000-0000-0000-0000-0000000000a1", "00000000-0000-0000-0000-0000000000a2"
OID = {"Krenko, Mob Boss": "oracle-krenko", "Magda, Brazen Outlaw": "oracle-magda"}


def _page(tag, rows):
    return {"header": "Test", "container": {"json_dict": {"cardlists": [{"tag": tag, "cardviews": [
        {"name": n, "slug": edhrec.slugify(n), "num_decks": d, **({"rank": r} if r else {})} for n, d, r in rows
    ]}]}}}


@pytest.fixture
def pages(monkeypatch, seed_cards, make_card):
    seed_cards([
        make_card(id=KRENKO, oracle_id=OID["Krenko, Mob Boss"], name="Krenko, Mob Boss",
                  type_line="Legendary Creature — Goblin Warrior", collector_number="1", prices={"usd": "2.13"},
                  color_identity=["R"]),
        make_card(id=MAGDA, oracle_id=OID["Magda, Brazen Outlaw"], name="Magda, Brazen Outlaw",
                  type_line="Legendary Creature — Dwarf Berserker", collector_number="2"),
    ])
    inventory.inventory_add(KRENKO, "nonfoil", 2)
    calls: list[tuple] = []
    page = _page("mono-redcommanders", [("Krenko, Mob Boss", 885, None), ("Magda, Brazen Outlaw", 434, None)])

    def color_ranking(slug, tf=None):
        calls.append(("color", slug, tf))
        return page
    monkeypatch.setattr(edhrec, "color_ranking", color_ranking)
    monkeypatch.setattr(edhrec, "top_ranking", lambda seg="week": (calls.append(("top", seg)), _page("salt", [("Krenko, Mob Boss", 9, None)]))[1])
    monkeypatch.setattr(edhrec, "resolve_names_to_oracle",
                        lambda names, **_: {n.casefold(): {"oracle_id": OID.get(n)} for n in names if n in OID})
    return calls


@pytest.mark.parametrize("kw, key", [
    (dict(scope="salt", timeframe="week"), ("salt", "all", "")),
    (dict(scope="cards", timeframe="month"), ("cards", "month", "")),
    (dict(color="wu"), ("commanders", "week", "color:azorius")),
    (dict(tag="Goblins"), ("commanders", "all", "tag:goblins")),
])
def test_ranking_key_is_offline_identity(kw, key):
    assert tuple(vars(edhrec.ranking_key(**kw)).values()) == key


def test_ranking_key_set_family_resolves_anchor(monkeypatch):
    monkeypatch.setattr(sets, "resolve", lambda s: type("R", (), {"code": "fin", "all_codes": ["fin"]})())
    assert edhrec.ranking_key(set_family="Final Fantasy").filter == "set:fin"


def test_ranking_key_rejects_stacked_filters():
    with pytest.raises(edhrec.EdhrecError):
        edhrec.ranking_key(color="r", tag="goblins")
    with pytest.raises(edhrec.EdhrecError):
        edhrec.ranking_key("cards", color="r")


@pytest.mark.parametrize("key, title", [
    (edhrec.RankingKey("commanders", "week", ""), "Top commanders · past week"),
    (edhrec.RankingKey("commanders", "year", "color:mono-red"), "Top commanders · Mono-Red · past 2 years"),
    (edhrec.RankingKey("commanders", "all", "tag:goblins"), "Top commanders · Goblins tag"),
    (edhrec.RankingKey("commanders", "", "set:fin"), "Top commanders · FIN family"),
    (edhrec.RankingKey("salt", "all", ""), "Saltiest cards"),
])
def test_ranking_title(key, title):
    assert edhrec.ranking_title(key) == title


def test_sync_stores_under_ranking_key_and_rankings_reads_cache(tmp_db, pages):
    key = edhrec.ranking_key(color="r")
    assert edhrec.cached_rankings(key) is None
    first = edhrec.rankings(color="r")
    assert [r.name for r in first.rows] == ["Krenko, Mob Boss", "Magda, Brazen Outlaw"]
    assert first.fetched_at and len(pages) == 1
    again = edhrec.rankings(color="r")                      # cached → no fetch
    assert len(pages) == 1 and [r.rank for r in again.rows] == [1, 2]
    edhrec.rankings(color="r", refresh=True)                # refresh → fetch
    assert len(pages) == 2


def test_cached_rankings_reads_only_the_newest_batch(tmp_db, pages):
    edhrec.sync_rankings("commanders", color="r")
    with db.connect() as conn:                              # an entity that fell off the list
        conn.execute("""INSERT INTO edhrec_rankings (scope, timeframe, filter, entity_slug, entity_name,
                        rank, fetched_at) VALUES ('commanders','week','color:mono-red','old','Old', 3, '2000-01-01')""")
        conn.commit()
    res = edhrec.cached_rankings(edhrec.ranking_key(color="r"))
    assert [r.name for r in res.rows] == ["Krenko, Mob Boss", "Magda, Brazen Outlaw"]


def test_explore_ranking_joins_collection_and_never_fetches(tmp_db, pages):
    empty = explore.ranking(color="r")
    assert not empty.cached and empty.rows == [] and not pages
    edhrec.sync_rankings("commanders", color="r")
    r = explore.ranking(color="r")
    assert r.cached and r.title == "Top commanders · Mono-Red · past week"
    krenko, magda = r.rows
    assert (krenko.rank, krenko.num_decks, krenko.facts.owned, krenko.facts.free) == (1, 885, 2, 2)
    assert krenko.facts.lowest_usd == 2.13 and krenko.facts.scryfall_id == KRENKO
    assert magda.facts.owned == 0


@pytest.fixture
def client(tmp_db):
    with TestClient(create_app(serve_frontend=False)) as c:
        yield c


def test_ranking_endpoint_and_job(client, pages, fake_scryfall):
    r = client.get("/api/explore/ranking", params={"scope": "commanders", "color": "r"})
    assert r.status_code == 200 and r.json()["cached"] is False
    stacked = client.get("/api/explore/ranking", params={"color": "r", "tag": "goblins"})
    assert stacked.status_code == 200 and stacked.json()["cached"] is False   # filters stack now
    assert client.get("/api/explore/ranking", params={"scope": "salt", "color": "r"}).status_code == 422

    job = client.post("/api/jobs/edhrec.rankings", json={"scope": "commanders", "color": "r"})
    assert job.status_code == 202, job.text
    job_id = job.json()["id"]
    with client.stream("GET", f"/api/jobs/{job_id}/events") as s:
        body = "".join(s.iter_text())
    assert "succeeded" in body and "Matching 2 cards" in body

    got = client.get("/api/explore/ranking", params={"color": "r"}).json()
    assert got["cached"] and got["filter"] == "color:mono-red"
    assert [(x["rank"], x["name"], x["facts"]["owned"]) for x in got["rows"]] == [(1, "Krenko, Mob Boss", 2), (2, "Magda, Brazen Outlaw", 0)]

    opts = client.get("/api/explore/ranking/options").json()
    assert opts["timeframes"] == ["week", "month", "year"]
    assert len(opts["colors"]) == 32 and opts["colors"][0] == {"slug": "colorless", "label": "Colorless", "colors": ""}


def test_empty_ranking_reads_as_empty_not_never_read(tmp_db, monkeypatch):
    """A list EDHREC leaves empty is a calm empty result, recorded so the web
    doesn't re-fetch forever — and no empty body is stored as a page."""
    class _RS:
        code, all_codes = "acr", ["acr"]
    monkeypatch.setattr(sets, "resolve", lambda s: _RS())
    monkeypatch.setattr(edhrec, "set_page", lambda code: {"header": "x", "container": {"json_dict": {"cardlists": []}}})
    res = edhrec.rankings(set_family="acr")
    assert res.rows == [] and res.fetched_at
    hit = edhrec.cached_rankings(edhrec.ranking_key(set_family="acr"))
    assert hit is not None and hit.rows == []
    r = explore.ranking(set_family="acr")
    assert r.cached and r.rows == [] and r.total == 0 and r.base == 0
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM edhrec_pages").fetchone()[0] == 0


def test_tag_redirect_is_followed_and_a_missing_tag_reads_plainly(tmp_db, pages, monkeypatch):
    seen: list[str] = []

    def tag_ranking(slug):
        seen.append(slug)
        if slug == "goblin":
            return {"redirect": "/tags/goblins"}
        if slug == "goblins":
            return _page("topcommanders", [("Krenko, Mob Boss", 900, None)])
        raise edhrec.EdhrecError("edhrec.sh raw tags/x exited 6: <Error>AccessDenied</Error> HTTP 403 from …")
    monkeypatch.setattr(edhrec, "tag_ranking", tag_ranking)
    res = edhrec.rankings(tag="goblin")
    assert seen == ["goblin", "goblins"] and [r.name for r in res.rows] == ["Krenko, Mob Boss"]
    with db.connect() as conn:
        assert [r[0] for r in conn.execute("SELECT slug FROM edhrec_pages")] == ["tags/goblins"]
    with pytest.raises(edhrec.EdhrecError, match="EDHREC has no “gobblinz” tag") as e:
        edhrec.rankings(tag="gobblinz")
    assert "AccessDenied" not in str(e.value)


def test_set_page_reads_a_bare_commanders_list_and_follows_redirects(tmp_db, monkeypatch):
    """ACR's page lists ``commanders`` (no per-code suffix); afic redirects to
    fic, which redirects to fin. Stubs are followed once and never stored."""
    class _RS:
        code, all_codes = "acr", ["acr", "afic"]
    monkeypatch.setattr(sets, "resolve", lambda s: _RS())
    monkeypatch.setattr(edhrec, "resolve_names_to_oracle", lambda names, **_: {})
    pages = {
        "acr": {"header": "ACR", "container": {"json_dict": {"cardlists": [
            {"tag": "commanders", "cardviews": [{"name": "Ezio Auditore da Firenze", "slug": "ezio", "num_decks": 900}]},
            {"tag": "partnerswith", "cardviews": [{"name": "Not A Commander List", "slug": "nope", "num_decks": 9999}]},
            {"tag": "cards", "cardviews": [{"name": "Some Card", "slug": "some", "num_decks": 5000}]},
        ]}}},
        "afic": {"redirect": "/sets/fic"},
        "fic": {"redirect": "/sets/fin"},
        "fin": {"header": "FIN", "container": {"json_dict": {"cardlists": [
            {"tag": "commanders(fin)", "cardviews": [{"name": "Cloud", "slug": "cloud", "num_decks": 1000}]}]}}},
    }
    asked: list[str] = []
    monkeypatch.setattr(edhrec, "set_page", lambda code: (asked.append(code), pages[code])[1])
    with db.connect() as conn:   # an older sync stored the stub as a page
        edhrec._store_page(conn, page_type="commanders", slug="sets/afic", timeframe="", page=pages["afic"], at="2026-01-01")
        conn.commit()
    res = edhrec.sync_rankings(set_family="acr")
    assert [r.name for r in res.rows] == ["Cloud", "Ezio Auditore da Firenze"]
    assert asked == ["acr", "afic", "fic", "fin"]
    with db.connect() as conn:
        assert sorted(r[0] for r in conn.execute("SELECT slug FROM edhrec_pages")) == ["sets/acr", "sets/fin"]


def _paged(tag, start, n, more, total=9):
    cvs = [{"name": f"Card {i}", "slug": f"card-{i}", "num_decks": 10_000 - i, "rank": i} for i in range(start, start + n)]
    return cvs, {"tag": tag, "cardviews": cvs, "more": more, "total_pages": total}


def test_paginated_rankings_read_the_pool_deep(tmp_db, monkeypatch):
    monkeypatch.setattr(edhrec, "resolve_names_to_oracle", lambda names, **_: {})
    _, first = _paged("pastweek", 1, 100, "commanders/week-pastweek-1.json")
    monkeypatch.setattr(edhrec, "commanders_ranking", lambda tf="week": {"container": {"json_dict": {"cardlists": [first]}}})
    asked: list[str] = []

    def more_page(path):
        asked.append(path)
        n = int(path.rsplit("-", 1)[1].removesuffix(".json"))
        if n == 3:
            raise edhrec.EdhrecError("HTTP 429")          # a failed later page ends the walk
        cvs, _ = _paged("", n * 100 + 1, 100, None)
        return {"cardviews": cvs, "more": f"commanders/week-pastweek-{n + 1}.json", "total_pages": 9}
    monkeypatch.setattr(edhrec, "more_page", more_page)
    res = edhrec.sync_rankings("commanders", "week")
    assert asked == ["commanders/week-pastweek-1.json", "commanders/week-pastweek-2.json", "commanders/week-pastweek-3.json"]
    assert len(res.rows) == 300 and res.rows[-1].rank == 300
    r = explore.ranking("commanders", "week", limit=100)
    assert (len(r.rows), r.total, r.pool) == (100, 300, 300)
    page2 = explore.ranking("commanders", "week", offset=100, limit=50)
    assert [x.rank for x in page2.rows] == list(range(101, 151))
    # The short read is recorded, not silent: the rows read are kept, marked partial.
    assert res.partial_reason == "rate_limited" and r.partial_reason == "rate_limited"
    assert edhrec.cached_rankings(edhrec.ranking_key("commanders", "week")).partial_reason == "rate_limited"


def test_partial_marker_clears_on_a_full_read_and_reaches_the_api(client, monkeypatch):
    monkeypatch.setattr(edhrec, "resolve_names_to_oracle", lambda names, **_: {})
    _, first = _paged("pastweek", 1, 100, "commanders/week-pastweek-1.json", total=3)
    monkeypatch.setattr(edhrec, "commanders_ranking", lambda tf="week": {"container": {"json_dict": {"cardlists": [first]}}})
    fail = {"on": True}

    def more_page(path):
        n = int(path.rsplit("-", 1)[1].removesuffix(".json"))
        if fail["on"]:
            raise edhrec.EdhrecError("edhrec.sh: HTTP 429 from EDHREC. Backing off for 35s.")
        cvs, _ = _paged("", n * 100 + 1, 100, None)
        return {"cardviews": cvs, "more": f"commanders/week-pastweek-{n + 1}.json", "total_pages": 3}
    monkeypatch.setattr(edhrec, "more_page", more_page)

    edhrec.sync_rankings("commanders", "week")
    got = client.get("/api/explore/ranking", params={"scope": "commanders", "timeframe": "week"}).json()
    assert (got["base"], got["pool_complete"], got["pool_partial_reason"]) == (100, False, "rate_limited")

    fail["on"] = False
    assert edhrec.rankings("commanders", "week", refresh=True).partial_reason is None
    got = client.get("/api/explore/ranking", params={"scope": "commanders", "timeframe": "week"}).json()
    assert (got["base"], got["pool_complete"], got["pool_partial_reason"]) == (300, True, None)


def test_ranking_options_offer_every_paper_family_owned_first(client, fake_scryfall, seed_cards, make_card):
    fake_scryfall(all_sets=[
        {"code": "blb", "name": "Bloomburrow", "set_type": "expansion", "released_at": "2024-08-02"},
        {"code": "pblb", "name": "Bloomburrow Promos", "set_type": "promo", "parent_set_code": "blb"},
        {"code": "fin", "name": "Final Fantasy", "set_type": "expansion", "released_at": "2025-06-13"},
        {"code": "ltr", "name": "The Lord of the Rings", "set_type": "expansion", "released_at": "2023-06-23"},
        {"code": "ydmu", "name": "Alchemy: Dominaria", "set_type": "alchemy", "digital": True},
    ])
    seed_cards([make_card(id="00000000-0000-0000-0000-0000000000f1", set="pblb", collector_number="1")])
    inventory.inventory_add("00000000-0000-0000-0000-0000000000f1", "nonfoil", 1)
    fams = client.get("/api/explore/ranking/options").json()["families"]
    assert [(f["value"], f["owned"]) for f in fams] == [("blb", True), ("fin", False), ("ltr", False)]
    assert fams[1] == {"value": "fin", "label": "Final Fantasy", "year": "2025", "owned": False}


def test_pool_depth_is_capped(tmp_db, monkeypatch):
    monkeypatch.setattr(edhrec, "resolve_names_to_oracle", lambda names, **_: {})
    monkeypatch.setattr(edhrec, "RANKING_POOL_PAGES", 2)
    _, first = _paged("x", 1, 100, "top/week-pastweek-1.json", total=300)
    monkeypatch.setattr(edhrec, "top_ranking", lambda seg="week": {"container": {"json_dict": {"cardlists": [first]}}})
    asked: list[str] = []
    monkeypatch.setattr(edhrec, "more_page", lambda p: (asked.append(p), {"cardviews": _paged("", 101, 100, None)[0], "more": "top/week-pastweek-2.json"})[1])
    assert len(edhrec.sync_rankings("cards", "week").rows) == 200 and len(asked) == 1


GOB, ELF, TREASURE = "00000000-0000-0000-0000-0000000000e1", "00000000-0000-0000-0000-0000000000e2", "00000000-0000-0000-0000-0000000000e3"


def test_filters_stack_on_the_most_selective_base(tmp_db, pages, seed_cards, make_card, monkeypatch):
    """Set family is the base read; color and tag narrow it locally (tag by its
    EDHREC list OR a matching creature type)."""
    seed_cards([
        make_card(id=GOB, oracle_id="oracle-gob", name="Set Goblin", collector_number="3",
                  type_line="Legendary Creature — Goblin Shaman", color_identity=["R"]),
        make_card(id=ELF, oracle_id="oracle-elf", name="Set Elf", collector_number="4",
                  type_line="Legendary Creature — Elf Druid", color_identity=["G"]),
        make_card(id=TREASURE, oracle_id="oracle-tre", name="Set Pirate", collector_number="5",
                  type_line="Legendary Creature — Human Pirate", color_identity=["R"]),
    ])
    oid = {**OID, "Set Goblin": "oracle-gob", "Set Elf": "oracle-elf", "Set Pirate": "oracle-tre"}
    monkeypatch.setattr(edhrec, "resolve_names_to_oracle",
                        lambda names, **_: {n.casefold(): {"oracle_id": oid.get(n)} for n in names if n in oid})

    class _RS:
        code, all_codes = "tst", ["tst"]
    monkeypatch.setattr(sets, "resolve", lambda s: _RS())
    monkeypatch.setattr(edhrec, "set_page", lambda code: _page("commanders", [
        ("Set Goblin", 300, None), ("Set Elf", 200, None), ("Set Pirate", 100, None), ("Krenko, Mob Boss", 50, None)]))
    monkeypatch.setattr(edhrec, "tag_ranking", lambda slug: _page("topcommanders", [("Set Pirate", 10, None)]))

    assert explore.ranking_bases(color="r", tag="goblins", set_family="tst") == [
        dict(scope="commanders", timeframe="week", set_family="tst"),
        dict(scope="commanders", timeframe="week", tag="goblins")]
    assert not explore.ranking(color="r", set_family="tst").cached
    explore.sync_ranking(color="r", tag="goblins", set_family="tst")
    assert not pages                                          # never read the color page: set is the base

    red = explore.ranking(color="r", set_family="tst")
    assert [x.name for x in red.rows] == ["Set Goblin", "Set Pirate", "Krenko, Mob Boss"]
    assert red.local_filters == ["color"] and red.title == "Top commanders · TST family · Mono-Red"
    gob = explore.ranking(color="r", tag="goblins", set_family="tst")
    # Goblin by creature type, Krenko too (Goblin Warrior), Pirate by the tag's own list
    assert [x.name for x in gob.rows] == ["Set Goblin", "Set Pirate", "Krenko, Mob Boss"]
    assert gob.local_filters == ["color", "tag"]
    # tag alone on the set base: Elf is neither a goblin nor on the tag's list
    tag_only = explore.ranking(tag="goblins", set_family="tst")
    assert [x.name for x in tag_only.rows] == ["Set Goblin", "Set Pirate", "Krenko, Mob Boss"]
    assert (tag_only.base, tag_only.pool, tag_only.local_filters) == (4, 3, ["tag"])
    monkeypatch.setattr(edhrec, "tag_ranking", lambda slug: _page("topcommanders", [("Nobody Here", 1, None)]))
    explore.sync_ranking(tag="angels", set_family="tst", refresh=True)
    nothing = explore.ranking(tag="angels", set_family="tst")
    assert nothing.rows == [] and (nothing.base, nothing.pool) == (4, 0)
    owned = explore.ranking(set_family="tst", own="owned")
    assert [x.name for x in owned.rows] == ["Krenko, Mob Boss"] and (owned.total, owned.pool, owned.owned, owned.unused) == (1, 4, 1, 1)
    assert [x.name for x in explore.ranking(set_family="tst", q="ELF").rows] == ["Set Elf"]


@pytest.mark.parametrize("tag, line, hit", [
    ("goblins", "Legendary Creature — Goblin Warrior", True),
    ("elves", "Legendary Creature — Elf Druid", True),
    ("dwarves", "Legendary Creature — Dwarf Berserker", True),
    ("faeries", "Legendary Creature — Faerie Rogue", True),
    ("allies", "Legendary Creature — Kor Ally", True),
    ("goblins", "Legendary Creature — Human Wizard", False),
    ("treasure", "Legendary Creature — Human Pirate", False),
    ("wizards", "Legendary Enchantment Creature — Human // Legendary Creature — Human Wizard", True),
])
def test_typal_match(tag, line, hit):
    assert explore.typal_match(tag, line) is hit


def test_stacked_ranking_endpoint_pages(client, pages):
    edhrec.sync_rankings("commanders", color="r")
    got = client.get("/api/explore/ranking", params={"color": "r", "limit": 1}).json()
    assert got["cached"] and got["total"] == 2 and got["pool"] == 2 and [x["name"] for x in got["rows"]] == ["Krenko, Mob Boss"]
    assert (got["owned"], got["unused"]) == (1, 1)
    more = client.get("/api/explore/ranking", params={"color": "r", "offset": 1, "limit": 50}).json()
    assert [x["name"] for x in more["rows"]] == ["Magda, Brazen Outlaw"] and more["offset"] == 1
    assert client.get("/api/explore/ranking", params={"own": "free"}).status_code == 422


def test_sync_rankings_names_with_the_shared_title(tmp_db, pages):
    assert edhrec.sync_rankings("commanders", color="r").name == "Top commanders · Mono-Red · past week"


KRAUM, TYMNA, TERGRID = ("00000000-0000-0000-0000-0000000000b1", "00000000-0000-0000-0000-0000000000b2",
                         "00000000-0000-0000-0000-0000000000b3")


@pytest.fixture
def partners(seed_cards, make_card):
    seed_cards([
        make_card(id=KRAUM, oracle_id="oracle-kraum", name="Kraum, Ludevic's Opus", collector_number="11",
                  type_line="Legendary Creature — Zombie Horror", mana_cost="{3}{U}{R}", color_identity=["U", "R"],
                  prices={"usd": "1.50"}),
        make_card(id=TYMNA, oracle_id="oracle-tymna", name="Tymna the Weaver", collector_number="12",
                  type_line="Legendary Creature — Human Cleric", mana_cost="{1}{W}{B}", color_identity=["W", "B"],
                  prices={"usd": "2.25"}),
        make_card(id=TERGRID, oracle_id="oracle-tergrid", name="Tergrid, God of Fright // Tergrid's Lantern",
                  collector_number="13", type_line="Legendary Creature — God // Legendary Artifact"),
    ])
    inventory.inventory_add(KRAUM, "nonfoil", 3)
    inventory.inventory_add(TYMNA, "nonfoil", 1)


def test_resolve_partner_pair_but_not_a_double_faced_card(tmp_db, partners, monkeypatch):
    monkeypatch.setattr(edhrec.scryfall, "collection", lambda *_: pytest.fail("local names need no Scryfall"))
    got = edhrec.resolve_names_to_oracle(
        ["Kraum, Ludevic's Opus // Tymna the Weaver", "Tergrid, God of Fright // Tergrid's Lantern"])
    pair = got["kraum, ludevic's opus // tymna the weaver"]
    assert pair["oracle_id"] is None and [p["oracle_id"] for p in pair["partners"]] == ["oracle-kraum", "oracle-tymna"]
    assert got["tergrid, god of fright // tergrid's lantern"]["oracle_id"] == "oracle-tergrid"
    assert edhrec.partner_halves("Sol Ring") is None
    assert edhrec.partner_halves("A // B") == ("A", "B")


def test_explore_ranking_joins_partner_pairs(tmp_db, partners, monkeypatch):
    pair = "Kraum, Ludevic's Opus // Tymna the Weaver"
    monkeypatch.setattr(edhrec, "commanders_ranking", lambda tf=None: _page("commanders", [(pair, 500, 1)]))
    monkeypatch.setattr(edhrec.scryfall, "collection", lambda *_: ([], []))
    edhrec.sync_rankings("commanders")
    row, = explore.ranking().rows
    f = row.facts
    assert f.oracle_id is None and f.scryfall_id == KRAUM and f.mana_cost == "{3}{U}{R}"
    assert f.partner.scryfall_id == TYMNA and f.partner.mana_cost == "{1}{W}{B}"
    assert f.lowest_usd == 3.75 and f.color_identity == ["W", "U", "B", "R"]
    assert (f.owned, f.free) == (1, 1)
    from magic_manager.api import explore as api_explore
    out = api_explore._facts(f)
    assert out.partner.scryfall_url and out.partner.mana_cost == "{1}{W}{B}"


def test_partner_pair_edges(tmp_db, partners, seed_cards, make_card, monkeypatch):
    monkeypatch.setattr(edhrec.scryfall, "collection", lambda *_: ([], []))
    # (a) both "halves" are faces of one card → not a pair
    seed_cards([make_card(id="00000000-0000-0000-0000-0000000000c1", oracle_id="oracle-mdfc",
                          name="Front Face", collector_number="21"),
                make_card(id="00000000-0000-0000-0000-0000000000c2", oracle_id="oracle-mdfc",
                          name="Back Face", collector_number="22")])
    assert "front face // back face" not in edhrec.resolve_names_to_oracle(["Front Face // Back Face"])
    # (b) one half unknown → no pair facts
    assert explore.facts_by_name(["Kraum, Ludevic's Opus // Nobody Here"]) == {}
    # (c) an unpriced half → the pair has no price
    a = explore.Facts(oracle_id="a", lowest_usd=1.0, color_identity=["R"], owned=2, free=1)
    b = explore.Facts(oracle_id="b", lowest_usd=None, color_identity=["W"], owned=0, free=0)
    pair = explore.pair_facts(a, b)
    assert pair.lowest_usd is None and pair.color_identity == ["W", "R"] and (pair.owned, pair.free) == (0, 0)


def test_partner_halves_fetched_from_scryfall_unless_local_only(tmp_db, monkeypatch, make_card):
    sam = make_card(id="00000000-0000-0000-0000-0000000000d1", oracle_id="oracle-sam",
                    name="Sam, Loyal Attendant", collector_number="31")
    frodo = make_card(id="00000000-0000-0000-0000-0000000000d2", oracle_id="oracle-frodo",
                      name="Frodo, Adventurous Hobbit", collector_number="32")
    asked: list[list[str]] = []

    def collection(ids):
        asked.append([i["name"] for i in ids])
        return [c for c in (sam, frodo) if c["name"] in {i["name"] for i in ids}], []
    monkeypatch.setattr(edhrec.scryfall, "collection", collection)
    pair = "Frodo, Adventurous Hobbit // Sam, Loyal Attendant"
    assert edhrec.resolve_names_to_oracle([pair], local_only=True) == {} and not asked
    got = edhrec.resolve_names_to_oracle([pair])
    assert [p["oracle_id"] for p in got[pair.casefold()]["partners"]] == ["oracle-frodo", "oracle-sam"]
    assert set(asked[0]) == {pair, "Frodo, Adventurous Hobbit", "Sam, Loyal Attendant"}
    # the halves were upserted: a local-only read now finds the pair without Scryfall
    asked.clear()
    assert edhrec.resolve_names_to_oracle([pair], local_only=True)[pair.casefold()]["partners"]
    assert not asked


def test_non_local_double_faced_card_resolves_as_one_card(tmp_db, monkeypatch, make_card):
    dfc = make_card(id="00000000-0000-0000-0000-0000000000e1", oracle_id="oracle-dfc",
                    name="Delver of Secrets // Insectile Aberration", collector_number="41")
    monkeypatch.setattr(edhrec.scryfall, "collection",
                        lambda ids: ([dfc], [i for i in ids if i["name"] != dfc["name"]]))
    got = edhrec.resolve_names_to_oracle([dfc["name"]])
    assert got[dfc["name"].casefold()]["oracle_id"] == "oracle-dfc"
    assert "partners" not in got[dfc["name"].casefold()]
