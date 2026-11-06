"""The flag picker: /api/flags (local = open; hosted = admins), /api/features.flag_admin, `mm flags`."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from magic_manager import features
from magic_manager.auth import store
from magic_manager.cli import app as cli_app
from magic_manager.web.app import create_app

from test_auth import ORIGIN, hosted, me, provider, sign_in  # noqa: F401 — fixtures
from test_admin import people  # noqa: F401 — fixture


def _row(body, name):
    return next(f for f in body["flags"] if f["name"] == name)


def test_local_get_put_persist(tmp_db):
    c = TestClient(create_app(serve_frontend=False))
    body = c.get("/api/flags").json()
    assert body["per_user"] is False and {f["name"] for f in body["flags"]} == set(features.declared())
    row = _row(body, "deals")
    assert row["effective"] is False and row["source"] == "default" and row["everyone"] is None
    r = c.put("/api/flags/deals", json={"scope": "everyone", "value": True})
    assert r.status_code == 200, r.text
    assert r.json()["effective"] is True and r.json()["source"] == "everyone" and r.json()["changed_at"]
    fresh = TestClient(create_app(serve_frontend=False))
    assert _row(fresh.get("/api/flags").json(), "deals")["effective"] is True
    assert fresh.get("/api/features").json()["flags"]["deals"] is True
    r = fresh.put("/api/flags/deals", json={"scope": "everyone", "value": None})
    assert r.json()["effective"] is False and r.json()["everyone"] is None


def test_local_errors_and_flag_admin(tmp_db):
    c = TestClient(create_app(serve_frontend=False))
    assert c.put("/api/flags/nope", json={"scope": "everyone", "value": True}).status_code == 422
    assert c.put("/api/flags/deals", json={"scope": "me", "value": True}).status_code == 422
    assert c.put("/api/flags/deals", json={"scope": "x", "value": True}).status_code == 422
    assert c.get("/api/features").json()["flag_admin"] is True


def test_hosted_admin_gate_and_me(people):
    (ca, ha, a), (cm, hm, m) = people
    r = cm.get("/api/flags")
    assert r.status_code == 403 and r.json()["code"] == "auth.admin_only"
    assert cm.put("/api/flags/deals", headers=hm, json={"scope": "me", "value": True}).status_code == 403
    assert cm.get("/api/features").json()["flag_admin"] is False
    assert ca.get("/api/features").json()["flag_admin"] is True
    body = ca.get("/api/flags").json()
    assert body["per_user"] is True
    r = ca.put("/api/flags/deals", headers=ha, json={"scope": "me", "value": True})
    assert r.status_code == 200 and r.json()["mine"] is True and r.json()["source"] == "user"
    assert r.json()["changed_by"]
    assert ca.get("/api/features").json()["flags"]["deals"] is True
    assert cm.get("/api/features").json()["flags"]["deals"] is False
    r = ca.put("/api/flags/deals", headers=ha, json={"scope": "everyone", "value": True})
    assert r.json()["everyone"] is True and r.json()["mine"] is True
    assert cm.get("/api/features").json()["flags"]["deals"] is True


def test_removing_a_user_clears_their_events(people):
    (ca, ha, a), (cm, hm, m) = people
    ca.put("/api/flags/deals", headers=ha, json={"scope": "me", "value": True})
    ca.put("/api/flags/deals", headers=ha, json={"scope": "everyone", "value": True})
    store.remove_user_rows(a)
    with store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM feature_flag_events WHERE user_id = ?", (a,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM feature_flag_events WHERE set_by = ?", (a,)).fetchone()[0] == 0
        assert conn.execute("SELECT set_by FROM feature_defaults WHERE flag = 'deals'").fetchone()[0] is None


def test_cli_flags(tmp_db):
    run = CliRunner().invoke
    assert run(cli_app, ["flags", "set", "deals", "on"]).exit_code == 0
    rows = json.loads(run(cli_app, ["flags", "ls", "--json"]).output)
    d = next(r for r in rows if r["name"] == "deals")
    assert d["effective"] is True and d["everyone"] is True and d["source"] == "everyone"
    assert run(cli_app, ["flags", "ls"]).exit_code == 0
    assert run(cli_app, ["flags", "set", "deals", "maybe"]).exit_code == 2
    assert run(cli_app, ["flags", "set", "nope", "on"]).exit_code == 2
    assert run(cli_app, ["flags", "set", "deals", "default"]).exit_code == 0
    assert features.flags()["deals"] is False
