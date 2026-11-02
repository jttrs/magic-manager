"""Per-user collection files in the split layout (Phase 3 §25.4 step 5).

* :func:`create` writes a new, empty ``users/<id>.db`` at :data:`db.CURRENT_VERSION`
  holding only the USER schema (in WAL when the catalog is — the hosted data dir). The schema is not a hand-written copy: it is read
  from a fresh in-memory DB built by the same migrations every file runs
  (``db._ensure_schema``), keeping only the tables :mod:`layout` classifies as user
  tables (+ their indexes and ``schema_version``) — the rule the splitter uses.
* :func:`ensure` = create on first sign-in, else bring the file to the current
  version (``db.migrate_split_file(…, 'user')``, which snapshots it first).
* :func:`migrate_all` = server start: the catalog once, then every user file.
* :func:`user_artifacts` / :func:`remove_user_files` find and delete every file that
  holds one user's collection (account deletion, §25.1 H10).
* :func:`bind_file` maps the owner's split file (``users/owner.db`` from
  ``mm db split``) to their auth id after their first sign-in (``mm auth bind``).

Every path is built through ``layout.user_db_path`` after the id is checked, never
from raw input.
"""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from . import db
from . import layout as _layout
from .analytics import consent as _consent

UNDO_SUFFIX = ".undo.db"
PENDING_SUFFIX = ".pending"
_lock = threading.Lock()


class UserFileError(Exception):
    """A user file can't be created, migrated or bound as asked (nothing changed)."""


def path_for(data_dir: Path, user: str) -> Path:
    return _layout.user_db_path(Path(data_dir), _layout.check_user(user))


def undo_path_for(user_db: Path) -> Path:
    """``users/<id>.undo.db`` beside ``users/<id>.db`` — the one naming rule (``undo`` uses it)."""
    return user_db.with_name(user_db.stem + UNDO_SUFFIX)


def pending_path_for(snapshot: Path) -> Path:
    """The not-yet-promoted restore point beside ``snapshot`` (``undo.SessionGuard``)."""
    return snapshot.with_name(snapshot.name + PENDING_SUFFIX)


def _undo_files(user_db: Path) -> list[Path]:
    undo = undo_path_for(user_db)
    return [undo, pending_path_for(undo)]


@lru_cache(maxsize=1)
def user_schema() -> tuple[str, ...]:
    """The CREATE statements of a current user file, in creation order (code-derived;
    the same for every user, so caching it per process is safe)."""
    conn = sqlite3.connect(":memory:", factory=db.Connection)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        db._ensure_schema(conn)
        conn.commit()
        user_tables = {"schema_version", *_layout.USER_TABLES}
        rows = conn.execute(
            "SELECT type, tbl_name, sql FROM sqlite_master "
            "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY rowid").fetchall()
        out = [r["sql"] for r in rows if r["type"] == "table" and r["tbl_name"] in user_tables]
        out += [r["sql"] for r in rows if r["type"] in ("index", "trigger") and r["tbl_name"] in user_tables]
        missing = set(_layout.USER_TABLES) - {r["tbl_name"] for r in rows if r["type"] == "table"}
        if missing:
            raise UserFileError(f"the migrations don't create user tables {sorted(missing)}")
        return tuple(out)
    finally:
        conn.close()


def create(data_dir: Path, user: str) -> Path:
    """Write ``users/<user>.db`` (empty, current schema). Refuses an existing file."""
    target = path_for(data_dir, user)
    with _lock:
        if target.exists():
            raise UserFileError(f"{target.name} already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f".{target.name}.new-{os.getpid()}.tmp")
        tmp.unlink(missing_ok=True)
        try:
            conn = sqlite3.connect(str(tmp))
            try:
                for sql in user_schema():
                    conn.execute(sql)
                conn.execute("INSERT INTO schema_version (version) VALUES (?)", (db.CURRENT_VERSION,))
                conn.commit()
                if db.is_wal(Path(data_dir) / _layout.CATALOG_FILENAME):
                    # A WAL data dir (hosted, replicated by Litestream) stays all-WAL.
                    conn.execute("PRAGMA journal_mode = WAL")
            finally:
                conn.close()
            os.chmod(tmp, 0o600)
            os.link(tmp, target)  # never overwrites: a concurrent create loses cleanly
        except FileExistsError as e:
            raise UserFileError(f"{target.name} already exists") from e
        finally:
            tmp.unlink(missing_ok=True)
    return target


def ensure(data_dir: Path, user: str) -> str:
    """``created`` | ``migrated`` | ``ok`` — the user's file exists at the current version."""
    target = path_for(data_dir, user)
    if not target.exists():
        try:
            create(data_dir, user)
            return "created"
        except UserFileError:
            if not target.exists():
                raise
    return "migrated" if db.migrate_split_file(target, "user") else "ok"


def user_files(data_dir: Path) -> list[Path]:
    """Every ``users/<name>.db`` (undo files, temp files and snapshots excluded)."""
    users = Path(data_dir) / _layout.USERS_SUBDIR
    if not users.is_dir():
        return []
    return sorted(p for p in users.glob("*.db") if p.is_file() and _layout._USER_RE.fullmatch(p.stem))


@dataclass
class MigrateReport:
    catalog: list[int] = field(default_factory=list)
    users: dict[str, list[int]] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)   # user file → why it didn't migrate


def migrate_all(data_dir: Path) -> MigrateReport:
    """Server start: the catalog once (a failure stops startup), then every user file
    (each snapshotted by ``migrate_split_file`` before it changes). One user's file
    that can't migrate is reported in ``failed`` and skipped — split connect refuses
    a file at the wrong version, so only that user is affected."""
    data_dir = Path(data_dir)
    out = MigrateReport()
    out.catalog = db.migrate_split_file(data_dir / _layout.CATALOG_FILENAME, "catalog")
    for p in user_files(data_dir):
        try:
            out.users[p.stem] = db.migrate_split_file(p, "user")
        except Exception as e:  # noqa: BLE001 — isolate one user's file from everyone else's
            out.failed[p.stem] = f"{type(e).__name__}: {e}"
    return out


# Settings written before any real use (the hosted first-visit privacy prompt) aren't
# "data": an otherwise-empty profile that holds only these can still be replaced.
_PROFILE_ONLY_SETTINGS = (_consent.SETTING_KEY,)


def has_user_data(user_db: Path) -> bool:
    """Any row in any user table, ignoring a stored privacy choice (an empty profile has none)."""
    conn = sqlite3.connect(f"{user_db.resolve().as_uri()}?mode=ro", uri=True)
    try:
        present = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        marks = ", ".join("?" for _ in _PROFILE_ONLY_SETTINGS)
        for t in _layout.USER_TABLES:
            if t not in present:
                continue
            if t == "settings":
                hit = conn.execute(f"SELECT 1 FROM settings WHERE key NOT IN ({marks}) LIMIT 1", _PROFILE_ONLY_SETTINGS).fetchone()
            else:
                hit = conn.execute(f'SELECT 1 FROM "{t}" LIMIT 1').fetchone()
            if hit:
                return True
        return False
    finally:
        conn.close()


@dataclass
class BindReport:
    source: str
    target: str
    replaced: str | None = None   # where an empty profile file was moved


def bind_file(data_dir: Path, user_id: str, source: str = _layout.DEFAULT_USER) -> BindReport:
    """Make ``users/<source>.db`` the file of auth user ``user_id`` (renamed to
    ``users/<user_id>.db``, with its undo file). The auth user's own file, if their
    first sign-in already created it, must hold no data; it is moved to
    ``<data dir>/replaced/``. Refuses (:class:`UserFileError`, nothing changed) when
    either file looks open (journal/WAL sidecars) — stop the server first."""
    data_dir = Path(data_dir)
    if not _layout.AUTH_ID_RE.fullmatch(user_id or ""):
        raise UserFileError(f"{user_id!r} is not a user id (see `mm auth users`)")
    src = _layout.user_db_path(data_dir, source)
    dst = _layout.user_db_path(data_dir, user_id)
    if src == dst:
        raise UserFileError("the file already belongs to that user")
    if not src.is_file():
        raise UserFileError(f"no file {src} to bind")
    with _lock:
        for p in (src, dst):
            if side := db.sidecars(p):
                raise UserFileError(f"{p.name} looks open ({', '.join(q.name for q in side)}) — stop the server first")
        report = BindReport(str(src), str(dst))
        if dst.exists():
            if has_user_data(dst):
                raise UserFileError(f"{dst.name} already holds data — refusing to replace it")
            ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            aside = data_dir / db.REPLACED_SUBDIR / f"users.replaced-{ts}"
            aside.mkdir(parents=True, exist_ok=True)
            os.replace(dst, aside / dst.name)
            for f in _undo_files(dst):
                if f.exists():
                    os.replace(f, aside / f.name)
            report.replaced = str(aside / dst.name)
        os.replace(src, dst)
        for old, new in zip(_undo_files(src), _undo_files(dst)):
            if old.exists():
                os.replace(old, new)
    return report


def _artifact_dirs(data_dir: Path) -> list[Path]:
    """Every directory a user's collection file (or a copy of it) can live in: ``users/``,
    its migration snapshots ``users/bak/``, split pair snapshots ``bak/split.bak-*/users/``,
    and what restores / binds set aside under ``replaced/``."""
    users = data_dir / _layout.USERS_SUBDIR
    dirs = [users, users / db.BAK_SUBDIR]
    dirs += sorted(p / _layout.USERS_SUBDIR for p in (data_dir / db.BAK_SUBDIR).glob(f"{db.SPLIT_SNAPSHOT_PREFIX}*"))
    replaced = data_dir / db.REPLACED_SUBDIR
    dirs += sorted(replaced.glob("*"))
    dirs += sorted(p / _layout.USERS_SUBDIR for p in replaced.glob("*"))
    return dirs


def user_artifacts(data_dir: Path, user: str) -> list[Path]:
    """Every file holding ``user``'s collection data under ``data_dir``: ``users/<id>.db``
    and its journal/WAL sidecars, the undo restore point (+ pending/temp), migration
    snapshots, the user's half of split pair snapshots, and set-aside copies under
    ``replaced/``. Matched by exact name (``<id>.db…`` / ``<id>.undo.db…`` /
    ``.<id>.db.…`` temp files) inside known directories only — never another user's
    file, never the catalog; directories that resolve outside ``data_dir`` (a symlink)
    are skipped. Files from before ``mm auth bind`` (named ``owner``) are not this id's."""
    _layout.check_user(user)
    data_dir = Path(data_dir)
    root = data_dir.resolve()
    name = re.compile(rf"\.?{re.escape(user)}(?:\.undo)?\.db(?:[.-].*)?")
    out: list[Path] = []
    for d in _artifact_dirs(data_dir):
        if not d.is_dir() or d.is_symlink():
            continue
        try:
            d.resolve().relative_to(root)
        except ValueError:
            continue
        out += sorted(p for p in d.iterdir() if name.fullmatch(p.name) and (p.is_file() or p.is_symlink()))
    return out


def litestream_dirs(data_dir: Path, user: str) -> list[Path]:
    """Litestream's local state for ``users/<id>.db`` (``users/.<id>.db-litestream/``:
    recent changes of the file, kept after the file is gone). Real directories inside
    ``users/`` only — a symlink is never followed."""
    _layout.check_user(user)
    users = Path(data_dir) / _layout.USERS_SUBDIR
    d = users / f".{user}.db-litestream"
    return [d] if d.is_dir() and not d.is_symlink() and not users.is_symlink() else []


def remove_user_files(data_dir: Path, user: str) -> list[Path]:
    """Delete every :func:`user_artifacts` file (the collection file before its sidecars),
    then Litestream's local state for it (:func:`litestream_dirs`). Idempotent: a missing
    file is skipped. Returns what was removed."""
    removed: list[Path] = []
    with _lock:
        for p in user_artifacts(data_dir, user):
            try:
                p.unlink()
            except FileNotFoundError:
                continue
            removed.append(p)
        for d in litestream_dirs(data_dir, user):
            shutil.rmtree(d, ignore_errors=True)
            removed.append(d)
    return removed
