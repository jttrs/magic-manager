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
                  type_line="Legendary Creature — Goblin Warrior", collector_number="1", prices={"usd": "2.13"}),
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
                        lambda names: {n.casefold(): {"oracle_id": OID.get(n)} for n in names if n in OID})
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


def test_ranking_endpoint_and_job(client, pages):
    r = client.get("/api/explore/ranking", params={"scope": "commanders", "color": "r"})
    assert r.status_code == 200 and r.json()["cached"] is False
    assert client.get("/api/explore/ranking", params={"color": "r", "tag": "goblins"}).status_code == 422
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


def test_empty_ranking_fails_instead_of_storing_nothing(tmp_db, monkeypatch):
    """A page with no lists (e.g. a redirect for a mistyped tag) must fail the
    sync, or the ranking stays 'never read' and the web view waits forever."""
    monkeypatch.setattr(edhrec, "tag_ranking", lambda slug: {"redirect": "/tags/goblins"})
    with pytest.raises(edhrec.EdhrecError, match="lists nothing"):
        edhrec.rankings(tag="goblin")
    assert edhrec.cached_rankings(edhrec.ranking_key(tag="goblin")) is None


def test_sync_rankings_names_with_the_shared_title(tmp_db, pages):
    assert edhrec.sync_rankings("commanders", color="r").name == "Top commanders · Mono-Red · past week"
