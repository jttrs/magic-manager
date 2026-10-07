"""Jumpstart engine (magic_manager.jumpstart) + its API adapter, offline.

A tiny fake set ``jt``: three pack versions over four cards, with a built
``Dogs`` pack pledging two of them, so buildable-now (free copies), the
buildable-set target (owned incl. pledged) and the whole-pack list all differ.
"""
from __future__ import annotations

import pytest

from magic_manager import db, decks, inventory, jumpstart, mtgjson
from magic_manager import front_cards


VARIANTS = [
    {"code": "JT", "fileName": "Cats1_JT", "name": "Cats (1)", "type": "Jumpstart", "releaseDate": "2025-01-01"},
    {"code": "JT", "fileName": "Cats2_JT", "name": "Cats (2)", "type": "Jumpstart", "releaseDate": "2025-01-01"},
    {"code": "JT", "fileName": "Dogs_JT", "name": "Dogs", "type": "Jumpstart", "releaseDate": "2025-01-01"},
]


@pytest.fixture
def jt(tmp_db, seed_cards, make_card, make_precon_deck, monkeypatch):
    seed_cards([
        make_card(id="a", set="jt", collector_number="1", name="Alpha", prices={"usd": "1.00", "usd_foil": "3.00"}),
        make_card(id="b", set="jt", collector_number="2", name="Bravo", color_identity=["W"], prices={"usd": "2.00", "usd_foil": None}),
        make_card(id="c", set="jt", collector_number="3", name="Charlie", prices={"usd": "5.00", "usd_foil": None}),
        make_card(id="d", set="jt", collector_number="4", name="Delta", color_identity=["R"], prices={"usd": "0.50", "usd_foil": None}),
    ])
    deck_files = {
        "Cats1_JT": make_precon_deck("Cats (1)", "Jumpstart", [
            {"sid": "a", "name": "Alpha", "set": "JT"}, {"sid": "b", "name": "Bravo", "count": 2, "set": "JT"}]),
        "Cats2_JT": make_precon_deck("Cats (2)", "Jumpstart", [
            {"sid": "a", "name": "Alpha", "set": "JT", "foil": True}, {"sid": "c", "name": "Charlie", "set": "JT"}]),
        "Dogs_JT": make_precon_deck("Dogs", "Jumpstart", [
            {"sid": "a", "name": "Alpha", "set": "JT"}, {"sid": "d", "name": "Delta", "set": "JT"}]),
    }
    monkeypatch.setattr(mtgjson, "deck_list", lambda set_code=None: [v for v in VARIANTS if set_code in (None, "jt", "JT")])
    monkeypatch.setattr(mtgjson, "jumpstart_variants", lambda code: list(VARIANTS) if code.lower() == "jt" else [])
    monkeypatch.setattr(mtgjson, "deck", lambda fn: deck_files[fn])
    monkeypatch.setattr(jumpstart, "deck_cached", lambda fn: True)
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets", lambda: [{"code": "jt", "name": "Jump Test", "parent_set_code": None,
                                                    "set_type": "expansion", "released_at": "2025-01-01"}])

    for sid, q in (("a", 2), ("b", 2), ("d", 1)):
        inventory.inventory_add(sid, "nonfoil", q)
    with db.connect() as conn:
        decks.deck_create("pack:dogs-jt", "Dogs", source_precon_file_name="Dogs_JT", precon_state="built", conn=conn)
    for sid in ("a", "d"):
        decks.deck_add_card("pack:dogs-jt", sid, "main", "nonfoil", 1)
    decks.deck_assign_batch("pack:dogs-jt", [("a", "nonfoil", 1), ("d", "nonfoil", 1)])
    return "jt"


def test_names_versions_and_colour_order():
    assert jumpstart.theme_of("Angels (1)") == "Angels"
    assert jumpstart.version_of("Angels (12)") == 12
    assert jumpstart.version_of("Corruption 2") == 2
    assert jumpstart.version_of("Aang") is None
    codes = ["WU", "G", "C", "B", "BR", "W"]
    assert sorted(codes, key=jumpstart.color_sort_key) == ["C", "W", "B", "G", "BR", "WU"]


def test_set_packs_free_coverage_and_ownership(jt):
    packs = {p.file_name: p for p in jumpstart.set_packs(jt)}
    # free: a 2-1=1, b 2, c 0, d 1-1=0
    cats1, cats2, dogs = packs["Cats1_JT"], packs["Cats2_JT"], packs["Dogs_JT"]
    assert (cats1.have, cats1.short, cats1.status) == (3, 0, "build")
    assert (cats2.have, cats2.short, cats2.status) == (1, 1, "close")
    assert (dogs.built, dogs.deconstructed, dogs.owned) == (1, 0, True)
    assert not cats1.owned
    assert cats1.theme == "Cats" and cats1.version == 1 and dogs.version is None
    assert cats1.color == "WG"
    # shipped finish prices the pack: Cats (2)'s Alpha is foil ($3) + Charlie $5
    assert cats2.usd_total == 8.0
    assert [c.free for c in cats1.cards] == [1, 2]
    # ordered by colour then theme: G (Dogs? no — Dogs is RG) …
    assert [p.color for p in jumpstart.set_packs(jt)] == sorted([p.color for p in packs.values()], key=jumpstart.color_sort_key)


def test_buildable_missing_counts_pledged_copies(jt):
    res = jumpstart.buildable_missing(jt)
    # target: Cats → a max 1, b 2, c 1; Dogs → a 1, d 1  ⇒ a2 b2 c1 d1; owned a2 b2 d1
    assert res.target == {"a": 2, "b": 2, "c": 1, "d": 1}
    assert [(r.scryfall_id, r.quantity, r.finish) for r in res.rows] == [("c", 1, "nonfoil")]
    assert (res.themes, res.variants, res.copies, res.usd) == (2, 3, 1, 5.0)


def test_missing_packs_full_contents_merged(jt):
    res = jumpstart.missing_packs(jt)
    assert [v["fileName"] for v, _ in res.packs] == ["Cats1_JT", "Cats2_JT"]
    assert sorted((r.scryfall_id, r.finish, r.quantity) for r in res.rows) == [
        ("a", "foil", 1), ("a", "nonfoil", 1), ("b", "nonfoil", 2), ("c", "nonfoil", 1)]
    assert res.usd == 1.0 + 3.0 + 4.0 + 5.0


def test_buy_text_routes_through_exports(jt):
    text, lines = jumpstart.buy_text(jt, "buildable", "manapool")
    assert lines == 1 and "Charlie" in text
    text, lines = jumpstart.buy_text(jt, "packs", "tcgplayer")
    assert lines == 4 and "Bravo" in text


def test_front_card_matches_versioned_pack_name(tmp_db):
    with db.connect() as conn:
        conn.execute("INSERT INTO front_cards (scryfall_id, set_code, family_anchor, name, normalized_name, "
                     "collector_number, prices_usd, finishes, fetched_at) VALUES "
                     "('f1', 'fjt', 'jt', 'Cats', 'cats', '1', 0.25, '[\"nonfoil\"]', '2025-01-01')")
    assert front_cards.front_card_for_theme("jt", "Cats (2)")["name"] == "Cats"
    assert front_cards.front_card_for_theme("jt", "Cats")["name"] == "Cats"
    assert front_cards.front_card_for_theme("jt", "Dogs") is None


def test_api_view_pack_and_buy_list(jt):
    from magic_manager.api import jumpstart as api
    v = api.view(jt)
    assert v.ready and v.name == "Jump Test" and v.themes == 2
    assert v.buildable.copies == 1 and v.whole_packs == 2 and v.whole.copies == 5
    d = api.pack(jt, "Cats2_JT")
    assert [(c.printing.name, c.foil, c.free) for c in d.cards] == [("Alpha", True, 1), ("Charlie", False, 0)]
    out = api.buy_list(jt, api.JumpstartBuyIn(shop="buildable", target="cardkingdom"))
    assert "Charlie" in out.text
    s = api.sets()
    jt_row = next(x for x in s.sets if x.code == "jt")
    assert (jt_row.packs, jt_row.themes, jt_row.owned_packs) == (3, 2, 1)
    with pytest.raises(LookupError):
        api.view("zzz")


def test_api_view_not_ready_until_read(jt, monkeypatch):
    from magic_manager.api import jumpstart as api
    monkeypatch.setattr(jumpstart, "deck_cached", lambda fn: False)
    v = api.view(jt)
    assert not v.ready and v.packs == []
