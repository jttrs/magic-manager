"""Tests for sld.py — Secret Lair drop discovery + live-Scryfall valuation.

Offline: monkeypatch mtgjson.deck_list / mtgjson.deck / mtgjson.deck_card_scryfall_ids
and scryfall.collection / scryfall.search. Mirrors tests/test_mtgjson_sealed.py.
"""

import pytest

from magic_manager import sld


# DeckList: a base + Foil-Edition sibling for "Alpha", a lone "Beta".
_DECKLIST = [
    {"code": "SLD", "fileName": "Alpha_SLD", "name": "Alpha",
     "releaseDate": "2026-01-10", "type": "Secret Lair Drop"},
    {"code": "SLD", "fileName": "AlphaFoil_SLD", "name": "Alpha Foil Edition",
     "releaseDate": "2026-01-10", "type": "Secret Lair Drop"},
    {"code": "SLD", "fileName": "Beta_SLD", "name": "Beta",
     "releaseDate": "2026-02-20", "type": "Secret Lair Drop"},
    # a non-drop entry that must be ignored
    {"code": "SLD", "fileName": "Other_SLD", "name": "Not A Drop",
     "releaseDate": "2026-03-01", "type": "Box Set"},
]

# Deck contents → scryfall ids. Alpha base has s1,s2; Alpha foil has s2,s3 (s2 dupe).
_DECK_IDS = {
    "Alpha_SLD": ["s1", "s2"],
    "AlphaFoil_SLD": ["s2", "s3"],
    "Beta_SLD": ["s4"],
}

# Scryfall card rows (prices are strings, like the real API).
_CARDS = {
    "s1": {"id": "s1", "collector_number": "1", "oracle_id": "o1",
           "prices": {"usd": "1.00", "usd_foil": "3.00"}},
    "s2": {"id": "s2", "collector_number": "2", "oracle_id": "o2",
           "prices": {"usd": "2.00", "usd_foil": "5.00"}},
    "s3": {"id": "s3", "collector_number": "3", "oracle_id": "o3",
           "prices": {"usd": "4.00", "usd_foil": None}},   # no foil price
    "s4": {"id": "s4", "collector_number": "4", "oracle_id": "o4",
           "prices": {"usd": "10.00", "usd_foil": "12.00"}},
}

# oracle_id → list of printings for the floor search (cheaper reprints exist).
_PRINTS = {
    "o1": [{"prices": {"usd": "1.00", "usd_foil": "3.00"}},
           {"prices": {"usd": "0.50", "usd_foil": "2.00"}}],   # floor 0.50 / 2.00
    "o2": [{"prices": {"usd": "2.00", "usd_foil": "5.00"}}],    # floor 2.00 / 5.00
    "o3": [{"prices": {"usd": "4.00", "usd_foil": None}},
           {"prices": {"usd": "3.00", "usd_foil": "9.00"}}],    # floor 3.00 / 9.00
    "o4": [{"prices": {"usd": "10.00", "usd_foil": "12.00"}}],
}


def _patch(monkeypatch):
    from magic_manager import mtgjson, scryfall
    monkeypatch.setattr(mtgjson, "deck_list",
                        lambda *, set_code=None: [d for d in _DECKLIST
                                                  if set_code is None or d["code"] == set_code.upper()])
    monkeypatch.setattr(mtgjson, "deck", lambda fn: {"_fn": fn})
    monkeypatch.setattr(mtgjson, "deck_card_scryfall_ids",
                        lambda deck, **k: list(_DECK_IDS.get(deck["_fn"], [])))
    monkeypatch.setattr(scryfall, "collection",
                        lambda ids: ([_CARDS[i["id"]] for i in ids if i["id"] in _CARDS],
                                     [i for i in ids if i["id"] not in _CARDS]))
    monkeypatch.setattr(scryfall, "search",
                        lambda q, **k: list(_PRINTS.get(q.split(":", 1)[1], [])))


# ---------- discovery / identity ----------

def test_group_drops_merges_foil_edition(monkeypatch):
    _patch(monkeypatch)
    groups = sld.all_drops()
    assert set(groups) == {"Alpha", "Beta"}           # "Not A Drop" excluded
    assert groups["Alpha"]["name"] == "Alpha"          # base wins as canonical
    assert set(groups["Alpha"]["file_names"]) == {"Alpha_SLD", "AlphaFoil_SLD"}


def test_recent_drops_orders_newest_first(monkeypatch):
    _patch(monkeypatch)
    chosen, total = sld.recent_drops(10)
    assert total == 2
    assert [g["name"] for g in chosen] == ["Beta", "Alpha"]   # 02-20 before 01-10


def test_identify_drop_exact_and_substring(monkeypatch):
    _patch(monkeypatch)
    assert sld.identify_drop("Alpha")["name"] == "Alpha"
    assert sld.identify_drop("bet")["name"] == "Beta"          # unique substring


def test_identify_drop_unknown_raises(monkeypatch):
    _patch(monkeypatch)
    with pytest.raises(LookupError):
        sld.identify_drop("Nonexistent")


def test_collect_drop_ids_dedupes_across_siblings(monkeypatch):
    _patch(monkeypatch)
    ids = sld.collect_drop_ids(["Alpha_SLD", "AlphaFoil_SLD"])
    assert ids == ["s1", "s2", "s3"]   # s2 dup dropped, order preserved


# ---------- valuation ----------

def test_value_drop_alpha_totals_and_floors(monkeypatch):
    _patch(monkeypatch)
    drop = sld.identify_drop("Alpha")
    v = sld.value_drop(drop)
    assert v.card_count == 3                              # s1,s2,s3
    # nonfoil own-printing: 1 + 2 + 4 = 7.00 (all 3 priced)
    assert v.nonfoil_total == pytest.approx(7.00) and v.nonfoil_ct == 3
    # foil own-printing: 3 + 5 = 8.00 (s3 has no foil → only 2 priced)
    assert v.foil_total == pytest.approx(8.00) and v.foil_ct == 2
    # nf floor: 0.50 + 2.00 + 3.00 = 5.50
    assert v.nf_floor_total == pytest.approx(5.50) and v.nf_floor_ct == 3
    # foil floor: 2.00 + 5.00 + 9.00 = 16.00 (o3 reprint HAS a foil price)
    assert v.foil_floor_total == pytest.approx(16.00) and v.foil_floor_ct == 3


def test_value_drop_no_floors_skips_search(monkeypatch):
    _patch(monkeypatch)
    from magic_manager import scryfall
    called = {"n": 0}
    orig = scryfall.search
    def counting(q, **k):
        called["n"] += 1
        return orig(q, **k)
    monkeypatch.setattr(scryfall, "search", counting)
    v = sld.value_drop(sld.identify_drop("Beta"), floors=False)
    assert v.nonfoil_total == pytest.approx(10.00)
    assert v.nf_floor_ct == 0 and v.foil_floor_ct == 0
    assert called["n"] == 0                               # no floor search when floors=False


def test_cell_formatting():
    assert sld.cell(7.0, 3, 3) == "$7.00"
    assert sld.cell(8.0, 2, 3) == "$8.00 (2)"             # partial coverage
    assert sld.cell(0.0, 0, 3) == "—"


def test_search_url_sorted_cns(monkeypatch):
    url = sld.search_url(["3", "1★", "2 "])
    # strips ★/space, sorts numerically → cn:1 or cn:2 or cn:3
    assert "cn%3A1" in url and "cn%3A2" in url and "cn%3A3" in url
    assert url.index("cn%3A1") < url.index("cn%3A3")
