"""Phase 3 step 6: per-user feature flags (auth.db overrides), the Admin page's API
and its CLI twins, and the owner-machine pin (``owner_machine``)."""
from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from magic_manager import features, layout, owner_machine
from magic_manager.auth import admin as admin_engine, store
from magic_manager.cli import app as cli_app

from test_auth import ORIGIN, api_routes, _concrete, hosted, me, provider, sign_in  # noqa: F401 — fixtures


# ---------- auth.db v2 ----------

def test_overrides_round_trip_and_cascade():
    u = store.redeem_invite(store.create_invite(is_admin=False).code, "discord", "1", "M", None)
    store.set_override(u.id, "deals", True, set_by=None)
    store.set_override(u.id, "companion", False)
    assert store.overrides(u.id) == {"deals": True, "companion": False}
    store.set_override(u.id, "deals", None)
    assert store.overrides(u.id) == {"companion": False}
    with pytest.raises(LookupError):
        store.set_override("zzzzzzzzzzzzzzzz", "deals", True)
    with store.connect() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (u.id,))
    assert store.all_overrides() == {}


def test_a_v1_auth_db_gains_the_v2_parts(tmp_path, monkeypatch):
    p = tmp_path / "old-auth.db"
    raw = sqlite3.connect(p)
    raw.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    raw.execute("INSERT INTO meta VALUES ('schema_version', '1')")
    raw.execute("""CREATE TABLE users (id TEXT PRIMARY KEY, display_name TEXT NOT NULL, email TEXT,
                   is_admin INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, disabled_at TEXT)""")
    raw.execute("INSERT INTO users VALUES ('aaaaaaaaaaaaaaaa', 'Old', NULL, 1, '2026-01-01T00:00:00+00:00', NULL)")
    raw.commit()
    raw.close()
    monkeypatch.setenv("MM_AUTH_DB", str(p))
    assert store.get_user("aaaaaaaaaaaaaaaa").last_seen_at is None
    store.create_session("aaaaaaaaaaaaaaaa")
    assert store.get_user("aaaaaaaaaaaaaaaa").last_seen_at
    with store.connect() as conn:
        assert conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0] == str(store.SCHEMA_VERSION)
    store.set_override("aaaaaaaaaaaaaaaa", "deals", True)
    assert store.overrides("aaaaaaaaaaaaaaaa") == {"deals": True}


# ---------- the flag layers ----------

def test_the_per_user_layer_is_hosted_only_and_on_top(monkeypatch):
    u = store.redeem_invite(store.create_invite(is_admin=False).code, "discord", "1", "M", None)
    store.set_override(u.id, "deals", True)
    store.set_override(u.id, "companion", False)
    store.set_override(u.id, "not_a_flag", True)  # stale/unknown overrides are ignored
    monkeypatch.setenv("MM_FEATURES", "companion")
    with layout.as_user(u.id):
        assert features.flags()["deals"] is False  # local: the per-user layer doesn't exist
        monkeypatch.setenv("MM_MODE", "hosted")
        got = features.flags()
        assert got["deals"] is True and got["companion"] is False and "not_a_flag" not in got
        features.require("deals")
        with pytest.raises(features.FeatureDisabled, match="for your profile"):
            features.require("companion")
    assert features.flags()["deals"] is False  # nobody bound: the server's defaults


# ---------- the owner-machine pin ----------

def test_local_mode_is_the_owners_machine():
    assert owner_machine.access() == {k: True for k in owner_machine.PATHS}
    owner_machine.require("manapool.server_login")


def test_hosted_pin_follows_admin_status_not_flags(monkeypatch):
    monkeypatch.setenv("MM_MODE", "hosted")
    member = store.redeem_invite(store.create_invite(is_admin=False).code, "discord", "1", "M", None)
    for flag in features.base_flags():
        store.set_override(member.id, flag, True)
    with pytest.raises(owner_machine.OwnerOnly) as e:
        owner_machine.require("manapool.server_login")  # nobody bound
    assert e.value.error_code == "auth.admin_only"
    with layout.as_user(member.id):
        assert all(features.flags().values())
        assert not any(owner_machine.access().values())
        for key in owner_machine.PATHS:
            with pytest.raises(owner_machine.OwnerOnly):
                owner_machine.require(key)
    with pytest.raises(KeyError):
        owner_machine.allowed("nope")


# ---------- the Admin API ----------

@pytest.fixture
def people(hosted, provider):
    """Admin A and member M signed in on one hosted app (two browsers)."""
    ca = TestClient(hosted, base_url=ORIGIN)
    sign_in(ca, provider, "discord", invite=store.create_invite(is_admin=True).code)
    provider.discord_user = {"id": "d-2", "username": "m", "global_name": "Member", "verified": True}
    cm = TestClient(hosted, base_url=ORIGIN)
    sign_in(cm, provider, "discord", invite=store.create_invite(is_admin=False).code)
    ha = {"Origin": ORIGIN, "X-CSRF-Token": me(ca)["csrf_token"]}
    hm = {"Origin": ORIGIN, "X-CSRF-Token": me(cm)["csrf_token"]}
    return (ca, ha, me(ca)["user"]["id"]), (cm, hm, me(cm)["user"]["id"])


def _admin_routes(app):
    return [r for r in api_routes(app) if r.path.startswith("/api/admin")]


def test_admin_routes_exist_only_when_hosted(tmp_db):
    from magic_manager.web.app import create_app
    assert _admin_routes(create_app(serve_frontend=False)) == []


def test_every_admin_route_refuses_a_member(people):
    (ca, ha, a), (cm, hm, m) = people
    routes = _admin_routes(ca.app)
    assert len(routes) >= 6
    for route in routes:
        for method in route.methods:
            path = route.path.replace("{user_id}", a).replace("{flag}", "deals")
            r = cm.request(method, path, headers=hm, json={"value": True})
            assert r.status_code == 403 and r.json()["code"] == "auth.admin_only", (method, path, r.text)
    assert store.overrides(a) == {} and store.overrides(m) == {}
    # signed out: the gate's 401 comes first
    anon = TestClient(ca.app, base_url=ORIGIN)
    assert anon.get("/api/admin/users").json()["code"] == "auth.required"


def test_admin_lists_users_without_any_collection(people, monkeypatch):
    from magic_manager import db
    (ca, ha, a), (cm, hm, m) = people
    opened = []
    real = db._open_split
    monkeypatch.setattr(db, "_open_split", lambda lay: opened.append(lay.path) or real(lay))
    body = ca.get("/api/admin/users").json()
    assert opened == []  # §25.0: no admin view of anyone's collection
    rows = {u["id"]: u for u in body["users"]}
    assert rows[a]["is_admin"] and not rows[m]["is_admin"]
    assert rows[m]["providers"] == ["discord"] and rows[m]["sessions"] == 1 and rows[m]["last_seen_at"]
    assert {p["key"] for p in body["owner_paths"]} == set(owner_machine.PATHS)
    deals = next(f for f in rows[m]["flags"] if f["name"] == "deals")
    assert deals["override"] is None and deals["owner_paths"] == ["deals.mac_tabs"] and deals["about"]


def test_admin_sets_a_flag_the_member_sees_it_and_the_pin_holds(people):
    (ca, ha, a), (cm, hm, m) = people
    assert cm.get("/api/features").json()["flags"]["cart_check"] is False
    r = ca.put(f"/api/admin/users/{m}/flags/cart_check", headers=ha, json={"value": True})
    assert r.status_code == 200
    f = next(x for x in r.json()["flags"] if x["name"] == "cart_check")
    assert f["override"] is True and f["effective"] is True
    feats = cm.get("/api/features").json()
    assert feats["flags"]["cart_check"] is True and feats["owner_paths"]["manapool.server_login"] is False
    r = cm.post("/api/cart/check", headers=hm, json={})
    assert r.status_code == 403 and r.json()["code"] == "auth.admin_only"
    # back to the default; an unknown flag is refused
    ca.put(f"/api/admin/users/{m}/flags/cart_check", headers=ha, json={"value": None})
    assert cm.get("/api/features").json()["flags"]["cart_check"] is False
    assert ca.put(f"/api/admin/users/{m}/flags/nope", headers=ha, json={"value": True}).status_code == 422
    assert ca.put("/api/admin/users/zzzzzzzzzzzzzzzz/flags/deals", headers=ha, json={"value": True}).status_code == 404
    # CSRF still applies to admin writes
    r = ca.put(f"/api/admin/users/{m}/flags/deals", headers={"Origin": ORIGIN}, json={"value": True})
    assert r.json()["code"] == "auth.csrf"


def test_admin_mints_invites_shown_once(people):
    (ca, ha, a), _ = people
    r = ca.post("/api/admin/invites", headers=ha, json={"admin": False, "expires_days": 3})
    assert r.status_code == 201
    inv = r.json()
    assert inv["url"] == f"{ORIGIN}/?invite={inv['code']}" and inv["admin"] is False
    dump = "\n".join(sqlite3.connect(store.path()).iterdump())
    assert inv["code"] not in dump and store.hash_secret(inv["code"]) in dump
    assert store.invite_is_admin(inv["code"]) is False
    assert ca.post("/api/admin/invites", headers=ha, json={"expires_days": 0}).status_code == 422
    assert ca.post("/api/admin/invites", headers=ha, json={"admin": True, "role": "x"}).status_code == 422


def test_admin_signs_out_disables_and_enables(people):
    (ca, ha, a), (cm, hm, m) = people
    assert ca.post(f"/api/admin/users/{m}/sign-out", headers=ha).json() == {"ended": 1}
    assert me(cm)["user"] is None
    r = ca.post(f"/api/admin/users/{m}/disable", headers=ha)
    assert r.status_code == 200 and r.json()["disabled_at"]
    assert store.get_user(m).disabled
    r = ca.post(f"/api/admin/users/{m}/enable", headers=ha)
    assert r.json()["disabled_at"] is None
    r = ca.post(f"/api/admin/users/{a}/disable", headers=ha)
    assert r.status_code == 409 and not store.get_user(a).disabled
    assert ca.post("/api/admin/users/NOT-AN-ID/disable", headers=ha).status_code == 422


def test_override_on_an_admin_route_flag_cannot_make_a_member_admin(people):
    (ca, ha, a), (cm, hm, m) = people
    for flag in features.base_flags():
        ca.put(f"/api/admin/users/{m}/flags/{flag}", headers=ha, json={"value": True})
    assert cm.get("/api/admin/users").status_code == 403
    assert cm.get("/api/analytics/summary").json()["code"] == "auth.admin_only"
    assert me(cm)["user"]["is_admin"] is False


# ---------- CLI twins ----------

def test_cli_twins():
    run = CliRunner().invoke
    r = run(cli_app, ["auth", "invite", "--expires", "2d", "--json"])
    inv = json.loads(r.output)
    m = store.redeem_invite(inv["code"], "discord", "9", "Member", None)
    assert run(cli_app, ["auth", "flag", "--user", m.id, "--flag", "deals", "--set", "on"]).exit_code == 0
    assert store.overrides(m.id) == {"deals": True}
    flags = json.loads(run(cli_app, ["auth", "flags", "--user", m.id, "--json"]).output)
    deals = next(f for f in flags if f["name"] == "deals")
    assert deals["effective"] is True and deals["owner_paths"] == ["deals.mac_tabs"]
    rows = json.loads(run(cli_app, ["auth", "users", "--json"]).output)
    assert rows[0]["overrides"] == {"deals": True}
    assert run(cli_app, ["auth", "flag", "--user", m.id, "--flag", "deals", "--set", "maybe"]).exit_code == 2
    assert run(cli_app, ["auth", "flag", "--user", m.id, "--flag", "nope", "--set", "on"]).exit_code == 2
    assert run(cli_app, ["auth", "flag", "--user", m.id, "--flag", "deals", "--set", "default"]).exit_code == 0
    assert store.overrides(m.id) == {}
    assert run(cli_app, ["auth", "revoke", "--user", m.id, "--disable"]).exit_code == 0
    assert store.get_user(m.id).disabled
    assert run(cli_app, ["auth", "enable", "--user", m.id]).exit_code == 0
    assert not store.get_user(m.id).disabled
    assert run(cli_app, ["auth", "enable", "--user", "zzzzzzzzzzzzzzzz"]).exit_code == 2


def test_a_job_refused_by_the_pin_fails_with_the_code(people, monkeypatch):
    from pydantic import BaseModel
    from magic_manager.api import jobs as jobs_api
    (ca, ha, a), (cm, hm, m) = people

    class In(BaseModel):
        pass

    def run(_inputs, _progress):
        owner_machine.require("manapool.server_login")
        return jobs_api.JobResult(summary="ran")
    monkeypatch.setitem(jobs_api._REGISTRY, "test.pinned",
                        jobs_api.JobSpec(name="test.pinned", title="Pinned", description="", input_model=In, run=run))
    with cm:
        job = cm.post("/api/jobs/test.pinned", headers=hm, json={}).json()
        cm.get(f"/api/jobs/{job['id']}/events")
        got = cm.get(f"/api/jobs/{job['id']}").json()
    assert got["status"] == "failed" and got["error_code"] == "auth.admin_only"
    assert "owner’s machine" in got["error"]
