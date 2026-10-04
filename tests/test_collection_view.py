"""collection_view.family_cards — the whole-family universe with ownership — and
its web adapter. Offline: seeded tmp DB + faked all_sets (family 'tst' with a
memorabilia child set). make_card shares one oracle_id by default, so tests pass
explicit oracle_id= where it matters.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

SETS = [
    {"code": "tst", "parent_set_code": None, "name": "Test Set", "set_type": "expansion"},
    {"code": "atst", "parent_set_code": "tst", "name": "Test Art Series", "set_type": "memorabilia"},
    {"code": "ttst", "parent_set_code": "tst", "name": "Test Tokens", "set_type": "token"},
]


@pytest.fixture
def family(monkeypatch, seed_cards, make_card):
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets", lambda: list(SETS))
    seed_cards([
        make_card(id="r1", oracle_id="o1", set="tst", collector_number="1", rarity="rare", name="Rare One"),
        make_card(id="c2", oracle_id="o2", set="tst", collector_number="2", rarity="common", name="Common Two",
                  prices={"usd": "0.10", "usd_foil": "0.50"}),
        make_card(id="b3", oracle_id="o1", set="tst", collector_number="300", rarity="rare", name="Rare One",
                  border_color="borderless", prices={"usd": "9.00", "usd_foil": None}, finishes=["nonfoil"]),
        make_card(id="art", oracle_id="o9", set="atst", collector_number="1", rarity="common", name="Art Card"),
        make_card(id="tok", oracle_id="o8", set="ttst", collector_number="1", rarity="common", name="Token",
                  layout="token", type_line="Token Creature — Bird"),
        make_card(id="pre", oracle_id="o1", set="tst", collector_number="1p", rarity="rare", name="Rare One",
                  promo_types=["prerelease"]),
        make_card(id="dig", oracle_id="o7", set="tst", collector_number="A-5", rarity="rare", name="A-Digital",
                  security_stamp="arena"),
    ])


def _own(sid, finish="nonfoil", qty=1):
    from magic_manager import db
    with db.connect() as conn:
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) VALUES (?,?,?,'2025-01-01')",
                     (sid, finish, qty))


def test_universe_keeps_catalogued_printings_only(tmp_db, family):
    from magic_manager import collection_view as cv
    ids = {c.scryfall_id for c in cv.family_cards("tst").cards}
    # memorabilia set, token set, prerelease variant and digital-only are dropped
    assert ids == {"r1", "c2", "b3"}


def test_ownership_overrides_every_exclusion(tmp_db, family):
    from magic_manager import collection_view as cv
    _own("art")
    _own("pre", "foil", 2)
    cards = {c.scryfall_id: c for c in cv.family_cards("tst").cards}
    assert {"art", "pre"} <= set(cards)
    assert cards["pre"].owned == {"foil": 2}


def test_owned_counts_flags_and_summary(tmp_db, family):
    from magic_manager import collection_view as cv
    _own("c2", "nonfoil", 3)
    _own("c2", "foil", 1)
    fc = cv.family_cards("tst")
    cards = {c.scryfall_id: c for c in fc.cards}
    c2, b3 = cards["c2"], cards["b3"]
    assert c2.owned == {"nonfoil": 3, "foil": 1} and c2.owned_total == 4
    assert c2.is_bulk and c2.standard_frame
    assert not b3.is_bulk and not b3.standard_frame and b3.finishes == ["nonfoil"]
    s = fc.summary
    assert (s.printings, s.owned_printings, s.owned_copies, s.missing_printings) == (3, 1, 4, 2)
    assert s.owned_usd == pytest.approx(3 * 0.10 + 0.50)
    assert s.missing_usd == pytest.approx(1.00 + 9.00)  # cheapest finish of each missing printing


def test_pledged_counts_come_from_deck_assignments(tmp_db, family):
    from magic_manager import collection_view as cv, db
    _own("r1", "nonfoil", 2)
    with db.connect() as conn:
        conn.execute("INSERT INTO decks (slug, name, created_at, updated_at) VALUES ('d','D','x','x')")
        deck_id = conn.execute("SELECT deck_id FROM decks WHERE slug='d'").fetchone()[0]
        conn.execute("INSERT INTO deck_assignments (deck_id, scryfall_id, finish, count, assigned_at) VALUES (?,?,?,?,'x')",
                     (deck_id, "r1", "nonfoil", 1))
    r1 = next(c for c in cv.family_cards("tst").cards if c.scryfall_id == "r1")
    assert r1.pledged == {"nonfoil": 1}


def test_unknown_family_raises(tmp_db, family):
    from magic_manager import collection_view as cv
    with pytest.raises(LookupError):
        cv.family_cards("zzz")


def test_buy_lines_use_the_exports_engine(tmp_db, family):
    from magic_manager import collection_view as cv
    text = cv.buy_lines([("r1", "nonfoil", 2), ("missing-id", "foil", 1)], "manapool")
    assert text.strip().splitlines() == ["2 Rare One (TST) 1"]


@pytest.fixture
def client(tmp_db, family):
    from magic_manager.web.app import create_app
    with TestClient(create_app(serve_frontend=False)) as c:
        yield c


def test_collection_endpoint(client):
    _own("r1")
    body = client.get("/api/collection", params=[("families", "tst"), ("families", "nope")]).json()
    assert [f["code"] for f in body["families"]] == ["tst"]
    assert body["skipped"] == ["nope"]
    r1 = next(c for c in body["cards"] if c["scryfall_id"] == "r1")
    assert r1["owned"] == {"nonfoil": 1} and r1["scryfall_url"] == "https://scryfall.com/card/tst/1"
    assert client.get("/api/collection").status_code == 422


def test_family_member_codes_dedupe(client):
    body = client.get("/api/collection", params=[("families", "tst"), ("families", "atst")]).json()
    assert [f["code"] for f in body["families"]] == ["tst"]


def test_buy_list_endpoint(client):
    r = client.post("/api/collection/buy-list", json={"target": "tcgplayer", "items": [{"scryfall_id": "b3", "finish": "nonfoil"}]})
    assert r.status_code == 200 and r.json()["lines"] == 1
