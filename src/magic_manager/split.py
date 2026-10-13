"""Split today's single DB into ``catalog.db`` + ``users/<user>.db`` (Phase 3 §25.4 step 3).

``split(source, data_dir, user)`` copies every table of a single-file DB at
:data:`db.CURRENT_VERSION` into the file :mod:`magic_manager.layout` assigns it
(catalog tables + ``catalog_settings`` → ``catalog.db``; user tables →
``users/<user>.db``; ``schema_version`` into both; legacy ``lists`` /
``list_rows`` are left behind). Copies are exact: the same stored
``CREATE TABLE`` / ``CREATE INDEX`` text, every row with its rowid, and each
AUTOINCREMENT sequence value.

The source is opened read-only and never changed. Both files are written to
temp names, then verified — per-table row count + content hash against the
source (read in the same transaction as the copy), the schema text, the
sequences, then through the real split connection: the ledger reconciles
(``inventory == SUM(inventory_events.delta)``), no catalog-ref orphans,
``integrity_check`` and ``foreign_key_check`` clean — and only then renamed
into place. Any failure raises :class:`SplitFailed` (with the report) and
leaves no file behind.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import db
from . import layout as _layout

_SIDECARS = ("-journal", "-wal", "-shm")
_JOURNAL_MODES = {"delete", "truncate", "persist", "wal"}
_CREATE_RE = re.compile(r"^(CREATE\s+(?:UNIQUE\s+)?(?:TABLE|INDEX|TRIGGER)\s+(?:IF\s+NOT\s+EXISTS\s+)?)", re.I)
# Attached-schema names on the copy connection.
_SRC, _CAT, _USR = "src", "cat", "usr"


class SplitError(Exception):
    """Base for split refusals and failures."""


class SplitRefused(SplitError):
    """Nothing was written: the inputs aren't splittable as given."""


class SplitFailed(SplitError):
    """The copy didn't verify; nothing was left in place. ``report`` says why."""

    def __init__(self, message: str, report: "SplitReport"):
        super().__init__(message)
        self.report = report


@dataclass
class TableCopy:
    table: str
    file: str            # 'catalog' | 'user'
    rows: int
    sha256: str
    ok: bool


@dataclass
class SplitReport:
    source: str
    catalog: str
    user_db: str
    user: str
    version: int
    journal_mode: str
    tables: list[TableCopy] = field(default_factory=list)
    sequences: dict[str, int] = field(default_factory=dict)
    legacy_skipped: dict[str, int] = field(default_factory=dict)
    ledger_drift: int | None = None
    catalog_ref_orphans: int | None = None
    integrity: dict[str, str] = field(default_factory=dict)
    fk_violations: int | None = None
    sizes: dict[str, int] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> dict:
        return {**asdict(self), "ok": self.ok}


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _qualify(sql: str, schema: str) -> str:
    """``CREATE TABLE t …`` → ``CREATE TABLE <schema>.t …`` (SQLite stores the
    text without the schema qualifier, so the copy's stored SQL is identical)."""
    out, n = _CREATE_RE.subn(lambda m: f"{m.group(1)}{schema}.", sql.lstrip(), count=1)
    if n != 1:
        raise SplitRefused(f"can't read the CREATE statement: {sql[:80]!r}")
    return out


def _sidecars(path: Path) -> list[Path]:
    return [p for p in (path.with_name(path.name + s) for s in _SIDECARS) if p.exists()]


def _unlink(path: Path) -> None:
    for p in (path, *_sidecars(path)):
        try:
            p.unlink()
        except FileNotFoundError:
            pass


def _layout_of(conn: sqlite3.Connection, schema: str, table: str) -> tuple[list[str], bool, bool]:
    """(copyable columns, has rowid, rowid is a column alias)."""
    info = conn.execute(f"PRAGMA {schema}.table_xinfo({_q(table)})").fetchall()
    cols = [r[1] for r in info if r[6] == 0]  # hidden != 0: generated/virtual columns
    listed = {r[1]: r for r in conn.execute(f"PRAGMA {schema}.table_list({_q(table)})")}
    has_rowid = not listed[table][4] if table in listed else True  # table_list.wr = WITHOUT ROWID
    pks = [r for r in info if r[5]]
    alias = has_rowid and len(pks) == 1 and (pks[0][2] or "").upper() == "INTEGER"
    return cols, has_rowid, alias


def _table_hash(conn: sqlite3.Connection, schema: str, table: str) -> tuple[int, str]:
    cols, has_rowid, _ = _layout_of(conn, schema, table)
    sel = ", ".join(_q(c) for c in cols)
    if has_rowid:
        sql = f"SELECT rowid, {sel} FROM {schema}.{_q(table)} ORDER BY rowid"
    else:
        pk = [r[1] for r in sorted(conn.execute(f"PRAGMA {schema}.table_info({_q(table)})"), key=lambda r: r[5]) if r[5]]
        sql = f"SELECT {sel} FROM {schema}.{_q(table)} ORDER BY {', '.join(_q(c) for c in pk)}"
    h = hashlib.sha256()
    n = 0
    for row in conn.execute(sql):
        h.update(repr(row).encode("utf-8"))  # repr keeps types apart: 1, 1.0, '1', b'1'
        h.update(b"\x1e")
        n += 1
    return n, h.hexdigest()


def _objects(conn: sqlite3.Connection, schema: str) -> list[tuple[str, str, str, str | None]]:
    return [tuple(r) for r in conn.execute(
        f"SELECT type, name, tbl_name, sql FROM {schema}.sqlite_master "
        f"WHERE name NOT LIKE 'sqlite_%' ORDER BY rowid")]


def split(source: Path, data_dir: Path, user: str = _layout.DEFAULT_USER, *, force: bool = False,
          progress: Callable[[str], None] | None = None) -> SplitReport:
    """Write ``<data_dir>/catalog.db`` + ``<data_dir>/users/<user>.db`` from ``source``.

    Refuses (:class:`SplitRefused`, nothing written) when the source is missing
    or not at :data:`db.CURRENT_VERSION`, holds an unclassified table or a view,
    or a target exists (unless ``force``) or has journal/WAL sidecars (it may be
    open). Raises :class:`SplitFailed` when the copy doesn't verify.
    """
    say = progress or (lambda _m: None)
    started = time.monotonic()
    source, data_dir = Path(source), Path(data_dir)
    catalog = data_dir / _layout.CATALOG_FILENAME
    try:
        user_db = _layout.user_db_path(data_dir, user)
    except _layout.LayoutError as e:
        raise SplitRefused(str(e)) from e
    if not source.is_file():
        raise SplitRefused(f"no DB to split at {source}")
    for target in (catalog, user_db):
        if target.resolve() == source.resolve():
            raise SplitRefused(f"target {target} is the source")
        if side := _sidecars(target):
            raise SplitRefused(f"{target} looks open ({', '.join(p.name for p in side)} present) — close it first")
        if target.exists() and not force:
            raise SplitRefused(f"{target} already exists (pass --force to replace it)")

    tmp = {
        "catalog": catalog.with_name(f".{catalog.name}.split-{os.getpid()}.tmp"),
        "user": user_db.with_name(f".{user_db.name}.split-{os.getpid()}.tmp"),
    }
    user_db.parent.mkdir(parents=True, exist_ok=True)
    for p in tmp.values():
        _unlink(p)

    conn = sqlite3.connect("file::memory:", uri=True, isolation_level=None)
    report: SplitReport | None = None
    try:
        conn.execute(f"ATTACH DATABASE ? AS {_SRC}", (source.resolve().as_uri() + "?mode=ro",))
        if not conn.execute(f"SELECT 1 FROM {_SRC}.sqlite_master WHERE name='schema_version'").fetchone():
            raise SplitRefused(f"{source} has no schema_version table")
        row = conn.execute(f"SELECT MAX(version) FROM {_SRC}.schema_version").fetchone()
        version = row[0] or 0
        if version != db.CURRENT_VERSION:
            raise SplitRefused(
                f"{source} is at schema v{version}; the splitter needs v{db.CURRENT_VERSION} "
                f"(upgrade it first: scripts/post_merge_upgrade.py)")
        journal = conn.execute(f"PRAGMA {_SRC}.journal_mode").fetchone()[0].lower()
        report = SplitReport(str(source), str(catalog), str(user_db), user, version, journal)

        # Which file each object goes to (indexes/triggers follow their table).
        dest: dict[str, str] = {}
        objects = _objects(conn, _SRC)
        for typ, name, tbl, _sql in objects:
            if typ == "view":
                raise SplitRefused(f"view {name!r} isn't in the layout registry")
            if typ != "table":
                continue
            try:
                kind = _layout.classify(name)
            except KeyError as e:
                raise SplitRefused(str(e).strip('"')) from e
            if kind == "legacy":
                report.legacy_skipped[name] = conn.execute(f"SELECT COUNT(*) FROM {_SRC}.{_q(name)}").fetchone()[0]
            elif kind in ("catalog", "user"):
                dest[name] = kind
        to_schema = {"catalog": _CAT, "user": _USR}

        for kind, path in tmp.items():
            conn.execute(f"ATTACH DATABASE ? AS {to_schema[kind]}", (str(path),))
            s = to_schema[kind]
            for pragma in ("page_size", "auto_vacuum", "user_version", "application_id"):
                val = conn.execute(f"PRAGMA {_SRC}.{pragma}").fetchone()[0]
                conn.execute(f"PRAGMA {s}.{pragma} = {int(val)}")

        say(f"copying {len(dest)} tables from {source.name} (v{version}) …")
        conn.execute("BEGIN")
        carried: list[tuple[str, str]] = [("schema_version", "catalog"), ("schema_version", "user")]
        sv_sql = next(sql for typ, name, _t, sql in objects if typ == "table" and name == "schema_version")
        for s in (_CAT, _USR):
            conn.execute(_qualify(sv_sql, s))
            conn.execute(f"INSERT INTO {s}.schema_version SELECT * FROM {_SRC}.schema_version")
        for typ, name, _tbl, sql in objects:
            if typ != "table" or name not in dest:
                continue
            s = to_schema[dest[name]]
            conn.execute(_qualify(sql, s))
            cols, has_rowid, alias = _layout_of(conn, _SRC, name)
            sel = ", ".join(_q(c) for c in cols)
            if has_rowid and not alias:
                sel = f"rowid, {sel}"
            conn.execute(f"INSERT INTO {s}.{_q(name)} ({sel}) SELECT {sel} FROM {_SRC}.{_q(name)}")
            carried.append((name, dest[name]))
        for typ, name, tbl, sql in objects:  # indexes + triggers after the rows
            if typ in ("index", "trigger") and sql and tbl in dest:
                conn.execute(_qualify(sql, to_schema[dest[tbl]]))
        # The inserts above touched each file's sqlite_sequence; make it the source's, row for row.
        for s in to_schema.values():
            if conn.execute(f"SELECT 1 FROM {s}.sqlite_master WHERE name='sqlite_sequence'").fetchone():
                conn.execute(f"DELETE FROM {s}.sqlite_sequence")
        has_seq = conn.execute(f"SELECT 1 FROM {_SRC}.sqlite_master WHERE name='sqlite_sequence'").fetchone()
        for name, seq in (conn.execute(f"SELECT name, seq FROM {_SRC}.sqlite_sequence").fetchall() if has_seq else []):
            if name not in dest:
                continue
            s = to_schema[dest[name]]
            conn.execute(f"INSERT INTO {s}.sqlite_sequence (name, seq) VALUES (?, ?)", (name, seq))
            report.sequences[name] = seq

        # Verify against the SAME source snapshot (still inside the read transaction).
        say("verifying row counts + content hashes …")
        for name, kind in carried:
            n_src, h_src = _table_hash(conn, _SRC, name)
            n_dst, h_dst = _table_hash(conn, to_schema[kind], name)
            ok = (n_src, h_src) == (n_dst, h_dst)
            report.tables.append(TableCopy(name, kind, n_dst, h_dst, ok))
            if not ok:
                report.problems.append(f"{kind} {name}: {n_dst} rows / hash differs from the source ({n_src} rows)")
        src_objs = [o for o in objects if (o[2] in dest or o[2] == "schema_version")]
        for kind, s in to_schema.items():
            want = sorted(o for o in src_objs if o[2] == "schema_version" or dest.get(o[2]) == kind)
            got = sorted(_objects(conn, s))
            if want != got:
                report.problems.append(f"{kind}: schema differs from the source ({sorted(set(want) ^ set(got))[:3]})")
            want_seq = sorted((n, q) for n, q in report.sequences.items() if dest[n] == kind)
            seq_tbl = conn.execute(f"SELECT 1 FROM {s}.sqlite_master WHERE name='sqlite_sequence'").fetchone()
            got_seq = sorted(tuple(r) for r in conn.execute(f"SELECT name, seq FROM {s}.sqlite_sequence")) if seq_tbl else []
            if want_seq != got_seq:
                report.problems.append(f"{kind}: sqlite_sequence {got_seq} != source {want_seq}")
        conn.execute("COMMIT")
        if journal in _JOURNAL_MODES:
            for s in to_schema.values():
                conn.execute(f"PRAGMA {s}.journal_mode = {journal}")
        for s in (*to_schema.values(), _SRC):
            conn.execute(f"DETACH DATABASE {s}")
        conn.close()

        say("verifying through the split connection …")
        verify_pair(tmp["user"], tmp["catalog"], user, report)
        report.sizes = {k: p.stat().st_size for k, p in tmp.items()}
        report.seconds = round(time.monotonic() - started, 1)
        if report.problems:
            raise SplitFailed("the split copy didn't verify: " + "; ".join(report.problems[:3]), report)
        for kind, final in (("catalog", catalog), ("user", user_db)):
            os.replace(tmp[kind], final)
        return report
    except BaseException:
        try:
            conn.close()
        except Exception:
            pass
        for p in tmp.values():
            _unlink(p)
        raise


def verify_pair(user_db: Path, catalog: Path, user: str, report: SplitReport) -> None:
    """Integrity, ledger, catalog refs and foreign keys of a split pair, opened
    with the real split connection; findings go to ``report.problems``."""
    from . import audit, ingest
    for kind, p in (("catalog", catalog), ("user", user_db)):
        report.integrity[kind] = db._check_integrity(p)
        if report.integrity[kind] != "ok":
            report.problems.append(f"{kind} integrity_check: {report.integrity[kind]}")
    try:
        conn = db._open_split(_layout.Layout("split", user_db, catalog, user))
    except _layout.LayoutError as e:
        report.problems.append(f"split connect: {e}")
        return
    try:
        drift = ingest.reconcile_inventory_ledger(conn)
        report.ledger_drift = len(drift)
        if drift:
            report.problems.append(f"ledger: {len(drift)} printing(s) where inventory != SUM(delta)")
        orphans = sum(f.rows for f in audit.catalog_refs(conn))
        report.catalog_ref_orphans = orphans
        if orphans:
            report.problems.append(f"catalog-refs: {orphans} user row(s) point at printings missing from cards")
        fks = [tuple(r) for s in ("main", _layout.CATALOG_SCHEMA)
               for r in conn.execute(f"PRAGMA {s}.foreign_key_check")]
        report.fk_violations = len(fks)
        if fks:
            report.problems.append(f"foreign_key_check: {len(fks)} violation(s), e.g. {fks[0]}")
    finally:
        conn.close()


def _mb(n: int) -> str:
    return f"{n / (1024 * 1024):,.1f} MB"


def format_report(r: SplitReport) -> str:
    """The plain-text report ``mm db split`` prints."""
    mark = lambda ok: "✓" if ok else "✗"  # noqa: E731
    lines = [
        f"{'SPLIT OK' if r.ok else 'SPLIT FAILED — nothing was written'}  ({r.seconds}s)",
        f"source:  {r.source}  (v{r.version}, journal {r.journal_mode}; opened read-only)",
        f"catalog: {r.catalog}" + (f"  {_mb(r.sizes['catalog'])}" if "catalog" in r.sizes else ""),
        f"user:    {r.user_db}" + (f"  {_mb(r.sizes['user'])}" if "user" in r.sizes else ""),
        "tables (rows · content hash vs source):",
    ]
    for t in sorted(r.tables, key=lambda t: (t.file, t.table)):
        lines.append(f"  {mark(t.ok)} {t.file:7} {t.table:24} {t.rows:>9,}  {t.sha256[:12]}")
    if r.sequences:
        lines.append("sequences kept: " + ", ".join(f"{k}={v}" for k, v in sorted(r.sequences.items())))
    if r.legacy_skipped:
        lines.append("legacy tables left in the source (not carried): "
                     + ", ".join(f"{k} ({v:,} rows)" for k, v in sorted(r.legacy_skipped.items())))
    checks = [
        ("ledger reconciles (inventory == SUM(delta))", r.ledger_drift, "drifting printing(s)"),
        ("catalog-refs", r.catalog_ref_orphans, "orphan user row(s)"),
        ("foreign_key_check", r.fk_violations, "violation(s)"),
    ]
    for label, n, unit in checks:
        if n is not None:
            lines.append(f"  {mark(n == 0)} {label}: {n} {unit}")
    for what, res in sorted(r.integrity.items()):
        lines.append(f"  {mark(res == 'ok')} integrity_check {what}: {res}")
    for p in r.problems:
        lines.append(f"  ✗ {p}")
    return "\n".join(lines)
