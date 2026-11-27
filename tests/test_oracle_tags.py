"""Oracle-tag filter: search the Tagger cache, resolve tags (with their subtrees) to cards."""
import json

from magic_manager import db, scryfall_tags


def _seed(conn):
    rows = [  # id, slug, label, parents, children
        ("t-burn", "burn", "burn", [], ["t-bp"]),
        ("t-bp", "burn-player", "burn player", ["t-burn"], []),
        ("t-gain", "lifegain", "lifegain", [], []),
        ("t-meta", "cycle", "cycle", [], []),
    ]
    for tid, slug, label, parents, kids in rows:
        conn.execute("INSERT INTO scryfall_tags (id, slug, label, type, parent_ids, child_ids) VALUES (?,?,?,?,?,?)",
                     (tid, slug, label, "oracle", json.dumps(parents), json.dumps(kids)))
    for oid, tid in [("o1", "t-burn"), ("o2", "t-bp"), ("o3", "t-gain"), ("o4", "t-meta")]:
        conn.execute("INSERT INTO card_oracle_tags (oracle_id, tag_id, weight) VALUES (?,?,?)", (oid, tid, "median"))


def test_search_rolls_up_and_hides_meta(tmp_db):
    with db.connect() as conn:
        _seed(conn)
        conn.commit()
    hits = scryfall_tags.oracle_tag_search("bur")
    assert [(h["slug"], h["cards"]) for h in hits] == [("burn", 2), ("burn-player", 1)]
    assert scryfall_tags.oracle_tag_search("cycle") == []          # a preview_exclude subtree
    tags, ids = scryfall_tags.oracles_with_tags(["burn", "lifegain", "nope"])
    assert [t["slug"] for t in tags] == ["burn", "lifegain"] and ids == {"o1", "o2", "o3"}


def test_routes(tmp_db):
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app
    with db.connect() as conn:
        _seed(conn)
        conn.commit()
    c = TestClient(create_app())
    assert [t["slug"] for t in c.get("/api/oracle-tags", params={"q": "burn"}).json()["tags"]] == ["burn", "burn-player"]
    assert c.get("/api/oracle-tags/cards", params={"tags": "burn-player,lifegain"}).json()["oracle_ids"] == ["o2", "o3"]
