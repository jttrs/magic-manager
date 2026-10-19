"""V36 (Phase 3 step 2): user tables lose their FOREIGN KEY into ``cards``,
catalog-describing keys move from ``settings`` to ``catalog_settings``, and
post-V36 migrations declare a target (``catalog`` | ``user``) that
``db.migrate_split_file`` runs per file."""
from __future__ import annotations

import inspect
import re
import shutil
import sqlite3

import pytest

from magic_manager import audit, db, layout

CARD_FK_TABLES = ("inventory", "inventory_events", "deck_cards", "deck_assignments", "wishlist_entries")


def _build_v35(path, monkeypatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(db, "MIGRATIONS", db.MIGRATIONS[:35])
        m.setattr(db, "CURRENT_VERSION", 35)
        with db.connect(path):
            pass
    raw = sqlite3.connect(path)  # foreign_keys OFF: lets us seed an orphan
    raw.executescript("""
        INSERT INTO cards (scryfall_id, oracle_id, name, set_code, collector_number, rarity)
            VALUES ('c1', 'o1', 'One', 'tst', '1', 'rare'), ('c2', 'o2', 'Two', 'tst', '2', 'common');
        INSERT INTO ingest_events (ingest_id, at, method, label) VALUES (7, 'now', 'adhoc', 'x');
        INSERT INTO inventory (scryfall_id, finish, quantity) VALUES ('c1', 'nonfoil', 2), ('gone', 'foil', 1);
        INSERT INTO inventory_events (ingest_id, scryfall_id, finish, delta, at) VALUES
            (7, 'c1', 'nonfoil', 2, 'now'), (7, 'gone', 'foil', 1, 'now'), (7, 'c2', 'foil', 5, 'now');
        DELETE FROM inventory_events WHERE scryfall_id = 'c2';   -- sequence now ahead of MAX(event_id)
        INSERT INTO decks (deck_id, slug, name, created_at, updated_at) VALUES (3, 'd', 'D', 'now', 'now');
        INSERT INTO deck_versions (deck_version_id, deck_id, version_number, status, is_current, effective_from, created_at)
            VALUES (5, 3, 1, 'tuned', 1, 'now', 'now');
        INSERT INTO deck_cards (deck_version_id, scryfall_id, board, finish, count) VALUES (5, 'c1', 'main', 'nonfoil', 1);
        INSERT INTO deck_assignments (deck_id, scryfall_id, finish, count, assigned_at) VALUES (3, 'c1', 'nonfoil', 1, 'now');
        INSERT INTO wishlist_entries (scryfall_id, finish, qty_wanted, added_at) VALUES ('c2', 'either', 1, 'now');
        INSERT INTO settings (key, value) VALUES
            ('sets.partial', '["tst"]'), ('scryfall_tags.source', 'o.gz'), ('scryfall_tags.art_source', 'a.gz'),
            ('front_set:msh', 'fmsc'), ('front_set:fin', ''), ('analytics.consent', '{}'), ('deals.match:u', 'm');
    """)
    raw.commit()
    raw.close()


def _dump(path) -> dict:
    con = sqlite3.connect(path)
    try:
        out = {}
        for t in CARD_FK_TABLES + ("settings",):
            out[t] = con.execute(f"SELECT rowid, * FROM {t} ORDER BY rowid").fetchall()
        out["indexes"] = sorted(con.execute(
            "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'").fetchall())
        out["sql"] = dict(con.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall())
        out["seq"] = dict(con.execute("SELECT name, seq FROM sqlite_sequence").fetchall())
        out["fks"] = {t: sorted((r[2], r[3], r[4]) for r in con.execute(f"PRAGMA foreign_key_list({t})"))
                      for t in CARD_FK_TABLES}
        return out
    finally:
        con.close()


@pytest.fixture
def v35(tmp_path, monkeypatch):
    path = tmp_path / "db" / "magic_manager.db"
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(path))
    _build_v35(path, monkeypatch)
    return path


def test_v36_drops_only_card_fks_and_keeps_everything_else(v35):
    before = _dump(v35)
    with db.connect() as conn:
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == db.CURRENT_VERSION
    after = _dump(v35)

    for t in CARD_FK_TABLES:
        assert after[t] == before[t], t                       # rows + rowids
        assert ("cards", "scryfall_id", "scryfall_id") in before["fks"][t]
        assert after["fks"][t] == [f for f in before["fks"][t] if f[0] != "cards"]
        stripped = re.sub(r",\s*FOREIGN KEY \(scryfall_id\) REFERENCES cards\(scryfall_id\)", "", before["sql"][t])
        assert after["sql"][t] == stripped                    # columns, CHECKs, comments intact
    # catalog_settings is V36's own; tables added by later migrations aren't V36's concern.
    assert [i for i in after["indexes"] if i[1] not in {"catalog_settings", "card_earmarks"}] == before["indexes"]
    assert after["seq"]["inventory_events"] == before["seq"]["inventory_events"] == 3
    assert after["sql"]["list_rows"] == before["sql"]["list_rows"]  # legacy left alone

    con = sqlite3.connect(v35)
    assert dict(con.execute("SELECT key, value FROM catalog_settings")) == {
        "sets.partial": '["tst"]', "scryfall_tags.source": "o.gz", "scryfall_tags.art_source": "a.gz",
        "front_set:msh": "fmsc", "front_set:fin": ""}
    assert dict(con.execute("SELECT key, value FROM settings")) == {"analytics.consent": "{}", "deals.match:u": "m"}
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    con.close()


def test_v36_keeps_user_fks_enforced_and_lets_orphans_through(v35):
    with db.connect() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO inventory_events (ingest_id, scryfall_id, finish, delta, at) "
                         "VALUES (999, 'c1', 'foil', 1, 'now')")
        conn.execute("INSERT INTO deck_cards (deck_version_id, scryfall_id, board, finish, count) "
                     "VALUES (5, 'nowhere', 'main', 'foil', 1)")
        found = {f.table: f for f in audit.catalog_refs(conn)}
    assert found["inventory"].scryfall_ids == ["gone"]
    assert found["inventory_events"].rows == 1
    assert found["deck_cards"].scryfall_ids == ["nowhere"]
    assert found["wishlist_entries"].rows == 0


def test_v36_is_idempotent(v35):
    with db.connect():
        pass
    once = _dump(v35)
    con = sqlite3.connect(v35)
    con.execute("PRAGMA foreign_keys = OFF")
    con.executescript(db.SCHEMA_V36)
    db._run_v36_python_migration(con)
    con.commit()
    con.close()
    assert _dump(v35) == once


def test_fresh_db_has_no_user_fk_into_cards(tmp_db):
    with db.connect() as conn:
        for t in layout.USER_TABLES:
            assert all(fk[2] != "cards" for fk in conn.execute(f"PRAGMA foreign_key_list({t})")), t


def test_catalog_settings_helper(tmp_db):
    with db.connect() as conn:
        assert db.catalog_setting(conn, "k") is None
        db.set_catalog_setting(conn, "k", "v")
        db.set_catalog_setting(conn, "k", "w")
        assert db.catalog_setting(conn, "k") == "w"
        db.set_catalog_setting(conn, "k", None)
        assert db.catalog_setting(conn, "k") is None


def test_catalog_keys_have_no_settings_writer():
    """Every catalog-key reader/writer goes through db.catalog_setting/set_catalog_setting."""
    from pathlib import Path
    src = Path(db.__file__).parent
    for f in src.rglob("*.py"):
        text = f.read_text()
        for key in db.CATALOG_SETTING_KEYS + db.CATALOG_SETTING_PREFIXES:
            for m in re.finditer(re.escape(key), text):
                line = text[text.rfind("\n", 0, m.start()) + 1:text.find("\n", m.end())]
                assert "settings" not in line.replace("catalog_settings", "").replace("settings_key", ""), (f, line)


def test_catalog_refs_cli_exit_code(v35):
    from typer.testing import CliRunner
    from magic_manager.cli import app
    r = CliRunner().invoke(app, ["audit", "catalog-refs"])
    assert r.exit_code == 1 and "inventory: 1 row(s)" in r.output
    with db.connect() as conn:
        conn.execute("DELETE FROM inventory WHERE scryfall_id = 'gone'")
        conn.execute("DELETE FROM inventory_events WHERE scryfall_id = 'gone'")
    r = CliRunner().invoke(app, ["audit", "catalog-refs"])
    assert r.exit_code == 0 and "OK" in r.output


# ---------- migration targets ----------

_TABLE_REF = re.compile(
    r"\b(?:CREATE\s+(?:TABLE|(?:UNIQUE\s+)?INDEX)\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\s+ON\s+)?"
    r"|ALTER\s+TABLE\s+|INSERT\s+(?:OR\s+\w+\s+)?INTO\s+|UPDATE\s+|DELETE\s+FROM\s+|DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?"
    r"|FROM\s+|JOIN\s+|REFERENCES\s+)\"?(\w+)", re.IGNORECASE)


def migration_tables(sql: str) -> set[str]:
    return {m.group(1) for m in _TABLE_REF.finditer(sql)}


def _check_targets(migrations, targets) -> list[str]:
    problems = []
    for v in range(db.SPLIT_BASE_VERSION + 1, len(migrations) + 1):
        target = targets.get(v)
        if target not in db.SPLIT_TARGETS:
            problems.append(f"V{v} has no target (catalog | user) in db.MIGRATION_TARGETS")
            continue
        sources = [migrations[v - 1]]
        for hooks in (db._PYTHON_HOOKS, db._FK_OFF_HOOKS):    # migrate_split_file runs these too
            if v in hooks:
                sources.append(inspect.getsource(hooks[v]))
        for t in sorted(set().union(*(migration_tables(src) for src in sources))):
            if t in layout.INFRA_TABLES:
                continue
            try:
                kind = layout.classify(t.removesuffix("__new"))
            except KeyError:
                problems.append(f"V{v} touches {t}, which magic_manager.layout doesn't classify")
                continue
            if kind != target:
                problems.append(f"V{v} ({target}) touches {kind} table {t}")
    return problems


def test_every_post_split_migration_has_a_matching_target():
    assert db.CURRENT_VERSION == len(db.MIGRATIONS)
    assert db.SPLIT_BASE_VERSION == 36 <= db.CURRENT_VERSION
    assert set(db.MIGRATION_TARGETS) == set(range(db.SPLIT_BASE_VERSION + 1, db.CURRENT_VERSION + 1))
    assert _check_targets(db.MIGRATIONS, db.MIGRATION_TARGETS) == []
    assert db.migration_target(36) == "single"


def test_target_check_catches_mistakes():
    fake = db.MIGRATIONS + [
        "ALTER TABLE cards ADD COLUMN x TEXT;",
        "CREATE TABLE IF NOT EXISTS settings_extra (k TEXT);",
        "UPDATE inventory SET notes = (SELECT name FROM cards LIMIT 1);",
    ]
    v = db.CURRENT_VERSION
    problems = _check_targets(fake, {**db.MIGRATION_TARGETS, v + 1: "user", v + 3: "user"})
    assert problems == [
        f"V{v + 1} (user) touches catalog table cards",
        f"V{v + 2} has no target (catalog | user) in db.MIGRATION_TARGETS",
        f"V{v + 3} (user) touches catalog table cards",
    ]
    with pytest.raises(KeyError):
        db.migration_target(10_000)


def test_target_check_reads_python_hooks(monkeypatch):
    v = db.CURRENT_VERSION + 1

    def hook(conn):
        conn.execute("UPDATE inventory SET notes = NULL")

    monkeypatch.setitem(db._PYTHON_HOOKS, v, hook)
    assert _check_targets(db.MIGRATIONS + ["ALTER TABLE cards ADD COLUMN x TEXT;"], {**db.MIGRATION_TARGETS, v: "catalog"}) == [
        f"V{v} (catalog) touches user table inventory"]


# ---------- per-target migrate on a split fixture ----------

def _keep_only(path, keep) -> None:
    con = sqlite3.connect(path)
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        if t not in keep and t not in layout.INFRA_TABLES:
            con.execute(f"DROP TABLE {t}")
    con.commit()
    con.close()


@pytest.fixture
def split_files(tmp_path):
    fresh_db = tmp_path / "fresh.db"
    with db.connect(fresh_db):
        pass
    data = tmp_path / "data"
    (data / "users").mkdir(parents=True)
    catalog, user = data / "catalog.db", data / "users" / "owner.db"
    shutil.copy(fresh_db, catalog)
    shutil.copy(fresh_db, user)
    _keep_only(catalog, layout.CATALOG_TABLES)
    _keep_only(user, set(layout.USER_TABLES))
    return catalog, user


def _version(path) -> int:
    with sqlite3.connect(path) as c:
        return c.execute("SELECT version FROM schema_version").fetchone()[0]


def test_migrate_split_file_runs_only_its_target(split_files, monkeypatch):
    catalog, user = split_files
    v = db.CURRENT_VERSION
    monkeypatch.setattr(db, "MIGRATIONS", db.MIGRATIONS + [
        "ALTER TABLE cards ADD COLUMN v_catalog TEXT;",
        "ALTER TABLE inventory ADD COLUMN v_user TEXT;",
    ])
    monkeypatch.setattr(db, "CURRENT_VERSION", v + 2)
    monkeypatch.setattr(db, "MIGRATION_TARGETS", {**db.MIGRATION_TARGETS, v + 1: "catalog", v + 2: "user"})
    assert _check_targets(db.MIGRATIONS, db.MIGRATION_TARGETS) == []

    assert db.migrate_split_file(catalog, "catalog") == [v + 1]
    assert db.migrate_split_file(user, "user") == [v + 2]
    assert _version(catalog) == _version(user) == v + 2
    with sqlite3.connect(catalog) as c:
        assert "v_catalog" in {r[1] for r in c.execute("PRAGMA table_info(cards)")}
    with sqlite3.connect(user) as u:
        assert "v_user" in {r[1] for r in u.execute("PRAGMA table_info(inventory)")}
    assert list((catalog.parent / "bak").glob("catalog.db.bak-*-pre-v*"))
    assert list((user.parent / "bak").glob("owner.db.bak-*-pre-v*"))

    assert db.migrate_split_file(catalog, "catalog") == []          # already current
    monkeypatch.setenv("MM_LAYOUT", "split")
    monkeypatch.setenv("MM_DATA_DIR", str(catalog.parent))
    monkeypatch.delenv("MAGIC_MANAGER_DB", raising=False)
    with db.connect() as conn:                                      # split connect accepts both
        conn.execute("SELECT v_catalog FROM cards").fetchall()
        conn.execute("SELECT v_user FROM inventory").fetchall()


def test_migrate_split_file_leaves_the_version_on_failure(split_files, monkeypatch):
    catalog, _user = split_files
    v = db.CURRENT_VERSION
    monkeypatch.setattr(db, "MIGRATIONS", db.MIGRATIONS + [
        "ALTER TABLE cards ADD COLUMN ok_col TEXT; ALTER TABLE inventory ADD COLUMN boom TEXT;"])
    monkeypatch.setattr(db, "CURRENT_VERSION", v + 1)
    monkeypatch.setattr(db, "MIGRATION_TARGETS", {**db.MIGRATION_TARGETS, v + 1: "catalog"})
    with pytest.raises(sqlite3.OperationalError):
        db.migrate_split_file(catalog, "catalog")                   # inventory isn't in the catalog file
    assert _version(catalog) == v                                   # not stamped; the pre-vN snapshot is the rollback
    assert list((catalog.parent / "bak").glob("catalog.db.bak-*"))


def test_migrate_split_file_refuses(split_files, tmp_path):
    catalog, _user = split_files
    with pytest.raises(ValueError):
        db.migrate_split_file(catalog, "single")
    with pytest.raises(layout.LayoutError, match="does not exist"):
        db.migrate_split_file(tmp_path / "nope.db", "user")
    assert not (tmp_path / "nope.db").exists()
    with sqlite3.connect(catalog) as c:
        c.execute("UPDATE schema_version SET version = 35")
    with pytest.raises(layout.LayoutError, match="split files start at"):
        db.migrate_split_file(catalog, "catalog")


# ---------- require_cards: the code-side guard that replaced the FKs ----------

_CARD_REF_INSERT = re.compile(
    r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+(inventory_events|inventory|deck_cards|deck_assignments|wishlist_entries)\b",
    re.IGNORECASE)
# Writers that store a scryfall_id without a guard, and why that's safe.
_UNGUARDED_OK = {
    ("decks.py", "create_version"): "copies rows of an existing version (already guarded)",
}


def _card_ref_writers() -> dict[tuple[str, str], str]:
    """(file, function) → that function's source, for every user-table INSERT of
    a scryfall_id in the engine (db.py migrations excluded)."""
    import ast
    from pathlib import Path
    out = {}
    for f in sorted(Path(db.__file__).parent.rglob("*.py")):
        text = f.read_text()
        if not _CARD_REF_INSERT.search(text):
            continue
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = ast.get_source_segment(text, node) or ""
                inner = [n for n in ast.walk(node) if n is not node and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                if _CARD_REF_INSERT.search(body) and not any(
                        _CARD_REF_INSERT.search(ast.get_source_segment(text, n) or "") for n in inner):
                    out[(f.name, node.name)] = body
    return {k: v for k, v in out.items() if not (k[0] == "db.py" and k[1].startswith("_run_v"))}


def test_every_card_ref_write_seam_is_guarded():
    writers = _card_ref_writers()
    assert {
        ("ingest.py", "record_delta"), ("ingest.py", "rebuild_inventory_from_ledger"),
        ("inventory.py", "inventory_add"), ("inventory.py", "inventory_set"),
        ("decks.py", "deck_add_card"), ("decks.py", "deck_assign_batch"),
    } <= set(writers)
    unguarded = sorted(k for k, body in writers.items() if "require_cards(" not in body and k not in _UNGUARDED_OK)
    assert unguarded == [], f"user-table writes of a scryfall_id without db.require_cards: {unguarded}"


def test_require_cards_refuses_unknown_and_batches(tmp_db, seed_cards, make_card):
    seed_cards([make_card(id=f"k{i}", collector_number=str(i)) for i in range(3)])
    with db.connect() as conn:
        with pytest.raises(sqlite3.IntegrityError, match="1 printing"):
            db.require_cards(conn, ["k0", "nope"])
        queries = []
        conn.set_trace_callback(queries.append)
        db.require_cards(conn, [f"k{i}" for i in range(3)] * 400)   # duplicates collapse
        db.require_cards(conn, ["k1"])                               # memo: no query
        conn.set_trace_callback(None)
        assert len([q for q in queries if "FROM cards" in q]) == 1


def test_require_cards_chunks(tmp_db, monkeypatch):
    monkeypatch.setattr(db, "_REQUIRE_CHUNK", 2)
    with db.connect() as conn:
        queries = []
        conn.set_trace_callback(queries.append)
        with pytest.raises(sqlite3.IntegrityError, match="5 printing"):
            db.require_cards(conn, ["a", "b", "c", "d", "e"])
        assert len([q for q in queries if "FROM cards" in q]) == 3


@pytest.mark.parametrize("write", [
    lambda: __import__("magic_manager.inventory", fromlist=["x"]).inventory_add("ghost", "nonfoil", 1),
    lambda: __import__("magic_manager.inventory", fromlist=["x"]).inventory_set("ghost", "foil", 2),
    lambda: __import__("magic_manager.wishlist", fromlist=["x"]).wishlist_add("ghost", "foil", "default", 1),
])
def test_engine_writes_refuse_unknown_printings(tmp_db, write):
    with pytest.raises(sqlite3.IntegrityError):
        write()
    with db.connect() as conn:
        for t in CARD_FK_TABLES:
            assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0, t


def test_deck_write_refuses_unknown_printing(tmp_db):
    from magic_manager import decks
    decks.deck_create("d", "D")
    with pytest.raises(sqlite3.IntegrityError):
        decks.deck_add_card("d", "ghost", "main", "nonfoil", 1)



def test_migrate_split_file_surfaces_a_snapshot_failure(split_files, monkeypatch):
    catalog, _user = split_files
    v = db.CURRENT_VERSION
    monkeypatch.setattr(db, "MIGRATIONS", db.MIGRATIONS + ["ALTER TABLE cards ADD COLUMN y TEXT;"])
    monkeypatch.setattr(db, "CURRENT_VERSION", v + 1)
    monkeypatch.setattr(db, "MIGRATION_TARGETS", {**db.MIGRATION_TARGETS, v + 1: "catalog"})

    def boom(**_k):
        raise RuntimeError("snapshot integrity check failed: nope")

    monkeypatch.setattr(db, "snapshot", boom)
    with pytest.raises(RuntimeError, match="snapshot integrity"):
        db.migrate_split_file(catalog, "catalog")
    assert _version(catalog) == v


def test_v36_tolerates_a_preexisting_user_fk_orphan(v35):
    raw = sqlite3.connect(v35)  # FKs off: a deck_cards row whose version is gone (legacy damage)
    raw.execute("INSERT INTO deck_cards (deck_version_id, scryfall_id, board, finish, count) "
                "VALUES (404, 'c1', 'main', 'foil', 1)")
    raw.commit()
    raw.close()
    with db.connect() as conn:
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == db.CURRENT_VERSION
        assert all(fk[2] != "cards" for fk in conn.execute("PRAGMA foreign_key_list(deck_cards)"))


def test_upsert_card_warms_the_guard(tmp_db, make_card):
    with db.connect() as conn:
        db.upsert_card(conn, make_card(id="w1"))
        queries = []
        conn.set_trace_callback(queries.append)
        db.require_cards(conn, ["w1"])
        conn.set_trace_callback(None)
        assert not [q for q in queries if "FROM cards" in q]


def test_bulk_import_with_one_unknown_printing_writes_nothing(tmp_db, seed_cards, make_card):
    from magic_manager import collection_sync
    from magic_manager.collection_sync import CollectionRow
    seed_cards([make_card(id="b1")])
    with pytest.raises(sqlite3.IntegrityError, match="ghost"):
        collection_sync.apply_import(
            [CollectionRow(qty=2, finish="nonfoil", scryfall_id="b1"),
             CollectionRow(qty=1, finish="foil", scryfall_id="ghost")], mode="add")
    with db.connect() as conn:
        for t in ("inventory", "inventory_events", "ingest_events"):
            assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0, t
