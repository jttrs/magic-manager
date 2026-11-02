"""Your data, self-serve (§25.1 H10, §25.4 step 7): download it, or delete your account.

**Export** (both modes) — :func:`export` builds ONE zip, in memory (no temp file):

* ``my-collection.db`` — a consistent copy of the user's own collection: in the split
  layout the bound user's ``users/<id>.db`` via SQLite's backup API; in the single
  layout ONLY the user tables, copied by the same code the splitter uses
  (``split.user_tables_db``) — never the shared catalog.
* CSVs a person can read (inventory, decks + their cards, wishlist, earmarks, card
  marks, purchases, import history and the inventory ledger), joined to the catalog
  read-only for card names / set / collector number.
* ``README.txt`` — what's inside and the row count of every table.

Whose data is decided by the layout alone (``db.layout()``: the bound user in the
split layout, failing closed in hosted mode when nobody is bound) — there is no user
parameter, so no caller can ask for someone else's file. It never contains auth
secrets, session or invite hashes, analytics, or another user's rows.

**Delete** (hosted) — :func:`delete_account` removes a user, crash-safe and
idempotent, in this order: (1) sign-in off + every session ended (``auth.db``), so
nothing new reaches their file; (2) every file holding their collection
(``userfiles.remove_user_files``: the file + sidecars, the undo restore point,
migration and pair snapshots, set-aside copies, Litestream's local state); (3) their analytics events
(``analytics.store.forget`` under their pseudonymous key); (4) their auth rows
(identities, sessions, flag overrides; unused invites they made are deleted, used
ones are unlinked); (5) the files once more (a request that was already past the
gate may have recreated an empty one). Re-running a half-done delete finishes it.
Refused for the last admin (:class:`LastAdmin`, checked inside step 1's transaction). Offsite backups age out on their
own retention: ``mm host prune-deleted`` removes a deleted id's replica once it is
older than 30 days (§25.4 step 8, ``offsite.prune_deleted``).
"""
from __future__ import annotations

import csv
import io
import sqlite3
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from . import db, split
from . import layout as _layout
from .auth.store import LastAdmin, check_not_last_admin  # noqa: F401 — re-exported for callers

DB_NAME = "my-collection.db"
# Typed by the user to confirm a deletion (the web form and the API check it).
DELETE_CONFIRMATION = "delete my account"
LAST_ADMIN = LastAdmin.error_code

# A cell starting with one of these runs as a formula in a spreadsheet: CSV cells
# that are text get a leading ' (the my-collection.db copy keeps the exact values).
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


class ExportFailed(RuntimeError):
    """The copy of the collection couldn't be made or didn't hold only user tables."""


# ---------- export ----------

@dataclass(frozen=True)
class Sheet:
    file: str
    about: str
    sql: str


# Card columns joined from the catalog (blank when a printing isn't in it).
_CARD = "c.name AS name, c.set_code AS set_code, c.collector_number AS collector_number"

SHEETS: tuple[Sheet, ...] = (
    Sheet("inventory.csv", "every printing you own: one row per printing and finish",
          f"""SELECT {_CARD}, i.finish, i.quantity, i.acquired_at, i.notes, i.scryfall_id
              FROM inventory i LEFT JOIN catalog.cards c ON c.scryfall_id = i.scryfall_id
              ORDER BY c.name, c.set_code, c.collector_number, i.finish"""),
    Sheet("decks.csv", "your decks and card pools",
          """SELECT d.slug, d.name, d.kind, d.format, d.precon_state AS state, d.source, d.author,
                    d.source_precon_file_name AS product, d.created_at, d.updated_at
              FROM decks d ORDER BY d.name, d.slug"""),
    Sheet("deck_cards.csv", "the cards of each deck's current version",
          f"""SELECT d.slug AS deck, d.name AS deck_name, dc.board, dc.count AS quantity, {_CARD},
                    dc.finish, dc.scryfall_id
              FROM decks d
              JOIN deck_cards dc ON dc.deck_version_id = COALESCE(d.current_version_id,
                   (SELECT v.deck_version_id FROM deck_versions v WHERE v.deck_id = d.deck_id AND v.is_current = 1
                    ORDER BY v.version_number DESC LIMIT 1))
              LEFT JOIN catalog.cards c ON c.scryfall_id = dc.scryfall_id
              ORDER BY d.name, d.slug, dc.board, c.name"""),
    Sheet("wishlist.csv", "cards you want, by category",
          f"""SELECT w.category, {_CARD}, w.finish, w.qty_wanted, w.priority, w.notes, w.added_at, w.scryfall_id
              FROM wishlist_entries w LEFT JOIN catalog.cards c ON c.scryfall_id = w.scryfall_id
              ORDER BY w.category, c.name"""),
    Sheet("earmarks.csv", "watched products and their store links (one row per link)",
          """SELECT p.kind, p.product_name, p.set_code, p.collector_number, p.finish, p.category,
                    l.store_name, l.store_url, l.asking_price, l.currency, l.captured_at,
                    t.mode AS target_mode, t.value AS target_value, p.notes, p.earmarked_at, p.scryfall_id
              FROM earmarked_products p
              LEFT JOIN earmark_links l ON l.product_id = p.product_id
              LEFT JOIN earmark_targets t ON t.product_id = p.product_id
              ORDER BY p.product_name, l.store_name"""),
    Sheet("card_earmarks.csv", "cards you marked to collect or for a deck",
          f"""SELECT e.name AS card, e.reason, d.slug AS deck, e.finish, c.set_code AS set_code,
                    c.collector_number AS collector_number, e.note, e.earmarked_at, e.scryfall_id
              FROM card_earmarks e
              LEFT JOIN decks d ON d.deck_id = e.deck_id
              LEFT JOIN catalog.cards c ON c.scryfall_id = e.scryfall_id
              ORDER BY e.name"""),
    Sheet("purchases.csv", "store orders you read in, one row per order line (prices in cents)",
          """SELECT p.store, p.store_order_id, p.ordered_at, p.currency, p.total_cents,
                    l.line_no, l.kind, l.name, l.set_name, l.condition, l.finish, l.quantity,
                    l.unit_price_cents, l.added, l.matched, l.scryfall_id, p.ingest_id
              FROM purchases p LEFT JOIN purchase_lines l ON l.purchase_id = p.purchase_id
              ORDER BY p.ordered_at, p.store, p.store_order_id, l.line_no"""),
    Sheet("history.csv", "every import and change to your collection (the purchase history)",
          """SELECT ingest_id, at, method, label, mode, status, rows_added, rows_updated, rows_zeroed,
                    reverts_ingest_id, notes
              FROM ingest_events ORDER BY ingest_id"""),
    Sheet("ledger.csv", "every copy added (+) or removed (-) by each import — your inventory is their sum",
          f"""SELECT e.ingest_id, e.at, {_CARD}, e.finish, e.delta, e.scryfall_id
              FROM inventory_events e LEFT JOIN catalog.cards c ON c.scryfall_id = e.scryfall_id
              ORDER BY e.event_id"""),
)


@dataclass
class Export:
    filename: str                                   # the zip's name
    data: bytes                                     # the zip
    layout: str                                     # 'single' | 'split'
    tables: dict[str, int] = field(default_factory=dict)   # collection.db rows per table
    sheets: dict[str, int] = field(default_factory=dict)   # CSV rows per file

    def chunks(self, size: int = 64 * 1024) -> Iterator[bytes]:
        view = memoryview(self.data)
        for i in range(0, len(view), size):
            yield bytes(view[i:i + size])


def _rollback_journal(data: bytes) -> bytes:
    """A WAL-mode file's bytes as a rollback-journal file (header bytes 18-19: 2 → 1;
    what ``PRAGMA journal_mode=DELETE`` writes), so the copy opens on its own —
    without a ``-wal`` beside it — and in memory."""
    if len(data) >= 20 and data[18:20] == b"\x02\x02":
        return data[:18] + b"\x01\x01" + data[20:]
    return data


def _user_db_bytes(lay: _layout.Layout) -> bytes:
    """The user's collection as SQLite file bytes (a consistent, read-only copy)."""
    if lay.kind == "single":
        try:
            return _rollback_journal(split.user_tables_db(lay.path))
        except split.SplitError as e:
            raise ExportFailed(str(e)) from e
    if not lay.path.is_file():
        raise ExportFailed("your collection file doesn't exist on this server")
    src = sqlite3.connect(f"{lay.path.resolve().as_uri()}?mode=ro", uri=True)
    mem = sqlite3.connect(":memory:")
    try:
        src.backup(mem)
        for t in sorted(_layout.LITESTREAM_TABLES):  # replication bookkeeping, not the user's data
            mem.execute(f'DROP TABLE IF EXISTS "{t}"')
        mem.commit()
        return _rollback_journal(mem.serialize())
    finally:
        src.close()
        mem.close()


def _open_copy(data: bytes, catalog: Path) -> sqlite3.Connection:
    """The copy in memory with the catalog attached read-only (for card names)."""
    conn = sqlite3.connect("file::memory:", uri=True)  # uri: the ATTACH below is a read-only URI
    conn.deserialize(data)
    conn.row_factory = sqlite3.Row
    conn.execute("ATTACH DATABASE ? AS catalog", (f"{catalog.resolve().as_uri()}?mode=ro",))
    return conn


def _check_user_only(conn: sqlite3.Connection) -> dict[str, int]:
    """Row counts of the copy — refusing anything that isn't a user table."""
    names = [r[0] for r in conn.execute("SELECT name FROM main.sqlite_master WHERE type = 'table' ORDER BY name")]
    stray = [n for n in names if n not in _layout.USER_TABLES and n not in _layout.INFRA_TABLES]
    if stray:
        raise ExportFailed(f"the collection copy holds tables that aren't yours to export: {stray}")
    return {n: conn.execute(f'SELECT COUNT(*) FROM main."{n}"').fetchone()[0]
            for n in names if n in _layout.USER_TABLES}


def _cell(v: object) -> object:
    if isinstance(v, str) and v.startswith(_FORMULA_START):
        return "'" + v
    return v


def _csv(conn: sqlite3.Connection, sheet: Sheet) -> tuple[str, int]:
    cur = conn.execute(sheet.sql)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow([d[0] for d in cur.description])
    n = 0
    for row in cur:
        w.writerow([_cell(v) for v in row])
        n += 1
    return buf.getvalue(), n


def _readme(when: datetime, tables: dict[str, int], sheets: dict[str, int]) -> str:
    lines = [
        "magic-manager — your data",
        "=========================",
        "",
        f"Exported {when.strftime('%Y-%m-%d %H:%M UTC')} (schema v{db.CURRENT_VERSION}).",
        "",
        f"{DB_NAME}",
        "  A copy of your collection: every table that holds your data, exactly as stored.",
        "  Open it with any SQLite tool (for example DB Browser for SQLite or `sqlite3`).",
        "  Card names, prices and sets live in the shared card catalog and are not in it;",
        "  each row keeps the card's Scryfall id (scryfall.com/card/<id> finds it).",
        "",
        "  Rows per table:",
        *(f"    {t:24} {n:>9,}" for t, n in tables.items()),
        "",
        "Spreadsheets (CSV, UTF-8):",
        *(f"  {s.file:20} {sheets[s.file]:>9,} rows — {s.about}" for s in SHEETS),
        "",
        "  Text cells that begin with = + - or @ start with an apostrophe so a",
        "  spreadsheet shows them instead of running them; the .db copy is unchanged.",
        "",
        "Not included: your sign-in details, other people's data, and usage analytics.",
        "",
    ]
    return "\n".join(lines)


def export(*, now: datetime | None = None) -> Export:
    """Build the export zip of the collection ``db.connect()`` opens in this context
    (the bound user in the split layout). Raises ``layout.NoUserBound`` hosted with
    nobody bound, :class:`ExportFailed` when the copy can't be made."""
    lay = db.layout()
    when = (now or datetime.now(UTC)).astimezone(UTC)
    data = _user_db_bytes(lay)
    catalog = lay.catalog if lay.kind == "split" else lay.path
    if catalog is None or not catalog.is_file():
        raise ExportFailed("the card catalog isn't available on this server")
    conn = _open_copy(data, catalog)
    try:
        tables = _check_user_only(conn)
        sheets: dict[str, tuple[str, int]] = {}
        for s in SHEETS:
            sheets[s.file] = _csv(conn, s)
    finally:
        conn.close()
    counts = {f: n for f, (_t, n) in sheets.items()}
    folder = f"magic-manager-export-{when.strftime('%Y-%m-%d')}"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        stamp = when.timetuple()[:6]

        def put(name: str, body: bytes) -> None:
            info = zipfile.ZipInfo(f"{folder}/{name}", date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            z.writestr(info, body)

        put("README.txt", _readme(when, tables, counts).encode("utf-8"))
        put(DB_NAME, data)
        for s in SHEETS:
            put(s.file, sheets[s.file][0].encode("utf-8"))
    return Export(f"{folder}.zip", buf.getvalue(), lay.kind, tables, counts)


def write_export(dest: Path, *, force: bool = False) -> Export:
    """``mm account export --to``: write the zip to ``dest`` (a directory gets the
    default file name). Refuses an existing file unless ``force``."""
    out = export()
    dest = Path(dest)
    if dest.is_dir():
        dest = dest / out.filename
    if dest.exists() and not force:
        raise FileExistsError(f"{dest} already exists (pass --force to replace it)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.partial")
    try:
        fd = tmp.open("wb")
        with fd:
            fd.write(out.data)
        tmp.chmod(0o600)
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return out


# ---------- delete ----------

@dataclass
class Deleted:
    user_id: str
    sessions_ended: int | None              # None: the auth row was already gone
    files: list[str] = field(default_factory=list)   # removed, relative to the data dir
    analytics_events: int = 0
    user_row: bool = False                  # the auth.db users row was removed now
    identities: int = 0
    invites_deleted: int = 0
    invites_unlinked: int = 0


def delete_account(user_id: str, *, data_dir: Path | None = None) -> Deleted:
    """Delete one user everywhere (see the module doc for the order). ``user_id`` is an
    auth id (checked before any path is built). Idempotent: an unknown or half-deleted
    id is swept again. Caller checks re-auth / confirmation / jobs; this checks the
    last-admin rule."""
    from . import family_status, market, userfiles
    from .analytics import consent, identity
    from .analytics import store as analytics_store
    from .auth import store
    if not _layout.AUTH_ID_RE.fullmatch(user_id or ""):
        raise ValueError(f"{user_id!r} is not a user id")
    data_dir = Path(data_dir or db.data_dir())
    out = Deleted(user_id, store.close_account(user_id))  # LastAdmin is checked in its transaction
    removed = userfiles.remove_user_files(data_dir, user_id)
    out.analytics_events = analytics_store.forget(identity.user_key(user_id))
    rows = store.remove_user_rows(user_id)
    removed += userfiles.remove_user_files(data_dir, user_id)
    out.files = sorted(str(p.relative_to(data_dir)) for p in removed)
    out.user_row, out.identities = rows.user, rows.identities
    out.invites_deleted, out.invites_unlinked = rows.invites_deleted, rows.invites_unlinked
    scope = str(userfiles.path_for(data_dir, user_id))
    for forget in (consent.forget_scope, market.forget_scope, family_status.forget_scope):
        forget(scope)
    return out
