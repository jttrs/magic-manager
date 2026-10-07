"""scenes — per-scene, per-finish completion over the Collection universe, and
its web adapter (CollectionOut.scenes + CollectionCardOut.scene). Offline:
seeded tmp DB, faked all_sets, a patched FAMILY_SCENES for family 'tst'."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

SETS = [{"code": "tst", "parent_set_code": None, "name": "Test Set", "set_type": "expansion", "released_at": "2025-02-01"}]
SCENES = [
    {"name": "Harbor", "artist": "A. Painter", "set": "tst", "cn_lo": 10, "cn_hi": 12},
    {"name": "Poster A", "artist": "Various artists", "kind": "poster", "set": "tst", "cn_lo": 20, "cn_hi": 21},
    {"name": "Empty", "artist": "Nobody", "set": "tst", "cn_lo": 90, "cn_hi": 91},
]


@pytest.fixture
def family(monkeypatch, seed_cards, make_card):
    import magic_manager.scryfall as scry
    from magic_manager import selectors
    monkeypatch.setattr(scry, "all_sets", lambda: list(SETS))
    monkeypatch.setitem(selectors.FAMILY_SCENES, "tst", SCENES)
    seed_cards([
        make_card(id="s10", oracle_id="o10", set="tst", collector_number="10", rarity="rare", name="Ten",
                  prices={"usd": "1.00", "usd_foil": "3.00"}),
        # a prerelease-stamped panel: excluded variant, but a scene keeps it
        make_card(id="s11", oracle_id="o11", set="tst", collector_number="11", rarity="rare", name="Eleven",
                  promo_types=["prerelease"], prices={"usd": "2.00", "usd_foil": None}),
        make_card(id="s12", oracle_id="o12", set="tst", collector_number="12", rarity="rare", name="Twelve",
                  prices={"usd": None, "usd_foil": "5.00"}),
        make_card(id="s12z", oracle_id="o12", set="tst", collector_number="12z", rarity="rare", name="Twelve",
                  prices={"usd": "99", "usd_foil": "99"}),
        make_card(id="p20", oracle_id="o20", set="tst", collector_number="20", rarity="mythic", name="Twenty",
                  finishes=["foil"], prices={"usd": None, "usd_foil": "50.00"}),
        make_card(id="p21", oracle_id="o21", set="tst", collector_number="21", rarity="mythic", name="TwentyOne",
                  prices={"usd": "10.00", "usd_foil": "20.00"}),
        make_card(id="x1", oracle_id="o1", set="tst", collector_number="1", rarity="common", name="One"),
        make_card(id="pre", oracle_id="o1", set="tst", collector_number="1p", rarity="common", name="One",
                  promo_types=["prerelease"]),
    ])


def _own(sid, finish="nonfoil", qty=1):
    from magic_manager import db
    with db.connect() as conn:
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) VALUES (?,?,?,'2025-01-01')",
                     (sid, finish, qty))


def test_scene_of_matches_plain_numbers_in_range():
    from magic_manager import scenes
    assert scenes.scene_of(SCENES, "TST", "11")["name"] == "Harbor"
    assert scenes.scene_of(SCENES, "tst", "12z") is None
    assert scenes.scene_of(SCENES, "tst", "13") is None
    assert scenes.scene_of(SCENES, "oth", "10") is None


def test_scene_printings_survive_variant_exclusions(tmp_db, family):
    from magic_manager import collection_view as cv
    ids = {c.scryfall_id for c in cv.family_cards("tst").cards}
    assert "s11" in ids            # prerelease, but a configured scene panel
    assert "pre" not in ids        # prerelease outside any scene still drops


def test_per_finish_progress(tmp_db, family):
    from magic_manager import scenes
    _own("s10", "nonfoil")
    _own("s12", "foil")
    _own("p21", "foil", 2)
    _, progress = scenes.family_scenes("tst")
    harbor, poster, empty = progress
    assert (harbor.key, harbor.rank, harbor.kind, harbor.artist) == ("tst:10-12", 0, "scene", "A. Painter")
    assert harbor.card_ids == ["s10", "s11", "s12"]
    assert harbor.owned_printings == 2
    nf, f = harbor.finishes["nonfoil"], harbor.finishes["foil"]
    assert (nf.printings, nf.owned, nf.missing_ids) == (3, 1, ["s11", "s12"])
    assert nf.missing_usd == pytest.approx(2.00) and nf.unpriced == 1   # s12 nonfoil unpriced
    assert (f.owned, f.missing_ids, f.missing_usd, f.unpriced) == (1, ["s10", "s11"], 3.00, 1)
    assert poster.kind == "poster"
    assert poster.finishes["nonfoil"].printings == 1                    # p20 is foil-only
    assert poster.finishes["foil"].missing_ids == ["p20"] and poster.finishes["foil"].missing_usd == 50.00
    assert empty.printings == 0


def test_price_override_reprices(tmp_db, family):
    from magic_manager import scenes
    fc, _ = scenes.family_scenes("tst")
    progress = scenes.progress(fc, {"s10": (4.00, 6.00)})
    assert progress[0].finishes["nonfoil"].missing_usd == pytest.approx(4.00 + 2.00)


def test_no_scenes_configured(tmp_db, family, monkeypatch):
    from magic_manager import scenes, selectors
    monkeypatch.delitem(selectors.FAMILY_SCENES, "tst")
    assert scenes.family_scenes("tst")[1] == []


@pytest.fixture
def client(tmp_db, family):
    from magic_manager.web.app import create_app
    with TestClient(create_app(serve_frontend=False)) as c:
        yield c


def test_collection_endpoint_carries_scenes(client):
    _own("s10")
    body = client.get("/api/collection", params=[("families", "tst")]).json()
    by_id = {c["scryfall_id"]: c for c in body["cards"]}
    assert by_id["s11"]["scene"] == "tst:10-12" and by_id["x1"]["scene"] is None
    assert [s["key"] for s in body["scenes"]] == ["tst:10-12", "tst:20-21"]   # empty scene dropped
    harbor = body["scenes"][0]
    assert harbor["printings"] == 3 and harbor["owned_printings"] == 1
    assert [f["finish"] for f in harbor["finishes"]] == ["nonfoil", "foil"]
    assert harbor["finishes"][0]["missing_ids"] == ["s11", "s12"]
