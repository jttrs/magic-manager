"""Phase 3 step 7 (§25.1 H10): download my data (both modes) and delete my account
(hosted) — ``magic_manager.account``, ``/api/account/*`` and the CLI twins."""
from __future__ import annotations

import csv
import hashlib
import io
import sqlite3
import zipfile
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from magic_manager import account, db, decks, inventory, layout, split, undo, userfiles, wishlist
from magic_manager.analytics import identity
from magic_manager.analytics import store as analytics_store
from magic_manager.auth import store
from magic_manager.cli import app as cli_app
from magic_manager.web import account_routes, auth_routes
from magic_manager.web.runtime import JobRecord

from test_auth import ORIGIN, hosted, me, provider, sign_in  # noqa: F401 — fixtures

A_ID = "00000000-0000-0000-0000-00000000000a"
B_ID = "00000000-0000-0000-0000-00000000000b"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _unzip(data: bytes) -> dict[str, bytes]:
    z = zipfile.ZipFile(io.BytesIO(data))
    assert z.testzip() is None
    return {n.split("/", 1)[1]: z.read(n) for n in z.namelist()}


def _db_of(files: dict[str, bytes]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.deserialize(files[account.DB_NAME])
    return conn


def _rows(text: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text.decode("utf-8"))))


def _counts(conn: sqlite3.Connection, schema: str = "main") -> dict[str, int]:
    names = [r[0] for r in conn.execute(f"SELECT name FROM {schema}.sqlite_master WHERE type='table'")]
    return {n: conn.execute(f'SELECT COUNT(*) FROM {schema}."{n}"').fetchone()[0]
            for n in names if n in layout.USER_TABLES}


@pytest.fixture
def collection(tmp_db, seed_cards, make_card):
    """A single-file collection: 2 cards (one named like a formula), inventory, a deck, a wishlist row."""
    seed_cards([make_card(id=A_ID, name="Alpha"), make_card(id=B_ID, name="=HYPERLINK(1)", collector_number="2")])
    inventory.inventory_add(A_ID, "nonfoil", 2)
    inventory.inventory_add(B_ID, "foil", 1)
    decks.deck_create("owners-deck", "Owner's deck")
    decks.deck_add_card("owners-deck", A_ID, "main", "nonfoil", 1)
    wishlist.wishlist_add(B_ID, "nonfoil", "later", 3)
    return tmp_db


# ---------- export: local single layout ----------

def test_local_export_holds_only_the_user_tables_and_readable_csvs(collection):
    out = account.export()
    files = _unzip(out.data)
    assert set(files) == {"README.txt", account.DB_NAME, *(s.file for s in account.SHEETS)}
    assert out.filename.startswith("magic-manager-export-") and out.layout == "single"
    copy = _db_of(files)
    tables = {r[0] for r in copy.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables <= set(layout.USER_TABLES) | layout.INFRA_TABLES and "cards" not in tables
    assert "edhrec_pages" not in tables and "catalog_settings" not in tables
    # row counts equal the live DB's user tables, table by table
    with db.connect() as live:
        assert _counts(copy) == _counts(live) == out.tables
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    inv = _rows(files["inventory.csv"])
    assert {(r["name"], r["finish"], r["quantity"]) for r in inv} == {("Alpha", "nonfoil", "2"), ("'=HYPERLINK(1)", "foil", "1")}
    # the .db keeps exact values; only the CSV text cell is defused
    assert copy.execute("SELECT COUNT(*) FROM inventory").fetchone()[0] == 2
    deck = _rows(files["deck_cards.csv"])
    assert [(r["deck"], r["name"], r["quantity"]) for r in deck] == [("owners-deck", "Alpha", "1")]
    assert _rows(files["wishlist.csv"])[0]["category"] == "later"
    assert len(_rows(files["ledger.csv"])) == 2 and len(_rows(files["history.csv"])) >= 2
    readme = files["README.txt"].decode()
    assert "inventory" in readme and "Not included" in readme


def test_local_export_copy_is_the_splitters_user_file(collection, tmp_path):
    """DRY: the single-layout copy is exactly what ``mm db split`` writes for the user."""
    split.split(collection, tmp_path / "data")
    user_file = tmp_path / "data" / "users" / "owner.db"
    copy = _db_of(_unzip(account.export().data))
    copy.execute("ATTACH DATABASE ? AS s", (str(user_file),))
    for t in layout.USER_TABLES:
        assert split._table_hash(copy, "main", t) == split._table_hash(copy, "s", t), t


def test_cli_export_writes_once_then_needs_force(collection, tmp_path):
    runner = CliRunner()
    dest = tmp_path / "mine.zip"
    r = runner.invoke(cli_app, ["account", "export", "--to", str(dest), "--json"])
    assert r.exit_code == 0, r.output
    assert _unzip(dest.read_bytes())[account.DB_NAME]
    assert oct(dest.stat().st_mode & 0o777) == "0o600"
    r = runner.invoke(cli_app, ["account", "export", "--to", str(dest)])
    assert r.exit_code == 2 and "--force" in r.output
    assert runner.invoke(cli_app, ["account", "export", "--to", str(dest), "--force"]).exit_code == 0
    r = runner.invoke(cli_app, ["account", "export", "--to", str(tmp_path)])
    assert r.exit_code == 0 and list(tmp_path.glob("magic-manager-export-*.zip"))
    assert not list(tmp_path.glob(".*.partial"))


# ---------- export: split layout ----------

@pytest.fixture
def two_users(collection, request):
    """The owner's split file + member M's own file with different data."""
    data = request.getfixturevalue("split_dir")
    m = store.redeem_invite(store.create_invite(is_admin=False).code, "discord", "m", "M", None)
    userfiles.create(data, m.id)
    with layout.as_user(m.id):
        inventory.inventory_add(B_ID, "nonfoil", 7)
    return data, m.id


def test_split_export_is_the_bound_users_file_only(two_users):
    data, m = two_users
    with layout.as_user(m):
        files = _unzip(account.export().data)
    copy = _db_of(files)
    copy.execute("ATTACH DATABASE ? AS f", (str(data / "users" / f"{m}.db"),))
    for t in layout.USER_TABLES:
        assert split._table_hash(copy, "main", t) == split._table_hash(copy, "f", t), t
    assert [(r["scryfall_id"], r["quantity"]) for r in _rows(files["inventory.csv"])] == [(B_ID, "7")]
    assert _rows(files["decks.csv"]) == []  # the owner's deck is not in it
    # the owner (MM_USER default) gets theirs
    owner = _db_of(_unzip(account.export().data))
    assert owner.execute("SELECT COUNT(*) FROM decks").fetchone()[0] == 1


def test_hosted_export_fails_closed_without_a_bound_user(two_users):
    layout.set_strict(True)
    try:
        with pytest.raises(layout.NoUserBound):
            account.export()
    finally:
        layout.set_strict(False)


def test_an_empty_profile_exports_valid_empty_files(two_users):
    data, _m = two_users
    fresh = store.redeem_invite(store.create_invite(is_admin=False).code, "discord", "e", "E", None)
    userfiles.create(data, fresh.id)
    with layout.as_user(fresh.id):
        out = account.export()
    files = _unzip(out.data)
    assert set(out.tables.values()) == {0}
    assert _db_of(files).execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    for s in account.SHEETS:
        assert files[s.file].decode().count("\r\n") == 1  # the header only


# ---------- delete ----------

def _artifacts(data: Path, uid: str) -> list[Path]:
    """Every kind of file a user's data can be in, created for the test."""
    users = data / "users"
    made = [users / f"{uid}.db-wal", users / f"{uid}.undo.db", users / f"{uid}.undo.db.pending",
            users / "bak" / f"{uid}.db.bak-2026-01-01-000000-pre-v38",
            data / "bak" / "split.bak-2026-01-01-000000" / "users" / f"{uid}.db",
            data / "replaced" / "users.replaced-20260101T000000Z" / f"{uid}.db",
            data / "replaced" / "split.replaced-2026-01-01-000000" / "users" / f"{uid}.undo.db"]
    for p in made:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    return [users / f"{uid}.db", *made]


def _everything_else(data: Path, keep: set[Path]) -> dict[str, str]:
    return {str(p.relative_to(data)): _sha(p) for p in sorted(data.rglob("*")) if p.is_file() and p not in keep}


@pytest.fixture
def admins_and_member(two_users):
    data, m = two_users
    a = store.redeem_invite(store.create_invite(is_admin=True).code, "discord", "a", "A", None)
    return data, a.id, m


def test_delete_removes_files_auth_rows_and_analytics_of_that_user_only(admins_and_member, monkeypatch):
    data, a, m = admins_and_member
    mine = _artifacts(data, m)
    _artifacts(data, a)
    other = store.redeem_invite(store.create_invite(is_admin=False).code, "google", "o", "O", None)
    # invites M made: one unused (deleted), one used by O-like user (unlinked)
    unused = store.create_invite(is_admin=False, created_by=m)
    used = store.create_invite(is_admin=False, created_by=m)
    store.redeem_invite(used.code, "discord", "z", "Z", None)
    store.set_override(m, "deals", True, set_by=a)
    store.set_override(other.id, "deals", True, set_by=m)
    store.create_session(m)
    with analytics_store.connect() as conn:
        for uid in (m, a):
            conn.execute("INSERT INTO events (event_id, name, version, category, source, ts, ts_ms, day, week, user_key) "
                         "VALUES (?, 'api.error', 1, 'error', 'server', '2026-11-01T00:00:00Z', 0, '2026-11-01', "
                         "'2026-W44', ?)", (uid, identity.user_key(uid)))
    keep = set(mine)
    before = _everything_else(data, keep)

    out = account.delete_account(m, data_dir=data)

    assert out.sessions_ended == 1 and out.user_row and out.identities == 1
    assert out.analytics_events == 1 and out.invites_deleted >= 1 and out.invites_unlinked == 1
    assert sorted(out.files) == sorted(str(p.relative_to(data)) for p in mine)
    assert not any(p.exists() for p in mine)
    assert _everything_else(data, keep) == before  # A's files and the catalog are untouched
    assert store.get_user(m) is None and store.get_user(a) is not None
    with store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM invites WHERE created_by = ? OR used_by = ?", (m, m)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM invites WHERE code_hash = ?", (store.hash_secret(unused.code),)).fetchone()[0] == 0
        assert conn.execute("SELECT used_by FROM invites WHERE code_hash = ?", (store.hash_secret(used.code),)).fetchone()[0]
        assert conn.execute("SELECT COUNT(*) FROM feature_overrides WHERE user_id = ? OR set_by = ?", (m, m)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (m,)).fetchone()[0] == 0
    assert store.overrides(other.id) == {"deals": True}
    with analytics_store.connect() as conn:
        assert [r[0] for r in conn.execute("SELECT user_key FROM events")] == [identity.user_key(a)]


def test_delete_is_idempotent_and_finishes_a_half_done_delete(admins_and_member, monkeypatch):
    data, a, m = admins_and_member
    mine = _artifacts(data, m)
    boom = RuntimeError("power cut")

    def crash(_key):
        raise boom
    with monkeypatch.context() as mp:
        mp.setattr(analytics_store, "forget", crash)
        with pytest.raises(RuntimeError):
            account.delete_account(m, data_dir=data)
    # step 1 + 2 done: signed out + disabled, files gone; the auth row is still there
    u = store.get_user(m)
    assert u is not None and u.disabled and not any(p.exists() for p in mine)
    r = CliRunner().invoke(cli_app, ["auth", "delete-user", m, "--yes", "--json"])
    assert r.exit_code == 0, r.output
    assert store.get_user(m) is None
    again = account.delete_account(m, data_dir=data)
    assert again.sessions_ended is None and again.files == [] and not again.user_row


def test_last_admin_cant_be_deleted(admins_and_member):
    data, a, m = admins_and_member
    with pytest.raises(account.LastAdmin) as e:
        account.delete_account(a, data_dir=data)
    assert e.value.error_code == "auth.last_admin"
    assert store.get_user(a) is not None
    r = CliRunner().invoke(cli_app, ["auth", "delete-user", a, "--yes"])
    assert r.exit_code == 2 and "only admin" in r.output
    second = store.redeem_invite(store.create_invite(is_admin=True).code, "google", "b", "B", None)
    store.revoke(second.id, disable=True)  # a disabled admin doesn't count
    with pytest.raises(account.LastAdmin):
        account.delete_account(a, data_dir=data)
    store.enable(second.id)
    assert account.delete_account(a, data_dir=data).user_row


def test_cli_delete_refuses_without_yes_bad_ids_and_open_files(admins_and_member, monkeypatch):
    data, a, m = admins_and_member
    runner = CliRunner()
    monkeypatch.setenv("MM_NONINTERACTIVE", "1")
    r = runner.invoke(cli_app, ["auth", "delete-user", m])
    assert r.exit_code == 2 and "--yes" in r.output and store.get_user(m) is not None
    assert runner.invoke(cli_app, ["auth", "delete-user", "../owner", "--yes"]).exit_code == 2
    (data / "users" / f"{m}.db-wal").write_bytes(b"")
    r = runner.invoke(cli_app, ["auth", "delete-user", m, "--yes"])
    assert r.exit_code == 2 and "looks open" in r.output
    assert runner.invoke(cli_app, ["auth", "delete-user", m, "--yes", "--force"]).exit_code == 0
    assert store.get_user(m) is None and not (data / "users" / f"{m}.db").exists()


def test_user_artifacts_never_match_another_user_or_a_bad_id(tmp_path):
    data = tmp_path
    for name in ("aaaaaaaaaaaaaaaa.db", "aaaaaaaaaaaaaaaab.db", "aaaaaaaaaaaaaaaa.dbx", "xaaaaaaaaaaaaaaaa.db"):
        (data / "users").mkdir(exist_ok=True)
        (data / "users" / name).write_bytes(b"")
    (data / "catalog.db").write_bytes(b"")
    got = [p.name for p in userfiles.user_artifacts(data, "aaaaaaaaaaaaaaaa")]
    assert got == ["aaaaaaaaaaaaaaaa.db"]
    with pytest.raises(layout.LayoutError):
        userfiles.user_artifacts(data, "../etc")


# ---------- routes ----------

@pytest.fixture
def web(collection, hosted, provider):
    """Admin A + member M signed in on one hosted app."""
    ca = TestClient(hosted, base_url=ORIGIN)
    sign_in(ca, provider, "discord", invite=store.create_invite(is_admin=True).code)
    provider.discord_user = {"id": "d-2", "username": "m", "global_name": "Member", "verified": True}
    cm = TestClient(hosted, base_url=ORIGIN)
    sign_in(cm, provider, "discord", invite=store.create_invite(is_admin=False).code)
    a, m = me(ca)["user"]["id"], me(cm)["user"]["id"]
    with layout.as_user(m):
        inventory.inventory_add(B_ID, "foil", 4)
    account_routes.export_limiter.reset()
    return (ca, {"Origin": ORIGIN, "X-CSRF-Token": me(ca)["csrf_token"]}, a), \
           (cm, {"Origin": ORIGIN, "X-CSRF-Token": me(cm)["csrf_token"]}, m)


def test_export_route_streams_the_signed_in_users_zip(web, split_dir):
    (ca, _ha, a), (cm, _hm, m) = web
    r = cm.get("/api/account/export", headers={"Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert "attachment" in r.headers["content-disposition"] and r.headers["cache-control"] == "no-store"
    files = _unzip(r.content)
    assert [(x["scryfall_id"], x["quantity"]) for x in _rows(files["inventory.csv"])] == [(B_ID, "4")]
    assert _db_of(files).execute("SELECT COUNT(*) FROM decks").fetchone()[0] == 0
    # cross-site: refused; signed out: 401
    r = cm.get("/api/account/export", headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403 and r.json()["code"] == "request.cross_site"
    assert TestClient(ca.app, base_url=ORIGIN).get("/api/account/export").json()["code"] == "auth.required"
    assert not list(split_dir.rglob("*.partial")) and not list(split_dir.rglob("*.tmp"))


def test_export_route_is_rate_limited(web, monkeypatch):
    _a, (cm, _hm, _m) = web
    monkeypatch.setattr(account_routes, "export_limiter", account_routes.ratelimit.Limiter(1))
    assert cm.get("/api/account/export").status_code == 200
    r = cm.get("/api/account/export")
    assert r.status_code == 429 and r.json()["code"] == "auth.rate_limited"


def _delete(c, headers, text=account.DELETE_CONFIRMATION):
    return c.post("/api/account/delete", headers=headers, json={"confirm": text})


def test_delete_route_checks_csrf_reauth_confirmation_and_jobs(web, split_dir, monkeypatch):
    (ca, ha, a), (cm, hm, m) = web
    a_file = split_dir / "users" / f"{a}.db"
    a_sha = _sha(a_file)
    assert _delete(cm, {"Origin": ORIGIN}).json()["code"] == "auth.csrf"
    assert _delete(cm, {"X-CSRF-Token": hm["X-CSRF-Token"]}).json()["code"] == "auth.origin"
    r = cm.post("/api/account/delete", headers=hm, json={"confirm": account.DELETE_CONFIRMATION, "user_id": a})
    assert r.status_code == 422  # no other fields: the user is never taken from the request
    r = _delete(cm, hm, "delete")
    assert r.status_code == 422 and r.json()["code"] == "account.confirm"
    # a running job of M's
    jobs = cm.app.state.jobs
    jobs._jobs["j1"] = JobRecord(id="j1", name="x", title="Read prices", inputs={}, status="running", user=m)
    r = _delete(cm, hm)
    assert r.status_code == 409 and r.json()["code"] == "account.jobs_running" and "Read prices" in r.json()["detail"]["message"]
    jobs._jobs["j1"].status = "succeeded"
    # stale sign-in: 11 minutes later
    real_now = store._now
    monkeypatch.setattr(store, "_now", lambda: real_now() + timedelta(minutes=11))
    r = _delete(cm, hm)
    assert r.status_code == 403 and r.json()["code"] == "auth.reauth_required"
    monkeypatch.setattr(store, "_now", real_now)
    assert store.get_user(m) is not None and (split_dir / "users" / f"{m}.db").exists()
    # fresh + confirmed: deleted, signed out, A untouched
    r = _delete(cm, hm, "  Delete My  Account ")
    assert r.status_code == 200 and r.json()["deleted"] is True
    assert "mm_session=" in r.headers.get("set-cookie", "")
    assert store.get_user(m) is None and not (split_dir / "users" / f"{m}.db").exists()
    assert cm.get("/api/undo").json()["code"] == "auth.required"
    assert _sha(a_file) == a_sha and store.get_user(a) is not None
    assert ca.get("/api/undo").status_code == 200


def test_delete_route_refuses_the_last_admin(web, split_dir):
    (ca, ha, a), _m = web
    r = _delete(ca, ha)
    assert r.status_code == 409 and r.json()["code"] == "auth.last_admin"
    assert store.get_user(a) is not None and (split_dir / "users" / f"{a}.db").exists()


def test_a_job_cant_start_while_the_account_is_being_deleted(web):
    _a, (cm, hm, m) = web
    with cm.app.state.jobs.closing_user(m), layout.as_user(m):
        r = cm.post("/api/jobs/scryfall.sync_tags", headers=hm, json={})
    assert r.status_code == 409 and "deleting your account" in r.json()["detail"]


def test_local_mode_has_export_but_no_delete(collection):
    from magic_manager.web.app import create_app
    c = TestClient(create_app(serve_frontend=False))
    r = c.get("/api/account/export")
    assert r.status_code == 200 and _unzip(r.content)[account.DB_NAME]
    assert c.post("/api/account/delete", json={"confirm": account.DELETE_CONFIRMATION}).status_code in (404, 405)


def test_reauth_window_is_ten_minutes():
    u = store.redeem_invite(store.create_invite(is_admin=True).code, "discord", "1", "U", None)
    new = store.create_session(u.id)
    s = store.session_for(new.token)
    assert s.fresh() and store.REAUTH_WINDOW == timedelta(minutes=10)
    assert not store.Session(s.user, s.csrf_token, s.token_hash).fresh()  # unknown age: not fresh
    assert undo  # imported for the guards used by the route


# ---------- review follow-ups ----------

def test_export_refuses_a_copy_holding_a_non_user_table(two_users):
    """The split copy is the whole user file: a stray (e.g. catalog) table in it must stop the export."""
    data, m = two_users
    f = data / "users" / f"{m}.db"
    raw = sqlite3.connect(f)
    raw.execute("CREATE TABLE cards (x)")
    raw.commit()
    raw.close()
    with layout.as_user(m), pytest.raises(account.ExportFailed, match="cards"):
        account.export()


def test_export_route_codes_a_failed_export(web, split_dir):
    _a, (cm, _hm, m) = web
    raw = sqlite3.connect(split_dir / "users" / f"{m}.db")
    raw.execute("CREATE TABLE edhrec_pages (x)")
    raw.commit()
    raw.close()
    r = cm.get("/api/account/export")
    assert r.status_code == 500 and r.json()["code"] == "account.export_failed"


def test_last_admin_is_checked_inside_the_closing_transaction(admins_and_member):
    data, a, m = admins_and_member
    with pytest.raises(store.LastAdmin):
        store.close_account(a)  # the step-1 write itself refuses, not only the pre-check
    assert not store.get_user(a).disabled


def test_session_freshness_uses_the_server_clock(monkeypatch):
    u = store.redeem_invite(store.create_invite(is_admin=True).code, "discord", "1", "U", None)
    s = store.session_for(store.create_session(u.id).token)
    assert 595 <= s.fresh_seconds_left() <= 600
    real = store._now
    monkeypatch.setattr(store, "_now", lambda: real() - timedelta(minutes=1))  # made "in the future"
    assert s.fresh_seconds_left() == 0 and not s.fresh()
    monkeypatch.setattr(store, "_now", lambda: real() + timedelta(minutes=10, seconds=1))
    assert not s.fresh()


def test_delete_route_refuses_while_a_restore_is_in_flight(web):
    _a, (cm, hm, m) = web
    with layout.as_user(m):
        guard = cm.app.state.undo_guards.current()
    guard._inflight = 1
    try:
        r = _delete(cm, hm)
    finally:
        guard._inflight = 0
    assert r.status_code == 409 and r.json()["code"] == "account.jobs_running"
    assert store.get_user(m) is not None


def test_a_failure_after_sign_in_is_off_is_coded_and_finishable(web, split_dir, monkeypatch):
    _a, (cm, hm, m) = web
    with monkeypatch.context() as mp:
        mp.setattr(analytics_store, "forget", lambda _k: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")))
        r = _delete(cm, hm)
    assert r.status_code == 500 and r.json()["code"] == "account.delete_incomplete"
    assert "mm_session=" in r.headers.get("set-cookie", "")
    assert store.get_user(m).disabled and not (split_dir / "users" / f"{m}.db").exists()
    assert account.delete_account(m).user_row  # an admin finishes it
    assert store.get_user(m) is None


def test_the_final_sweep_removes_a_file_recreated_mid_delete(admins_and_member, monkeypatch):
    data, a, m = admins_and_member
    real = store.remove_user_rows

    def recreate_then_remove(uid):
        userfiles.create(data, uid)  # a request already past the gate recreated it
        return real(uid)
    monkeypatch.setattr(store, "remove_user_rows", recreate_then_remove)
    out = account.delete_account(m, data_dir=data)
    assert not (data / "users" / f"{m}.db").exists()
    assert out.files.count(f"users/{m}.db") == 2
