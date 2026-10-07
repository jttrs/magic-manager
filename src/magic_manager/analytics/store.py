"""The analytics store: a SEPARATE, disposable SQLite file (never the collection DB).

Lives beside the collection DB as ``analytics.db`` (``MM_ANALYTICS_DB`` overrides).
It is not in the undo snapshot (``undo.USER_TABLES``) nor in ``db/bak`` whole-file
backups, and has its own tiny schema version in ``meta``. Delete the file and it
is recreated empty — nothing in the app depends on it.

Portable SQL only (no SQLite date functions, no JSON functions): timestamps are
stored both as ISO text and integer epoch ms, the day/week buckets are columns,
and properties are a long ``event_props`` table — so moving to its own database
and role later is a backend change (swap :func:`connect`), not a schema rethink.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .. import db
from . import catalog as cat_mod

SCHEMA_VERSION = 1
FILE_NAME = "analytics.db"

_SCHEMA = [
    "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    """CREATE TABLE IF NOT EXISTS events (
        event_id    TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        version     INTEGER NOT NULL,
        category    TEXT NOT NULL,
        source      TEXT NOT NULL,
        ts          TEXT NOT NULL,
        ts_ms       INTEGER NOT NULL,
        day         TEXT NOT NULL,
        week        TEXT NOT NULL,
        session_id  TEXT,
        request_id  TEXT,
        user_key    TEXT,
        key_version TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS events_day ON events (day, name)",
    "CREATE INDEX IF NOT EXISTS events_category_day ON events (category, day)",
    "CREATE INDEX IF NOT EXISTS events_session ON events (session_id)",
    "CREATE INDEX IF NOT EXISTS events_user ON events (user_key)",
    """CREATE TABLE IF NOT EXISTS event_props (
        event_id TEXT NOT NULL,
        key      TEXT NOT NULL,
        value    TEXT NOT NULL,
        PRIMARY KEY (event_id, key)
    )""",
    """CREATE TABLE IF NOT EXISTS daily_counts (
        day      TEXT NOT NULL,
        name     TEXT NOT NULL,
        category TEXT NOT NULL,
        dims     TEXT NOT NULL,
        n        INTEGER NOT NULL,
        PRIMARY KEY (day, name, dims)
    )""",
]

_lock = threading.Lock()
_ready: set[str] = set()


def path() -> Path:
    override = os.environ.get("MM_ANALYTICS_DB")
    return Path(override) if override else db.db_dir() / FILE_NAME


@contextmanager
def connect(p: Path | None = None) -> Iterator[sqlite3.Connection]:
    target = p or path()
    target.parent.mkdir(parents=True, exist_ok=True)
    existed = target.exists()
    conn = sqlite3.connect(target, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        key = str(target.resolve())
        if key not in _ready or not existed:
            with _lock:
                conn.execute("PRAGMA journal_mode = WAL")
                for stmt in _SCHEMA:
                    conn.execute(stmt)
                conn.execute("INSERT INTO meta (key, value) VALUES ('schema_version', ?) "
                             "ON CONFLICT (key) DO UPDATE SET value = excluded.value", (str(SCHEMA_VERSION),))
                conn.commit()
                _ready.add(key)
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _week(d: date) -> str:
    return (d - timedelta(days=d.weekday())).isoformat()


@dataclass
class Row:
    """One validated event ready to write."""
    checked: cat_mod.Checked
    session_id: str | None = None
    request_id: str | None = None
    user_key: str | None = None
    key_version: str | None = None
    at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


def insert(rows: Iterable[Row], *, p: Path | None = None) -> int:
    """Write events + their props, and bump the daily aggregate, in one transaction."""
    rows = list(rows)
    if not rows:
        return 0
    with connect(p) as conn:
        for r in rows:
            ev = r.checked.event
            at = r.at.astimezone(UTC)
            day = at.date()
            conn.execute(
                "INSERT INTO events (event_id, name, version, category, source, ts, ts_ms, day, week,"
                " session_id, request_id, user_key, key_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (r.event_id, ev.name, ev.version, ev.category, ev.source,
                 at.isoformat(timespec="milliseconds"), int(at.timestamp() * 1000),
                 day.isoformat(), _week(day), r.session_id, r.request_id, r.user_key, r.key_version))
            conn.executemany("INSERT INTO event_props (event_id, key, value) VALUES (?,?,?)",
                             [(r.event_id, k, v) for k, v in r.checked.props.items()])
            conn.execute(
                "INSERT INTO daily_counts (day, name, category, dims, n) VALUES (?,?,?,?,1) "
                "ON CONFLICT (day, name, dims) DO UPDATE SET n = daily_counts.n + 1",
                (day.isoformat(), ev.name, ev.category, cat_mod.dims_key(ev, r.checked.props)))
    return len(rows)


def _delete_events(conn: sqlite3.Connection, where: str, params: tuple) -> int:
    conn.execute(f"DELETE FROM event_props WHERE event_id IN (SELECT event_id FROM events WHERE {where})", params)
    return conn.execute(f"DELETE FROM events WHERE {where}", params).rowcount


def prune(*, now: datetime | None = None, catalog: cat_mod.Catalog | None = None, p: Path | None = None) -> dict[str, int]:
    """Apply the catalog's retention: raw errors / usage / aggregates past their limit."""
    cat = catalog or cat_mod.load()
    today = (now or datetime.now(UTC)).astimezone(UTC).date()
    keep = cat.retention
    cut = {k: (today - timedelta(days=keep[f"{k}_days"])).isoformat() for k in ("error", "usage", "aggregate")}
    with connect(p) as conn:
        errors = _delete_events(conn, "category = 'error' AND day < ?", (cut["error"],))
        usage = _delete_events(conn, "category = 'usage' AND day < ?", (cut["usage"],))
        aggregates = conn.execute("DELETE FROM daily_counts WHERE day < ?", (cut["aggregate"],)).rowcount
        conn.execute("INSERT INTO meta (key, value) VALUES ('last_pruned', ?) "
                     "ON CONFLICT (key) DO UPDATE SET value = excluded.value", (today.isoformat(),))
    return {"errors": errors, "usage": usage, "aggregates": aggregates}


def forget(user_key: str, *, p: Path | None = None) -> int:
    """Delete every raw event recorded under this pseudonymous user key."""
    with connect(p) as conn:
        return _delete_events(conn, "user_key = ?", (user_key,))


def stats(*, p: Path | None = None) -> dict:
    with connect(p) as conn:
        meta = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta")}
        by_cat = {r["category"]: r["n"] for r in conn.execute("SELECT category, COUNT(*) AS n FROM events GROUP BY category")}
        first = conn.execute("SELECT MIN(day) FROM daily_counts").fetchone()[0]
    return {"path": str(p or path()), "schema_version": int(meta.get("schema_version", 0)),
            "last_pruned": meta.get("last_pruned"), "events": by_cat, "first_day": first}
