"""sets.apply_counts — the web checklist write (modify-mode semantics, one
ledger event) and its POST /api/collection/checklist adapter."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from magic_manager import db, ingest, inventory, sets
from magic_manager.sets import CountChange


@pytest.fixture
def two(seed_cards, make_card):
    seed_cards([make_card(id="a", name="Alpha", collector_number="1"),
                make_card(id="b", name="Beta", collector_number="2"),
                make_card(id="c", name="Gamma", collector_number="3")])
    inventory.inventory_add("a", "nonfoil", 3)
    inventory.inventory_add("c", "foil", 1)


def _qty(sid, fin):
    with db.connect() as c:
        r = c.execute("SELECT quantity FROM inventory WHERE scryfall_id=? AND finish=?", (sid, fin)).fetchone()
        return r["quantity"] if r else 0


def _events(method="checklist"):
    with db.connect() as c:
        return c.execute("SELECT * FROM ingest_events WHERE method=?", (method,)).fetchall()


def test_sets_each_row_and_never_touches_untouched(two):
    res = sets.apply_counts([
        CountChange("a", "nonfoil", 5, expected=3),   # +2
        CountChange("b", "foil", 2, expected=0),      # new
        CountChange("a", "foil", 0, expected=0),      # no-op
    ], label="web:checklist · Test")
    assert (res["added"], res["updated"], res["zeroed"]) == (1, 1, 0)
    assert (res["copies_added"], res["copies_removed"]) == (4, 0)
    assert _qty("a", "nonfoil") == 5 and _qty("b", "foil") == 2
    assert _qty("c", "foil") == 1     # untouched row survives
    ev = _events()
    assert len(ev) == 1 and ev[0]["label"] == "web:checklist · Test" and ev[0]["ingest_id"] == res["ingest_id"]
    with db.connect() as c:
        assert ingest.reconcile_inventory_ledger(c) == []


def test_zero_removes_and_records_negative_delta(two):
    res = sets.apply_counts([CountChange("a", "nonfoil", 0)], label="x")
    assert res["zeroed"] == 1 and res["copies_removed"] == 3
    assert _qty("a", "nonfoil") == 0
    with db.connect() as c:
        d = c.execute("SELECT delta FROM inventory_events WHERE ingest_id=?", (res["ingest_id"],)).fetchone()
    assert d["delta"] == -3


def test_noop_leaves_no_event(two):
    res = sets.apply_counts([CountChange("a", "nonfoil", 3)], label="x")
    assert res["ingest_id"] is None and res["rows"] == []
    assert _events() == []


def test_stale_expected_refuses_everything(two):
    with pytest.raises(sets.StaleCounts) as e:
        sets.apply_counts([CountChange("b", "nonfoil", 1, expected=0),
                           CountChange("a", "nonfoil", 4, expected=2)], label="x")
    # Every stale cell is reported with its current count, so the editor can rebase it.
    assert e.value.rows == [{"scryfall_id": "a", "finish": "nonfoil", "expected": 2, "current": 3}]
    assert _qty("b", "nonfoil") == 0 and _events() == []


def test_below_pledged_refused(two):
    with db.connect() as c:
        c.execute("INSERT INTO decks (slug, name, created_at, updated_at) VALUES ('d', 'D', '2025-01-01', '2025-01-01')")
        did = c.execute("SELECT deck_id FROM decks WHERE slug='d'").fetchone()[0]
        c.execute("INSERT INTO deck_assignments VALUES (?, 'a', 'nonfoil', 2, '2025-01-01')", (did,))
    with pytest.raises(sets.BelowPledged):
        sets.apply_counts([CountChange("a", "nonfoil", 1)], label="x")
    assert sets.apply_counts([CountChange("a", "nonfoil", 2)], label="x")["copies_removed"] == 1


@pytest.mark.parametrize("bad", [
    [CountChange("zzz", "nonfoil", 1)],
    [CountChange("a", "etched", 1)],
    [CountChange("a", "nonfoil", -1)],
    [CountChange("a", "nonfoil", 1), CountChange("a", "nonfoil", 2)],
])
def test_invalid_changes_refused(two, bad):
    with pytest.raises((ValueError, LookupError)):
        sets.apply_counts(bad, label="x")
    assert _qty("a", "nonfoil") == 3


def test_route(two, monkeypatch):
    from magic_manager.web.app import create_app
    with TestClient(create_app(serve_frontend=False)) as client:
        assert client.get("/api/undo").json() is None
        r = client.post("/api/collection/checklist", json={
            "family": "Test", "changes": [{"scryfall_id": "a", "finish": "nonfoil", "qty": 4, "expected": 3}]})
        assert r.status_code == 200, r.text
        assert r.json()["copies_added"] == 1
        # The write guard took the restore point before the first write.
        assert client.get("/api/undo").json()["reason"] == "before saving a checklist"
        r = client.post("/api/collection/checklist", json={
            "family": "Test", "changes": [{"scryfall_id": "a", "finish": "nonfoil", "qty": 9, "expected": 3}]})
        assert r.status_code == 409
        assert r.json()["detail"]["stale"] == [{"scryfall_id": "a", "finish": "nonfoil", "expected": 3, "current": 4}]
        with db.connect() as c:
            c.execute("INSERT INTO decks (slug, name, created_at, updated_at) VALUES ('d', 'D', '2025-01-01', '2025-01-01')")
            did = c.execute("SELECT deck_id FROM decks WHERE slug='d'").fetchone()[0]
            c.execute("INSERT INTO deck_assignments VALUES (?, 'a', 'nonfoil', 2, '2025-01-01')", (did,))
        r = client.post("/api/collection/checklist", json={
            "family": "Test", "changes": [{"scryfall_id": "a", "finish": "nonfoil", "qty": 1}]})
        assert r.status_code == 409 and "built decks" in r.json()["detail"]
        r = client.post("/api/collection/checklist", json={
            "family": "Test", "changes": [{"scryfall_id": "a", "finish": "nonfoil", "qty": 5},
                                          {"scryfall_id": "a", "finish": "nonfoil", "qty": 6}]})
        assert r.status_code == 422
        r = client.post("/api/collection/checklist", json={
            "family": "Test", "changes": [{"scryfall_id": "nope", "finish": "nonfoil", "qty": 1}]})
        assert r.status_code == 404


# ---------- the XLSX/MD modify path shares the per-row writer ----------

def _md(path, rows):
    """Markdown master-list rows: (cn, nonfoil, foil)."""
    path.write_text("\n".join(f"- (TST) {cn} [N:{n} F:{f}] — card {cn}" for cn, n, f in rows) + "\n",
                    encoding="utf-8")
    return path


@pytest.fixture
def four(seed_cards, make_card, fake_scryfall):
    cards = [make_card(id=sid, name=name, collector_number=cn)
             for sid, name, cn in (("a", "Alpha", "1"), ("b", "Beta", "2"), ("c", "Gamma", "3"), ("d", "Delta", "4"))]
    seed_cards(cards)
    fake_scryfall(collection_found=cards)
    inventory.inventory_add("a", "nonfoil", 3)
    inventory.inventory_add("c", "foil", 1)
    inventory.inventory_add("d", "nonfoil", 4)


def test_xlsx_modify_sets_rows_and_leaves_absent_rows(four, tmp_path):
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 5, 0), ("2", 2, 0), ("4", 1, 0)])
    res = sets.ingest_inventory_from_xlsx(md, mode="replace", label="set:tst")
    assert (res["added"], res["updated"], res["zeroed"]) == (1, 2, 0)
    assert (_qty("a", "nonfoil"), _qty("b", "nonfoil"), _qty("d", "nonfoil")) == (5, 2, 1)
    assert _qty("c", "foil") == 1             # absent from the file → untouched
    with db.connect() as c:
        assert ingest.reconcile_inventory_ledger(c) == []
    assert len(_events()) == 1


def test_xlsx_modify_zero_untouched_zeroes_absent_rows(four, tmp_path):
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 1, 0)])
    res = sets.ingest_inventory_from_xlsx(md, mode="replace", zero_untouched=True, label="set:tst")
    assert (res["updated"], res["zeroed"]) == (1, 2)
    assert (_qty("a", "nonfoil"), _qty("c", "foil"), _qty("d", "nonfoil")) == (1, 0, 0)
    with db.connect() as c:
        assert ingest.reconcile_inventory_ledger(c) == []
        deltas = sorted(r["delta"] for r in c.execute(
            "SELECT delta FROM inventory_events WHERE ingest_id=?", (res["ingest_id"],)))
    assert deltas == [-4, -2, -1]
