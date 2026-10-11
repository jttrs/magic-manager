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
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import db
from .analytics import consent
from .sets import PARTIAL_SETS_KEY

# Your data, parents before children. Card/price/EDHREC/tag tables are caches
# and are never touched (cards only ever grow, so restored rows' FKs hold).
USER_TABLES = (
    "settings", "set_targets", "imports",
    "ingest_events", "inventory", "inventory_events",
    "decks", "deck_cards", "deck_versions", "deck_assignments",
    "wishlist_entries", "earmarked_products", "earmark_links", "earmark_prices", "earmark_targets",
    "purchases", "purchase_lines",
)

# ``settings`` keys a restore must NOT roll back: they reflect the latest choice
# (opting out of tracking, then pressing Undo, must not opt you back in), or
# describe the card catalog, which a restore never touches.
KEEP_SETTINGS = (consent.SETTING_KEY, PARTIAL_SETS_KEY)

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


# Every user table, grouped in plain words, so a restore never rolls back
# something the confirm dialog didn't mention. Each group counts the rows that
# differ (added, removed or edited) between now and the snapshot.
DETAIL_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cards in your collection", ("inventory",)),
    ("acquisition history", ("ingest_events", "inventory_events", "imports")),
    ("decks", ("decks",)),
    ("deck lists", ("deck_cards", "deck_versions")),
    ("cards sleeved in decks", ("deck_assignments",)),
    ("wishlist", ("wishlist_entries",)),
    ("watched products", ("earmarked_products", "earmark_links", "earmark_targets")),
    ("price history", ("earmark_prices",)),
    ("store orders", ("purchases", "purchase_lines")),
    ("set targets", ("set_targets",)),
    ("settings", ("settings",)),
)
assert sorted(t for _, ts in DETAIL_GROUPS for t in ts) == sorted(USER_TABLES)


def _pk_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cols = [(r[5], r[1]) for r in conn.execute(f"PRAGMA main.table_info({table})") if r[5]]
    return [c for _, c in sorted(cols)]


def _details(conn: sqlite3.Connection) -> list[dict]:
    """Rows that differ per :data:`DETAIL_GROUPS` group (nonzero groups only).
    Assumes ``snap`` is attached with the same schema."""
    live, saved = _tables(conn), _tables(conn, "snap")
    out = []
    for label, tables in DETAIL_GROUPS:
        rows = 0
        for t in tables:
            if t not in live or t not in saved:
                continue
            cl = ", ".join(f'"{c}"' for c in _columns(conn, "main", t))
            pk = ", ".join(f'"{c}"' for c in _pk_columns(conn, t)) or cl
            where, args = "", ()
            if t == "settings":
                where = f" WHERE key NOT IN ({', '.join('?' for _ in KEEP_SETTINGS)})"
                args = KEEP_SETTINGS
            # Distinct keys present on either side of the difference: an edited
            # row counts once, like an added or removed one.
            rows += conn.execute(
                f"SELECT COUNT(*) FROM ("
                f"SELECT {pk} FROM (SELECT {cl} FROM main.{t}{where} EXCEPT SELECT {cl} FROM snap.{t}{where}) "
                f"UNION SELECT {pk} FROM (SELECT {cl} FROM snap.{t}{where} EXCEPT SELECT {cl} FROM main.{t}{where}))",
                args * 4).fetchone()[0]
        if rows:
            out.append({"label": label, "rows": rows})
    return out


def _schema_version(conn: sqlite3.Connection, schema: str = "main") -> int:
    return int(conn.execute(f"SELECT MAX(version) FROM {schema}.schema_version").fetchone()[0] or 0)


def _copy_into(conn: sqlite3.Connection, schema: str, reason: str) -> None:
    """Copy the user tables into the attached, empty ``schema``. Runs inside the
    caller's transaction, so every table comes from the same point in time."""
    present = _tables(conn)
    for t in USER_TABLES:
        if t in present:
            conn.execute(f"CREATE TABLE {schema}.{t} AS SELECT * FROM main.{t}")
    conn.execute(f"CREATE TABLE {schema}._meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute(f"CREATE TABLE {schema}.schema_version (version INTEGER)")
    conn.execute(f"INSERT INTO {schema}.schema_version VALUES (?)", (_schema_version(conn),))
    conn.executemany(f"INSERT INTO {schema}._meta VALUES (?, ?)", [
        ("taken_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
        ("reason", reason),
    ])


def _fresh_tmp(dest: Path) -> Path:
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.unlink(missing_ok=True)
    return tmp


def _write(conn: sqlite3.Connection, dest: Path, reason: str) -> None:
    """Copy the user tables into a fresh file, then atomically move it to ``dest``."""
    tmp = _fresh_tmp(dest)
    conn.commit()
    conn.execute("ATTACH DATABASE ? AS snap", (str(tmp),))
    try:
        # One read transaction: a concurrent writer can't commit between the
        # inventory and inventory_events copies (inventory == SUM(delta) holds).
        conn.execute("BEGIN")
        try:
            _copy_into(conn, "snap", reason)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.execute("DETACH DATABASE snap")
    os.replace(tmp, dest)


def take(reason: str = "manual", dest: Path | None = None) -> dict | None:
    """Overwrite the one snapshot slot (or ``dest``) with your current data."""
    with db.connect() as conn:
        _write(conn, dest or snapshot_path(), reason)
    return info() if dest is None else None


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
            details = _details(conn) if restorable else []
        finally:
            conn.execute("DETACH DATABASE snap")
    return {
        "taken_at": meta.taken_at, "reason": meta.reason, "restorable": restorable,
        "current": now, "snapshot": then,
        "changes": {k: then[k] - now[k] for k in now},
        "details": details,
    }


def restore() -> dict:
    """Swap: your current data becomes the snapshot, the snapshot becomes live.

    The swap copy and the replacement happen in ONE write transaction, so no
    write can land between them (it would be overwritten and missing from the
    swap file). The web app also holds the job runner's user-data lock."""
    path = snapshot_path()
    if not path.exists():
        raise UndoError("There’s no restore point yet.")
    tmp = _fresh_tmp(path.with_name(path.name + ".next"))
    try:
        with db.connect() as conn:
            conn.commit()
            conn.execute("ATTACH DATABASE ? AS snap", (str(path),))
            try:
                conn.execute("ATTACH DATABASE ? AS swap", (str(tmp),))
                try:
                    meta = _read_meta(conn)
                    if meta.schema_version != _schema_version(conn):
                        raise UndoError("The app’s database changed shape since this restore point was taken, so it can’t be restored.")
                    conn.execute("BEGIN IMMEDIATE")
                    try:
                        _copy_into(conn, "swap", "before your last restore")
                        _replace_from_snap(conn)
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        raise
                finally:
                    conn.execute("DETACH DATABASE swap")
            finally:
                conn.execute("DETACH DATABASE snap")
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    consent.clear_cache()
    return info() or {}


def _replace_from_snap(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA defer_foreign_keys = ON")
    live, saved = _tables(conn), _tables(conn, "snap")
    kept = []
    if "settings" in live:
        marks = ", ".join("?" for _ in KEEP_SETTINGS)
        kept = conn.execute(f"SELECT key, value FROM main.settings WHERE key IN ({marks})",
                            KEEP_SETTINGS).fetchall()
    tables = [t for t in USER_TABLES if t in live]
    for t in reversed(tables):
        conn.execute(f"DELETE FROM main.{t}")
    for t in tables:
        if t not in saved:
            continue
        cols = [c for c in _columns(conn, "main", t) if c in set(_columns(conn, "snap", t))]
        cl = ", ".join(f'"{c}"' for c in cols)
        conn.execute(f"INSERT INTO main.{t} ({cl}) SELECT {cl} FROM snap.{t}")
    for k, v in kept:
        conn.execute("INSERT INTO main.settings (key, value) VALUES (?, ?) "
                     "ON CONFLICT (key) DO UPDATE SET value = excluded.value", (k, v))
    if "settings" in live:  # a kept key absent live stays absent (not resurrected from the snapshot)
        gone = [k for k in KEEP_SETTINGS if k not in {k for k, _ in kept}]
        if gone:
            conn.execute(f"DELETE FROM main.settings WHERE key IN ({', '.join('?' for _ in gone)})", gone)


class SessionGuard:
    """Takes the snapshot before the first write of each app session: the first
    write after the server starts, or after ``gap`` seconds without a write.

    The snapshot is taken into a pending file and only becomes THE restore
    point once a request that may have written finishes (:meth:`end` with
    ``wrote=True``). A request refused before writing (a 4xx) must not rotate
    the one slot — it would destroy the previous session's restore point while
    nothing changed. Requests overlapping an in-flight pending snapshot join it.
    """

    def __init__(self, gap: float = SESSION_GAP_SECONDS, clock=time.monotonic):
        self._gap = gap
        self._clock = clock
        self._last: float | None = None
        self._lock = threading.Lock()
        self._inflight = 0       # requests sharing the pending snapshot
        self._wrote = False      # any of them may have written

    @staticmethod
    def pending_path() -> Path:
        return snapshot_path().with_name(SNAPSHOT_FILE + ".pending")

    def begin(self, reason: str) -> bool:
        """Call before a write. Returns True when the caller must call
        :meth:`end` (this request takes part in a new session's snapshot).
        If the snapshot fails, the session is NOT marked started."""
        with self._lock:
            if self._inflight:
                self._inflight += 1
                return True
            now = self._clock()
            if self._last is not None and now - self._last <= self._gap:
                self._last = now
                return False
            take(reason, dest=self.pending_path())
            self._inflight, self._wrote = 1, False
            return True

    def end(self, wrote: bool) -> None:
        """Settle a :meth:`begin` that returned True. ``wrote`` = the request
        succeeded or failed unexpectedly (it may have written)."""
        with self._lock:
            self._wrote = self._wrote or wrote
            self._inflight -= 1
            if self._inflight:
                return
            pending = self.pending_path()
            if self._wrote:
                os.replace(pending, snapshot_path())
                self._last = self._clock()
            else:
                pending.unlink(missing_ok=True)

    @contextmanager
    def restoring(self) -> Iterator[None]:
        """Hold off session snapshots while a restore runs. :class:`UndoError`
        if a write that opened a session is still in flight — its pending
        snapshot would later be promoted over the restore's swap copy."""
        with self._lock:
            if self._inflight:
                raise UndoError("A change is still being saved — try again in a moment.")
            yield
