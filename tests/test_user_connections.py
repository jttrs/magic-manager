"""Phase 3 step 5: per-request user connection, user file lifecycle, per-user undo,
jobs carry the user, user-scoped caches, catalog-first writes (§25.3, §25.4).

The two-user isolation proof signs in two users on a hosted app (owner/admin A and
member B, whose every flag an admin turned on) and drives EVERY ``/api`` route as
B, recording which collection file each connection opens: only B's — and A's file
and restore point are byte-identical afterwards. Step 6: B is also refused every
owner-machine path (``owner_machine.PATHS``) whatever the flags say."""
from __future__ import annotations

import hashlib
import sqlite3
import subprocess
from pathlib import Path

import pytest
from pydantic import BaseModel
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from magic_manager import analytics, auth, db, decks, features, inventory, layout, market, undo, userfiles
from magic_manager.auth import admin as admin_engine
from magic_manager.analytics import consent
from magic_manager.api import jobs as jobs_api
from magic_manager.auth import store
from magic_manager.cli import app as cli_app
from magic_manager.web import auth_routes
from magic_manager.web.runtime import JobManager, JobRecord, JobsBusy

from test_auth import ORIGIN, _concrete, api_routes, hosted, me, provider, sign_in  # noqa: F401 — fixtures

A_ID = "00000000-0000-0000-0000-00000000000a"
B_ID = "00000000-0000-0000-0000-00000000000b"
UA, UB = "aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb"


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _copies() -> int:
    with db.connect() as conn:
        return conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM inventory").fetchone()[0]


@pytest.fixture
def owner_split(tmp_db, seed_cards, make_card, request):
    """The owner's collection (2 copies + a built deck) split into catalog + users/owner.db."""
    seed_cards([make_card(id=A_ID, name="Alpha"), make_card(id=B_ID, name="Beta", collector_number="2")])
    inventory.inventory_add(A_ID, "nonfoil", 2)
    decks.deck_create("owners-deck", "Owner's deck")
    decks.deck_add_card("owners-deck", A_ID, "main", "nonfoil", 1)
    return request.getfixturevalue("split_dir")


# ---------- layout: the bound user picks the file; hosted fails closed ----------

def test_bound_user_picks_the_file_and_mm_user_is_the_default(owner_split):
    userfiles.create(owner_split, UB)
    assert db.layout().path.name == "owner.db" and _copies() == 2
    with layout.as_user(UB):
        assert db.layout().path == owner_split / "users" / f"{UB}.db"
        assert _copies() == 0
    assert _copies() == 2


def test_strict_mode_fails_closed(owner_split, monkeypatch):
    layout.set_strict(True)
    monkeypatch.setenv("MM_USER", "owner")  # never a fallback when hosted
    with pytest.raises(layout.NoUserBound):
        db.layout()
    with pytest.raises(layout.NoUserBound):
        with db.connect():
            pass
    for bad in ("owner", "../owner", "AAAAAAAAAAAAAAAA", "a" * 17, "a/aaaaaaaaaaaaaa"):
        with pytest.raises(layout.LayoutError):
            layout.bind_user(bad)
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(owner_split / "x.db"))
    with pytest.raises(layout.LayoutError, match="split layout"):
        with layout.as_user(UA):
            db.layout()


def test_anonymous_hosted_consent_is_the_default_without_a_file(owner_split, monkeypatch):
    monkeypatch.setenv("MM_MODE", "hosted")
    layout.set_strict(True)
    c = consent.get(fresh=True)
    assert (c.errors, c.usage, c.asked) == (True, False, False)


# ---------- user files ----------

def _user_schema(p: Path) -> dict[str, list]:
    with sqlite3.connect(p) as c:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {t: [tuple(r)[1:6] for r in c.execute(f"PRAGMA table_info({t})")] for t in tables}


def test_new_user_file_has_exactly_the_split_user_schema(owner_split):
    p = userfiles.create(owner_split, UA)
    assert _user_schema(p) == _user_schema(owner_split / "users" / "owner.db")
    with sqlite3.connect(p) as c:
        idx = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")}
        assert c.execute("SELECT version FROM schema_version").fetchone()[0] == db.CURRENT_VERSION
    with sqlite3.connect(owner_split / "users" / "owner.db") as c:
        assert idx == {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")}
    with pytest.raises(userfiles.UserFileError):
        userfiles.create(owner_split, UA)
    assert not userfiles.has_user_data(p)
    assert userfiles.ensure(owner_split, UA) == "ok" and userfiles.ensure(owner_split, UB) == "created"
    with layout.as_user(UA):  # the real split connect accepts it, writes land in it
        inventory.inventory_add(B_ID, "foil", 3)
        assert _copies() == 3
    assert userfiles.has_user_data(p)


def test_migrate_all_runs_each_target_once_per_file(owner_split, monkeypatch):
    userfiles.create(owner_split, UA)
    calls = []
    monkeypatch.setattr(db, "migrate_split_file", lambda p, t: calls.append((Path(p).name, t)) or [])
    rep = userfiles.migrate_all(owner_split)
    (owner_split / "users" / f"{UA}.undo.db").write_bytes(b"")  # undo files are not user files
    assert calls == [("catalog.db", "catalog"), (f"{UA}.db", "user"), ("owner.db", "user")]
    assert rep.users == {UA: [], "owner": []}
    assert [p.name for p in userfiles.user_files(owner_split)] == [f"{UA}.db", "owner.db"]


def test_bind_hands_the_owner_file_to_the_auth_user(owner_split):
    userfiles.create(owner_split, UA)  # A's first sign-in made an empty profile
    with layout.as_user(UA):
        undo.take("A's empty session")
    owner_undo = owner_split / "users" / "owner.undo.db"
    undo.take("owner's session")
    rep = userfiles.bind_file(owner_split, UA)
    assert not (owner_split / "users" / "owner.db").exists() and not owner_undo.exists()
    assert rep.replaced and Path(rep.replaced).exists()
    with layout.as_user(UA):
        assert _copies() == 2 and undo.info()["reason"] == "owner's session"
    # a user whose file holds data is never overwritten; bad ids never touch the filesystem
    userfiles.create(owner_split, "owner")
    with pytest.raises(userfiles.UserFileError, match="no file"):
        userfiles.bind_file(owner_split, UB, "nobody")
    with layout.as_user("owner"):
        inventory.inventory_add(B_ID, "nonfoil", 1)
    with pytest.raises(userfiles.UserFileError, match="already holds data"):
        userfiles.bind_file(owner_split, UA, "owner")
    with pytest.raises(userfiles.UserFileError, match="not a user id"):
        userfiles.bind_file(owner_split, "../x", "owner")


def test_bind_ignores_a_stored_privacy_choice(owner_split):
    """The owner's first hosted visit answers the privacy prompt before `mm auth bind`."""
    userfiles.create(owner_split, UA)
    with layout.as_user(UA):
        consent.update(usage=True)
    assert not userfiles.has_user_data(owner_split / "users" / f"{UA}.db")
    assert userfiles.bind_file(owner_split, UA).replaced
    with layout.as_user(UA):
        assert _copies() == 2


def test_ensure_tolerates_a_concurrent_create(owner_split, monkeypatch):
    def racing(data_dir, user):
        userfiles.path_for(data_dir, user).write_bytes(b"")  # the other sign-in won
        raise userfiles.UserFileError("already exists")
    monkeypatch.setattr(userfiles, "create", racing)
    monkeypatch.setattr(db, "migrate_split_file", lambda p, t: [])
    assert userfiles.ensure(owner_split, UA) == "ok"


def test_one_bad_user_file_does_not_stop_the_others(owner_split, monkeypatch):
    userfiles.create(owner_split, UA)
    real = db.migrate_split_file

    def flaky(p, target):
        if Path(p).stem == UA:
            raise layout.LayoutError("stuck at v12")
        return real(p, target)
    monkeypatch.setattr(db, "migrate_split_file", flaky)
    rep = userfiles.migrate_all(owner_split)
    assert rep.failed == {UA: "LayoutError: stuck at v12"} and rep.users == {"owner": []}
    monkeypatch.setattr(db, "migrate_split_file", lambda p, t: (_ for _ in ()).throw(RuntimeError("catalog")))
    with pytest.raises(RuntimeError):  # the catalog still stops startup
        userfiles.migrate_all(owner_split)


def test_bind_refuses_an_open_file(owner_split):
    (owner_split / "users" / "owner.db-journal").write_bytes(b"")
    with pytest.raises(userfiles.UserFileError, match="looks open"):
        userfiles.bind_file(owner_split, UA)


def test_cli_bind(owner_split):
    u = store.redeem_invite(store.create_invite(is_admin=True).code, "discord", "s1", "Owner", None)
    r = CliRunner().invoke(cli_app, ["auth", "bind", "--user", "nosuchuser00000"])
    assert r.exit_code == 2 and "no user" in r.output
    r = CliRunner().invoke(cli_app, ["auth", "bind", "--user", u.id, "--json"])
    assert r.exit_code == 0, r.output
    assert (owner_split / "users" / f"{u.id}.db").exists()
    r = CliRunner().invoke(cli_app, ["auth", "bind", "--user", u.id])
    assert r.exit_code == 2 and "no file" in r.output


# ---------- per-user undo ----------

def test_undo_is_per_user(owner_split):
    userfiles.create(owner_split, UA)
    guards = undo.SessionGuards(gap=60)
    with layout.as_user(UA):
        ga = guards.current()
        assert ga.begin("A writes")
        inventory.inventory_add(B_ID, "foil", 1)
        ga.end(True)
        assert undo.snapshot_path().name == f"{UA}.undo.db"
    go = guards.current()
    assert go is not ga and go.begin("owner writes")  # A's session doesn't start the owner's
    go.end(True)
    with layout.as_user(UA):
        assert undo.restore()["changes"]["copies"] == 1  # current (0) vs swapped (1)
        assert _copies() == 0
    assert _copies() == 2  # the owner's data untouched by A's restore


# ---------- jobs carry the user ----------

class _In(BaseModel):
    pass


def _count_job(seen: list):
    def run(_inputs, _progress):
        seen.append((layout.bound_user(), _copies()))
        return jobs_api.JobResult(summary="ok")
    return jobs_api.JobSpec(name="test.count", title="Count", description="", input_model=_In, run=run, mutates=True)


def test_job_runs_as_its_submitter_and_is_visible_only_to_them(owner_split, monkeypatch):
    import asyncio
    userfiles.create(owner_split, UA)
    seen: list = []
    monkeypatch.setitem(jobs_api._REGISTRY, "test.count", _count_job(seen))
    layout.set_strict(True)

    async def go():
        m = JobManager()
        await m.startup()
        try:
            with layout.as_user(UA):
                rec = await m.submit("test.count", {})
            await m._execute(rec.id)
            with layout.as_user(UA):
                assert m.get(rec.id) is rec and m.list() == [rec] and m.events_after(rec.id, 0)
                with pytest.raises(JobsBusy):  # A's own mutating job would block A's restore
                    rec.status = "running"
                    with m.no_mutating_jobs():
                        pass
                rec.status = "succeeded"
            with layout.as_user(UB):
                with pytest.raises(KeyError):
                    m.get(rec.id)
                with pytest.raises(KeyError):
                    m.events_after(rec.id, 0)
                assert m.list() == []
                rec.status = "running"
                with m.no_mutating_jobs():  # …but never B's
                    pass
            # an unbound job in hosted mode fails closed instead of opening someone's file
            orphan = await m.submit("test.count", {})
            await m._execute(orphan.id)
            assert orphan.status == "failed" and "NoUserBound" in orphan.error
        finally:
            await m.shutdown()
    asyncio.run(go())
    assert set(seen) == {(UA, 0)}  # (the in-memory broker may run it as well)


def test_job_history_is_trimmed_per_user():
    m = JobManager(max_history=1)
    for i, user in enumerate((UA, UA, UB)):
        m._jobs[str(i)] = JobRecord(id=str(i), name="x", title="X", inputs={}, status="succeeded",
                                    created_at=f"2026-01-0{i + 1}", user=user)
    m._trim()
    assert sorted(m._jobs) == ["1", "2"]  # A keeps its newest; B's only job survives A's flood


# ---------- process-wide caches are user-scoped ----------

def test_product_cost_memo_is_per_user(owner_split, monkeypatch):
    userfiles.create(owner_split, UA)
    market._cost_memo.clear()
    calls = []
    monkeypatch.setattr(market, "_sealed_cost", lambda s, n: calls.append(db.user_scope()) or {"who": db.user_scope()})
    monkeypatch.setattr(market, "_inventory_fingerprint", lambda: (0, 0, 0))  # identical fingerprints
    own = market.product_cost("sealed", "tst", "Box")
    with layout.as_user(UA):
        theirs = market.product_cost("sealed", "tst", "Box")
    assert own != theirs and len(calls) == 2
    market._cost_memo.clear()


def test_set_targets_index_is_per_user(owner_split):
    from magic_manager import family_status
    userfiles.create(owner_split, UA)
    family_status._ST_INDEX.clear()
    with db.connect() as conn:
        conn.execute("INSERT INTO set_targets (anchor_code, related_codes, created_at, updated_at) VALUES ('spm', '[\"mar\"]', 't', 't')")
    assert family_status._set_targets_index()[0] == {"spm": "spm", "mar": "spm"}
    with layout.as_user(UA):
        assert family_status._set_targets_index()[0] == {}
    family_status._ST_INDEX.clear()


def test_consent_is_per_user(owner_split, monkeypatch):
    userfiles.create(owner_split, UA)
    consent.update(usage=False)
    with layout.as_user(UA):
        assert consent.update(usage=True).usage
    assert not consent.get().usage
    with layout.as_user(UA):
        assert consent.get().usage
    # a job/telemetry event recorded outside the request context uses the event's user
    monkeypatch.setenv("MM_ANALYTICS", "on")
    assert analytics.record("job.started", {"job": "x"}, ctx=analytics.Context(user_id=UA))
    assert not analytics.record("job.started", {"job": "x"})


# ---------- §25.3: catalog writes commit before the dependent user write ----------

def test_catalog_first_refuses_after_a_user_write(owner_split):
    with db.connect() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES ('k', 'v')")
        with pytest.raises(RuntimeError, match="25.3"):
            with db.catalog_first(conn):
                pass


NEW = "00000000-0000-0000-0000-0000000000ee"


def _fail_after_catalog_commit(monkeypatch, module, attr):
    """Make the first user write raise — after checking, on a SECOND connection,
    that the new card was already committed (so a crash can't orphan a user row)."""
    seen = {}
    orig = getattr(module, attr)

    def boom(*a, **k):
        with sqlite3.connect(db.layout().catalog) as other:
            seen["committed"] = bool(other.execute("SELECT 1 FROM cards WHERE scryfall_id = ?", (NEW,)).fetchone())
        raise RuntimeError("crash after the catalog commit")
    monkeypatch.setattr(module, attr, boom)
    return seen, orig


def _no_user_rows() -> bool:
    with db.connect() as conn:
        return not any(conn.execute(f"SELECT 1 FROM {t} WHERE scryfall_id = ?", (NEW,)).fetchone()
                       for t in ("inventory", "inventory_events", "deck_cards"))


def test_decksource_commits_cards_before_the_deck(owner_split, monkeypatch, make_card):
    from magic_manager import decksource
    monkeypatch.setattr(decksource, "_resolve_cards", lambda cards: ({NEW: make_card(id=NEW, name="New", collector_number="99")}, {}, {}, []))
    seen, _ = _fail_after_catalog_commit(monkeypatch, decks, "deck_add_card")
    with pytest.raises(RuntimeError, match="crash"):
        decksource.import_deck([{"scryfall_id": NEW, "qty": 1, "board": "main", "finish": "nonfoil"}], slug="d")
    assert seen["committed"] and _no_user_rows()
    with db.connect() as conn:
        assert not conn.execute("SELECT 1 FROM decks WHERE slug = 'd'").fetchone()


def test_cli_inventory_import_commits_cards_before_the_ledger(owner_split, monkeypatch, make_card, tmp_path):
    from magic_manager import cli
    from magic_manager import parsers
    result = parsers.ParseResult(entries=[parsers.Entry(qty=1, raw="1 New", name="New", set="tst", collector_number="9",
                                                         foil=False, section="mainboard", card=make_card(id=NEW, name="New", collector_number="99"))])
    monkeypatch.setattr(cli, "_resolve_block", lambda text, path: result)
    seen, _ = _fail_after_catalog_commit(monkeypatch, cli.inv_mod, "inventory_add")
    f = tmp_path / "b.txt"
    f.write_text("1 New\n")
    r = CliRunner().invoke(cli_app, ["inventory", "import", str(f)])
    assert isinstance(r.exception, RuntimeError)
    assert seen["committed"] and _no_user_rows()


def test_collection_resolve_commits_cards_first(owner_split, monkeypatch, make_card):
    from magic_manager import collection_sync, scryfall
    monkeypatch.setattr(scryfall, "resolve_identifiers", lambda *a: ({NEW: make_card(id=NEW, collector_number="99")}, {}, {}, []))
    with db.connect() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES ('pending', 'user write')")
        with pytest.raises(RuntimeError, match="25.3"):  # a caller's open user write can't be committed early
            collection_sync.resolve_rows([collection_sync.CollectionRow(qty=1, finish="nonfoil", scryfall_id=NEW)], conn=conn)
    res = collection_sync.resolve_rows([collection_sync.CollectionRow(qty=1, finish="nonfoil", scryfall_id=NEW)])
    assert res is not None
    with sqlite3.connect(db.layout().catalog) as other:
        assert other.execute("SELECT 1 FROM cards WHERE scryfall_id = ?", (NEW,)).fetchone()


# ---------- the two-user isolation proof (every /api route) ----------

@pytest.fixture
def two_users(owner_split, hosted, provider, monkeypatch):
    """Owner A (bound to users/owner.db) and member B, both signed in on one hosted app."""
    assert auth.PROFILES_OPEN  # step 6: profiles are open
    c = TestClient(hosted, base_url=ORIGIN)
    sign_in(c, provider, "discord", invite=store.create_invite(is_admin=True).code)
    a = me(c)["user"]["id"]
    tok_a = c.cookies.get("mm_session")
    assert CliRunner().invoke(cli_app, ["auth", "bind", "--user", a]).exit_code == 0
    c.cookies.clear()
    provider.discord_user = {"id": "d-2", "username": "friend", "global_name": "Friend", "verified": True}
    sign_in(c, provider, "discord", invite=store.create_invite(is_admin=False).code)
    b = me(c)["user"]["id"]
    tok_b = c.cookies.get("mm_session")
    return c, owner_split, (a, tok_a), (b, tok_b)


def _as(c: TestClient, token: str) -> dict:
    c.cookies.set("mm_session", token)
    return {"Origin": ORIGIN, "X-CSRF-Token": me(c)["csrf_token"]}


def test_each_user_sees_only_their_own_collection(two_users):
    c, data, (a, ta), (b, tb) = two_users
    assert (data / "users" / f"{a}.db").exists() and (data / "users" / f"{b}.db").exists()
    h = _as(c, tb)
    assert c.get("/api/decks").json() == []
    r = c.post("/api/ingest/commit", headers=h, json={"items": [{"scryfall_id": B_ID, "finish": "foil", "qty": 5}], "source": "search"})
    assert r.status_code == 200, r.text
    assert c.post("/api/decks", headers=h, json={"name": "B's deck"}).status_code == 201
    b_history = c.get("/api/history").json()
    _as(c, ta)
    assert [d["slug"] for d in c.get("/api/decks").json()] == ["owners-deck"]
    a_history = c.get("/api/history").json()
    assert a_history != b_history
    with layout.as_user(a):
        assert _copies() == 2
    with layout.as_user(b):
        assert _copies() == 5
    # each user's undo restore point is their own file
    assert (data / "users" / f"{b}.undo.db").exists()


def test_no_api_route_opens_another_users_file(two_users, monkeypatch):
    c, data, (a, ta), (b, tb) = two_users
    h = _as(c, ta)
    c.post("/api/ingest/commit", headers=h, json={"items": [{"scryfall_id": A_ID, "finish": "foil", "qty": 1}], "source": "search"})
    a_files = [data / "users" / f"{a}.db", data / "users" / f"{a}.undo.db"]
    before = [_sha(p) for p in a_files]
    assert all(before)

    opened: list[Path] = []
    real_open = db._open_split
    monkeypatch.setattr(db, "_open_split", lambda lay: opened.append(lay.path) or real_open(lay))

    def offline(*_a, **_k):
        raise OSError("offline in this test")
    for name in ("run", "Popen", "check_output", "check_call"):
        monkeypatch.setattr(subprocess, name, offline)
    monkeypatch.setattr(auth_routes, "write_limiter", auth_routes.ratelimit.Limiter(100_000))

    # B gets every flag turned on by an admin override: still only B's file, and
    # every owner-machine path refused (test_member_is_refused_every_pinned_path).
    for flag in features.base_flags():
        admin_engine.set_flag(b, flag, True, actor=a)
    h = _as(c, tb)
    calls = 0
    for route in api_routes(c.app):
        if not route.path.startswith("/api/") or route.path in ("/api/auth/logout",):
            continue
        for method in route.methods:
            for path in {_concrete(route.path), route.path.replace("{", "").replace("}", "")}:
                c.request(method, path, headers=h, json={})
                calls += 1
    # every job too, submitted as B
    for spec in jobs_api.all_specs():
        c.post(f"/api/jobs/{spec.name}", headers=h, json={})
        calls += 1
    assert calls > 100
    assert opened and set(opened) == {data / "users" / f"{b}.db"}, sorted(set(opened))
    assert [_sha(p) for p in a_files] == before


def test_jobs_are_visible_only_to_their_user(two_users, monkeypatch):
    c, data, (a, ta), (b, tb) = two_users
    seen: list = []
    monkeypatch.setitem(jobs_api._REGISTRY, "test.count", _count_job(seen))
    with c:  # lifespan: the job runner
        h = _as(c, ta)
        job = c.post("/api/jobs/test.count", headers=h, json={}).json()
        events = c.get(f"/api/jobs/{job['id']}/events")
        assert events.status_code == 200 and "succeeded" in events.text
        assert c.get(f"/api/jobs/{job['id']}").json()["status"] == "succeeded"
        assert [j["id"] for j in c.get("/api/jobs").json()] == [job["id"]]
        assert "user" not in c.get(f"/api/jobs/{job['id']}").json()
        _as(c, tb)
        assert c.get(f"/api/jobs/{job['id']}").status_code == 404
        assert c.get(f"/api/jobs/{job['id']}/events").status_code == 404
        assert c.get("/api/jobs").json() == []
    assert seen == [(a, 2)]


def test_startup_migrates_every_user_file(owner_split, hosted, monkeypatch):
    calls = []
    monkeypatch.setattr(userfiles, "migrate_all", lambda d: calls.append(d) or userfiles.MigrateReport())
    with TestClient(hosted):
        pass
    assert calls == [owner_split]


def test_sign_in_fails_closed_when_the_file_cannot_be_prepared(owner_split, hosted, provider, monkeypatch):
    from test_auth import _error
    monkeypatch.setattr(userfiles, "ensure", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    c = TestClient(hosted, base_url=ORIGIN)
    r = sign_in(c, provider, "discord", invite=store.create_invite(is_admin=True).code)
    assert _error(r) == "profile_unavailable" and not c.cookies.get("mm_session")
    with store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    # an existing session whose file can't be made: refused, never another user's file
    u = store.users()[0][0]
    s = store.create_session(u.id)
    c.cookies.set("mm_session", s.token)
    r = c.get("/api/decks")
    assert r.status_code == 503 and r.json()["code"] == "auth.profile_unavailable"


def test_a_session_without_a_file_gets_an_empty_one(owner_split, hosted):
    u = store.redeem_invite(store.create_invite(is_admin=True).code, "google", "x", "X", None)
    s = store.create_session(u.id)
    c = TestClient(hosted, base_url=ORIGIN)
    c.cookies.set("mm_session", s.token)
    assert c.get("/api/decks").json() == []
    assert (owner_split / "users" / f"{u.id}.db").exists()


# ---------- step 6: owner-machine paths are admin-only, whatever the flags say ----------

def test_member_is_refused_every_pinned_path(two_users, monkeypatch):
    from magic_manager import addcards, owner_machine, storefetch, tabs
    from magic_manager.api import deals as deals_api
    c, data, (a, ta), (b, tb) = two_users
    for flag in features.base_flags():  # an admin turned EVERYTHING on for B: the pin still wins
        admin_engine.set_flag(b, flag, True, actor=a)

    def never(*_a, **_k):
        raise AssertionError("an owner-machine subprocess ran for a member")
    monkeypatch.setattr(subprocess, "run", never)

    h = _as(c, tb)
    feats = c.get("/api/features").json()
    assert all(feats["flags"].values()) and set(feats["owner_paths"]) == set(owner_machine.PATHS)
    assert not any(feats["owner_paths"].values())
    refused = [("GET", "/api/cart/setup", None), ("POST", "/api/cart/check", {}),
               ("GET", "/api/deals/tabs", None), ("GET", "/api/analytics/summary", None),
               ("GET", "/api/analytics/trace/0123456789abcdef", None)]
    for method, path, body in refused:
        r = c.request(method, path, headers=h, json=body)
        assert r.status_code == 403 and r.json()["code"] == "auth.admin_only", (path, r.status_code, r.text)
    # the companion paths (the member's own browser) are theirs to use
    r = c.post("/api/deals/tabs", headers=h, json={"tabs": []})
    assert r.status_code == 200, r.text

    with layout.as_user(b):
        # deals: never the server Mac's tabs, in the job and at the AppleScript seam
        seen = {}
        monkeypatch.setattr(deals_api.deals, "read_and_compare", lambda urls, **k: seen.update(k) or [])
        deals_api._run_read_prices(deals_api.ReadPricesInput(urls=["https://x.example/p"]), lambda e: None)
        assert seen["tabs_on_mac"] is False
        for seam in (storefetch._osascript, tabs._osascript):
            with pytest.raises(owner_machine.OwnerOnly):
                seam("return 1")
        # the deck fetch (step 9): Moxfield is refused before anything runs (the companion
        # reads it); plain-HTTP sources run with no browser allowed on this machine at all
        with pytest.raises(owner_machine.OwnerOnly):
            _fetch_args(monkeypatch)
        args = _fetch_args(monkeypatch, "https://archidekt.com/decks/123")
        assert "--no-browser" in args["argv"] and args["env"]["MM_NO_SERVER_BROWSER"] == "1"
    with layout.as_user(a):  # the admin keeps the owner-machine paths
        assert owner_machine.access() == {k: True for k in owner_machine.PATHS}
        args = _fetch_args(monkeypatch)
        assert "--no-browser" not in args["argv"] and "MM_NO_SERVER_BROWSER" not in args["env"]
    _as(c, ta)
    assert all(c.get("/api/features").json()["owner_paths"].values())


def _fetch_args(monkeypatch, url: str = "https://moxfield.com/decks/abc") -> dict:
    from magic_manager import addcards
    got: dict = {}

    class FakeProc:
        def __init__(self, argv, **kw):
            got.update(argv=argv, env=kw["env"])
            import io
            self.stdout, self.stderr, self.returncode = io.StringIO('{"cards": []}'), io.StringIO(""), 0

        def wait(self):
            return 0
    monkeypatch.setattr(addcards.subprocess, "Popen", FakeProc)
    addcards.fetch_deck_payload(url)
    return got


def test_a_disabled_admin_is_not_an_admin(owner_split, monkeypatch):
    from magic_manager import owner_machine
    monkeypatch.setenv("MM_MODE", "hosted")
    u = store.redeem_invite(store.create_invite(is_admin=True).code, "google", "z", "Z", None)
    assert not owner_machine.is_admin()  # nobody bound: fail closed
    with layout.as_user(u.id):
        assert owner_machine.is_admin()
        store.revoke(u.id, disable=True)
        assert not owner_machine.is_admin()
