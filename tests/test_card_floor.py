"""Tests for magic_manager.card_floor — the central cheapest-printing engine.

Covers the lifted ``cheapest_floor`` helper, ``FloorPair.collapse``, the LIVE
batched anywhere floor (batching request count + finish modes + fail-soft via a
counting/raising scryfall.search stub), and the LOCAL ``local_floors`` (in-family
scope vs whole-DB, finish modes) against a seeded tmp DB.
"""

from __future__ import annotations

import re

import pytest

from magic_manager import card_floor


# ---------- cheapest_floor (the one lifted helper) ----------

def test_cheapest_floor_prefers_nonfoil_on_tie():
    assert card_floor.cheapest_floor(5.0, 5.0) == (5.0, "nonfoil")


def test_cheapest_floor_picks_cheaper_finish():
    assert card_floor.cheapest_floor(10.0, 3.0) == (3.0, "foil")
    assert card_floor.cheapest_floor(2.0, 9.0) == (2.0, "nonfoil")


def test_cheapest_floor_falls_back_when_one_missing():
    assert card_floor.cheapest_floor(None, 4.0) == (4.0, "foil")
    assert card_floor.cheapest_floor(7.0, None) == (7.0, "nonfoil")
    assert card_floor.cheapest_floor(None, None) == (None, None)


def test_cheapest_floor_prefer_foil():
    # equal → prefer foil when asked; cheaper nonfoil still wins on price
    assert card_floor.cheapest_floor(5.0, 5.0, prefer="foil") == (5.0, "foil")
    assert card_floor.cheapest_floor(2.0, 9.0, prefer="foil") == (2.0, "nonfoil")


def test_floorpair_collapse_keeps_location():
    pair = card_floor.FloorPair(
        nonfoil=card_floor.Floor(2.85, "nonfoil", "frf", "55"),
        foil=card_floor.Floor(3.46, "foil", "acr", "160"),
    )
    fl = pair.collapse()
    assert (fl.usd, fl.finish, fl.set_code, fl.collector_number) == (2.85, "nonfoil", "frf", "55")


# ---------- live, batched anywhere floor ----------

def _pr(oid, usd, foil, set_code="xx", cn="1"):
    return {"oracle_id": oid, "set": set_code, "collector_number": cn,
            "prices": {"usd": usd, "usd_foil": foil}}


# Two printings per oracle; the cheaper nonfoil / foil live on different prints.
_PRINTS = {
    "o1": [_pr("o1", "1.00", "3.00", "aaa", "1"), _pr("o1", "0.50", "9.00", "bbb", "2")],
    "o2": [_pr("o2", "2.00", "5.00", "ccc", "3")],
    "o3": [_pr("o3", "4.00", None, "ddd", "4"), _pr("o3", None, "9.00", "eee", "5")],
}


def _make_search_stub(counter: dict):
    def stub(q, **k):
        counter["n"] += 1
        oids = re.findall(r"oracleid:([0-9a-zA-Z-]+)", q)
        out = []
        for oid in oids:
            out.extend(_PRINTS.get(oid, []))
        return out
    return stub


def test_anywhere_floors_batches_requests(monkeypatch):
    """N oracle_ids → ⌈N/_FLOOR_CHUNK⌉ searches, NOT one per id."""
    from magic_manager import scryfall
    counter = {"n": 0}
    monkeypatch.setattr(scryfall, "search", _make_search_stub(counter))
    monkeypatch.setattr(card_floor, "_FLOOR_CHUNK", 2)
    ids = ["o1", "o2", "o3"]  # 3 ids, chunk 2 → 2 requests
    card_floor.anywhere_floors(ids)
    assert counter["n"] == 2


def test_anywhere_floors_either_picks_cheapest(monkeypatch):
    from magic_manager import scryfall
    monkeypatch.setattr(scryfall, "search", _make_search_stub({"n": 0}))
    res = card_floor.anywhere_floors(["o1", "o2", "o3"], finish_mode="either")
    # o1: nonfoil 0.50 (bbb) beats foil 3.00
    assert (res["o1"].usd, res["o1"].finish, res["o1"].set_code) == (0.50, "nonfoil", "bbb")
    # o3: cheapest nonfoil 4.00 vs cheapest foil 9.00 → nonfoil 4.00
    assert (res["o3"].usd, res["o3"].finish) == (4.00, "nonfoil")


def test_anywhere_floors_preserve_keeps_finishes_distinct(monkeypatch):
    from magic_manager import scryfall
    monkeypatch.setattr(scryfall, "search", _make_search_stub({"n": 0}))
    res = card_floor.anywhere_floors(["o1", "o3"], finish_mode="preserve")
    # o1: cheapest nonfoil on bbb (0.50), cheapest foil on aaa (3.00) — different prints
    assert (res["o1"].nonfoil.usd, res["o1"].nonfoil.set_code) == (0.50, "bbb")
    assert (res["o1"].foil.usd, res["o1"].foil.set_code) == (3.00, "aaa")
    # o3: foil only on eee (9.00), nonfoil only on ddd (4.00)
    assert (res["o3"].nonfoil.usd, res["o3"].nonfoil.set_code) == (4.00, "ddd")
    assert (res["o3"].foil.usd, res["o3"].foil.set_code) == (9.00, "eee")


def test_anywhere_floors_dedupes_ids(monkeypatch):
    from magic_manager import scryfall
    counter = {"n": 0}
    monkeypatch.setattr(scryfall, "search", _make_search_stub(counter))
    monkeypatch.setattr(card_floor, "_FLOOR_CHUNK", 20)
    res = card_floor.anywhere_floors(["o1", "o1", "o2", ""], finish_mode="either")
    assert counter["n"] == 1                       # one chunk, dupes/blank collapsed
    assert set(res) == {"o1", "o2"}


def test_card_floors_many_price_only_shape(monkeypatch):
    """The sld-compatible tuple projection: {oid: (min_usd, min_usd_foil)}."""
    from magic_manager import scryfall
    monkeypatch.setattr(scryfall, "search", _make_search_stub({"n": 0}))
    out = card_floor.card_floors_many(["o1", "o3"])
    assert out["o1"] == (0.50, 3.00)               # min nonfoil, min foil
    assert out["o3"] == (4.00, 9.00)


def test_card_floors_many_unpriced_maps_to_none_pair(monkeypatch):
    from magic_manager import scryfall
    monkeypatch.setattr(scryfall, "search", lambda q, **k: [])
    assert card_floor.card_floors_many(["zzz"]) == {"zzz": (None, None)}


# ---------- local / in-family floor (no network) ----------

def test_local_floors_in_family_scope(tmp_db, seed_cards, make_card):
    """family_codes restricts the floor to the family; a cheaper out-of-family
    printing is ignored for in-family but found when scope is whole-DB."""
    seed_cards([
        make_card(id="fam", oracle_id="o-s", set="tla", collector_number="5",
                  prices={"usd": "8.00", "usd_foil": None}),
        make_card(id="out", oracle_id="o-s", set="other", collector_number="9",
                  prices={"usd": "1.00", "usd_foil": None}),
    ])
    in_fam = card_floor.local_floors(["o-s"], family_codes={"tla"}, finish_mode="either")
    assert (in_fam["o-s"].usd, in_fam["o-s"].set_code) == (8.00, "tla")
    whole = card_floor.local_floors(["o-s"], family_codes=None, finish_mode="either")
    assert (whole["o-s"].usd, whole["o-s"].set_code) == (1.00, "other")


def test_local_floors_preserve_and_cheapest_cn(tmp_db, seed_cards, make_card):
    seed_cards([
        make_card(id="a", oracle_id="o-m", set="tla", collector_number="12",
                  prices={"usd": "12.00", "usd_foil": "20.00"}),
        make_card(id="b", oracle_id="o-m", set="tla", collector_number="309",
                  prices={"usd": "4.00", "usd_foil": None}),
    ])
    res = card_floor.local_floors(["o-m"], family_codes={"tla"}, finish_mode="preserve")
    assert (res["o-m"].nonfoil.usd, res["o-m"].nonfoil.collector_number) == (4.00, "309")
    assert (res["o-m"].foil.usd, res["o-m"].foil.collector_number) == (20.00, "12")


def test_local_floors_empty_family_returns_nothing(tmp_db, seed_cards, make_card):
    seed_cards([make_card(id="x", oracle_id="o-x", set="tla", collector_number="1",
                          prices={"usd": "1.00", "usd_foil": None})])
    assert card_floor.local_floors(["o-x"], family_codes=set()) == {}


def test_local_floors_absent_oracle_omitted(tmp_db, seed_cards, make_card):
    seed_cards([make_card(id="x", oracle_id="o-x", set="tla", collector_number="1",
                          prices={"usd": "1.00", "usd_foil": None})])
    res = card_floor.local_floors(["o-x", "o-missing"], family_codes={"tla"})
    assert set(res) == {"o-x"}                     # unknown oracle simply absent
