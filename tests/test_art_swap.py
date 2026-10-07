"""On-theme art swaps (deck editor → Art): the art_swap engine over the V30 art
tags, its ranking rule (free copies first via deck_edit.most_free, else the
cheapest), the Scryfall look-up, and the /api/art routes. Offline: tags and
taggings are written straight into the V30 tables; scryfall.search is faked."""
from __future__ import annotations

import pytest

from magic_manager import art_swap, db, decks, inventory, scryfall

CAT, HOUSECAT, MOON = "tag-cat", "tag-housecat", "tag-moon"
A1, A2, A3, B1, C1 = "a1", "a2", "a3", "b1", "c1"


@pytest.fixture
def art(tmp_db, seed_cards, make_card):
    seed_cards([
        make_card(id=A1, oracle_id="oa", name="Alpha", set="aaa", collector_number="1",
                  illustration_id="ill-plain", prices={"usd": "1.00", "usd_foil": None}),
        make_card(id=A2, oracle_id="oa", name="Alpha", set="bbb", collector_number="2",
                  illustration_id="ill-cat", prices={"usd": "5.00", "usd_foil": None}),
        make_card(id=A3, oracle_id="oa", name="Alpha", set="ccc", collector_number="3",
                  illustration_id="ill-housecat", prices={"usd": "2.00", "usd_foil": None}),
        make_card(id=B1, oracle_id="ob", name="Beta", set="aaa", collector_number="4", illustration_id="ill-cat2"),
        make_card(id=C1, oracle_id="oc", name="Gamma", set="aaa", collector_number="5", illustration_id="ill-none"),
    ])
    with db.connect() as conn:
        conn.executemany(
            "INSERT INTO scryfall_tags (id, slug, label, type, parent_ids, child_ids) VALUES (?,?,?,?,?,?)",
            [(CAT, "cat", "cat", "illustration", "[]", f'["{HOUSECAT}"]'),
             (HOUSECAT, "housecat", "housecat", "illustration", f'["{CAT}"]', "[]"),
             (MOON, "moon", "moon", "illustration", "[]", "[]")])
        conn.executemany("INSERT INTO illustration_art_tags (illustration_id, tag_id, weight) VALUES (?,?,?)",
                         [("ill-cat", CAT, "strong"), ("ill-housecat", HOUSECAT, "median"), ("ill-cat2", CAT, None)])
        conn.commit()
    return tmp_db


def _rows(res):
    return {r["scryfall_id"]: r for r in res["rows"]}


def test_tags_synced_and_search(tmp_db, art):
    assert art_swap.tags_synced()
    out = art_swap.search_tags("cat")
    assert out["synced"] and [t["label"] for t in out["tags"]] == ["cat", "housecat"]


def test_tags_not_synced(tmp_db):
    assert art_swap.search_tags("cat") == {"synced": False, "tags": []}


def test_cheapest_on_theme_printing_when_you_own_none(art):
    res = art_swap.swaps("cat", [A1, B1, C1])
    rows = _rows(res)
    assert res["tag"]["label"] == "cat"
    # housecat is a child of cat, so A3 qualifies — and it's cheaper than A2
    assert rows[A1]["status"] == "swap" and rows[A1]["pick"] == A3
    assert rows[A1]["candidates"] == [A3, A2]
    assert rows[B1]["status"] == "on_theme" and rows[B1]["pick"] == B1
    assert rows[C1] == {"scryfall_id": C1, "oracle_id": "oc", "status": "none", "pick": None, "candidates": []}
    assert res["matched"][A3] == ["housecat"]


def test_free_copy_beats_cheaper_printing(art):
    inventory.inventory_add(A2, "nonfoil", 1)
    rows = _rows(art_swap.swaps("cat", [A1]))
    assert rows[A1]["pick"] == A2 and rows[A1]["candidates"] == [A2, A3]


def test_pledged_copies_are_not_free(art):
    inventory.inventory_add(A2, "nonfoil", 1)
    decks.deck_create("other", "Other")
    decks.deck_add_card("other", A2, "main", "nonfoil", 1)
    decks.deck_assign_batch("other", [(A2, "nonfoil", 1)])
    assert _rows(art_swap.swaps("cat", [A1]))[A1]["pick"] == A3


def test_unknown_tag(art):
    with pytest.raises(LookupError):
        art_swap.swaps("no-such-tag", [A1])


def test_lookup_scryfall_adds_missing_printings(art, make_card, monkeypatch):
    queries = []
    new = make_card(id="a4", oracle_id="oa", name="Alpha", set="ddd", collector_number="9", illustration_id="ill-cat")

    def fake_search(q, **_):
        queries.append(q)
        if "oracleid:ob" in q:
            raise scryfall.ScryfallError("Scryfall error: Your query didn't match any cards.")
        yield from [new, make_card(id=A2, oracle_id="oa", set="bbb", collector_number="2")] if "oracleid:oa" in q else []

    monkeypatch.setattr(art_swap, "_ORACLE_CHUNK", 1)
    monkeypatch.setattr(scryfall, "search", fake_search)
    assert art_swap.lookup_scryfall("cat", [A1, B1]) == {"searched": 2, "added": 1}
    assert all(q.startswith("art:cat game:paper unique:prints (") for q in queries)
    assert "a4" in _rows(art_swap.swaps("cat", [A1]))[A1]["candidates"]
    assert art_swap.lookup_scryfall("cat", [A1]) == {"searched": 1, "added": 0}


def test_lookup_scryfall_reraises_real_failures(art, monkeypatch):
    def boom(q, **_):
        raise scryfall.ScryfallError("scryfall.sh search exited 7: network down")
        yield  # pragma: no cover

    monkeypatch.setattr(scryfall, "search", boom)
    with pytest.raises(scryfall.ScryfallError):
        art_swap.lookup_scryfall("cat", [A1])


def test_free_by_finish_ignores_other_finish_pledges(art):
    inventory.inventory_add(A2, "nonfoil", 1)
    inventory.inventory_add(A2, "foil", 1)
    decks.deck_create("other", "Other")
    decks.deck_add_card("other", A2, "main", "foil", 1)
    decks.deck_assign_batch("other", [(A2, "foil", 1)])
    res = art_swap.swaps("cat", [A1])
    assert res["free_by_finish"][A2] == {"nonfoil": 1, "foil": 0}
    assert A1 not in res["free_by_finish"]


def test_api_routes(art):
    from fastapi.testclient import TestClient

    from magic_manager.web.app import create_app

    body = {"tag": "cat", "cards": [{"scryfall_id": A1, "board": "main", "finish": "either", "count": 1}]}
    with TestClient(create_app(serve_frontend=False)) as client:
        t = client.get("/api/art/tags", params={"q": "cat"}).json()
        assert t["synced"] and t["tags"][0]["slug"] == "cat"
        s = client.post("/api/art/swaps", json=body).json()
        assert s["rows"][0]["pick"] == A3 and s["printings"][A3]["set_code"] == "ccc"
        assert client.post("/api/art/swaps", json={**body, "tag": "nope"}).status_code == 404
