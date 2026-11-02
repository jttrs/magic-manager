"""Offsite backups for the hosted data dir (Phase 3 §25.4 step 8, H2/H3/H10).

What goes offsite, and how (``docs/home-server.md`` has the runbook + the cost sums):

* **Precious, continuously** — ``auth.db`` and every ``users/<id>.db`` — by
  **Litestream** (a separate always-on process; :func:`litestream_config` writes
  its config, :func:`replicate` starts it with the credentials from the server's
  ``.env``). New users appear at runtime: Litestream's directory watcher (``dir``
  + ``pattern`` + ``watch: true``, v0.5.4+) picks a new file up within seconds, so
  no config regeneration or reload is needed. The pattern matches exactly the
  16-character auth ids (:func:`user_file_pattern`), so restore points
  (``<id>.undo.db``) and temp files are never replicated. Snapshots are kept
  :data:`RETENTION_DAYS` (30) days.
* **The catalog, weekly** (``catalog.db``, a rebuildable cache with heavy write
  churn on syncs — continuous replication would burn the free tier's write ops):
  :func:`catalog_backup` = ``VACUUM INTO`` → integrity check → gzip → upload
  ``catalog/catalog-<ts>.db.gz`` + a JSON manifest (written last), keeping
  :data:`CATALOG_KEEP` (2).
* **Not replicated:** ``analytics.db`` (disposable, H14), undo restore points,
  migration snapshots.
* **Deleted accounts age out** (H10): Litestream stops writing a deleted file's
  replica but never deletes it, so :func:`prune_deleted` removes the replica of
  an id that has no ``auth.db`` row and no local file once its newest object is
  older than the retention.

The laptop's **re-pull** (:func:`pull`, ``mm db pull``) restores one user file
(+ the newest catalog snapshot, or keeps the local one) into a LOCAL split data
dir with a separate read-only token, verifies it, and only then swaps it in. It
never writes to the store and refuses a hosted data dir.

Settings (environment, else the gitignored ``.env`` via :mod:`magic_manager.secrets`):
``MM_OFFSITE_URL`` (``s3://<bucket>/<prefix>?endpoint=https://<account>.r2.cloudflarestorage.com``,
or ``file:///dir`` for rehearsals), ``MM_OFFSITE_ACCESS_KEY_ID``,
``MM_OFFSITE_SECRET_ACCESS_KEY``; ``MM_LITESTREAM`` = the binary (else ``litestream``
on PATH).
"""
from __future__ import annotations

import gzip
import json
import os
import re
import shutil
import sqlite3
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import db
from . import layout as _layout
from . import objectstore
from . import secrets as secrets_mod
from . import userfiles

ENV_URL = "MM_OFFSITE_URL"
ENV_KEY_ID = "MM_OFFSITE_ACCESS_KEY_ID"
ENV_SECRET = "MM_OFFSITE_SECRET_ACCESS_KEY"
ENV_LITESTREAM = "MM_LITESTREAM"

LITESTREAM_VERSION = "0.5.17"
RETENTION_DAYS = 30
CATALOG_KEEP = 2
CATALOG_PREFIX = "catalog/"
USERS_PREFIX = f"{_layout.USERS_SUBDIR}/"
AUTH_FILE = "auth.db"
CONFIG_FILE = "litestream.yml"
LOCAL_COPY_NOTE = "LOCAL-COPY.txt"
# Litestream intervals chosen for the R2 free tier (docs/home-server.md § Costs):
# idle cost is dominated by the L0-retention sweep (2 LISTs per database per check).
SYNC_INTERVAL = "10s"
L0_RETENTION_CHECK = "1h"
SNAPSHOT_INTERVAL = "24h"

_STAMP = "%Y%m%dT%H%M%SZ"
_CATALOG_KEY = re.compile(r"catalog/catalog-(\d{8}T\d{6}Z)\.(db\.gz|json)")
Progress = Callable[[str], None]


class OffsiteError(RuntimeError):
    """An offsite operation can't run or didn't verify (nothing live was changed)."""


class PullRefused(OffsiteError):
    """``mm db pull`` refused before writing anything (exit 2)."""


def _say(progress: Progress | None, msg: str) -> None:
    if progress:
        progress(msg)


# ---------- settings ----------

def offsite_url(url: str | None = None) -> str:
    """``url`` if given, else ``MM_OFFSITE_URL``; validated (no credentials in it)."""
    value = url or secrets_mod.get(ENV_URL)
    if not value:
        raise OffsiteError(f"no offsite URL: set {ENV_URL} (environment or the gitignored .env)")
    objectstore.parse_url(value)
    return value


def credentials() -> objectstore.Credentials | None:
    key, secret = secrets_mod.get(ENV_KEY_ID), secrets_mod.get(ENV_SECRET)
    return objectstore.Credentials(key, secret) if key and secret else None


def store(url: str | None = None) -> objectstore.Store:
    return objectstore.open_store(offsite_url(url), credentials())


def litestream_bin() -> str:
    exe = os.environ.get(ENV_LITESTREAM) or shutil.which("litestream")
    if not exe:
        raise OffsiteError(f"litestream not found: install v{LITESTREAM_VERSION} (docs/home-server.md) "
                           f"or set {ENV_LITESTREAM}")
    return exe


def litestream_env(creds: objectstore.Credentials | None, base: dict[str, str] | None = None) -> dict[str, str]:
    """The environment Litestream runs with: credentials only in its environment
    (never its config file, argv or logs)."""
    env = dict(os.environ if base is None else base)
    for k in ("LITESTREAM_ACCESS_KEY_ID", "LITESTREAM_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        env.pop(k, None)
    env.pop(ENV_SECRET, None)
    if creds is not None:
        env["LITESTREAM_ACCESS_KEY_ID"] = creds.access_key_id
        env["LITESTREAM_SECRET_ACCESS_KEY"] = creds.secret_access_key
    return env


# ---------- Litestream config ----------

def user_file_pattern() -> str:
    """Glob for ``users/<auth id>.db`` only: as many ``?`` as an auth id has
    characters (``layout.AUTH_ID_RE``) — ``<id>.undo.db`` and temp files don't match."""
    m = re.fullmatch(r"\[a-z0-9\]\{(\d+)\}", _layout.AUTH_ID_RE.pattern)
    if not m:
        raise OffsiteError("layout.AUTH_ID_RE changed shape; update offsite.user_file_pattern")
    return "?" * int(m.group(1)) + ".db"


def _q(s: str) -> str:
    return json.dumps(str(s))  # a JSON string is a valid YAML double-quoted scalar


def litestream_config(data_dir: Path, url: str) -> str:
    """Litestream's YAML for the data dir (no credentials in it)."""
    data_dir = Path(data_dir).resolve()
    offsite_url(url)
    return "\n".join([
        "# Generated by `mm host litestream-config` (magic_manager.offsite) — re-generate, don't edit.",
        "# No credentials here: Litestream reads LITESTREAM_ACCESS_KEY_ID / LITESTREAM_SECRET_ACCESS_KEY",
        "# from the environment `mm host replicate` gives it.",
        "snapshot:",
        f"  interval: {SNAPSHOT_INTERVAL}",
        f"  retention: {RETENTION_DAYS * 24}h",
        f"l0-retention-check-interval: {L0_RETENTION_CHECK}",
        "dbs:",
        f"  - path: {_q(data_dir / AUTH_FILE)}",
        "    replica:",
        f"      url: {_q(objectstore.child_url(url, AUTH_FILE))}",
        f"      sync-interval: {SYNC_INTERVAL}",
        f"  - dir: {_q(data_dir / _layout.USERS_SUBDIR)}",
        f"    pattern: {_q(user_file_pattern())}",
        "    watch: true",
        "    replica:",
        f"      url: {_q(objectstore.child_url(url, _layout.USERS_SUBDIR))}",
        f"      sync-interval: {SYNC_INTERVAL}",
        "",
    ])


def write_config(data_dir: Path, url: str, out: Path | None = None) -> Path:
    out = Path(out) if out else Path(data_dir) / CONFIG_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(litestream_config(data_dir, url))
    os.replace(tmp, out)
    return out


def replicate_argv(config: Path, exec_cmd: str | None = None) -> list[str]:
    argv = [litestream_bin(), "replicate", "-config", str(config), "-no-expand-env"]
    if exec_cmd:
        argv += ["-exec", exec_cmd]
    return argv


def replicate(data_dir: Path, url: str | None = None, *, exec_cmd: str | None = None):
    """Write the config and replace this process with ``litestream replicate``."""
    data_dir = Path(data_dir)
    url = offsite_url(url)
    if not (data_dir / AUTH_FILE).is_file():
        raise OffsiteError(f"no {AUTH_FILE} in {data_dir} — is this the hosted data dir?")
    (data_dir / _layout.USERS_SUBDIR).mkdir(mode=0o700, exist_ok=True)
    creds = credentials()
    if objectstore.parse_url(url).scheme == "s3" and creds is None:
        raise OffsiteError(f"no offsite credentials: set {ENV_KEY_ID} + {ENV_SECRET} in the server's .env")
    config = write_config(data_dir.resolve(), url)
    argv = replicate_argv(config, exec_cmd)
    os.execvpe(argv[0], argv, litestream_env(creds))


def restore(replica_url: str, out: Path, *, creds: objectstore.Credentials | None) -> dict:
    """``litestream restore`` one database from its replica URL into ``out`` (which
    must not exist). Returns Litestream's JSON summary."""
    out = Path(out)
    if out.exists():
        raise OffsiteError(f"refusing to restore over {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    argv = [litestream_bin(), "restore", "-no-expand-env", "-json", "-o", str(out), replica_url]
    try:
        r = subprocess.run(argv, env=litestream_env(creds), capture_output=True, text=True, timeout=3600)
    except subprocess.TimeoutExpired:
        out.unlink(missing_ok=True)
        raise OffsiteError("litestream restore timed out after an hour") from None
    if r.returncode != 0 or not out.is_file():
        tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
        raise OffsiteError(f"litestream restore failed ({r.returncode}): {' | '.join(tail)}")
    try:
        return json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {}
    except (json.JSONDecodeError, IndexError):
        return {}


# ---------- table fingerprints (restore verification) ----------

def fingerprints(path: Path) -> dict[str, tuple[int, str]]:
    """``table → (rows, content hash)`` of every table but SQLite's and Litestream's
    own (``_litestream_*``), read-only — the same hash the splitter verifies with."""
    from .split import _table_hash
    conn = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)
    try:
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
                 if r[0] not in _layout.LITESTREAM_TABLES]
        return {n: _table_hash(conn, "main", n) for n in names}
    finally:
        conn.close()


# ---------- the weekly catalog snapshot ----------

@dataclass
class CatalogBackup:
    key: str
    size: int
    sha256: str
    version: int
    bytes_db: int
    kept: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _catalog_sets(objs: list[objectstore.Obj]) -> dict[str, set[str]]:
    """``timestamp → {'db.gz', 'json'}`` of the catalog snapshots in a listing."""
    out: dict[str, set[str]] = {}
    for o in objs:
        if m := _CATALOG_KEY.fullmatch(o.key):
            out.setdefault(m.group(1), set()).add(m.group(2))
    return out


def catalog_backup(data_dir: Path, st: objectstore.Store, *, keep: int = CATALOG_KEEP,
                   now: datetime | None = None, progress: Progress | None = None) -> CatalogBackup:
    """``VACUUM INTO`` a consistent copy of the live catalog (works under WAL while
    the server runs), check it, gzip it, upload it + its manifest, keep the newest
    ``keep``. The local temp files are removed either way."""
    if keep < 1:
        raise ValueError("keep at least one catalog snapshot")
    data_dir = Path(data_dir)
    live = data_dir / _layout.CATALOG_FILENAME
    if not live.is_file():
        raise OffsiteError(f"no catalog at {live}")
    stamp = (now or datetime.now(UTC)).strftime(_STAMP)
    work = data_dir / db.BAK_SUBDIR / f".offsite-{stamp}"
    work.mkdir(parents=True, mode=0o700)
    try:
        copy, packed = work / "catalog.db", work / "catalog.db.gz"
        _say(progress, f"VACUUM INTO a copy of {live.name} …")
        src = sqlite3.connect(f"{live.resolve().as_uri()}?mode=ro", uri=True)
        try:
            src.execute("VACUUM INTO ?", (str(copy),))
        finally:
            src.close()
        if (result := db._check_integrity(copy)) != "ok":
            raise OffsiteError(f"catalog copy failed integrity_check: {result}")
        version = _version_of(copy)
        _say(progress, "compressing …")
        with open(copy, "rb") as fin, gzip.open(packed, "wb", compresslevel=6) as fout:
            shutil.copyfileobj(fin, fout, 1024 * 1024)
        digest = objectstore.file_sha256(packed)
        key = f"{CATALOG_PREFIX}catalog-{stamp}.db.gz"
        manifest = work / "manifest.json"
        manifest.write_text(json.dumps({"key": key, "sha256": digest, "size": packed.stat().st_size,
                                        "schema_version": version, "created": stamp,
                                        "bytes_db": copy.stat().st_size}, indent=2))
        _say(progress, f"uploading {key} ({packed.stat().st_size / 1e6:,.1f} MB) …")
        st.put(key, packed)
        st.put(f"{CATALOG_PREFIX}catalog-{stamp}.json", manifest)  # written last = complete
        out = CatalogBackup(key, packed.stat().st_size, digest, version, copy.stat().st_size)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    sets_ = _catalog_sets(st.list(CATALOG_PREFIX))
    complete = sorted((t for t, kinds in sets_.items() if kinds == {"db.gz", "json"}), reverse=True)
    out.kept = complete[:keep]
    for t in sorted(sets_):
        if t in out.kept or (t not in complete and t >= stamp):
            continue
        for ext in sorted(sets_[t]):
            st.delete(f"{CATALOG_PREFIX}catalog-{t}.{ext}")
            out.deleted.append(f"{CATALOG_PREFIX}catalog-{t}.{ext}")
    return out


def latest_catalog(st: objectstore.Store) -> str | None:
    """Timestamp of the newest COMPLETE catalog snapshot in the store."""
    sets_ = _catalog_sets(st.list(CATALOG_PREFIX))
    done = sorted(t for t, kinds in sets_.items() if kinds == {"db.gz", "json"})
    return done[-1] if done else None


def fetch_catalog(st: objectstore.Store, stamp: str, dest: Path) -> dict:
    """Download snapshot ``stamp`` to ``dest`` (uncompressed), checking its sha256."""
    dest = Path(dest)
    manifest_path = dest.with_name(dest.name + ".manifest.json")
    packed = dest.with_name(dest.name + ".gz")
    try:
        st.get(f"{CATALOG_PREFIX}catalog-{stamp}.json", manifest_path)
        manifest = json.loads(manifest_path.read_text())
        st.get(f"{CATALOG_PREFIX}catalog-{stamp}.db.gz", packed)
        if objectstore.file_sha256(packed) != manifest.get("sha256"):
            raise OffsiteError(f"catalog snapshot {stamp} doesn't match its manifest (sha256)")
        with gzip.open(packed, "rb") as fin, open(dest, "wb") as fout:
            shutil.copyfileobj(fin, fout, 1024 * 1024)
        return manifest
    finally:
        packed.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)


def _version_of(path: Path) -> int:
    from .hostops import file_version
    return file_version(path) or 0


# ---------- deleted accounts age out ----------

@dataclass
class PrunePlan:
    deleted_ids: dict[str, list[str]] = field(default_factory=dict)   # id → keys to delete
    waiting: dict[str, str] = field(default_factory=dict)             # id → newest object (ISO)
    live: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def prune_plan(objs: list[objectstore.Obj], keep_ids: set[str], now: datetime,
               retention_days: int = RETENTION_DAYS) -> PrunePlan:
    """Pure: which replicas under ``users/`` to delete. An id in ``keep_ids`` (an
    auth row or a local file) is never touched; any other id's objects go once the
    newest of them is older than ``retention_days``."""
    groups: dict[str, list[objectstore.Obj]] = {}
    for o in objs:
        parts = o.key.split("/")
        if len(parts) >= 3 and parts[0] == _layout.USERS_SUBDIR and parts[1].endswith(".db"):
            groups.setdefault(parts[1][:-3], []).append(o)
    plan = PrunePlan()
    cutoff = now - timedelta(days=retention_days)
    for uid, items in sorted(groups.items()):
        if uid in keep_ids:
            plan.live.append(uid)
            continue
        newest = max(o.modified for o in items)
        if newest < cutoff:
            plan.deleted_ids[uid] = sorted(o.key for o in items)
        else:
            plan.waiting[uid] = newest.isoformat(timespec="seconds")
    return plan


def known_ids(data_dir: Path) -> set[str]:
    """Every id that may still own a replica: rows in ``auth.db`` + local user files.
    Raises when ``auth.db`` can't be read (never prune blind)."""
    data_dir = Path(data_dir)
    auth = data_dir / AUTH_FILE
    if not auth.is_file():
        raise OffsiteError(f"no {AUTH_FILE} in {data_dir} — refusing to prune without the account list")
    conn = sqlite3.connect(f"{auth.resolve().as_uri()}?mode=ro", uri=True)
    try:
        ids = {r[0] for r in conn.execute("SELECT id FROM users")}
    except sqlite3.Error as e:
        raise OffsiteError(f"can't read the account list: {e}") from None
    finally:
        conn.close()
    return ids | {p.stem for p in userfiles.user_files(data_dir)}


def prune_deleted(data_dir: Path, st: objectstore.Store, *, apply: bool, now: datetime | None = None,
                  retention_days: int = RETENTION_DAYS) -> PrunePlan:
    plan = prune_plan(st.list(USERS_PREFIX), known_ids(data_dir), now or datetime.now(UTC), retention_days)
    if apply:
        for keys in plan.deleted_ids.values():
            for k in keys:
                st.delete(k)
    return plan


# ---------- restore drill / first-replica check ----------

@dataclass
class FileCheck:
    name: str
    ok: bool
    detail: str
    tables: dict[str, int] = field(default_factory=dict)


@dataclass
class VerifyReport:
    files: list[FileCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.files) and all(f.ok for f in self.files)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "files": [asdict(f) for f in self.files]}


def verify_replicas(data_dir: Path, url: str | None = None, *, progress: Progress | None = None) -> VerifyReport:
    """Restore ``auth.db`` and every user file from the replica into a scratch dir
    under ``<data dir>/bak/`` and compare each table (rows + content hash) with the
    live file; user files also pass the split checks (integrity, ledger, catalog
    refs, foreign keys) against the live catalog. Run it when the app is quiet —
    a write after Litestream's last sync shows up as a difference. Read-only for
    the live files; the scratch dir is removed."""
    from .split import SplitReport, verify_pair
    data_dir = Path(data_dir)
    url = offsite_url(url)
    creds = credentials()
    names = [AUTH_FILE] + [f"{_layout.USERS_SUBDIR}/{p.name}" for p in userfiles.user_files(data_dir)]
    scratch = data_dir / db.BAK_SUBDIR / f".verify-{datetime.now(UTC).strftime(_STAMP)}"
    scratch.mkdir(parents=True, mode=0o700)
    report = VerifyReport()
    try:
        for name in names:
            _say(progress, f"restoring {name} from the replica …")
            out = scratch / name
            try:
                restore(objectstore.child_url(url, name), out, creds=creds)
            except OffsiteError as e:
                report.files.append(FileCheck(name, False, str(e)))
                continue
            problems = []
            if (res := db._check_integrity(out)) != "ok":
                problems.append(f"integrity_check: {res}")
            live, got = fingerprints(data_dir / name), fingerprints(out)
            diff = sorted(t for t in set(live) | set(got) if live.get(t) != got.get(t))
            if diff:
                problems.append("differs from live: " + ", ".join(
                    f"{t} ({live.get(t, (0,))[0]} live / {got.get(t, (0,))[0]} restored rows)" for t in diff))
            if name != AUTH_FILE:
                r = SplitReport("", "", str(out), "", 0, "")
                verify_pair(out, data_dir / _layout.CATALOG_FILENAME, Path(name).stem, r)
                problems += r.problems
            report.files.append(FileCheck(name, not problems, "; ".join(problems) or "restored = live",
                                          {t: n for t, (n, _h) in got.items()}))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return report


# ---------- the laptop's re-pull (H3) ----------

@dataclass
class PullReport:
    to: str
    user: str
    user_db: str
    catalog: str
    catalog_source: str                 # 'remote <stamp>' | 'kept'
    migrated: dict[str, list[int]] = field(default_factory=dict)
    tables: dict[str, int] = field(default_factory=dict)
    replaced: str | None = None
    restore: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def env(self) -> str:
        return f"MM_LAYOUT=split MM_DATA_DIR={self.to} MM_USER={self.user}"


def _split_problems(r) -> tuple[list[str], list[str]]:
    """``verify_pair`` findings split into hard failures and warnings. Rows pointing at
    printings the catalog lacks are a WARNING when the catalog is the weekly snapshot:
    the user may have added cards from a set synced after it (the copy works; those
    cards show without names until the set is synced or the next snapshot)."""
    hard = [p for p in r.problems if not p.startswith("catalog-refs:")]
    warn = [f"{p} — the catalog snapshot predates them: sync those sets (mm set sync) or pull after the "
            "next weekly snapshot (mm host catalog-backup on the server)" for p in r.problems if p.startswith("catalog-refs:")]
    return hard, warn


def _is_hosted_dir(path: Path) -> bool:
    if (path / AUTH_FILE).exists() or (path / f".{AUTH_FILE}-litestream").exists():
        return True
    if (os.environ.get("MM_MODE") or "").strip().lower() == "hosted" and os.environ.get("MM_DATA_DIR"):
        try:
            return Path(os.environ["MM_DATA_DIR"]).resolve() == path.resolve()
        except OSError:
            return True
    return False


def pull(user: str, to: Path, *, url: str | None = None, catalog: str = "remote", force: bool = False,
         progress: Progress | None = None, now: datetime | None = None) -> PullReport:
    """Restore ``users/<user>.db`` from the offsite replica (+ the newest catalog
    snapshot, or keep ``<to>/catalog.db`` with ``catalog='keep'``) into the LOCAL
    split data dir ``to``. Verified (integrity, ledger, catalog refs, foreign keys)
    in a staging dir before anything is swapped in; existing files are moved to
    ``<to>/replaced/pull-<ts>/`` only with ``force``. Never writes to the store."""
    if catalog not in ("remote", "keep"):
        raise ValueError("catalog must be 'remote' or 'keep'")
    if not _layout.AUTH_ID_RE.fullmatch(user or ""):
        raise PullRefused(f"{user!r} is not a user id (the hosted file is users/<id>.db; see `mm auth users` on the server)")
    to = Path(to).expanduser().resolve()
    url = offsite_url(url)
    if _is_hosted_dir(to):
        raise PullRefused(f"{to} is a hosted data dir (it has {AUTH_FILE}) — pull only into a local copy dir")
    target_user = _layout.user_db_path(to, user)
    target_catalog = to / _layout.CATALOG_FILENAME
    for f in (target_user, target_catalog):
        if side := db.sidecars(f):
            raise PullRefused(f"{f} looks open ({', '.join(p.name for p in side)}) — close what uses the copy first")
    existing = [f for f in (target_user, target_catalog if catalog == "remote" else None) if f and f.exists()]
    if existing and not force:
        raise PullRefused(f"{', '.join(str(f) for f in existing)} already exist — pass --force to replace them "
                          f"(the old files are kept under {to / db.REPLACED_SUBDIR})")
    if catalog == "keep" and not target_catalog.is_file():
        raise PullRefused(f"--catalog keep: no {target_catalog} to keep")
    creds = credentials()
    st = objectstore.open_store(url, creds)
    stamp = (now or datetime.now(UTC)).strftime(_STAMP)
    staging = to / f".pull-{stamp}"
    to.mkdir(parents=True, exist_ok=True, mode=0o700)
    staging.mkdir(mode=0o700)
    try:
        staged_user = _layout.user_db_path(staging, user)
        _say(progress, f"restoring users/{user}.db from the replica …")
        summary = restore(objectstore.child_url(url, f"{_layout.USERS_SUBDIR}/{user}.db"), staged_user, creds=creds)
        if catalog == "remote":
            snap = latest_catalog(st)
            if not snap:
                raise OffsiteError("no catalog snapshot offsite yet (the server's weekly job uploads one) — "
                                   "use --catalog keep with an existing local catalog.db")
            staged_catalog = staging / _layout.CATALOG_FILENAME
            _say(progress, f"downloading catalog snapshot {snap} …")
            fetch_catalog(st, snap, staged_catalog)
            source = f"remote {snap}"
        else:
            staged_catalog, source = target_catalog, "kept"
        migrated: dict[str, list[int]] = {}
        for kind, f in (("catalog", staged_catalog), ("user", staged_user)):
            v = _version_of(f)
            if v > db.CURRENT_VERSION:
                raise OffsiteError(f"the pulled {kind} file is at schema v{v}, this checkout's code is at "
                                   f"v{db.CURRENT_VERSION} — update this checkout (git pull) and pull again")
            if v < db.CURRENT_VERSION:
                if kind == "catalog" and catalog == "keep":
                    raise OffsiteError(f"the kept catalog is at v{v}, this code needs v{db.CURRENT_VERSION} — "
                                       "pull with --catalog remote")
                migrated[kind] = db.migrate_split_file(f, kind)
        _say(progress, "verifying …")
        from .split import SplitReport, verify_pair
        r = SplitReport("", str(staged_catalog), str(staged_user), user, db.CURRENT_VERSION, "")
        verify_pair(staged_user, staged_catalog, user, r)
        hard, warnings = _split_problems(r)
        if hard:
            raise OffsiteError("the pulled copy didn't verify: " + "; ".join(hard))
        tables = {t: n for t, (n, _h) in fingerprints(staged_user).items() if t in _layout.USER_TABLES}
        replaced = None
        moving = [f for f in (target_user, target_catalog if catalog == "remote" else None) if f and f.exists()]
        if moving:
            aside = to / db.REPLACED_SUBDIR / f"pull-{stamp}"
            n = 1
            while aside.exists():  # never overwrite an earlier set-aside copy
                n += 1
                aside = to / db.REPLACED_SUBDIR / f"pull-{stamp}-{n}"
            for f in moving:
                dest = aside / f.relative_to(to)
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.replace(f, dest)
            replaced = str(aside)
        target_user.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.replace(staged_user, target_user)
        if catalog == "remote":
            os.replace(staged_catalog, target_catalog)
        for f in (target_user, target_catalog):
            os.chmod(f, 0o600)
        (to / LOCAL_COPY_NOTE).write_text(
            f"This is a LOCAL COPY of users/{user}.db pulled {stamp} from {objectstore.child_url(url, '').rstrip('/')}.\n"
            "The hosted server is the source of truth: changes made here are NOT sent back,\n"
            "and the next `mm db pull --force` replaces this copy.\n")
        return PullReport(str(to), user, str(target_user), str(target_catalog), source, migrated, tables,
                          replaced, summary, warnings)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


# ---------- disaster recovery: rebuild a hosted data dir from offsite ----------

@dataclass
class RestoreReport:
    data_dir: str
    users: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)     # replicas with no account in auth.db (deleted)
    missing: list[str] = field(default_factory=list)     # accounts with no replica (their file starts empty)
    catalog: str = ""
    versions: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def restore_all(data_dir: Path, *, url: str | None = None, progress: Progress | None = None) -> RestoreReport:
    """Rebuild a hosted data dir (a new server, the vendor move) from the offsite copy:
    ``auth.db``, then the file of every account it lists (replicas of deleted accounts
    still inside retention are NOT brought back), then the newest catalog snapshot.
    Refuses unless ``data_dir`` is empty. Each user file is verified against the
    catalog; everything ends WAL and private (0700/0600). Files older than this code
    are migrated by the server at start (each snapshotted first)."""
    from . import hostops
    from .split import SplitReport, verify_pair
    data_dir = Path(data_dir).expanduser().resolve()
    if data_dir.exists() and any(data_dir.iterdir()):
        raise PullRefused(f"{data_dir} isn't empty — restore only into a new, empty data dir")
    url = offsite_url(url)
    creds = credentials()
    st = objectstore.open_store(url, creds)
    snap = latest_catalog(st)
    if not snap:
        raise OffsiteError("no catalog snapshot offsite — nothing to rebuild the catalog from")
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    report = RestoreReport(str(data_dir), catalog=snap)
    _say(progress, "restoring auth.db …")
    restore(objectstore.child_url(url, AUTH_FILE), data_dir / AUTH_FILE, creds=creds)
    accounts = known_ids(data_dir)
    replicas = sorted({o.key.split("/")[1][:-3] for o in st.list(USERS_PREFIX)
                       if len(o.key.split("/")) >= 3 and o.key.split("/")[1].endswith(".db")})
    for uid in replicas:
        if uid not in accounts or not _layout.AUTH_ID_RE.fullmatch(uid):
            report.skipped.append(uid)
            continue
        _say(progress, f"restoring users/{uid}.db …")
        restore(objectstore.child_url(url, f"{_layout.USERS_SUBDIR}/{uid}.db"),
                _layout.user_db_path(data_dir, uid), creds=creds)
        report.users.append(uid)
    report.missing = sorted(a for a in accounts if a not in replicas and _layout.AUTH_ID_RE.fullmatch(a))
    _say(progress, f"downloading catalog snapshot {snap} …")
    fetch_catalog(st, snap, data_dir / _layout.CATALOG_FILENAME)
    problems = []
    for uid in report.users:
        r = SplitReport("", "", "", uid, 0, "")
        f = _layout.user_db_path(data_dir, uid)
        cat, usr = _version_of(data_dir / _layout.CATALOG_FILENAME), _version_of(f)
        if cat == usr == db.CURRENT_VERSION:
            verify_pair(f, data_dir / _layout.CATALOG_FILENAME, uid, r)
            hard, warn = _split_problems(r)
            problems += [f"{uid}: {p}" for p in hard]
            report.warnings += [f"{uid}: {p}" for p in warn]
    report.versions = {k: v for k, v in hostops.data_versions(data_dir).items() if v is not None}
    hostops.set_wal(data_dir, apply=True)
    hostops.secure_permissions(data_dir, apply=True)
    if problems:
        raise OffsiteError("the restored files didn't verify: " + "; ".join(problems))
    return report
