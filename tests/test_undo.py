"""undo — one snapshot of your data, restore = swap, the session guard."""
from __future__ import annotations

import pytest

from magic_manager import db, decks, inventory, undo

A = "dddd0000-0000-0000-0000-000000000001"


@pytest.fixture
def owned(tmp_db, seed_cards, make_card):
    seed_cards([make_card(id=A, set="tst", collector_number="1", name="Alpha")])
    inventory.inventory_add(A, "nonfoil", 2)


def _copies():
    with db.connect() as conn:
        return conn.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory").fetchone()[0]


def test_take_then_restore_swaps_and_is_undoable(owned):
    assert undo.info() is None
    undo.take("before test")
    inventory.inventory_add(A, "nonfoil", 3)
    decks.deck_create("new-deck", "New Deck")
    info = undo.info()
    assert info["reason"] == "before test" and info["restorable"]
    assert info["changes"]["copies"] == -3 and info["changes"]["decks"] == -1

    undo.restore()
    assert _copies() == 2
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM decks").fetchone()[0] == 0
        # inventory still equals the ledger after the restore
        from magic_manager import ingest
        assert ingest.reconcile_inventory_ledger(conn) == []

    # the restore is itself undoable: restoring again brings the 5 copies back
    assert undo.info()["changes"]["copies"] == 3
    undo.restore()
    assert _copies() == 5


def test_restore_does_not_roll_back_consent(owned):
    from magic_manager.analytics import consent
    consent.update(usage=True)
    with db.connect() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES ('other', 'old')")
    undo.take("before opt-out")
    consent.update(usage=False)
    with db.connect() as conn:
        conn.execute("UPDATE settings SET value = 'new' WHERE key = 'other'")
    undo.restore()
    assert consent.get(fresh=True).usage is False
    with db.connect() as conn:
        assert conn.execute("SELECT value FROM settings WHERE key = 'other'").fetchone()[0] == "old"


def test_restore_refuses_without_a_snapshot_or_across_schema_change(owned):
    with pytest.raises(undo.UndoError):
        undo.restore()
    undo.take()
    import sqlite3
    c = sqlite3.connect(undo.snapshot_path())
    c.execute("UPDATE schema_version SET version = version - 1")
    c.commit()
    c.close()
    assert undo.info()["restorable"] is False
    with pytest.raises(undo.UndoError, match="changed shape"):
        undo.restore()


def test_session_guard_snapshots_once_per_session(owned, monkeypatch):
    taken = []
    monkeypatch.setattr(undo, "take", lambda reason: taken.append(reason))
    t = [0.0]
    g = undo.SessionGuard(gap=60, clock=lambda: t[0])
    assert g.before_write("first") is True
    t[0] = 30
    assert g.before_write("second") is False
    t[0] = 200                     # a long pause starts a new session
    assert g.before_write("third") is True
    assert taken == ["first", "third"]


def test_prune_keeps_the_newest(tmp_db):
    import os
    bak = db.bak_dir()
    bak.mkdir(parents=True, exist_ok=True)
    live = db.db_path().name
    for i in range(5):
        p = bak / f"{live}.bak-2026-01-0{i + 1}-000000"
        p.write_bytes(b"x" * 10)
        os.utime(p, (1_000_000 + i, 1_000_000 + i))
    doomed, freed = db.prune_snapshots(keep=2)
    assert [p.name[-12:] for p in doomed] == ["01-03-000000", "01-02-000000", "01-01-000000"]
    assert freed == 30 and len(db.list_snapshots()) == 5           # dry run deletes nothing
    db.prune_snapshots(keep=2, apply=True)
    assert [p.name.endswith(("05-000000", "04-000000")) for p in db.list_snapshots()] == [True, True]


def test_web_write_takes_the_session_snapshot(owned):
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app
    client = TestClient(create_app(serve_frontend=False))
    assert client.get("/api/undo").json() is None
    r = client.post("/api/decks", json={"name": "Brand New", "format": "commander"})
    assert r.status_code == 201
    info = client.get("/api/undo").json()
    assert info["reason"] == "before creating a deck" and info["changes"]["decks"] == -1
    assert client.post("/api/undo/restore").status_code == 200
    assert client.get("/api/undo").json()["changes"]["decks"] == 1
