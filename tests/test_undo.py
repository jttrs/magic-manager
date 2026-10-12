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


def test_restore_does_not_resurrect_kept_setting_absent_live(owned):
    with db.connect() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES ('sets.partial', '[\"tst\"]')")
    undo.take("before sync")
    with db.connect() as conn:
        conn.execute("DELETE FROM settings WHERE key = 'sets.partial'")
    undo.restore()
    with db.connect() as conn:
        assert conn.execute("SELECT 1 FROM settings WHERE key = 'sets.partial'").fetchone() is None


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


def _write(g, reason):
    """One write request through the guard: begin, then settle as written."""
    joined = g.begin(reason)
    if joined:
        g.end(wrote=True)
    return joined


def _guard(monkeypatch, t):
    taken = []

    def fake_take(reason, dest=None):
        taken.append(reason)
        dest.write_text(reason)
    monkeypatch.setattr(undo, "take", fake_take)
    return undo.SessionGuard(gap=60, clock=lambda: t[0]), taken


def test_session_guard_snapshots_once_per_session(owned, monkeypatch):
    t = [0.0]
    g, taken = _guard(monkeypatch, t)
    assert _write(g, "first") is True
    t[0] = 30
    assert _write(g, "second") is False
    t[0] = 200                     # a long pause starts a new session
    assert _write(g, "third") is True
    assert taken == ["first", "third"]
    assert undo.snapshot_path().read_text() == "third"


def test_session_guard_failed_snapshot_does_not_start_the_session(owned, monkeypatch):
    """PR99-3: a failed take() leaves the next write still 'first of the session'."""
    t = [0.0]
    g, taken = _guard(monkeypatch, t)
    monkeypatch.setattr(undo, "take", lambda reason, dest=None: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        _write(g, "first")
    _, taken = _guard(monkeypatch, t)  # take works again
    t[0] = 1
    assert _write(g, "retry") is True and taken == ["retry"]


def test_session_guard_refused_request_keeps_the_previous_restore_point(owned, monkeypatch):
    """PR99-4: a request that wrote nothing must not rotate the one slot."""
    t = [0.0]
    g, taken = _guard(monkeypatch, t)
    undo.snapshot_path().write_text("previous session")
    assert g.begin("refused") is True
    g.end(wrote=False)
    assert undo.snapshot_path().read_text() == "previous session"
    assert not g.pending_path().exists()
    # still a fresh session: the next write snapshots and keeps it
    assert g.begin("real") is True
    assert g.begin("overlapping") is True          # joins, no second snapshot
    g.end(wrote=False)
    g.end(wrote=True)
    assert taken == ["refused", "real"] and undo.snapshot_path().read_text() == "real"
    t[0] = 10
    assert g.begin("same session") is False


def test_restore_refused_while_a_session_snapshot_is_pending(owned, monkeypatch):
    """A pending snapshot promoted after a restore would overwrite its swap copy."""
    t = [0.0]
    g, _ = _guard(monkeypatch, t)
    assert g.begin("in flight") is True
    with pytest.raises(undo.UndoError, match="still being saved"):
        with g.restoring():
            pass
    g.end(wrote=True)
    with g.restoring():
        pass


def _probe_during(monkeypatch, statement_prefix: str) -> list[str]:
    """While the undo connection runs ``statement_prefix``, try to commit a
    write from a second connection; record whether it got through."""
    import sqlite3
    from contextlib import contextmanager
    real = db.connect
    seen: list[str] = []

    def probe(sql: str) -> None:
        if seen or not sql.lstrip().startswith(statement_prefix):
            return
        other = sqlite3.connect(db.db_path(), timeout=0, isolation_level=None)
        try:
            other.execute("INSERT INTO settings (key, value) VALUES ('probe', 'x')")
            seen.append("wrote")
        except sqlite3.OperationalError as e:
            seen.append(str(e))
        finally:
            other.close()

    @contextmanager
    def traced(*a, **k):
        with real(*a, **k) as conn:
            conn.set_trace_callback(probe)
            yield conn
    monkeypatch.setattr(undo.db, "connect", traced)
    return seen


def test_snapshot_is_one_point_in_time(owned, monkeypatch):
    """PR99-1: no write can commit between the per-table copies."""
    seen = _probe_during(monkeypatch, "CREATE TABLE snap.inventory_events")
    undo.take("t")
    assert seen == ["database is locked"]


def test_restore_holds_the_write_lock_from_the_swap_copy_on(owned, monkeypatch):
    """PR99-2: nothing can land between capturing the swap file and replacing."""
    undo.take("t")
    inventory.inventory_add(A, "nonfoil", 1)
    seen = _probe_during(monkeypatch, "CREATE TABLE swap.inventory")
    undo.restore()
    assert seen == ["database is locked"]
    assert _copies() == 2
    assert undo.info()["changes"]["copies"] == 1  # the swap file holds the 3


def test_info_details_cover_every_restored_table(owned, monkeypatch):
    """PR99-7: edits that leave the headline counts equal still show up."""
    # Adding a card bumps decks.updated_at (to the second); a fixed clock keeps the
    # decks row identical, so the test can't flake across a second boundary.
    monkeypatch.setattr(db, "_utcnow_iso", lambda: "2026-01-01T00:00:00+00:00")
    decks.deck_create("d", "D")
    undo.take("t")
    decks.deck_add_card("d", A, "main", "nonfoil", 1)
    info = undo.info()
    assert all(v == 0 for v in info["changes"].values())
    assert info["details"] == [{"label": "deck lists", "rows": 1}]
    with db.connect() as conn:          # an edit in place counts once, not twice
        conn.execute("UPDATE decks SET name = 'Renamed' WHERE slug = 'd'")
    assert {"label": "decks", "rows": 1} in undo.info()["details"]


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


def test_refused_web_write_keeps_the_restore_point(owned):
    """PR99-4: a 4xx write (or invalid job input) leaves the slot alone."""
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app
    client = TestClient(create_app(serve_frontend=False))
    assert client.post("/api/decks", json={"format": "commander"}).status_code == 422
    assert client.post("/api/jobs/ingest.precon", json={}).status_code == 422
    assert client.get("/api/undo").json() is None
    assert client.post("/api/decks", json={"name": "Brand New", "format": "commander"}).status_code == 201
    assert client.get("/api/undo").json()["reason"] == "before creating a deck"


def test_restore_refused_while_a_mutating_job_is_queued(owned):
    """PR99-2: a queued/running mutating job can't write on top of a restore."""
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app
    from magic_manager.web.runtime import JobRecord
    app = create_app(serve_frontend=False)
    client = TestClient(app)
    undo.take("t")
    app.state.jobs._jobs["x"] = JobRecord(id="x", name="trueup.apply", title="Apply true-up", inputs={})
    r = client.post("/api/undo/restore")
    assert r.status_code == 409 and "Apply true-up" in r.json()["detail"]
    app.state.jobs._jobs["x"].status = "succeeded"
    assert client.post("/api/undo/restore").status_code == 200


def test_cli_undo_says_nothing_when_nothing_changed(owned):
    """PR99-6: the 'nothing' fallback is reachable."""
    from typer.testing import CliRunner
    from magic_manager.cli import app
    r = CliRunner().invoke(app, ["db", "undo", "--take"])
    assert r.exit_code == 0, r.output
    assert "restoring would change: nothing" in r.output


def test_unexpected_server_error_keeps_the_session_snapshot(owned, monkeypatch):
    """A 5xx/crash may have written something: keep the snapshot taken before it."""
    from fastapi.testclient import TestClient
    from magic_manager.api import decks as decks_api
    from magic_manager.web.app import create_app

    def boom(body):
        decks.deck_create("half-written", "Half")
        raise RuntimeError("crashed after writing")
    monkeypatch.setattr(decks_api, "create", boom)
    client = TestClient(create_app(serve_frontend=False), raise_server_exceptions=False)
    assert client.post("/api/decks", json={"name": "X", "format": "commander"}).status_code == 500
    info = client.get("/api/undo").json()
    assert info["reason"] == "before creating a deck" and info["changes"]["decks"] == -1
