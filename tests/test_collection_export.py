"""Phase 3 — collection export + the export diff / reconciled-CSV flow.

Export is direction-agnostic over the same engine: incoming = local inventory,
landing = a service CSV (via --against) or empty. Key guarantees tested here:
  - write_csv(read_csv(fixture)) round-trips identity (modulo condition default
    + column order) for every service;
  - the export diff compares inventory vs the --against CSV correctly;
  - select_export_rows shapes full vs delta;
  - export NEVER mutates the DB (the ledger stays reconciled with no new events).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from magic_manager import collection_sync as cs
from magic_manager import db, ingest

FIXTURES = Path(__file__).parent / "fixtures" / "collection"


# ---------- round-trip identity ----------

@pytest.mark.parametrize("service,fixture", [
    ("manabox", "manabox_sample.csv"),
    ("moxfield", "moxfield_sample.csv"),
    ("archidekt", "archidekt_sample.csv"),
    ("mtggoldfish", "mtggoldfish_sample.csv"),
])
def test_write_read_round_trip(service, fixture, tmp_path):
    rows = cs.read_csv(FIXTURES / fixture, service)
    text = cs.write_csv(rows, service)
    p = tmp_path / "rt.csv"
    p.write_text(text)
    back = cs.read_csv(p, service)
    # Same multiset of (name, set, cn, finish, qty) survives the round trip.
    def key(rs):
        return sorted((r.name, r.set, r.collector_number, r.finish, r.qty) for r in rs)
    assert key(back) == key(rows)


# ---------- select_export_rows: full vs delta ----------

def _row(sid, finish, qty, *, cn="1", name="X"):
    return cs.CollectionRow(qty=qty, finish=finish, scryfall_id=sid,
                            set="c21", collector_number=cn, name=name)


def test_export_mode_full_emits_everything():
    inv = [_row("a", "nonfoil", 1), _row("b", "foil", 2)]
    diff = cs.diff_collections(inv, [_row("a", "nonfoil", 1), _row("b", "foil", 2)])
    out = cs.select_export_rows(inv, diff, mode="full")
    assert len(out) == 2  # full = entire inventory regardless of diff


def test_export_mode_delta_emits_only_added_and_changed():
    inv = [_row("a", "nonfoil", 1, name="Same"),
           _row("b", "foil", 5, name="Changed"),
           _row("c", "nonfoil", 1, name="New")]
    landing = [_row("a", "nonfoil", 1, name="Same"),
               _row("b", "foil", 2, name="Changed")]  # c absent, b qty differs
    diff = cs.diff_collections(inv, landing)
    out = cs.select_export_rows(inv, diff, mode="delta")
    names = {r.name for r in out}
    assert names == {"Changed", "New"}   # Same (unchanged) excluded


def test_export_mode_delta_set_cn_key():
    inv = [cs.CollectionRow(qty=2, finish="nonfoil", set="c21", collector_number="5", name="SR")]
    landing = [cs.CollectionRow(qty=1, finish="nonfoil", set="c21", collector_number="5", name="SR")]
    diff = cs.diff_collections(inv, landing, key="set_cn")
    out = cs.select_export_rows(inv, diff, mode="delta", key="set_cn")
    assert len(out) == 1


def test_select_export_rows_bad_mode():
    with pytest.raises(ValueError):
        cs.select_export_rows([], {"added": [], "changed": []}, mode="bogus")


# ---------- F1: id-less landing (moxfield export) auto-keys on set+cn ----------

def test_export_against_idless_service_matches_on_setcn():
    # Inventory (id-ful) vs an id-LESS moxfield --against CSV for the SAME card.
    # A correct diff keys on set+cn and reports it unchanged, not added+removed.
    inventory = [cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id="sid-X",
                                  set="fin", collector_number="233", name="Lightning")]
    landing = [cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id=None,
                                set="fin", collector_number="233", name="Lightning")]
    diff = cs.diff_collections(inventory, landing)   # key="auto"
    assert diff["key"] == "set_cn"                    # auto-fell back to set+cn
    assert diff["unchanged_count"] == 1
    assert not diff["added"] and not diff["removed"] and not diff["changed"]


def test_resolve_diff_key_auto():
    idful = [cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id="a",
                              set="fin", collector_number="1", name="X")]
    idless = [cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id=None,
                               set="fin", collector_number="1", name="X")]
    assert cs.resolve_diff_key(idful, idful) == "scryfall_id"   # both fully id-ful
    assert cs.resolve_diff_key(idful, idless) == "set_cn"       # one side id-less
    assert cs.resolve_diff_key([], []) == "set_cn"              # empty → safe default


def test_export_delta_uses_diff_key_for_idless(tmp_db, make_card):
    # Delta export against an id-less landing: the selected rows must match on the
    # same (set,cn) key the diff used, not the stale scryfall_id default.
    inv = [cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id="sid-1",
                            set="fin", collector_number="1", name="Have"),
           cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id="sid-2",
                            set="fin", collector_number="2", name="New")]
    landing = [cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id=None,
                                set="fin", collector_number="1", name="Have")]  # id-less
    diff = cs.diff_collections(inv, landing)
    assert diff["key"] == "set_cn"
    out = cs.select_export_rows(inv, diff, mode="delta")
    assert {r.name for r in out} == {"New"}   # only the card the service lacks


# ---------- export does NOT mutate the DB ----------

def test_export_never_writes_inventory(tmp_db, make_card):
    # Seed one inventory row via a real add (so there IS something to export).
    card = make_card(id="sid-1", name="Sol Ring", set="c21", collector_number="263")
    with db.connect() as conn:
        db.upsert_cards(conn, [card])
    cs.apply_import([cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id="sid-1",
                                      set="c21", collector_number="263", name="Sol Ring")],
                    mode="add",
                    diff=cs.diff_collections([cs.CollectionRow(qty=1, finish="nonfoil",
                                             scryfall_id="sid-1", set="c21",
                                             collector_number="263", name="Sol Ring")]))

    with db.connect() as conn:
        events_before = conn.execute("SELECT COUNT(*) n FROM ingest_events").fetchone()["n"]
        inv_before = conn.execute("SELECT scryfall_id, quantity FROM inventory").fetchall()

    # Export path: materialize inventory, diff vs empty, select, render. No writes.
    incoming = cs.inventory_rows()
    diff = cs.diff_collections(incoming, [])
    out = cs.select_export_rows(incoming, diff, mode="full")
    text = cs.write_csv(out, "manabox")
    assert "Sol Ring" in text

    with db.connect() as conn:
        events_after = conn.execute("SELECT COUNT(*) n FROM ingest_events").fetchone()["n"]
        inv_after = conn.execute("SELECT scryfall_id, quantity FROM inventory").fetchall()
        assert ingest.reconcile_inventory_ledger(conn) == []
    assert events_before == events_after                  # no new ingest events
    assert [tuple(r) for r in inv_before] == [tuple(r) for r in inv_after]


# ---------- inventory_rows is the public materializer ----------

def test_inventory_rows_reflects_db(tmp_db, make_card):
    card = make_card(id="sid-9", name="Opt", set="c21", collector_number="99")
    with db.connect() as conn:
        db.upsert_cards(conn, [card])
    cs.apply_import([cs.CollectionRow(qty=3, finish="foil", scryfall_id="sid-9",
                                      set="c21", collector_number="99", name="Opt")],
                    mode="add",
                    diff={"added": [], "removed": [], "changed": [], "unchanged_count": 0})
    rows = cs.inventory_rows()
    assert len(rows) == 1
    assert rows[0].scryfall_id == "sid-9" and rows[0].qty == 3 and rows[0].finish == "foil"
