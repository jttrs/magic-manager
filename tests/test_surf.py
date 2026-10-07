"""Card surfer (Explore → Surf random cards): the surf engine's filter → Scryfall
query compiler, its Python twin (``matches``), the two draw sources, and the
/api/surf routes. Offline: scryfall.random_card / search_total / collection are
faked."""
from __future__ import annotations

import pytest

from magic_manager import db, inventory, scryfall, scryfall_art, surf
from magic_manager.surf import Filters, build_query, matches


# ---------- query compiler ----------

def test_empty_filters_are_the_base_query():
    assert build_query(Filters()) == surf.BASE


def test_every_filter_compiles_to_scryfall_syntax():
    f = Filters(art=("dragon", "moon"), families=("fin",), colors="UW", flavor="has",
                types=("creature", "artifact"), legendary="only", rarity=("rare",),
                artist='Rebecca "Guay"', treatments=("borderless", "oldframe"))
    q = build_query(f, set_codes=["fin", "fic"])
    assert q == (f"{surf.BASE} (art:dragon or art:moon) (s:fin or s:fic) id=wu has:flavor "
                 "(t:creature or t:artifact) t:legendary r:rare a:\"Rebecca Guay\" "
                 "(border:borderless or (frame:1993 or frame:1997))")


@pytest.mark.parametrize("f, part", [
    (Filters(colors="gr", color_match="within"), "id<=rg"),
    (Filters(colors="c"), "id=c"),
    (Filters(colors="cw"), "id=w"),
    (Filters(flavor="none"), "-has:flavor"),
    (Filters(legendary="not"), "-t:legendary"),
    (Filters(treatments=("fullart",)), "is:fullart"),
])
def test_single_filters(f, part):
    assert build_query(f).endswith(part)


# ---------- the Python twin ----------

def _card(make_card, **kw):
    base = dict(type_line="Legendary Creature — Dragon", color_identity=["R"], rarity="mythic",
                flavor_text="Fire.", artist="Jane Doe", frame="2015")
    base.update(kw)
    return make_card(**base)


@pytest.mark.parametrize("f, ok", [
    (Filters(), True),
    (Filters(colors="r"), True),
    (Filters(colors="rg"), False),
    (Filters(colors="rg", color_match="within"), True),
    (Filters(colors="c"), False),
    (Filters(types=("creature",)), True),
    (Filters(types=("instant",)), False),
    (Filters(legendary="only"), True),
    (Filters(legendary="not"), False),
    (Filters(rarity=("rare",)), False),
    (Filters(flavor="has"), True),
    (Filters(flavor="none"), False),
    (Filters(artist="jane"), True),
    (Filters(artist="john"), False),
    (Filters(treatments=("borderless",)), False),
    (Filters(treatments=("oldframe",)), False),
])
def test_matches(make_card, f, ok):
    assert matches(_card(make_card), f) is ok


def test_unknown_treatment_keys_are_ignored(make_card):
    f = Filters(treatments=("nope",), types=("nope",), rarity=("nope",))
    assert build_query(f) == surf.BASE
    assert matches(_card(make_card), f)
    mixed = Filters(treatments=("nope", "borderless"))
    assert build_query(mixed) == f"{surf.BASE} border:borderless"


def test_matches_tokens_never(make_card):
    assert not matches(_card(make_card, type_line="Token Creature — Dragon"), Filters())


def test_matches_flavor_on_a_face(make_card):
    dfc = _card(make_card, flavor_text=None, card_faces=[{"name": "A", "flavor_text": None}, {"name": "B", "flavor_text": "Moon."}])
    assert matches(dfc, Filters(flavor="has")) and not matches(dfc, Filters(flavor="none"))


def test_local_prefilter_skips_unknown_fields(make_card):
    c = _card(make_card, flavor_text=None, artist=None, frame=None)
    assert matches(c, Filters(flavor="has", artist="x", treatments=("oldframe",)), local=True)
    assert not matches(c, Filters(rarity=("common",)), local=True)


# ---------- normalize ----------

def test_normalize_dfc(make_card):
    c = make_card(id="d1", name="Front // Back", image_uris=None, flavor_text=None, artist=None,
                  card_faces=[{"name": "Front", "flavor_text": "Up.", "artist": "Ann", "image_uris": {"large": "f.jpg"}},
                              {"name": "Back", "flavor_text": "Down.", "artist": "Ann", "image_uris": {"large": "b.jpg"}}])
    n = surf.normalize(c)
    assert n["image"] == "f.jpg" and n["artist"] == "Ann"
    assert [f["flavor_text"] for f in n["faces"]] == ["Up.", "Down."]
    assert n["prices"] == {"nonfoil": 1.0, "foil": 2.0}


# ---------- draw: all of Magic ----------

@pytest.fixture
def owned_world(tmp_db, seed_cards, make_card):
    cards = [
        make_card(id=f"c{i}", oracle_id=f"o{i}", name=f"Card {i}", collector_number=str(i),
                  rarity="rare" if i % 2 else "common", illustration_id=f"ill{i}")
        for i in range(6)
    ]
    seed_cards(cards)
    for i in range(5):  # c5 not owned
        inventory.inventory_add(f"c{i}", "nonfoil", 1 + i)
    with db.connect() as conn:
        conn.execute("INSERT INTO scryfall_tags (id, slug, label, type, parent_ids, child_ids) "
                     "VALUES ('t-moon','moon','moon','illustration','[]','[]')")
        conn.executemany("INSERT INTO illustration_art_tags (illustration_id, tag_id, weight) VALUES (?, 't-moon', 'strong')",
                         [("ill1",), ("ill3",)])
        conn.commit()
    return {c["id"]: c for c in cards}


def test_draw_scryfall(owned_world, monkeypatch):
    calls = []
    pool = [owned_world["c1"], {**owned_world["c2"], "layout": "art_series"}, owned_world["c5"]]

    def fake_random(q):
        calls.append(q)
        return pool.pop(0) if pool else None
    monkeypatch.setattr(scryfall, "random_card", fake_random)
    monkeypatch.setattr(scryfall, "search_total", lambda q, **k: 42)
    d = surf.draw(Filters(flavor="has"), n=3, with_total=True)
    assert d.total == 42 and d.query.endswith("has:flavor")
    # the art-series card is skipped; then nothing more matches
    assert [c["scryfall_id"] for c in d.cards] == ["c1", "c5"] and d.exhausted
    c1 = d.cards[0]
    assert c1["owned"] == 2 and c1["owned_any"] == 2 and c1["art_tags"] == [{"slug": "moon", "label": "moon"}]
    assert d.cards[1]["owned"] == 0


def test_draw_scryfall_nothing_matches(tmp_db, monkeypatch):
    monkeypatch.setattr(scryfall, "search_total", lambda q, **k: 0)
    monkeypatch.setattr(scryfall, "random_card", lambda q: pytest.fail("no draw when nothing matches"))
    d = surf.draw(Filters(artist="nobody"), with_total=True)
    assert d.cards == [] and d.exhausted and d.total == 0


# ---------- draw: your cards ----------

def _fake_collection(world, monkeypatch, **extra):
    def coll(ids):
        return [{**world[i["id"]], **extra.get(i["id"], {})} for i in ids], []
    monkeypatch.setattr(scryfall, "collection", coll)


def test_draw_owned_pages_without_repeats(owned_world, monkeypatch):
    _fake_collection(owned_world, monkeypatch)
    seen, offset = [], 0
    for _ in range(5):
        d = surf.draw(Filters(), source="owned", n=2, seed=3, offset=offset)
        assert d.total == 5
        seen += [c["scryfall_id"] for c in d.cards]
        offset = d.next_offset
        if d.exhausted:
            break
    assert sorted(seen) == ["c0", "c1", "c2", "c3", "c4"]  # every owned card once, c5 never
    # the same seed gives the same order
    again = surf.draw(Filters(), source="owned", n=5, seed=3)
    assert [c["scryfall_id"] for c in again.cards] == seen


def test_draw_owned_filters_locally_then_remotely(owned_world, monkeypatch):
    # Only c1 and c3 carry the moon art tag; c3 has no flavor on Scryfall.
    _fake_collection(owned_world, monkeypatch, c3={"flavor_text": None}, c1={"flavor_text": "Moonrise."})
    d = surf.draw(Filters(art=("moon",), flavor="has"), source="owned", n=4)
    assert d.total == 2 and [c["scryfall_id"] for c in d.cards] == ["c1"] and d.exhausted
    assert d.cards[0]["flavor_text"] == "Moonrise."


def test_draw_owned_unknown_art_tag_matches_nothing(owned_world, monkeypatch):
    _fake_collection(owned_world, monkeypatch)
    d = surf.draw(Filters(art=("nope",)), source="owned")
    assert d.cards == [] and d.total == 0 and d.exhausted


def test_art_tags_for_illustrations(owned_world):
    assert scryfall_art.art_tags_for_illustrations(["ill1", "ill2", None]) == {"ill1": [{"slug": "moon", "label": "moon"}]}


# ---------- API ----------

def test_api_routes(owned_world, monkeypatch):
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app

    pool = [owned_world["c1"]]
    monkeypatch.setattr(scryfall, "random_card", lambda q: pool.pop(0) if pool else None)
    monkeypatch.setattr(scryfall, "search_total", lambda q, **k: 1)
    monkeypatch.setattr(scryfall, "all_sets", lambda: [
        {"code": "BLB", "name": "Bloomburrow", "set_type": "expansion", "released_at": "2024-08-02"},
        {"code": "pblb", "name": "Bloomburrow Promos", "set_type": "promo", "parent_set_code": "blb"},
        {"code": "LEA", "name": "Limited Edition Alpha", "set_type": "core", "released_at": "1993-08-05"},
        {"code": "ymkm", "name": "Alchemy", "set_type": "alchemy", "digital": True},
    ])
    with TestClient(create_app(serve_frontend=False)) as client:
        o = client.get("/api/surf/options").json()
        assert o["families"] == [{"value": "blb", "label": "Bloomburrow", "year": "2024"},
                                 {"value": "lea", "label": "Limited Edition Alpha", "year": "1993"}]
        assert [t["value"] for t in o["treatments"]][:2] == ["borderless", "fullart"]
        r = client.post("/api/surf/draw", json={"filters": {"colors": "g", "types": ["Creature"]}, "n": 2, "with_total": True})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1 and [c["name"] for c in body["cards"]] == ["Card 1"]
        assert "id=g" in body["query"] and "t:creature" in body["query"]
        assert client.post("/api/surf/draw", json={"n": 99}).status_code == 422

        def boom(q):
            raise scryfall.ScryfallError("down")
        monkeypatch.setattr(scryfall, "random_card", boom)
        assert client.post("/api/surf/draw", json={}).status_code == 502
