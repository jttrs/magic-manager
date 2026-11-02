"""Home-server operations for the hosted (split) data dir (Phase 3 §25.4 step 8, H7).

Pure decisions + small file operations the deploy kit (``deploy/macos/``) calls
through ``mm host …``; nothing here talks to launchd, git remotes or the network.

* **Migration hold, split-aware.** Auto-deploy must never upgrade a database. The
  hosted server migrates every file at start (``userfiles.migrate_all``), so code
  whose schema version is newer than the catalog OR any user file is held back
  until the owner runs the upgrade explicitly (``deploy/macos/bin/upgrade.sh
  --apply``: pair snapshot first, per ``post_merge_upgrade.py``).
  :func:`code_version_from_source` reads the version from the new code's
  ``db.py`` text (the length of its ``MIGRATIONS`` list, failing closed);
  :func:`hold_decision` is the rule.
* **WAL.** Litestream needs ``journal_mode=WAL``. :func:`set_wal` turns it on for
  the catalog, ``auth.db`` and every user file at cutover (services stopped); WAL
  is a property of the file, so it sticks — nothing in ``db.connect`` changes it,
  and ``userfiles.create`` makes new user files WAL when the catalog is.
* **Permissions.** :func:`secure_permissions` makes the data dir 0700 and its
  files 0600 (the collection files hold personal data; ``auth.db`` holds sessions).
"""
from __future__ import annotations

import ast
import os
import sqlite3
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import db
from . import layout as _layout
from . import userfiles

AUTH_FILE = "auth.db"


class HostOpsError(RuntimeError):
    """The data dir isn't in a state this operation can run in (nothing changed)."""


# ---------- schema versions + the deploy hold ----------

def code_version_from_source(text: str) -> int:
    """``CURRENT_VERSION`` of a ``db.py`` text without importing it: the number of
    elements of its ``MIGRATIONS`` list, read with :mod:`ast` (comments, a missing last
    comma or any element shape count the same). Fails closed — raises when the text
    doesn't parse, has no ``MIGRATIONS`` list, or no longer says
    ``CURRENT_VERSION = len(MIGRATIONS)``."""
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        raise HostOpsError(f"db.py doesn't parse: {e}") from None
    count, derived = None, False
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (
            node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else None)
        if not isinstance(target, ast.Name):
            continue
        if target.id == "MIGRATIONS" and isinstance(node.value, ast.List):
            count = len(node.value.elts)
        elif target.id == "CURRENT_VERSION":
            v = node.value
            derived = (isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "len"
                       and len(v.args) == 1 and isinstance(v.args[0], ast.Name) and v.args[0].id == "MIGRATIONS")
    if not count:
        raise HostOpsError("can't find a non-empty MIGRATIONS list in db.py")
    if not derived:
        raise HostOpsError("db.py no longer sets CURRENT_VERSION = len(MIGRATIONS); update hostops.code_version_from_source")
    return count


def code_version_at(ref: str, repo: Path) -> int:
    """The schema version of ``src/magic_manager/db.py`` at git ``ref`` in ``repo``."""
    try:
        text = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:src/magic_manager/db.py"],
                              check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise HostOpsError(f"can't read db.py at {ref}: {getattr(e, 'stderr', '') or e}".strip()) from None
    return code_version_from_source(text)


def file_version(path: Path) -> int | None:
    """``schema_version`` of one SQLite file, opened read-only (None if unreadable)."""
    try:
        conn = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return int(row[0]) if row and row[0] is not None else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def collection_files(data_dir: Path) -> dict[str, Path]:
    """The files the code's schema version applies to: ``catalog`` + each user file
    (``users/<name>``). ``auth.db`` keeps its own small schema (``auth.store``)."""
    data_dir = Path(data_dir)
    out = {"catalog": data_dir / _layout.CATALOG_FILENAME}
    out.update({f"users/{p.stem}": p for p in userfiles.user_files(data_dir)})
    return out


def data_versions(data_dir: Path) -> dict[str, int | None]:
    return {label: file_version(p) for label, p in collection_files(data_dir).items()}


@dataclass
class HoldDecision:
    hold: bool
    code_version: int
    versions: dict[str, int | None]
    behind: dict[str, int | None] = field(default_factory=dict)   # files the new code would migrate
    ahead: dict[str, int | None] = field(default_factory=dict)    # files newer than the code (a rollback)

    @property
    def message(self) -> str:
        if not self.hold:
            return f"ok: every file is at v{self.code_version}"
        parts = []
        if self.behind:
            parts.append("needs a database upgrade to v{}: {}".format(
                self.code_version, ", ".join(f"{k} (v{v if v is not None else '?'})" for k, v in sorted(self.behind.items()))))
        if self.ahead:
            parts.append("files are NEWER than this code (v{}): {}".format(
                self.code_version, ", ".join(f"{k} (v{v})" for k, v in sorted(self.ahead.items()))))
        return "HOLD — " + "; ".join(parts)


def hold_decision(code_version: int, versions: dict[str, int | None]) -> HoldDecision:
    """Hold when the catalog OR any user file is not at ``code_version``: older
    files would be migrated by the server's start-up (never automatic), unreadable
    ones are unknown, newer ones mean the code would go backwards."""
    behind = {k: v for k, v in versions.items() if v is None or v < code_version}
    ahead = {k: v for k, v in versions.items() if v is not None and v > code_version}
    if "catalog" not in versions:
        behind["catalog"] = None
    return HoldDecision(bool(behind or ahead), code_version, dict(versions), behind, ahead)


# ---------- WAL ----------

def wal_files(data_dir: Path) -> list[Path]:
    """The files the hosted data dir runs in WAL: catalog, auth.db, every user file
    (undo restore points are local scratch, not replicated, left as they are)."""
    data_dir = Path(data_dir)
    files = [data_dir / _layout.CATALOG_FILENAME, data_dir / AUTH_FILE, *userfiles.user_files(data_dir)]
    return [p for p in files if p.is_file()]


@dataclass
class WalChange:
    path: str
    before: str
    after: str


def set_wal(data_dir: Path, *, apply: bool) -> list[WalChange]:
    """Turn WAL on for :func:`wal_files` (dry run unless ``apply``). Refuses, before
    changing anything, when a file looks open (journal/WAL sidecars present) —
    stop the server and Litestream first."""
    files = wal_files(data_dir)
    if not files:
        raise HostOpsError(f"no database files under {data_dir}")
    out = []
    for p in files:
        before = "wal" if db.is_wal(p) else "delete"
        if before != "wal" and (side := db.sidecars(p)):
            raise HostOpsError(f"{p.name} looks open ({', '.join(s.name for s in side)}) — stop the server and Litestream first")
        out.append(WalChange(str(p), before, "wal" if apply or before == "wal" else before))
    if apply:
        for p, change in zip(files, out):
            if change.before == "wal":
                continue
            conn = sqlite3.connect(str(p), timeout=5)
            try:
                mode = conn.execute("PRAGMA journal_mode = WAL").fetchone()[0].lower()
            finally:
                conn.close()
            if mode != "wal" or not db.is_wal(p):
                raise HostOpsError(f"{p.name}: couldn't turn on WAL (journal_mode={mode})")
    return out


# ---------- permissions ----------

@dataclass
class PermChange:
    path: str
    before: str
    after: str


def secure_permissions(data_dir: Path, *, apply: bool) -> list[PermChange]:
    """Directories under ``data_dir`` → 0700, files → 0600 (only what isn't already;
    symlinks are never followed). Dry run unless ``apply``."""
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        raise HostOpsError(f"no data dir at {data_dir}")
    out = []
    for p in [data_dir, *sorted(data_dir.rglob("*"))]:
        if p.is_symlink():
            continue
        st = p.lstat()
        want = 0o700 if stat.S_ISDIR(st.st_mode) else 0o600
        have = stat.S_IMODE(st.st_mode)
        if have != want:
            out.append(PermChange(str(p), oct(have), oct(want)))
            if apply:
                os.chmod(p, want)
    return out
