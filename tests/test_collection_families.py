"""api.collection: the family picker with unowned families, catalog_read, and
the collection.read_family job. Offline: faked all_sets, seeded tmp DB."""
from __future__ import annotations

import pytest

from magic_manager import inventory, sets
from magic_manager import scryfall as scry
from magic_manager.api import collection as coll

SETS = [
    {"code": "own", "parent_set_code": None, "name": "Owned Set", "set_type": "expansion", "released_at": "2024-01-01"},
    {"code": "new", "parent_set_code": None, "name": "New Set", "set_type": "expansion", "released_at": "2025-01-01"},
    {"code": "old", "parent_set_code": None, "name": "Old Set", "set_type": "core", "released_at": "2020-01-01"},
    # Two local printings of 300: an old lookup left a partial catalog.
    {"code": "prt", "parent_set_code": None, "name": "Partial Set", "set_type": "expansion", "released_at": "2019-01-01", "card_count": 300},
    {"code": "sld", "parent_set_code": None, "name": "Secret Lair", "set_type": "box", "released_at": "2023-01-01"},
    {"code": "dig", "parent_set_code": None, "name": "Digital", "set_type": "expansion", "digital": True, "released_at": "2022-01-01"},
]


@pytest.fixture
def world(monkeypatch, seed_cards, make_card):
    monkeypatch.setattr(scry, "all_sets", lambda: list(SETS))
    seed_cards([make_card(id="o1", set="own", name="Own Card"),
                make_card(id="p1", set="prt", name="Part One"), make_card(id="p2", set="prt", name="Part Two", collector_number="2")])
    inventory.inventory_add("o1", "nonfoil", 1)


def test_unowned_families_listed_after_owned(world):
    owned = coll.families()
    assert [f.code for f in owned] == ["own"] and owned[0].owned and owned[0].year == "2024"
    allf = coll.families(include_unowned=True)
    assert [f.code for f in allf] == ["own", "new", "old", "prt"]      # newest first, no sld / digital
    assert [f.owned for f in allf] == [True, False, False, False]
    assert allf[1].year == "2025" and allf[1].name == "New Set"


def test_catalog_read_flag(world):
    assert coll.family_view(["own"]).families[0].catalog_read is True
    assert coll.family_view(["new"]).families[0].catalog_read is False
    assert coll.family_view(["prt"]).families[0].catalog_read is False   # 2 of 300 = not read


def test_unread_set_codes_counts_partial_sets(world):
    assert sets.unread_set_codes(["own", "new", "prt"]) == ["new", "prt"]


def test_read_family_syncs_only_unsynced(world, monkeypatch):
    calls = []
    monkeypatch.setattr(sets, "sync", lambda codes, progress=None: calls.append(list(codes)) or 0)
    events = []
    res = coll._run_read_family(coll.ReadFamilyInput(family="new"), events.append)
    assert calls == [["new"]] and res.artifacts[0].data["synced"] == ["new"]
    calls.clear()
    coll._run_read_family(coll.ReadFamilyInput(family="prt"), events.append)
    assert calls == [["prt"]]
    calls.clear()
    res = coll._run_read_family(coll.ReadFamilyInput(family="own"), events.append)
    assert calls == [] and res.artifacts[0].data["synced"] == []
