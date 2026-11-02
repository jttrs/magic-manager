"""Phase 3 step 8 (§25.4, H2/H3/H7): offsite backups, the laptop's re-pull, the
split-aware deploy hold, WAL, and the macOS deploy kit — ``magic_manager.objectstore``,
``offsite``, ``hostops``, ``mm host …`` / ``mm db pull`` and ``deploy/macos``.

Offline: Litestream itself is replaced by a copy (``offsite.restore`` is the one seam
that runs it); the S3 client runs against an ``httpx.MockTransport``. The real
Litestream round trip is the rehearsal in ``scripts/rehearse_home_deploy.py``.
"""
from __future__ import annotations

import fnmatch
import hashlib
import os
import plistlib
import shutil
import sqlite3
import stat
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from xml.sax.saxutils import escape

import httpx
import pytest
import yaml
from typer.testing import CliRunner

from magic_manager import account, db, hostops, inventory, layout, objectstore, offsite, split, userfiles
from magic_manager.auth import store
from magic_manager.cli import app as cli_app

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "deploy" / "macos"
A_ID = "00000000-0000-0000-0000-00000000000a"
UID = "abcdefghij234567"
OTHER = "zzzzzzzzzzzzzzzz"


@pytest.fixture
def owner_split(tmp_db, seed_cards, make_card, request, monkeypatch):
    """A split data dir from a small collection (2 copies of one card); auth.db lives in it."""
    monkeypatch.delenv("MM_AUTH_DB", raising=False)
    seed_cards([make_card(id=A_ID, name="Alpha")])
    inventory.inventory_add(A_ID, "nonfoil", 2)
    return request.getfixturevalue("split_dir")


# ---------- objectstore ----------

def test_sigv4_matches_the_aws_documented_examples():
    c = objectstore.Credentials("AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    when = datetime(2013, 5, 24, tzinfo=UTC)
    empty = hashlib.sha256(b"").hexdigest()
    get = objectstore.sign("GET", "examplebucket.s3.amazonaws.com", "/test.txt", {}, {"range": "bytes=0-9"},
                           empty, c, "us-east-1", when)
    assert get["Authorization"].endswith("Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41")
    listing = objectstore.sign("GET", "examplebucket.s3.amazonaws.com", "/", {"max-keys": "2", "prefix": "J"}, {},
                               empty, c, "us-east-1", when)
    assert listing["Authorization"].endswith("Signature=34b48302e7b5fa45bde8084f4b7868a86f0a534bc59db6670ed5711ef69dc6f7")
    assert "wJalr" not in repr(c)


@pytest.mark.parametrize("url", [
    "s3://bucket/p",                                            # no endpoint
    "s3://key:secret@bucket/p?endpoint=https://x.example",      # credentials in the URL
    "s3://bucket/p?endpoint=http://x.example",                  # plain http off localhost
    "https://bucket/p", "file://relative/dir", "",
])
def test_bad_offsite_urls_are_refused(url):
    with pytest.raises(ValueError):
        objectstore.parse_url(url)


def test_offsite_url_parsing_and_child_urls():
    loc = objectstore.parse_url("s3://mm-backups/prod?endpoint=https://acct.r2.cloudflarestorage.com")
    assert (loc.bucket, loc.prefix, loc.endpoint, loc.region) == ("mm-backups", "prod", "https://acct.r2.cloudflarestorage.com", "auto")
    assert objectstore.child_url("s3://b/p?endpoint=https://h", "users/x.db") == "s3://b/p/users/x.db?endpoint=https://h"
    assert objectstore.child_url("file:///r/", "auth.db") == "file:///r/auth.db"


def test_file_store_round_trip_and_key_safety(tmp_path):
    st = objectstore.FileStore(tmp_path / "remote")
    src = tmp_path / "a.bin"
    src.write_bytes(b"hello")
    st.put("catalog/a.bin", src)
    assert [o.key for o in st.list("catalog/")] == ["catalog/a.bin"]
    st.get("catalog/a.bin", tmp_path / "b.bin")
    assert (tmp_path / "b.bin").read_bytes() == b"hello"
    for bad in ("../x", "/abs", "a//b", "a/./b"):
        with pytest.raises(ValueError):
            st.put(bad, src)
    st.delete("catalog/a.bin")
    assert st.list() == []


class FakeS3:
    """Path-style S3 with ListObjectsV2 pagination; checks every request is signed."""

    def __init__(self, page: int = 2):
        self.objects: dict[str, bytes] = {}
        self.page = page
        self.seen: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request)
        auth = request.headers.get("authorization", "")
        assert auth.startswith("AWS4-HMAC-SHA256 Credential=AKID/") and "/auto/s3/aws4_request" in auth
        assert "SECRET" not in auth
        parts = request.url.path.lstrip("/").split("/", 1)
        assert parts[0] == "bucket"
        if request.method == "PUT":
            body = request.read()
            assert request.headers["x-amz-content-sha256"] == hashlib.sha256(body).hexdigest()
            self.objects[parts[1]] = body
            return httpx.Response(200)
        if request.method == "GET" and len(parts) == 2:
            if parts[1] not in self.objects:
                return httpx.Response(404, text="<Error><Code>NoSuchKey</Code></Error>")
            return httpx.Response(200, content=self.objects[parts[1]])
        if request.method == "GET":
            q = {k: v[0] for k, v in parse_qs(urlsplit(str(request.url)).query).items()}
            keys = sorted(k for k in self.objects if k.startswith(q.get("prefix", "")))
            start = int(q.get("continuation-token", "0"))
            chunk = keys[start:start + self.page]
            more = start + self.page < len(keys)
            items = "".join(f"<Contents><Key>{escape(k)}</Key><Size>{len(self.objects[k])}</Size>"
                            f"<LastModified>2026-10-01T00:00:00.000Z</LastModified></Contents>" for k in chunk)
            xml = (f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">{items}'
                   f"<IsTruncated>{'true' if more else 'false'}</IsTruncated>"
                   + (f"<NextContinuationToken>{start + self.page}</NextContinuationToken>" if more else "")
                   + "</ListBucketResult>")
            return httpx.Response(200, text=xml)
        if request.method == "DELETE":
            self.objects.pop(parts[1], None)
            return httpx.Response(204)
        return httpx.Response(405)


def test_s3_store_puts_lists_pages_gets_and_deletes(tmp_path):
    fake = FakeS3()
    loc = objectstore.parse_url("s3://bucket/mm?endpoint=https://acct.r2.cloudflarestorage.com")
    st = objectstore.S3Store(loc, objectstore.Credentials("AKID", "SECRET"),
                             client=httpx.Client(transport=httpx.MockTransport(fake.handler)))
    for i in range(5):
        f = tmp_path / f"f{i}"
        f.write_bytes(b"x" * i)
        st.put(f"catalog/f{i}", f)
    assert sorted(fake.objects) == [f"mm/catalog/f{i}" for i in range(5)]
    listed = st.list("catalog/")
    assert [o.key for o in listed] == [f"catalog/f{i}" for i in range(5)]   # 3 pages, prefix stripped
    assert listed[3].size == 3 and listed[0].modified.tzinfo is not None
    st.get("catalog/f4", tmp_path / "out")
    assert (tmp_path / "out").read_bytes() == b"xxxx"
    st.delete("catalog/f4")
    assert "mm/catalog/f4" not in fake.objects
    with pytest.raises(objectstore.StoreError) as e:
        st.get("catalog/missing", tmp_path / "o2")
    assert "404" in str(e.value) and "NoSuchKey" in str(e.value) and "SECRET" not in str(e.value)


# ---------- Litestream config ----------

def test_user_pattern_matches_auth_ids_only():
    pat = offsite.user_file_pattern()
    assert fnmatch.fnmatchcase(f"{store.new_user_id()}.db", pat)
    for name in (f"{UID}.undo.db", "owner.db", f".{UID}.db.new-1.tmp", f"{UID}.db-wal", f"{UID}.undo.db.pending"):
        assert not fnmatch.fnmatchcase(name, pat), name


def test_litestream_config_replicates_auth_and_users_without_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv(offsite.ENV_KEY_ID, "AKID-should-not-appear")
    monkeypatch.setenv(offsite.ENV_SECRET, "SECRET-should-not-appear")
    url = "s3://bucket/mm?endpoint=https://acct.r2.cloudflarestorage.com"
    text = offsite.litestream_config(tmp_path, url)
    assert "should-not-appear" not in text
    cfg = yaml.safe_load(text)
    assert cfg["snapshot"] == {"interval": "24h", "retention": "720h"}       # 30 days
    assert cfg["l0-retention-check-interval"] == "1h"
    auth, users = cfg["dbs"]
    assert auth["path"] == str(tmp_path.resolve() / "auth.db")
    assert auth["replica"]["url"] == "s3://bucket/mm/auth.db?endpoint=https://acct.r2.cloudflarestorage.com"
    assert users["dir"] == str(tmp_path.resolve() / "users") and users["watch"] is True
    assert users["pattern"] == offsite.user_file_pattern()
    assert users["replica"]["url"] == "s3://bucket/mm/users?endpoint=https://acct.r2.cloudflarestorage.com"
    assert not any("catalog" in str(d) or "analytics" in str(d) for d in cfg["dbs"])
    out = offsite.write_config(tmp_path, url)
    assert stat.S_IMODE(out.stat().st_mode) == 0o600


def test_litestream_gets_credentials_only_through_its_environment(monkeypatch, tmp_path):
    env = offsite.litestream_env(objectstore.Credentials("AKID", "SECRET"),
                                 {"PATH": "/bin", "AWS_SECRET_ACCESS_KEY": "old", offsite.ENV_SECRET: "x"})
    assert env["LITESTREAM_ACCESS_KEY_ID"] == "AKID" and env["LITESTREAM_SECRET_ACCESS_KEY"] == "SECRET"
    assert "AWS_SECRET_ACCESS_KEY" not in env and offsite.ENV_SECRET not in env
    monkeypatch.setenv(offsite.ENV_LITESTREAM, "/opt/litestream")
    argv = offsite.replicate_argv(tmp_path / "litestream.yml")
    assert argv[:2] == ["/opt/litestream", "replicate"] and "-no-expand-env" in argv
    assert not any("SECRET" in a or "AKID" in a for a in argv)


def test_replicate_refuses_a_non_hosted_dir_and_missing_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(offsite.secrets_mod, "_dotenv_get", lambda name: None)
    with pytest.raises(offsite.OffsiteError, match="auth.db"):
        offsite.replicate(tmp_path, "file:///r")
    (tmp_path / "auth.db").touch()
    with pytest.raises(offsite.OffsiteError, match="credentials"):
        offsite.replicate(tmp_path, "s3://b/p?endpoint=https://h.example")


# ---------- catalog snapshot ----------

def test_catalog_backup_uploads_a_restorable_copy_and_keeps_two(owner_split, tmp_path):
    st = objectstore.FileStore(tmp_path / "remote")
    stamps = []
    for day in range(3):
        r = offsite.catalog_backup(owner_split, st, now=datetime(2026, 11, 1 + day, tzinfo=UTC))
        stamps.append(r.key)
        assert r.version == db.CURRENT_VERSION
    assert len(r.kept) == 2 and [k for k in r.deleted if k.endswith(".db.gz")] == [stamps[0]]
    assert not list((owner_split / "bak").glob(".offsite-*"))          # temp files gone
    latest = offsite.latest_catalog(st)
    out = tmp_path / "restored.db"
    offsite.fetch_catalog(st, latest, out)
    assert db._check_integrity(out) == "ok"
    live = offsite.fingerprints(owner_split / "catalog.db")
    assert offsite.fingerprints(out) == live


def test_a_tampered_catalog_snapshot_is_refused(owner_split, tmp_path):
    st = objectstore.FileStore(tmp_path / "remote")
    r = offsite.catalog_backup(owner_split, st)
    (tmp_path / "remote" / r.key).write_bytes(b"not it")
    with pytest.raises(offsite.OffsiteError, match="sha256"):
        offsite.fetch_catalog(st, offsite.latest_catalog(st), tmp_path / "x.db")


# ---------- deleted accounts age out ----------

def _obj(key: str, days_old: float, now: datetime) -> objectstore.Obj:
    return objectstore.Obj(key, 1, now - timedelta(days=days_old))


def test_prune_plan_keeps_known_ids_and_waits_out_retention():
    now = datetime(2026, 11, 1, tzinfo=UTC)
    objs = [_obj(f"users/{UID}.db/ltx/9/a.ltx", 90, now),                 # known: never touched
            _obj(f"users/{OTHER}.db/ltx/9/a.ltx", 40, now),               # deleted 40 days ago
            _obj(f"users/{OTHER}.db/ltx/0/b.ltx", 31, now),
            _obj("users/yyyyyyyyyyyyyyyy.db/ltx/9/a.ltx", 50, now),        # deleted, but written 2 days ago
            _obj("users/yyyyyyyyyyyyyyyy.db/ltx/0/b.ltx", 2, now),
            _obj("auth.db/ltx/9/a.ltx", 400, now), _obj("catalog/catalog-x.db.gz", 400, now)]
    plan = offsite.prune_plan(objs, {UID}, now)
    assert plan.live == [UID]
    assert plan.deleted_ids == {OTHER: [f"users/{OTHER}.db/ltx/0/b.ltx", f"users/{OTHER}.db/ltx/9/a.ltx"]}
    assert list(plan.waiting) == ["yyyyyyyyyyyyyyyy"]


def test_prune_never_runs_blind_and_keeps_accounts_and_local_files(owner_split, tmp_path):
    st = objectstore.FileStore(tmp_path / "remote")
    with pytest.raises(offsite.OffsiteError, match="auth.db"):
        offsite.prune_deleted(owner_split, st, apply=True)
    m = store.redeem_invite(store.create_invite(is_admin=True).code, "discord", "m", "M", None)
    for uid in (m.id, "owner", OTHER):
        f = tmp_path / "remote" / "users" / f"{uid}.db" / "ltx" / "9" / "a.ltx"
        f.parent.mkdir(parents=True)
        f.write_bytes(b"x")
        old = (datetime.now(UTC) - timedelta(days=45)).timestamp()
        os.utime(f, (old, old))
    plan = offsite.prune_deleted(owner_split, st, apply=True)
    assert set(plan.live) == {m.id, "owner"} and list(plan.deleted_ids) == [OTHER]
    assert sorted(o.key.split("/")[1] for o in st.list("users/")) == sorted([f"{m.id}.db", "owner.db"])


# ---------- the laptop's re-pull ----------

def _put_replica(src: Path, root: Path, name: str) -> Path:
    out = root / name / "db"
    out.parent.mkdir(parents=True, exist_ok=True)
    db.backup_file(src, out)
    return out


@pytest.fixture
def remote(owner_split, tmp_path, monkeypatch):
    """A fake offsite store: users/<UID>.db/ (the owner's file, as ``<replica>/db`` — a
    Litestream replica is a directory) + one catalog snapshot. ``offsite.restore`` (the
    Litestream seam) copies from it."""
    root = tmp_path / "remote"
    st = objectstore.FileStore(root)
    _put_replica(owner_split / "users" / "owner.db", root, f"users/{UID}.db")
    offsite.catalog_backup(owner_split, st)
    calls = []

    def fake_restore(replica_url, out, *, creds):
        calls.append(replica_url)
        out = Path(out)
        if out.exists():
            raise offsite.OffsiteError("exists")
        out.parent.mkdir(parents=True, exist_ok=True)
        src = Path(urlsplit(replica_url).path) / "db"
        if not src.is_file():
            raise offsite.OffsiteError("no backup")
        shutil.copy(src, out)
        return {"txid": "1"}

    monkeypatch.setattr(offsite, "restore", fake_restore)
    return f"file://{root}", calls


def test_pull_restores_verifies_and_marks_a_local_copy(remote, tmp_path):
    url, calls = remote
    to = tmp_path / "laptop"
    r = offsite.pull(UID, to, url=url)
    assert calls == [f"{url}/users/{UID}.db"]
    assert r.catalog_source.startswith("remote ") and r.tables["inventory"] == 1
    assert (to / "users" / f"{UID}.db").is_file() and (to / "catalog.db").is_file()
    assert "LOCAL COPY" in (to / offsite.LOCAL_COPY_NOTE).read_text()
    assert stat.S_IMODE((to / "users" / f"{UID}.db").stat().st_mode) == 0o600
    assert not list(to.glob(".pull-*"))
    pair = db._open_split(layout.Layout("split", to / "users" / f"{UID}.db", to / "catalog.db", UID))
    assert pair.execute("SELECT quantity FROM inventory").fetchone()[0] == 2
    pair.close()


def test_pull_refuses_to_overwrite_without_force_then_sets_the_old_copy_aside(remote, tmp_path):
    url, _calls = remote
    to = tmp_path / "laptop"
    offsite.pull(UID, to, url=url)
    before = (to / "users" / f"{UID}.db").read_bytes()
    with pytest.raises(offsite.PullRefused, match="--force"):
        offsite.pull(UID, to, url=url)
    assert (to / "users" / f"{UID}.db").read_bytes() == before
    r = offsite.pull(UID, to, url=url, force=True)
    assert r.replaced and (Path(r.replaced) / "users" / f"{UID}.db").read_bytes() == before
    r2 = offsite.pull(UID, to, url=url, catalog="keep", force=True)
    assert r2.catalog_source == "kept"


def test_pull_refuses_hosted_dirs_bad_ids_and_open_files(remote, tmp_path, monkeypatch):
    url, calls = remote
    hosted = tmp_path / "hosted"
    hosted.mkdir()
    (hosted / "auth.db").touch()
    with pytest.raises(offsite.PullRefused, match="hosted"):
        offsite.pull(UID, hosted, url=url)
    monkeypatch.setenv("MM_MODE", "hosted")
    monkeypatch.setenv("MM_DATA_DIR", str(tmp_path / "live"))
    with pytest.raises(offsite.PullRefused, match="hosted"):
        offsite.pull(UID, tmp_path / "live", url=url)
    monkeypatch.delenv("MM_MODE")
    for bad in ("owner", "../etc/passwd", "ABCDEFGHIJ234567"):
        with pytest.raises(offsite.PullRefused):
            offsite.pull(bad, tmp_path / "x", url=url)
    to = tmp_path / "laptop"
    offsite.pull(UID, to, url=url)
    (to / "users" / f"{UID}.db-wal").touch()
    with pytest.raises(offsite.PullRefused, match="open"):
        offsite.pull(UID, to, url=url, force=True)
    assert calls == [f"{url}/users/{UID}.db"]   # refusals never reached the store


def test_pull_that_doesnt_verify_swaps_nothing_in(remote, tmp_path):
    url, _calls = remote
    replica = Path(urlsplit(url).path) / "users" / f"{UID}.db" / "db"
    raw = sqlite3.connect(replica)
    raw.execute("UPDATE inventory SET quantity = quantity + 5")   # ledger no longer reconciles
    raw.commit()
    raw.close()
    to = tmp_path / "laptop"
    with pytest.raises(offsite.OffsiteError, match="ledger"):
        offsite.pull(UID, to, url=url)
    assert not (to / "users" / f"{UID}.db").exists() and not (to / "catalog.db").exists()
    assert not list(to.glob(".pull-*"))


def test_pull_refuses_a_file_newer_than_this_code(remote, tmp_path):
    url, _calls = remote
    replica = Path(urlsplit(url).path) / "users" / f"{UID}.db" / "db"
    raw = sqlite3.connect(replica)
    raw.execute("UPDATE schema_version SET version = ?", (db.CURRENT_VERSION + 1,))
    raw.commit()
    raw.close()
    with pytest.raises(offsite.OffsiteError, match="git pull"):
        offsite.pull(UID, tmp_path / "laptop", url=url)


def test_cli_pull_exit_codes_and_local_copy_notice(remote, tmp_path):
    url, _calls = remote
    to = tmp_path / "laptop"
    runner = CliRunner()
    ok = runner.invoke(cli_app, ["db", "pull", "--from", url, "--user", UID, "--to", str(to)])
    assert ok.exit_code == 0, ok.output
    assert "LOCAL COPY" in ok.output and f"MM_USER={UID}" in ok.output
    again = runner.invoke(cli_app, ["db", "pull", "--from", url, "--user", UID, "--to", str(to)])
    assert again.exit_code == 2 and "--force" in again.output


def test_restore_all_rebuilds_an_empty_dir_without_deleted_accounts(remote, owner_split, tmp_path):
    url, _calls = remote
    root = Path(urlsplit(url).path)
    m = store.redeem_invite(store.create_invite(is_admin=True).code, "discord", "m", "M", None)
    # the replica holds the owner file under m's id, plus a deleted account's file
    os.replace(root / "users" / f"{UID}.db", root / "users" / f"{m.id}.db")
    _put_replica(owner_split / "users" / "owner.db", root, f"users/{OTHER}.db")
    _put_replica(owner_split / "auth.db", root, "auth.db")
    new = tmp_path / "new-server"
    r = offsite.restore_all(new, url=url)
    assert r.users == [m.id] and r.skipped == [OTHER]
    assert sorted(p.name for p in (new / "users").iterdir()) == [f"{m.id}.db"]
    assert all(db.is_wal(p) for p in hostops.wal_files(new))
    assert stat.S_IMODE(new.stat().st_mode) == 0o700
    with pytest.raises(offsite.PullRefused, match="empty"):
        offsite.restore_all(new, url=url)


# ---------- WAL ----------

def test_wal_is_set_once_and_sticks_through_connect_create_and_snapshots(owner_split, monkeypatch):
    assert not db.is_wal(owner_split / "catalog.db")
    dry = hostops.set_wal(owner_split, apply=False)
    assert {c.after for c in dry} == {"delete"} and not db.is_wal(owner_split / "catalog.db")
    hostops.set_wal(owner_split, apply=True)
    assert all(db.is_wal(p) for p in hostops.wal_files(owner_split))
    inventory.inventory_add(A_ID, "foil", 1)                  # a split connect + write
    assert db.is_wal(owner_split / "users" / "owner.db") and db.is_wal(owner_split / "catalog.db")
    new = userfiles.create(owner_split, UID)                  # a new user in a WAL dir is WAL
    assert db.is_wal(new)
    # a migration snapshot of a WAL file with un-checkpointed commits keeps them
    hold = sqlite3.connect(owner_split / "users" / "owner.db")
    hold.execute("PRAGMA wal_autocheckpoint = 0")
    hold.execute("INSERT INTO settings (key, value) VALUES ('wal-test', '1')")
    hold.commit()
    snap = db.snapshot(src=owner_split / "users" / "owner.db", label="t")
    hold.close()
    got = sqlite3.connect(snap).execute("SELECT value FROM settings WHERE key = 'wal-test'").fetchone()
    assert got == ("1",)


def test_a_user_file_in_a_non_wal_dir_stays_rollback_journal(owner_split):
    assert not db.is_wal(userfiles.create(owner_split, UID))


def test_set_wal_refuses_open_files(owner_split):
    (owner_split / "users" / "owner.db-journal").touch()
    with pytest.raises(hostops.HostOpsError, match="open"):
        hostops.set_wal(owner_split, apply=True)
    assert not db.is_wal(owner_split / "catalog.db")


def test_secure_permissions(owner_split):
    os.chmod(owner_split / "catalog.db", 0o644)
    changes = hostops.secure_permissions(owner_split, apply=True)
    assert any(c.path.endswith("catalog.db") for c in changes)
    for p in [owner_split, *owner_split.rglob("*")]:
        assert stat.S_IMODE(p.stat().st_mode) == (0o700 if p.is_dir() else 0o600), p
    assert hostops.secure_permissions(owner_split, apply=True) == []


# ---------- the split-aware deploy hold ----------

def test_code_version_is_read_from_db_py_text():
    text = (ROOT / "src" / "magic_manager" / "db.py").read_text()
    assert hostops.code_version_from_source(text) == db.CURRENT_VERSION
    assert hostops.code_version_at("HEAD", ROOT) >= db.SPLIT_BASE_VERSION
    with pytest.raises(hostops.HostOpsError):
        hostops.code_version_from_source("nothing here")


@pytest.mark.parametrize("versions,hold,behind", [
    ({"catalog": 37, "users/a": 37}, False, set()),
    ({"catalog": 36, "users/a": 37}, True, {"catalog"}),            # the catalog alone
    ({"catalog": 37, "users/a": 37, "users/b": 36}, True, {"users/b"}),   # any one user file
    ({"catalog": 37, "users/a": None}, True, {"users/a"}),          # unreadable = unknown = hold
    ({"users/a": 37}, True, {"catalog"}),                           # no catalog at all
])
def test_hold_decision(versions, hold, behind):
    d = hostops.hold_decision(37, versions)
    assert d.hold is hold and set(d.behind) == behind
    assert d.message.startswith("HOLD") is hold


def test_hold_when_files_are_newer_than_the_code():
    d = hostops.hold_decision(37, {"catalog": 38, "users/a": 37})
    assert d.hold and d.ahead == {"catalog": 38} and "NEWER" in d.message


def test_cli_deploy_check_exit_codes(owner_split):
    runner = CliRunner()
    ok = runner.invoke(cli_app, ["host", "deploy-check", "--ref", "HEAD", "--repo", str(ROOT), "--data-dir", str(owner_split)])
    assert ok.exit_code == 0, ok.output
    raw = sqlite3.connect(owner_split / "users" / "owner.db")
    raw.execute("UPDATE schema_version SET version = version - 1")
    raw.commit()
    raw.close()
    held = runner.invoke(cli_app, ["host", "deploy-check", "--ref", "HEAD", "--repo", str(ROOT), "--data-dir", str(owner_split)])
    assert held.exit_code == 3 and "HOLD" in held.output and "users/owner" in held.output
    bad = runner.invoke(cli_app, ["host", "deploy-check", "--ref", "no-such-ref", "--repo", str(ROOT), "--data-dir", str(owner_split)])
    assert bad.exit_code == 2


# ---------- Litestream's own tables and local state ----------

def test_export_drops_litestreams_bookkeeping_tables(owner_split):
    raw = sqlite3.connect(owner_split / "users" / "owner.db")
    raw.execute("CREATE TABLE _litestream_seq (id INTEGER PRIMARY KEY, seq INTEGER)")
    raw.execute("CREATE TABLE _litestream_lock (id INTEGER)")
    raw.commit()
    raw.close()
    e = account.export()
    assert not any(t.startswith("_litestream") for t in e.tables) and e.tables["inventory"] == 1


def test_account_file_removal_includes_litestream_state_of_that_user_only(tmp_path):
    users = tmp_path / "users"
    for uid in (UID, OTHER):
        (users / f".{uid}.db-litestream" / "ltx" / "0").mkdir(parents=True)
        (users / f".{uid}.db-litestream" / "ltx" / "0" / "1.ltx").write_bytes(b"data")
        (users / f"{uid}.db").write_bytes(b"x")
    removed = userfiles.remove_user_files(tmp_path, UID)
    assert users / f".{UID}.db-litestream" in removed and not (users / f".{UID}.db-litestream").exists()
    assert (users / f".{OTHER}.db-litestream").is_dir() and (users / f"{OTHER}.db").exists()
    with pytest.raises(layout.LayoutError):
        userfiles.litestream_dirs(tmp_path, "../x")


def test_fingerprints_ignore_litestream_tables(owner_split):
    before = offsite.fingerprints(owner_split / "users" / "owner.db")
    raw = sqlite3.connect(owner_split / "users" / "owner.db")
    raw.execute("CREATE TABLE _litestream_seq (id INTEGER PRIMARY KEY, seq INTEGER)")
    raw.execute("INSERT INTO _litestream_seq VALUES (1, 9)")
    raw.commit()
    raw.close()
    assert offsite.fingerprints(owner_split / "users" / "owner.db") == before
    assert set(before) >= set(layout.USER_TABLES)


# ---------- the deploy kit (deploy/macos) ----------

SCRIPTS = sorted([*KIT.glob("*.sh"), *(KIT / "bin").iterdir()])


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_kit_scripts_parse(script):
    assert subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0
    assert os.access(script, os.X_OK), f"{script} isn't executable"


@pytest.mark.skipif(not shutil.which("shellcheck"), reason="shellcheck not installed")
def test_kit_scripts_pass_shellcheck():
    r = subprocess.run(["shellcheck", "-x", *map(str, SCRIPTS)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout


def _install(tmp_path, *args, env=None):
    base = {"HOME": str(tmp_path / "home"), "PATH": os.environ["PATH"], **(env or {})}
    return subprocess.run(["bash", str(KIT / "install.sh"), "--origin", "https://mini.example.ts.net",
                           "--data", str(tmp_path / "data"), "--kit", str(tmp_path / "kit dir"),
                           "--logs", str(tmp_path / "logs"), "--launch-agents", str(tmp_path / "agents"), *args],
                          capture_output=True, text=True, env=base)


def test_installer_dry_run_writes_nothing(tmp_path):
    r = _install(tmp_path)
    assert r.returncode == 0, r.stderr
    assert "Dry run — nothing was written" in r.stdout and "MM_LAYOUT=split" in r.stdout
    assert not any(tmp_path.iterdir())


@pytest.mark.parametrize("args,err", [
    (["--origin", "http://mini.example"], "--origin must be"),
    (["--port", "80"], "--port"),
    (["--owner-id", "OWNER"], "--owner-id"),
    (["--data", str(ROOT / "data")], "outside the app checkout"),
    (["--kit", "relative/kit"], "absolute"),
    (["--logs", "/x/$(id)"], "unsupported character"),
    (["--trusted-proxy", "nginx"], "--trusted-proxy"),
])
def test_installer_refuses_bad_settings(tmp_path, args, err):
    r = _install(tmp_path, *args)
    assert r.returncode == 2 and err in r.stderr


@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("gpg"), reason="--apply is macOS-only and needs gpg")
def test_installer_apply_is_private_idempotent_and_never_touches_other_agents(tmp_path):
    kit = tmp_path / "kit dir"
    (kit / "bin").mkdir(parents=True)
    fake = kit / "bin" / "litestream"
    fake.write_text(f"#!/bin/sh\necho {offsite.LITESTREAM_VERSION}\n")
    fake.chmod(0o755)
    env = {"MM_INSTALL_NO_LAUNCHCTL": "1"}
    r = _install(tmp_path, "--apply", "--owner-id", UID, "--trusted-proxy", "tailscale", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    keyring = kit / "gnupg"
    assert stat.S_IMODE(keyring.stat().st_mode) == 0o700
    fprs = subprocess.run(["gpg", "--batch", "--with-colons", "--fingerprint"], capture_output=True, text=True,
                          env={**os.environ, "GNUPGHOME": str(keyring)}).stdout
    assert "fpr:::::::::968479A1AFF927E37D1A566BB5690EEEBB952194:" in fprs
    agents = sorted(p.name for p in (tmp_path / "agents").iterdir())
    assert agents == [f"com.magic-manager.hosted.{s}.plist" for s in ("catalog-backup", "deploy", "litestream", "serve")]
    for p in (tmp_path / "agents").iterdir():
        plist = plistlib.loads(p.read_bytes())
        assert plist["Umask"] == 0o077 and str(kit) in plist["ProgramArguments"][1]
        assert plist["Label"] not in ("com.magic-manager.serve", "com.magic-manager.deploy", "com.magic-manager.scrape-canary")
    henv = (kit / "hosted.env").read_text()
    assert stat.S_IMODE((kit / "hosted.env").stat().st_mode) == 0o600
    assert f"MM_OWNER_ID={UID}" in henv
    assert "MM_TRUSTED_PROXY=tailscale" in henv
    assert not any(k in henv for k in ("MM_OAUTH", "MM_OFFSITE", "ACCESS_KEY", "MANAPOOL", "MM_ANALYTICS_SECRET"))
    assert stat.S_IMODE((tmp_path / "data").stat().st_mode) == 0o700 and not any((tmp_path / "data").iterdir())
    assert stat.S_IMODE((kit / "deploy.sh").stat().st_mode) == 0o700
    again = _install(tmp_path, "--apply", "--owner-id", UID, "--trusted-proxy", "tailscale", env=env)
    assert again.returncode == 0 and "(new)" not in again.stdout and "(changed)" not in again.stdout
    assert not (kit / ".install-stage").exists()


def test_launchd_templates_are_valid_and_private(tmp_path):
    for t in (KIT / "launchd").glob("*.plist.in"):
        text = t.read_text().replace("@KIT@", "/k").replace("@LOGS@", "/l")
        plist = plistlib.loads(text.encode())
        assert plist["Label"] == f"com.magic-manager.hosted.{t.name.removesuffix('.plist.in')}"
        assert plist["Umask"] == 0o077
        assert "@" not in text


# ---------- review follow-ups ----------

@pytest.mark.parametrize("tail", ["    SCHEMA_V38,  # user: add x\n", "    SCHEMA_V38\n", "    SCHEMA_EXTRA,\n"])
def test_code_version_counts_every_migrations_element(tail):
    text = (ROOT / "src" / "magic_manager" / "db.py").read_text()
    head, sep, rest = text.partition("\n]\nCURRENT_VERSION = len(MIGRATIONS)")
    assert sep
    if not head.endswith(","):
        head += ","
    assert hostops.code_version_from_source(head + "\n" + tail + sep + rest) == db.CURRENT_VERSION + 1


def test_code_version_fails_closed_when_db_py_changes_shape():
    text = (ROOT / "src" / "magic_manager" / "db.py").read_text()
    with pytest.raises(hostops.HostOpsError, match="CURRENT_VERSION"):
        hostops.code_version_from_source(text.replace("CURRENT_VERSION = len(MIGRATIONS)", "CURRENT_VERSION = 37"))
    with pytest.raises(hostops.HostOpsError, match="parse"):
        hostops.code_version_from_source("MIGRATIONS = [")


def test_litestream_version_is_pinned_the_same_everywhere():
    import re
    install = (KIT / "install.sh").read_text()
    docker = (ROOT / "Dockerfile").read_text()
    assert re.search(r"^LITESTREAM_VERSION=(\S+)$", install, re.M).group(1) == offsite.LITESTREAM_VERSION
    assert re.search(r"^ARG LITESTREAM_VERSION=(\S+)$", docker, re.M).group(1) == offsite.LITESTREAM_VERSION


def _replica_file(url: str, name: str) -> Path:
    return Path(urlsplit(url).path) / name / "db"


def test_verify_replicas_passes_on_equal_and_names_what_differs(remote, owner_split, tmp_path, monkeypatch):
    url, _calls = remote
    root = Path(urlsplit(url).path)
    data = owner_split
    m = store.redeem_invite(store.create_invite(is_admin=True).code, "discord", "m", "M", None)
    userfiles.bind_file(data, m.id)                           # owner.db → users/<m>.db
    os.replace(root / "users" / f"{UID}.db", root / "users" / f"{m.id}.db")
    _put_replica(data / "auth.db", root, "auth.db")
    ok = offsite.verify_replicas(data, url)
    assert ok.ok and [f.name for f in ok.files] == ["auth.db", f"users/{m.id}.db"]
    raw = sqlite3.connect(_replica_file(url, f"users/{m.id}.db"))
    raw.execute("INSERT INTO settings (key, value) VALUES ('drift', '1')")
    raw.commit()
    raw.close()
    bad = offsite.verify_replicas(data, url)
    user = bad.files[1]
    assert not bad.ok and not user.ok and "settings" in user.detail
    runner = CliRunner()
    r = runner.invoke(cli_app, ["host", "verify-replica", "--data-dir", str(data)], env={"MM_OFFSITE_URL": url})
    assert r.exit_code == 1 and "REPLICA CHECK FAILED" in r.output
    shutil.rmtree(root / "auth.db")
    missing = offsite.verify_replicas(data, url)
    assert not missing.files[0].ok and "no backup" in missing.files[0].detail
    assert not list((data / "bak").glob(".verify-*"))


def test_pull_keep_refuses_an_older_local_catalog(remote, tmp_path):
    url, _calls = remote
    to = tmp_path / "laptop"
    offsite.pull(UID, to, url=url)
    raw = sqlite3.connect(to / "catalog.db")
    raw.execute("UPDATE schema_version SET version = version - 1")
    raw.commit()
    raw.close()
    before = (to / "users" / f"{UID}.db").read_bytes()
    with pytest.raises(offsite.OffsiteError, match="--catalog remote"):
        offsite.pull(UID, to, url=url, catalog="keep", force=True)
    assert (to / "users" / f"{UID}.db").read_bytes() == before


def test_forced_pulls_in_the_same_second_keep_every_set_aside_copy(remote, tmp_path):
    url, _calls = remote
    to = tmp_path / "laptop"
    when = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
    offsite.pull(UID, to, url=url, now=when)
    first = (to / "users" / f"{UID}.db").read_bytes()
    r1 = offsite.pull(UID, to, url=url, force=True, now=when)
    r2 = offsite.pull(UID, to, url=url, force=True, now=when)
    assert r1.replaced != r2.replaced
    assert (Path(r1.replaced) / "users" / f"{UID}.db").read_bytes() == first


def test_pull_warns_but_succeeds_when_the_snapshot_predates_a_card(remote, tmp_path):
    url, _calls = remote
    raw = sqlite3.connect(_replica_file(url, f"users/{UID}.db"))
    raw.execute("INSERT INTO wishlist_entries (scryfall_id, finish, category, qty_wanted, added_at) "
                "VALUES ('11111111-1111-1111-1111-111111111111', 'nonfoil', 'later', 1, '2026-11-01')")
    raw.commit()
    raw.close()
    r = offsite.pull(UID, tmp_path / "laptop", url=url)
    assert r.warnings and "catalog-refs" in r.warnings[0] and "mm set sync" in r.warnings[0]


def test_restore_all_lists_accounts_with_no_offsite_copy(remote, owner_split, tmp_path):
    url, _calls = remote
    root = Path(urlsplit(url).path)
    m = store.redeem_invite(store.create_invite(is_admin=True).code, "discord", "m", "M", None)
    shutil.rmtree(root / "users" / f"{UID}.db")
    _put_replica(owner_split / "auth.db", root, "auth.db")
    r = offsite.restore_all(tmp_path / "new", url=url)
    assert r.users == [] and r.missing == [m.id]


def test_prune_dry_run_leaves_the_store_untouched(owner_split, tmp_path):
    st = objectstore.FileStore(tmp_path / "remote")
    f = tmp_path / "remote" / "users" / f"{OTHER}.db" / "ltx" / "9" / "a.ltx"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"x")
    old = (datetime.now(UTC) - timedelta(days=45)).timestamp()
    os.utime(f, (old, old))
    store.create_invite(is_admin=True)   # makes auth.db
    plan = offsite.prune_deleted(owner_split, st, apply=False)
    assert list(plan.deleted_ids) == [OTHER] and f.exists()


def test_stale_deploy_lock_is_taken_over_and_a_live_one_is_obeyed(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    shutil.copy(KIT / "bin" / "common.sh", kit / "common.sh")
    (kit / "hosted.env").write_text(f"export MM_KIT={kit}\n")
    script = f'. "{kit}/common.sh"; take_lock && echo TOOK || echo SKIPPED'
    (kit / "deploy.lock").mkdir()
    (kit / "deploy.lock" / "pid").write_text("999999\n")      # no such process
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert "TOOK" in r.stdout and "stale" in r.stdout and not (kit / "deploy.lock").exists()
    (kit / "deploy.lock").mkdir()
    (kit / "deploy.lock" / "pid").write_text(f"{os.getpid()}\n")  # alive
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert "SKIPPED" in r.stdout and (kit / "deploy.lock").exists()
