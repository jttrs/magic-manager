"""Catalog/user table split (docs/webapp-architecture-decision.md §25, step 1).

* every table a fresh DB creates is classified exactly once in ``layout``;
* catalog and user table names never collide;
* the split layout's ``db.connect`` reads across both files and writes each
  table to its own file;
* the single layout (the default, and whenever ``MAGIC_MANAGER_DB`` is set)
  is unchanged.
"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from magic_manager import db, layout, undo


def _objects(path: Path) -> dict[str, set[str]]:
    with sqlite3.connect(path) as c:
        rows = c.execute(
            "SELECT type, name FROM sqlite_master WHERE type IN ('table','view','trigger')"
        ).fetchall()
    out: dict[str, set[str]] = {"table": set(), "view": set(), "trigger": set()}
    for kind, name in rows:
        out[kind].add(name)
    return out


@pytest.fixture
def fresh_db(tmp_path) -> Path:
    p = tmp_path / "fresh.db"
    with db.connect(p):
        pass
    return p


def test_every_table_classified_exactly_once(fresh_db):
    objs = _objects(fresh_db)
    groups = [set(layout.USER_TABLES), layout.CATALOG_TABLES, layout.INFRA_TABLES, layout.LEGACY_TABLES]
    assert len(layout.USER_TABLES) == len(set(layout.USER_TABLES))
    for i, a in enumerate(groups):
        for b in groups[i + 1:]:
            assert not a & b, f"classified twice: {sorted(a & b)}"
    unclassified = objs["table"] - set().union(*groups)
    assert not unclassified, f"add these to magic_manager.layout: {sorted(unclassified)}"
    stale = set().union(*groups) - objs["table"]
    assert not stale, f"classified but never created: {sorted(stale)}"
    for t in objs["table"]:
        assert layout.classify(t) in {"user", "catalog", "infra", "legacy"}
    # A view/trigger could reference tables in the other file — none exist yet.
    assert not objs["view"] and not objs["trigger"]


def test_undo_uses_the_registry():
    assert undo.USER_TABLES is layout.USER_TABLES
    with pytest.raises(KeyError):
        layout.classify("no_such_table")


def test_catalog_and_user_names_unique():
    assert not set(layout.USER_TABLES) & layout.CATALOG_TABLES


# ---------- layout resolution ----------

def _resolve(env):
    return layout.resolve(env, single_path=Path("/x/db/magic_manager.db"), default_dir=Path("/x/db"))


def test_resolve_single_by_default():
    assert _resolve({}) == layout.Layout("single", Path("/x/db/magic_manager.db"))
    assert _resolve({"MM_LAYOUT": "single"}).kind == "single"


def test_magic_manager_db_forces_single():
    lay = _resolve({"MAGIC_MANAGER_DB": "/t/a.db", "MM_LAYOUT": "split"})
    assert lay.kind == "single"


def test_resolve_split_paths():
    assert _resolve({"MM_LAYOUT": "split"}) == layout.Layout(
        "split", Path("/x/db/users/owner.db"), Path("/x/db/catalog.db"), "owner")
    lay = _resolve({"MM_LAYOUT": "Split", "MM_DATA_DIR": "/data", "MM_USER": "u_1-a"})
    assert lay.path == Path("/data/users/u_1-a.db") and lay.catalog == Path("/data/catalog.db")


@pytest.mark.parametrize("env", [
    {"MM_LAYOUT": "postgres"},
    {"MM_LAYOUT": "split", "MM_USER": "../owner"},
    {"MM_LAYOUT": "split", "MM_USER": "a/b"},
])
def test_resolve_rejects_bad_settings(env):
    with pytest.raises(layout.LayoutError):
        _resolve(env)


# ---------- split connect ----------

def _keep_only(path: Path, keep: set[str]) -> None:
    con = sqlite3.connect(path)  # foreign_keys is OFF on a raw connection
    for t in _objects(path)["table"] - keep - layout.INFRA_TABLES:
        con.execute(f"DROP TABLE {t}")
    con.commit()
    con.close()


@pytest.fixture
def split_env(fresh_db, tmp_path, monkeypatch, make_card):
    """A split data dir built from a fresh DB.

    Step-2 workaround: user tables still declare FOREIGN KEYs to ``cards``,
    which lives in the other file, so rows referencing a card are seeded on a
    raw connection with foreign keys off.
    """
    data = tmp_path / "data"
    (data / "users").mkdir(parents=True)
    catalog, user = data / "catalog.db", data / "users" / "owner.db"
    shutil.copy(fresh_db, catalog)
    shutil.copy(fresh_db, user)
    _keep_only(catalog, set(layout.CATALOG_TABLES))
    _keep_only(user, set(layout.USER_TABLES))

    card = make_card(id="c-1", name="Sol Ring")
    with sqlite3.connect(catalog) as c:
        c.row_factory = sqlite3.Row
        db.upsert_card(c, card)
    with sqlite3.connect(user) as u:
        u.execute("INSERT INTO inventory (scryfall_id, finish, quantity) VALUES ('c-1', 'nonfoil', 3)")

    monkeypatch.delenv("MAGIC_MANAGER_DB", raising=False)
    monkeypatch.setenv("MM_LAYOUT", "split")
    monkeypatch.setenv("MM_DATA_DIR", str(data))
    return catalog, user


def test_split_files_hold_only_their_tables(split_env):
    catalog, user = split_env
    assert _objects(catalog)["table"] - layout.INFRA_TABLES == layout.CATALOG_TABLES
    assert _objects(user)["table"] - layout.INFRA_TABLES == set(layout.USER_TABLES)


def test_split_connect_reads_across_files(split_env):
    with db.connect() as conn:
        dbs = {r["name"]: r["file"] for r in conn.execute("PRAGMA database_list")}
        assert Path(dbs["main"]) == split_env[1] and Path(dbs["catalog"]) == split_env[0]
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        row = conn.execute(
            "SELECT c.name, i.quantity FROM inventory i JOIN cards c USING (scryfall_id)"
        ).fetchone()
        assert (row["name"], row["quantity"]) == ("Sol Ring", 3)


def test_split_writes_land_in_their_own_file(split_env, make_card):
    catalog, user = split_env
    with db.transaction() as conn:
        db.upsert_card(conn, make_card(id="c-2", name="Arcane Signet", collector_number="2"))
        conn.execute("INSERT INTO settings (key, value) VALUES ('k', 'v')")
        conn.execute("INSERT INTO decks (slug, name, created_at, updated_at) VALUES ('d', 'D', 'now', 'now')")
    with sqlite3.connect(catalog) as c:
        assert c.execute("SELECT name FROM cards WHERE scryfall_id='c-2'").fetchone() == ("Arcane Signet",)
    with sqlite3.connect(user) as u:
        assert u.execute("SELECT value FROM settings WHERE key='k'").fetchone() == ("v",)
        assert u.execute("SELECT name FROM decks WHERE slug='d'").fetchone() == ("D",)


def test_split_rolls_back_both_files(split_env, make_card):
    catalog, user = split_env
    with pytest.raises(RuntimeError):
        with db.connect() as conn:
            db.upsert_card(conn, make_card(id="c-3", collector_number="3"))
            conn.execute("INSERT INTO settings (key, value) VALUES ('k2', 'v')")
            raise RuntimeError("boom")
    with sqlite3.connect(catalog) as c:
        assert c.execute("SELECT 1 FROM cards WHERE scryfall_id='c-3'").fetchone() is None
    with sqlite3.connect(user) as u:
        assert u.execute("SELECT 1 FROM settings WHERE key='k2'").fetchone() is None


def test_split_never_creates_or_migrates(split_env, tmp_path, monkeypatch):
    catalog, user = split_env
    with db.connect():
        pass
    assert _objects(user)["table"] - layout.INFRA_TABLES == set(layout.USER_TABLES)

    with sqlite3.connect(catalog) as c:
        c.execute("UPDATE schema_version SET version = version - 1")
    with pytest.raises(layout.LayoutError, match="catalog DB is at schema"):
        with db.connect():
            pass

    monkeypatch.setenv("MM_USER", "nobody")
    with pytest.raises(layout.LayoutError, match="does not exist"):
        with db.connect():
            pass
    assert not (catalog.parent / "users" / "nobody.db").exists()


@pytest.mark.xfail(strict=True, reason="step 2: user schema without FKs into the catalog file")
def test_split_inventory_write_through_engine(split_env):
    from magic_manager import inventory
    inventory.inventory_add("c-1", "nonfoil", 1)


# ---------- single layout unchanged ----------

def test_single_connect_unchanged(tmp_db, monkeypatch):
    monkeypatch.setenv("MM_LAYOUT", "split")  # MAGIC_MANAGER_DB still wins
    with db.connect() as conn:
        names = [r["name"] for r in conn.execute("PRAGMA database_list")]
        assert names == ["main"]
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert set(layout.USER_TABLES) | layout.CATALOG_TABLES <= tables
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == db.CURRENT_VERSION
