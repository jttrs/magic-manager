"""SQLite store for magic-manager.

Single file at the repo root: ``magic_manager.db``. Schema is created on first
connect; subsequent versions add migrations to the ``MIGRATIONS`` list and bump
``CURRENT_VERSION``.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

DB_FILENAME = "magic_manager.db"


def db_path() -> Path:
    override = os.environ.get("MAGIC_MANAGER_DB")
    if override:
        return Path(override)
    return _repo_root() / DB_FILENAME


def _repo_root() -> Path:
    # walk up from this file until we find pyproject.toml; fall back to cwd
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS cards (
    scryfall_id        TEXT PRIMARY KEY,
    oracle_id          TEXT,
    name               TEXT NOT NULL,
    set_code           TEXT NOT NULL,
    collector_number   TEXT NOT NULL,
    rarity             TEXT NOT NULL,
    mana_cost          TEXT,
    cmc                REAL,
    type_line          TEXT,
    colors             TEXT,           -- JSON array
    color_identity     TEXT,           -- JSON array
    prices_usd         REAL,
    prices_usd_foil    REAL,
    prices_updated_at  TEXT,
    image_uri          TEXT,
    scryfall_uri       TEXT,
    is_promo           INTEGER NOT NULL DEFAULT 0,
    is_token           INTEGER NOT NULL DEFAULT 0,
    frame_effects      TEXT,           -- JSON array
    finishes           TEXT,           -- JSON array (e.g. ["nonfoil","foil"])
    oracle_text        TEXT,
    UNIQUE (set_code, collector_number)
);

CREATE INDEX IF NOT EXISTS cards_name_idx ON cards (name);
CREATE INDEX IF NOT EXISTS cards_set_idx  ON cards (set_code);

CREATE TABLE IF NOT EXISTS lists (
    label       TEXT PRIMARY KEY,
    kind        TEXT NOT NULL DEFAULT 'other',
    source      TEXT NOT NULL DEFAULT 'manual',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS list_rows (
    label        TEXT NOT NULL,
    scryfall_id  TEXT NOT NULL,
    finish       TEXT NOT NULL CHECK (finish IN ('nonfoil','foil')),
    quantity     INTEGER NOT NULL CHECK (quantity >= 0),
    priority     INTEGER,
    notes        TEXT,
    PRIMARY KEY (label, scryfall_id, finish),
    FOREIGN KEY (label) REFERENCES lists(label) ON DELETE CASCADE,
    FOREIGN KEY (scryfall_id) REFERENCES cards(scryfall_id)
);

CREATE INDEX IF NOT EXISTS list_rows_card_idx ON list_rows (scryfall_id);

CREATE TABLE IF NOT EXISTS imports (
    run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    command       TEXT NOT NULL,
    source_path   TEXT,
    rows_changed  INTEGER NOT NULL DEFAULT 0,
    at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT
);
"""


SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS ingest_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    at            TEXT NOT NULL,           -- ISO timestamp (UTC)
    label         TEXT NOT NULL,
    mode          TEXT NOT NULL CHECK (mode IN ('replace','additive')),
    source_path   TEXT NOT NULL,           -- input/<slug>-<slice>.xlsx (pre-archive)
    archived_path TEXT,                    -- input/processed/...; NULL if archive failed
    file_sha256   TEXT NOT NULL,
    rows_added    INTEGER NOT NULL DEFAULT 0,
    rows_updated  INTEGER NOT NULL DEFAULT 0,
    rows_zeroed   INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL CHECK (status IN ('success','failed')),
    error         TEXT
);

CREATE INDEX IF NOT EXISTS ingest_log_hash_idx ON ingest_log (file_sha256);
"""


# V1.3: Universes Beyond awareness — flavor names + treatment fields.
# ALTER TABLE ADD COLUMN is not idempotent in SQLite, but _ensure_schema()
# runs migrations only once (MIGRATIONS[have:]).
SCHEMA_V3 = """
ALTER TABLE cards ADD COLUMN flavor_name     TEXT;
ALTER TABLE cards ADD COLUMN promo_types     TEXT;
ALTER TABLE cards ADD COLUMN border_color    TEXT;
ALTER TABLE cards ADD COLUMN full_art        INTEGER;
ALTER TABLE cards ADD COLUMN security_stamp  TEXT;
ALTER TABLE cards ADD COLUMN is_reskin       INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS cards_is_reskin_idx ON cards (is_reskin);
"""


# ---------- migration-authoring convention ----------
#
# Always-safe ops in a migration: CREATE TABLE, ALTER TABLE ADD COLUMN,
# CREATE INDEX, INSERT of seed data. These never lose data.
#
# Never-direct ops: DROP COLUMN, RENAME COLUMN, changing PK/FK, changing
# CHECK constraints. SQLite doesn't support these cleanly; use the
# copy-rebuild dance below if you really need them.
#
# Precious tables (data the user can't reconstruct):
#   - list_rows         the inventory the user typed in
#   - lists             labels + their kind/source
#   - ingest_log        audit trail of which checklist landed when
#   - precons / precon_cards    (when V2 ships them)
#
# Re-derivable tables (recovery = re-run a sync):
#   - cards             every column is rebuilt by `mm set sync <name>`
#   - schema_version    bookkeeping
#   - settings          flags; nothing irreplaceable
#
# Copy-rebuild dance for destructive changes:
#   BEGIN;
#   CREATE TABLE list_rows__new (...new shape...);
#   INSERT INTO list_rows__new SELECT ...projection... FROM list_rows;
#   DROP TABLE list_rows;
#   ALTER TABLE list_rows__new RENAME TO list_rows;
#   -- recreate indexes
#   COMMIT;
#
# Auto-snapshot: when MIGRATIONS gets a new entry, every existing user's
# next `mm` invocation triggers `_ensure_schema()`, which calls
# `snapshot(label="pre-vN")` BEFORE applying anything. That backup lives
# alongside `magic_manager.db` and is the recovery path if anything goes
# wrong. Don't bypass it.

MIGRATIONS: list[str] = [
    SCHEMA_V1,
    SCHEMA_V2,
    SCHEMA_V3,
]
CURRENT_VERSION = len(MIGRATIONS)


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a connection with foreign keys + Row factory + ensured schema."""
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _ensure_schema(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(MIGRATIONS[0])  # idempotent CREATE IF NOT EXISTS
    cur = conn.execute("SELECT version FROM schema_version")
    row = cur.fetchone()
    have = row["version"] if row else 0
    if have > 0 and have < CURRENT_VERSION:
        # Take a pre-migration snapshot so a botched migration is recoverable.
        # Skipped on a fresh DB (have == 0) since there's nothing to lose.
        # The snapshot opens its own sqlite handle on the file we're about to
        # mutate; that's safe because we haven't started any transaction yet
        # on `conn` (the migrations run after this).
        try:
            backup = snapshot(label=f"pre-v{CURRENT_VERSION}")
            import sys
            print(f"info: pre-migration snapshot saved to {backup}", file=sys.stderr)
        except Exception as e:
            # If snapshot fails (disk full, permissions, etc.) we still want
            # to surface that loudly rather than apply migrations blindly.
            raise RuntimeError(
                f"refusing to apply migrations: pre-migration snapshot failed ({e}). "
                f"Fix the underlying issue or back up {db_path()} manually before retrying."
            ) from e
    for i, sql in enumerate(MIGRATIONS[have:], start=have + 1):
        if i != 1:  # MIGRATIONS[0] already ran above
            conn.executescript(sql)
    if have < CURRENT_VERSION:
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (CURRENT_VERSION,))


# ---------- snapshots, restore, integrity ----------

def _check_integrity(path: Path) -> str:
    """Run ``PRAGMA integrity_check`` against ``path``. Returns 'ok' or the
    first integrity-check message (which is what SQLite emits when a problem
    is found)."""
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        return row[0] if row else "(no result)"
    finally:
        conn.close()


def snapshot(*, label: str | None = None, dest: Path | None = None) -> Path:
    """Copy the active DB to a timestamped backup. Returns the backup path.

    The default location is alongside the live DB, named
    ``<live>.bak-<YYYY-MM-DD-HHMMSS>[-<label>]``. ``label`` is a short slug
    recorded in the filename so future-you can tell snapshots apart
    (e.g. ``"pre-v4"``).

    Verifies the copy with ``PRAGMA integrity_check`` before returning. If
    integrity fails, deletes the bad copy and raises.

    IMPORTANT: call this OUTSIDE any active ``connect()`` context. Taking a
    snapshot while a writer is mid-transaction can capture an inconsistent
    state.
    """
    src = db_path()
    if not src.exists():
        raise FileNotFoundError(f"no DB to snapshot at {src}")
    if dest is None:
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        suffix = f"-{label}" if label else ""
        dest = src.with_name(f"{src.name}.bak-{ts}{suffix}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    result = _check_integrity(dest)
    if result != "ok":
        try:
            dest.unlink()
        except OSError:
            pass
        raise RuntimeError(f"snapshot integrity check failed: {result}")
    return dest


def restore(backup_path: Path) -> Path:
    """Replace the active DB with ``backup_path``.

    The current live DB is renamed to ``<live>.replaced-<timestamp>`` rather
    than deleted, so a mistaken restore is itself recoverable. Returns the
    path the old live DB was moved to (or ``None`` if there was no live DB).

    Refuses to run if ``backup_path`` doesn't exist or fails integrity check.
    """
    backup_path = Path(backup_path)
    if not backup_path.exists():
        raise FileNotFoundError(f"backup not found: {backup_path}")
    result = _check_integrity(backup_path)
    if result != "ok":
        raise RuntimeError(f"refusing to restore: backup failed integrity check: {result}")

    live = db_path()
    replaced: Path | None = None
    if live.exists():
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        replaced = live.with_name(f"{live.name}.replaced-{ts}")
        live.rename(replaced)
    shutil.copy2(backup_path, live)
    return replaced  # type: ignore[return-value]


def list_snapshots() -> list[Path]:
    """Return ``<live>.bak-*`` files alongside the live DB, newest first."""
    live = db_path()
    parent = live.parent
    if not parent.exists():
        return []
    candidates = list(parent.glob(f"{live.name}.bak-*"))
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


# ---------- card upserts ----------

def upsert_card(conn: sqlite3.Connection, card: dict) -> None:
    """Insert or update a single Scryfall card row."""
    conn.execute(
        """
        INSERT INTO cards (
            scryfall_id, oracle_id, name, set_code, collector_number,
            rarity, mana_cost, cmc, type_line, colors, color_identity,
            prices_usd, prices_usd_foil, prices_updated_at,
            image_uri, scryfall_uri, is_promo, is_token,
            frame_effects, finishes, oracle_text,
            flavor_name, promo_types, border_color, full_art,
            security_stamp, is_reskin
        ) VALUES (
            :scryfall_id, :oracle_id, :name, :set_code, :collector_number,
            :rarity, :mana_cost, :cmc, :type_line, :colors, :color_identity,
            :prices_usd, :prices_usd_foil, :prices_updated_at,
            :image_uri, :scryfall_uri, :is_promo, :is_token,
            :frame_effects, :finishes, :oracle_text,
            :flavor_name, :promo_types, :border_color, :full_art,
            :security_stamp, :is_reskin
        )
        ON CONFLICT(scryfall_id) DO UPDATE SET
            oracle_id          = excluded.oracle_id,
            name               = excluded.name,
            set_code           = excluded.set_code,
            collector_number   = excluded.collector_number,
            rarity             = excluded.rarity,
            mana_cost          = excluded.mana_cost,
            cmc                = excluded.cmc,
            type_line          = excluded.type_line,
            colors             = excluded.colors,
            color_identity     = excluded.color_identity,
            prices_usd         = excluded.prices_usd,
            prices_usd_foil    = excluded.prices_usd_foil,
            prices_updated_at  = excluded.prices_updated_at,
            image_uri          = excluded.image_uri,
            scryfall_uri       = excluded.scryfall_uri,
            is_promo           = excluded.is_promo,
            is_token           = excluded.is_token,
            frame_effects      = excluded.frame_effects,
            finishes           = excluded.finishes,
            oracle_text        = excluded.oracle_text,
            flavor_name        = excluded.flavor_name,
            promo_types        = excluded.promo_types,
            border_color       = excluded.border_color,
            full_art           = excluded.full_art,
            security_stamp     = excluded.security_stamp,
            is_reskin          = excluded.is_reskin
        """,
        _card_row(card),
    )


def upsert_cards(conn: sqlite3.Connection, cards: Iterable[dict]) -> int:
    n = 0
    for c in cards:
        upsert_card(conn, c)
        n += 1
    return n


def _card_row(c: dict) -> dict:
    """Project a raw Scryfall card JSON into our row schema."""
    def f(key: str, default=None):
        return c.get(key, default)

    prices = f("prices") or {}
    image_uris = f("image_uris") or {}
    # for double-faced cards image_uris may live on card_faces[0]
    if not image_uris and f("card_faces"):
        image_uris = (c["card_faces"][0] or {}).get("image_uris") or {}

    def usd(v):
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    promo_types = f("promo_types") or []
    return {
        "scryfall_id":      f("id"),
        "oracle_id":        f("oracle_id"),
        "name":             f("name"),
        "set_code":         (f("set") or "").lower(),
        "collector_number": f("collector_number"),
        "rarity":           f("rarity") or "common",
        "mana_cost":        f("mana_cost"),
        "cmc":              f("cmc"),
        "type_line":        f("type_line"),
        "colors":           json.dumps(f("colors") or []),
        "color_identity":   json.dumps(f("color_identity") or []),
        "prices_usd":       usd(prices.get("usd")),
        "prices_usd_foil":  usd(prices.get("usd_foil")),
        "prices_updated_at": f("released_at"),  # close-enough proxy; refine later
        "image_uri":        image_uris.get("normal") or image_uris.get("large"),
        "scryfall_uri":     f("scryfall_uri"),
        "is_promo":         1 if f("promo") else 0,
        "is_token":         1 if (f("layout") == "token") else 0,
        "frame_effects":    json.dumps(f("frame_effects") or []),
        "finishes":         json.dumps(f("finishes") or []),
        "oracle_text":      f("oracle_text"),
        # V1.3 — UB awareness fields. ``flavor_name`` lives on card_faces[0]
        # for split / double-faced cards, mirroring the image_uris pattern
        # already used above.
        "flavor_name":      (
            f("flavor_name")
            or ((c.get("card_faces") or [{}])[0] or {}).get("flavor_name")
        ),
        "promo_types":      json.dumps(promo_types),
        "border_color":     f("border_color"),
        "full_art":         1 if f("full_art") else 0,
        "security_stamp":   f("security_stamp"),
        # is_reskin is the canonical "this is a Universes Beyond reskin" signal
        # per docs/scryfall-set-families-and-bonus-sheets.md §4a. The discriminator
        # is `promo_types contains "sourcematerial"`, NOT flavor_name (some MAR
        # cards keep their oracle name but get Marvel-themed art).
        "is_reskin":        1 if "sourcematerial" in promo_types else 0,
    }


# ---------- list helpers ----------

def upsert_list(conn: sqlite3.Connection, label: str, *, kind: str = "other",
                source: str = "manual", notes: str | None = None) -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO lists (label, kind, source, created_at, updated_at, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(label) DO UPDATE SET
            kind = excluded.kind,
            source = excluded.source,
            updated_at = excluded.updated_at,
            notes = COALESCE(excluded.notes, lists.notes)
        """,
        (label, kind, source, now, now, notes),
    )


def upsert_list_row(conn: sqlite3.Connection, label: str, scryfall_id: str,
                    finish: str, quantity: int, *,
                    priority: int | None = None, notes: str | None = None) -> None:
    if quantity == 0:
        conn.execute(
            "DELETE FROM list_rows WHERE label = ? AND scryfall_id = ? AND finish = ?",
            (label, scryfall_id, finish),
        )
        return
    conn.execute(
        """
        INSERT INTO list_rows (label, scryfall_id, finish, quantity, priority, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(label, scryfall_id, finish) DO UPDATE SET
            quantity = excluded.quantity,
            priority = COALESCE(excluded.priority, list_rows.priority),
            notes    = COALESCE(excluded.notes, list_rows.notes)
        """,
        (label, scryfall_id, finish, quantity, priority, notes),
    )


def record_import(conn: sqlite3.Connection, command: str, source_path: str | None,
                  rows_changed: int) -> None:
    from datetime import datetime, timezone
    conn.execute(
        "INSERT INTO imports (command, source_path, rows_changed, at) VALUES (?, ?, ?, ?)",
        (command, source_path, rows_changed,
         datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )


def record_ingest_log(
    conn: sqlite3.Connection, *,
    label: str,
    mode: str,
    source_path: str,
    archived_path: str | None,
    file_sha256: str,
    rows_added: int,
    rows_updated: int,
    rows_zeroed: int,
    status: str,
    error: str | None = None,
) -> int:
    from datetime import datetime, timezone
    cur = conn.execute(
        """
        INSERT INTO ingest_log
            (at, label, mode, source_path, archived_path, file_sha256,
             rows_added, rows_updated, rows_zeroed, status, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            label, mode, source_path, archived_path, file_sha256,
            rows_added, rows_updated, rows_zeroed, status, error,
        ),
    )
    return cur.lastrowid


def find_ingest_log_by_hash(conn: sqlite3.Connection, file_sha256: str) -> list[dict]:
    """Return prior ingest_log entries with this file hash, newest first."""
    rows = conn.execute(
        """
        SELECT id, at, label, mode, source_path, archived_path, status, error,
               rows_added, rows_updated, rows_zeroed
        FROM ingest_log
        WHERE file_sha256 = ?
        ORDER BY id DESC
        """,
        (file_sha256,),
    ).fetchall()
    return [dict(r) for r in rows]

