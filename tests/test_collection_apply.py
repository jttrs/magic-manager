"""Phase 1 — apply_import's three modes + the ledger invariant + dedup.

Mirrors the inventory-checklist add/modify/zero_untouched tests. The crucial
assertion in every apply test is that ``ingest.reconcile_inventory_ledger()``
returns ``[]`` afterward — proving ``inventory.quantity == SUM(delta)`` held.
"""

from __future__ import annotations

import pytest

from magic_manager import collection_sync as cs
from magic_manager import db, ingest
from magic_manager import inventory as inv_mod


@pytest.fixture
def seeded(tmp_db, make_card):
    """Two cards present in the cards table (apply needs the FK target)."""
    cards = [
        make_card(id="sid-1", name="Sol Ring", set="c21", collector_number="263"),
        make_card(id="sid-2", name="Solemn", set="c21", collector_number="264"),
    ]
    with db.connect() as conn:
        db.upsert_cards(conn, cards)
    return cards


def _rows(*specs):
    """specs = (sid, finish, qty) tuples → resolved CollectionRows."""
    return [cs.CollectionRow(qty=q, finish=f, scryfall_id=s, set="c21",
                             collector_number="1", name=s) for s, f, q in specs]


def _inv():
    with db.connect() as conn:
        return {(r["scryfall_id"], r["finish"]): r["quantity"]
                for r in conn.execute("SELECT scryfall_id, finish, quantity FROM inventory")}


def _reconciles():
    with db.connect() as conn:
        return ingest.reconcile_inventory_ledger(conn) == []


# ---------- add (additive) ----------

def test_apply_add_is_additive(seeded):
    cs.apply_import(_rows(("sid-1", "nonfoil", 2)), mode="add",
                    diff=cs.diff_collections(_rows(("sid-1", "nonfoil", 2))))
    assert _inv()[("sid-1", "nonfoil")] == 2
    # Apply again → sums to 4.
    cs.apply_import(_rows(("sid-1", "nonfoil", 2)), mode="add",
                    diff=cs.diff_collections(_rows(("sid-1", "nonfoil", 2))))
    assert _inv()[("sid-1", "nonfoil")] == 4
    assert _reconciles()


# ---------- modify (replace; absent untouched) ----------

def test_apply_modify_replaces_and_leaves_absent(seeded):
    # Seed sid-1=2, sid-2=3 via add.
    cs.apply_import(_rows(("sid-1", "nonfoil", 2), ("sid-2", "foil", 3)), mode="add",
                    diff=cs.diff_collections(_rows(("sid-1", "nonfoil", 2), ("sid-2", "foil", 3))))
    # Modify with ONLY sid-1 → set to 5; sid-2 untouched.
    rows = _rows(("sid-1", "nonfoil", 5))
    cs.apply_import(rows, mode="modify", diff=cs.diff_collections(rows))
    inv = _inv()
    assert inv[("sid-1", "nonfoil")] == 5    # replaced
    assert inv[("sid-2", "foil")] == 3       # absent from file → untouched
    assert _reconciles()


# ---------- overwrite (replace + zero the removed landing rows) ----------

def test_apply_overwrite_zeros_absent(seeded):
    cs.apply_import(_rows(("sid-1", "nonfoil", 2), ("sid-2", "foil", 3)), mode="add",
                    diff=cs.diff_collections(_rows(("sid-1", "nonfoil", 2), ("sid-2", "foil", 3))))
    # Overwrite with ONLY sid-1 → sid-2 (in diff.removed) is zeroed/deleted.
    rows = _rows(("sid-1", "nonfoil", 2))
    diff = cs.diff_collections(rows)   # landing defaults to current inventory
    assert any(r["scryfall_id"] == "sid-2" for r in diff["removed"])
    res = cs.apply_import(rows, mode="overwrite", diff=diff)
    inv = _inv()
    assert inv.get(("sid-1", "nonfoil")) == 2
    assert ("sid-2", "foil") not in inv   # zeroed → row deleted
    assert res["zeroed"] >= 1
    assert _reconciles()


def test_apply_overwrite_requires_diff(seeded):
    with pytest.raises(ValueError):
        cs.apply_import(_rows(("sid-1", "nonfoil", 1)), mode="overwrite", diff=None)


def test_apply_unresolved_row_raises(seeded):
    bad = [cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id=None,
                            set="c21", collector_number="263", name="?")]
    with pytest.raises(ValueError):
        cs.apply_import(bad, mode="add", diff={"added": [], "removed": [], "changed": [], "unchanged_count": 0})


# ---------- provenance: the event is tagged collection-import ----------

def test_apply_opens_collection_import_event(seeded):
    rows = _rows(("sid-1", "nonfoil", 1))
    res = cs.apply_import(rows, mode="add", diff=cs.diff_collections(rows),
                          source_sha256="deadbeef")
    with db.connect() as conn:
        ev = conn.execute("SELECT method, source_sha256 FROM ingest_events "
                          "WHERE ingest_id = ?", (res["ingest_id"],)).fetchone()
    assert ev["method"] == "collection-import"
    assert ev["source_sha256"] == "deadbeef"


# ---------- dedup: find_events_by_sha surfaces a prior import ----------

def test_dedup_find_events_by_sha(seeded):
    rows = _rows(("sid-1", "nonfoil", 1))
    cs.apply_import(rows, mode="add", diff=cs.diff_collections(rows),
                    source_sha256="abc123")
    with db.connect() as conn:
        prior = ingest.find_events_by_sha(conn, "abc123")
    assert len(prior) == 1
    assert prior[0]["method"] == "collection-import"
