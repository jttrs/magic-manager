"""One undo snapshot of YOUR data — a single restore point for "undo that".

Only the tables you own are copied (inventory + the provenance ledger, decks,
their cards/assignments/versions, wishlist, earmarks, set targets, settings) —
a few MB, versus the 677 MB live DB that is mostly the rebuildable card/price
cache. The snapshot is a separate SQLite file beside the DB (``undo.db``), with
exactly one slot.

* :func:`take` overwrites the slot (atomically: written to a temp file, then
  renamed). The web app takes one before the first write of each session
  (:class:`SessionGuard`).
* :func:`restore` SWAPS: the current data becomes the new snapshot, then the
  snapshot's rows replace the live ones in one transaction — so a restore is
  itself undoable. Refused across a schema change.

``db.snapshot`` / ``db.restore`` (whole-file backups in ``db/bak``) are the
heavyweight sibling for migrations; this is the everyday undo.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import db

# Your data, parents before children. Card/price/EDHREC/tag tables are caches
# and are never touched (cards only ever grow, so restored rows' FKs hold).
USER_TABLES = (
    "settings", "set_targets", "imports",
    "ingest_events", "inventory", "inventory_events",
    "decks", "deck_cards", "deck_versions", "deck_assignments",
    "wishlist_entries", "earmarked_products", "earmark_links", "earmark_prices", "earmark_targets",
)

SESSION_GAP_SECONDS = 30 * 60
SNAPSHOT_FILE = "undo.db"


class UndoError(RuntimeError):
    """Nothing to restore, or the snapshot no longer fits the schema."""


def snapshot_path() -> Path:
    return db.db_dir() / SNAPSHOT_FILE


def _tables(conn: sqlite3.Connection, schema: str = "main") -> set[str]:
    return {r[0] for r in conn.execute(f"SELECT name FROM {schema}.sqlite_master WHERE type='table'")}


def _columns(conn: sqlite3.Connection, schema: str, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA {schema}.table_info({table})")]


def _summary(conn: sqlite3.Connection, schema: str = "main") -> dict[str, int]:
    """What a person would notice: copies, printings, decks, built decks, wishlist, earmarks."""
    def one(sql: str) -> int:
        try:
            return int(conn.execute(sql.format(s=schema)).fetchone()[0] or 0)
        except sqlite3.OperationalError:
            return 0
    return {
        "copies": one("SELECT SUM(quantity) FROM {s}.inventory WHERE quantity > 0"),
        "printings": one("SELECT COUNT(*) FROM {s}.inventory WHERE quantity > 0"),
        "decks": one("SELECT COUNT(*) FROM {s}.decks"),
        "built": one("SELECT COUNT(*) FROM {s}.decks WHERE precon_state = 'built'"),
        "wishlist": one("SELECT COUNT(*) FROM {s}.wishlist_entries"),
        "earmarks": one("SELECT COUNT(*) FROM {s}.earmarked_products"),
    }


def _schema_version(conn: sqlite3.Connection, schema: str = "main") -> int:
    return int(conn.execute(f"SELECT MAX(version) FROM {schema}.schema_version").fetchone()[0] or 0)


def _write(conn: sqlite3.Connection, dest: Path, reason: str) -> None:
    """Copy the user tables into a fresh file, then atomically move it to ``dest``."""
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.unlink(missing_ok=True)
    conn.commit()
    conn.execute("ATTACH DATABASE ? AS snap", (str(tmp),))
    try:
        present = _tables(conn)
        for t in USER_TABLES:
            if t in present:
                conn.execute(f"CREATE TABLE snap.{t} AS SELECT * FROM main.{t}")
        conn.execute("CREATE TABLE snap._meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("CREATE TABLE snap.schema_version (version INTEGER)")
        conn.execute("INSERT INTO snap.schema_version VALUES (?)", (_schema_version(conn),))
        conn.executemany("INSERT INTO snap._meta VALUES (?, ?)", [
            ("taken_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
            ("reason", reason),
        ])
        conn.commit()
    finally:
        conn.execute("DETACH DATABASE snap")
    os.replace(tmp, dest)


def take(reason: str = "manual") -> dict:
    """Overwrite the one snapshot slot with your current data."""
    with db.connect() as conn:
        _write(conn, snapshot_path(), reason)
    return info()


@dataclass
class _Snap:
    taken_at: str
    reason: str
    schema_version: int


def _read_meta(conn: sqlite3.Connection) -> _Snap:
    meta = dict(conn.execute("SELECT key, value FROM snap._meta").fetchall())
    return _Snap(taken_at=meta.get("taken_at", ""), reason=meta.get("reason", ""),
                 schema_version=_schema_version(conn, "snap"))


def info() -> dict | None:
    """The snapshot (time, reason) and what restoring it would change, or None."""
    path = snapshot_path()
    if not path.exists():
        return None
    with db.connect() as conn:
        conn.execute("ATTACH DATABASE ? AS snap", (str(path),))
        try:
            meta = _read_meta(conn)
            now, then = _summary(conn, "main"), _summary(conn, "snap")
            restorable = meta.schema_version == _schema_version(conn)
        finally:
            conn.execute("DETACH DATABASE snap")
    return {
        "taken_at": meta.taken_at, "reason": meta.reason, "restorable": restorable,
        "current": now, "snapshot": then,
        "changes": {k: then[k] - now[k] for k in now},
    }


def restore() -> dict:
    """Swap: your current data becomes the snapshot, the snapshot becomes live."""
    path = snapshot_path()
    if not path.exists():
        raise UndoError("There’s no restore point yet.")
    swap = path.with_name(path.name + ".next")
    with db.connect() as conn:
        conn.execute("ATTACH DATABASE ? AS snap", (str(path),))
        try:
            meta = _read_meta(conn)
            if meta.schema_version != _schema_version(conn):
                raise UndoError("The app’s database changed shape since this restore point was taken, so it can’t be restored.")
        finally:
            conn.execute("DETACH DATABASE snap")
        _write(conn, swap, "before your last restore")
        conn.execute("ATTACH DATABASE ? AS snap", (str(path),))
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("PRAGMA defer_foreign_keys = ON")
            live, saved = _tables(conn), _tables(conn, "snap")
            tables = [t for t in USER_TABLES if t in live]
            for t in reversed(tables):
                conn.execute(f"DELETE FROM main.{t}")
            for t in tables:
                if t not in saved:
                    continue
                cols = [c for c in _columns(conn, "main", t) if c in set(_columns(conn, "snap", t))]
                cl = ", ".join(f'"{c}"' for c in cols)
                conn.execute(f"INSERT INTO main.{t} ({cl}) SELECT {cl} FROM snap.{t}")
            conn.commit()
        except Exception:
            conn.rollback()
            swap.unlink(missing_ok=True)
            raise
        finally:
            conn.execute("DETACH DATABASE snap")
    os.replace(swap, path)
    return info() or {}


class SessionGuard:
    """Takes the snapshot before the first write of each app session: the first
    write after the server starts, or after ``gap`` seconds without a write."""

    def __init__(self, gap: float = SESSION_GAP_SECONDS, clock=time.monotonic):
        self._gap = gap
        self._clock = clock
        self._last: float | None = None
        self._lock = threading.Lock()

    def before_write(self, reason: str) -> bool:
        """Snapshot if this write starts a new session. Returns True when it did."""
        with self._lock:
            now = self._clock()
            fresh = self._last is None or now - self._last > self._gap
            self._last = now
            if fresh:
                take(reason)
            return fresh
