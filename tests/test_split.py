"""Phase 3 step 3: the splitter, split-aware snapshots, and split rehearsals."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from magic_manager import db, decks, inventory, layout, scryfall_art, scryfall_tags, sets, split
from magic_manager.cli import app

ROOT = Path(__file__).resolve().parent.parent
A = "00000000-0000-0000-0000-00000000000a"
B = "00000000-0000-0000-0000-00000000000b"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def source(tmp_db, seed_cards, make_card):
    """A populated single DB with rowid gaps, sequences past max(rowid) and legacy rows."""
    seed_cards([make_card(id=A, name="Alpha"), make_card(id=B, name="Beta", collector_number="2")])
    inventory.inventory_add(A, "nonfoil", 2)
    inventory.inventory_add(B, "foil", 1)
    decks.deck_create("keep", "Keep")
    decks.deck_create("gone", "Gone")
    decks.deck_add_card("keep", A, "main", "nonfoil", 1)
    decks.deck_assign_batch("keep", [(A, "nonfoil", 1)])
    decks.deck_delete("gone")  # decks sequence now > max(deck_id)
    with db.connect() as conn:
        for code in ("x", "y"):
            conn.execute("INSERT INTO set_targets (anchor_code, related_codes, created_at, updated_at) "
                         "VALUES (?, '[]', 't', 't')", (code,))
        conn.execute("DELETE FROM set_targets WHERE anchor_code = 'x'")  # rowid gap in a non-INTEGER-PK table
        db.set_catalog_setting(conn, "sets.partial", '["abc"]')
        conn.execute("INSERT INTO settings (key, value) VALUES ('analytics.consent', 'yes')")
        conn.execute("INSERT INTO lists (label, created_at, updated_at) VALUES ('legacy', 't', 't')")
    return tmp_db


def _schema(path: Path) -> list[tuple]:
    with sqlite3.connect(path) as c:
        return sorted(c.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))


def _rows(path: Path, table: str) -> list[tuple]:
    with sqlite3.connect(path) as c:
        return c.execute(f"SELECT rowid, * FROM {table} ORDER BY rowid").fetchall()


def test_split_copies_exactly_and_never_touches_the_source(source, tmp_path):
    before = _sha(source)
    data = tmp_path / "data"
    r = split.split(source, data)
    assert r.ok and r.problems == []
    assert _sha(source) == before and not list(source.parent.glob(f"{source.name}-*"))

    catalog, user = data / "catalog.db", data / "users" / "owner.db"
    assert {t.table for t in r.tables if t.file == "catalog"} == layout.CATALOG_TABLES | {"schema_version"}
    assert {t.table for t in r.tables if t.file == "user"} == set(layout.USER_TABLES) | {"schema_version"}
    src_schema = _schema(source)
    for f, kind in ((catalog, "catalog"), (user, "user")):
        want = [o for o in src_schema if o[2] == "schema_version" or (o[2] not in layout.LEGACY_TABLES
                and layout.classify(o[2]) == kind)]
        assert _schema(f) == want  # same stored CREATE TABLE / INDEX text
    for t in ("set_targets", "decks", "inventory", "inventory_events", "settings"):
        assert _rows(user, t) == _rows(source, t)
    for t in ("cards", "catalog_settings"):
        assert _rows(catalog, t) == _rows(source, t)
    with sqlite3.connect(source) as s, sqlite3.connect(user) as u:
        src_seq = dict(s.execute("SELECT name, seq FROM sqlite_sequence WHERE name != 'lists'"))
        assert dict(u.execute("SELECT name, seq FROM sqlite_sequence")) == src_seq
        assert src_seq["decks"] > u.execute("SELECT MAX(deck_id) FROM decks").fetchone()[0]
        assert u.execute("SELECT version FROM schema_version").fetchall() == [(db.CURRENT_VERSION,)]
    assert r.legacy_skipped == {"lists": 1, "list_rows": 0}
    assert (r.ledger_drift, r.catalog_ref_orphans, r.fk_violations) == (0, 0, 0)
    assert r.integrity == {"catalog": "ok", "user": "ok"}
    assert not list(data.rglob("*.tmp"))


def test_split_files_open_with_split_connect(source, tmp_path, monkeypatch):
    data = tmp_path / "data"
    split.split(source, data, "alice")
    monkeypatch.delenv("MAGIC_MANAGER_DB")
    monkeypatch.setenv("MM_LAYOUT", "split")
    monkeypatch.setenv("MM_DATA_DIR", str(data))
    monkeypatch.setenv("MM_USER", "alice")
    with db.connect() as conn:
        assert [tuple(r) for r in conn.execute(
            "SELECT c.name, i.quantity FROM inventory i JOIN cards c USING (scryfall_id) ORDER BY c.name"
        )] == [("Alpha", 2), ("Beta", 1)]
        assert db.catalog_setting(conn, "sets.partial") == '["abc"]'


def test_split_keeps_wal_journal_mode(source, tmp_path):
    with sqlite3.connect(source) as c:
        c.execute("PRAGMA journal_mode = WAL")
    r = split.split(source, tmp_path / "data")
    assert r.journal_mode == "wal"
    for f in (tmp_path / "data" / "catalog.db", tmp_path / "data" / "users" / "owner.db"):
        with sqlite3.connect(f) as c:
            assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_split_refuses(source, tmp_path):
    data = tmp_path / "data"
    with pytest.raises(split.SplitRefused, match="no DB"):
        split.split(tmp_path / "missing.db", data)
    with pytest.raises(split.SplitRefused, match="invalid user"):
        split.split(source, data, "../evil")
    split.split(source, data)
    with pytest.raises(split.SplitRefused, match="already exists"):
        split.split(source, data)
    assert split.split(source, data, force=True).ok
    (data / "catalog.db-journal").write_bytes(b"")
    with pytest.raises(split.SplitRefused, match="looks open"):
        split.split(source, data, force=True)


@pytest.mark.parametrize("sql, match", [
    ("UPDATE schema_version SET version = version - 1", "schema v"),
    ("CREATE TABLE mystery (x)", "not classified"),
    ("CREATE VIEW v AS SELECT 1", "view"),
])
def test_split_refuses_unsplittable_sources(source, tmp_path, sql, match):
    with sqlite3.connect(source) as c:
        c.execute(sql)
    with pytest.raises(split.SplitRefused, match=match):
        split.split(source, tmp_path / "data")
    assert not (tmp_path / "data" / "catalog.db").exists()


@pytest.mark.parametrize("sql, problem", [
    ("INSERT INTO inventory (scryfall_id, finish, quantity) VALUES ('zz', 'nonfoil', 1)", "catalog-refs"),
    (f"UPDATE inventory SET quantity = 9 WHERE scryfall_id = '{A}'", "ledger"),
])
def test_split_failure_writes_nothing(source, tmp_path, sql, problem):
    with sqlite3.connect(source) as c:
        c.execute(sql)
    data = tmp_path / "data"
    with pytest.raises(split.SplitFailed) as e:
        split.split(source, data)
    assert any(p.startswith(problem) for p in e.value.report.problems)
    assert [p for p in data.rglob("*") if p.is_file()] == []


def test_split_failure_on_hash_mismatch(source, tmp_path, monkeypatch):
    real = split._table_hash

    def lying(conn, schema, table):
        n, h = real(conn, schema, table)
        return (n, "x" * 64) if (schema, table) == (split._USR, "decks") else (n, h)
    monkeypatch.setattr(split, "_table_hash", lying)
    with pytest.raises(split.SplitFailed, match="decks"):
        split.split(source, tmp_path / "data")
    assert not (tmp_path / "data" / "users" / "owner.db").exists()


def test_cli_db_split(source, tmp_path):
    runner = CliRunner()
    data = tmp_path / "data"
    res = runner.invoke(app, ["db", "split", "--to", str(data)])
    assert res.exit_code == 0, res.output
    assert "SPLIT OK" in res.output and "ledger reconciles" in res.output
    res = runner.invoke(app, ["db", "split", "--to", str(data)])
    assert res.exit_code == 2 and "already exists" in res.output
    res = runner.invoke(app, ["db", "split", "--to", str(data), "--force", "--json"])
    assert res.exit_code == 0
    out = json.loads(res.stdout)
    assert out["ok"] and out["ledger_drift"] == 0 and out["sizes"]["user"] > 0
    with sqlite3.connect(source) as c:
        c.execute("INSERT INTO inventory (scryfall_id, finish, quantity) VALUES ('zz', 'nonfoil', 1)")
    res = runner.invoke(app, ["db", "split", "--to", str(data), "--force"])
    assert res.exit_code == 1 and "SPLIT FAILED" in res.output


# ---------- split-aware snapshot / restore ----------

@pytest.fixture
def split_env(source, tmp_path, monkeypatch):
    data = tmp_path / "data"
    split.split(source, data)
    monkeypatch.delenv("MAGIC_MANAGER_DB")
    monkeypatch.setenv("MM_LAYOUT", "split")
    monkeypatch.setenv("MM_DATA_DIR", str(data))
    return data


def _qty() -> int:
    with db.connect() as conn:
        return conn.execute("SELECT quantity FROM inventory WHERE scryfall_id = ?", (A,)).fetchone()[0]


def test_split_snapshot_restore_round_trip(split_env):
    snap = db.snapshot(label="t")
    assert snap.parent == split_env / "bak" and snap.name.startswith("split.bak-") and snap.name.endswith("-t")
    assert (snap / "catalog.db").is_file() and (snap / "users" / "owner.db").is_file()
    assert db.list_snapshots() == [snap]
    assert db.snapshot_size(snap) > 0

    inventory.inventory_add(A, "nonfoil", 5)
    with db.connect() as conn:
        db.set_catalog_setting(conn, "sets.partial", None)
    assert _qty() == 7

    replaced = db.restore(snap)
    assert _qty() == 2
    with db.connect() as conn:
        assert db.catalog_setting(conn, "sets.partial") == '["abc"]'
    assert replaced.parent == split_env / "replaced"
    assert (replaced / "catalog.db").is_file() and (replaced / "users" / "owner.db").is_file()

    with pytest.raises(ValueError, match="pair snapshot directory"):
        db.restore(snap / "catalog.db")


def test_split_snapshots_are_per_user_and_prunable(split_env, monkeypatch):
    first = db.snapshot(label="a")
    second = db.snapshot(label="b")
    assert set(db.list_snapshots()) == {first, second}
    monkeypatch.setenv("MM_USER", "someone-else")
    assert db.list_snapshots() == []
    monkeypatch.setenv("MM_USER", "owner")
    doomed, freed = db.prune_snapshots(keep=1, apply=True)
    assert len(doomed) == 1 and freed > 0 and not doomed[0].exists()
    with pytest.raises(FileExistsError):
        db.snapshot(dest=db.list_snapshots()[0])


def test_cli_snapshots_and_integrity_in_split(split_env):
    runner = CliRunner()
    assert runner.invoke(app, ["db", "snapshot"]).exit_code == 0
    res = runner.invoke(app, ["db", "snapshots"])
    assert res.exit_code == 0 and "split.bak-" in res.output
    res = runner.invoke(app, ["db", "integrity"])
    assert res.exit_code == 0 and res.output.count(": ok") == 2


def test_single_snapshot_unchanged(source):
    snap = db.snapshot(label="s")
    assert snap.is_file() and snap.parent == db.bak_dir()
    assert db.list_snapshots() == [snap]


# ---------- split rehearsals ----------

def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def post_v36(monkeypatch):
    """A fake catalog migration and a fake user migration past V36."""
    v = db.CURRENT_VERSION
    monkeypatch.setattr(db, "MIGRATIONS", db.MIGRATIONS + [
        "ALTER TABLE cards ADD COLUMN v_catalog TEXT;",
        "ALTER TABLE inventory ADD COLUMN v_user TEXT;",
    ])
    monkeypatch.setattr(db, "CURRENT_VERSION", v + 2)
    monkeypatch.setattr(db, "MIGRATION_TARGETS", {**db.MIGRATION_TARGETS, v + 1: "catalog", v + 2: "user"})
    return v


@pytest.fixture
def split_data(source, tmp_path, monkeypatch):
    data = tmp_path / "data"
    split.split(source, data)
    monkeypatch.delenv("MAGIC_MANAGER_DB")
    return data


def test_rehearse_split_runs_each_target_on_copies(split_data, post_v36, capsys):
    before = {f: _sha(f) for f in split_data.rglob("*.db")}
    assert _load("rehearse_migration").main(["--layout", "split", "--data-dir", str(split_data)]) == 0
    out = capsys.readouterr().out
    assert f"catalog schema_version: {post_v36} → {post_v36 + 2}  (applied: V{post_v36 + 1})" in out
    assert f"user schema_version: {post_v36} → {post_v36 + 2}  (applied: V{post_v36 + 2})" in out
    assert "ingest_events" in out and "DIVERGED" not in out and "OK: user precious" in out
    assert {f: _sha(f) for f in split_data.rglob("*.db")} == before  # live pair untouched


def test_rehearse_split_catches_a_precious_change(split_data, post_v36, monkeypatch, capsys):
    monkeypatch.setattr(db, "MIGRATIONS", db.MIGRATIONS[:-1] + ["UPDATE ingest_events SET label = 'x';"])
    assert _load("rehearse_migration").main(["--layout", "split", "--data-dir", str(split_data)]) == 1
    assert "DIVERGED" in capsys.readouterr().out


@pytest.fixture
def no_network(monkeypatch):
    monkeypatch.setattr(sets, "backfill_released_at", lambda: 0)
    monkeypatch.setattr(scryfall_tags, "sync_kinds", lambda: "stubbed")
    monkeypatch.setattr(decks, "unclassified_precon_count", lambda **k: 0)
    monkeypatch.setattr(scryfall_art, "backfill_illustration_ids", lambda: 0)


def test_post_merge_split_rehearsal(split_data, post_v36, no_network, capsys):
    before = {f: _sha(f) for f in split_data.rglob("*.db")}
    assert _load("post_merge_upgrade").main(["--layout", "split", "--data-dir", str(split_data)]) == 0
    out = capsys.readouterr().out
    assert f"catalog catalog.db: applied V{post_v36 + 1}" in out and f"user owner.db: applied V{post_v36 + 2}" in out
    assert "✗" not in out and "ledger reconciles" in out
    assert {f: _sha(f) for f in split_data.rglob("*.db")} == before


def test_post_merge_split_apply_snapshots_the_pair(split_data, post_v36, no_network, capsys):
    assert _load("post_merge_upgrade").main(["--layout", "split", "--data-dir", str(split_data), "--apply"]) == 0
    assert len(list((split_data / "bak").glob("split.bak-*-pre-post-merge-upgrade"))) == 1
    with sqlite3.connect(split_data / "users" / "owner.db") as u:
        assert "v_user" in {r[1] for r in u.execute("PRAGMA table_info(inventory)")}
    assert "mm db restore" in capsys.readouterr().out


def test_post_merge_split_arg_errors(tmp_path):
    pmu = _load("post_merge_upgrade")
    with pytest.raises(SystemExit):
        pmu.main(["--layout", "split"])
    with pytest.raises(SystemExit):
        pmu.main(["--data-dir", str(tmp_path)])
    assert pmu.main(["--layout", "split", "--data-dir", str(tmp_path)]) == 1  # no files there
