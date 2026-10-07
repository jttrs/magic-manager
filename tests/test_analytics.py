"""Analytics: catalog validation, the no-PII guard, consent (opt-out / opt-in),
retention pruning, delete-my-data, the separate store, and the web wiring
(request ids, coded errors, client ingest, flag-gated dashboard)."""
from __future__ import annotations

import json
import re
import sqlite3
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from magic_manager import analytics, edhrec, undo
from magic_manager.analytics import catalog, consent, dashboard, identity, store
from magic_manager.api import jobs as jobs_api
from magic_manager.web.app import create_app

ROOT = Path(__file__).resolve().parent.parent
SID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def on(tmp_db, monkeypatch):
    """Recording ON (the suite default is MM_ANALYTICS=off)."""
    monkeypatch.delenv("MM_ANALYTICS", raising=False)
    consent.clear_cache()
    return tmp_db


@pytest.fixture
def client(on):
    with TestClient(create_app(serve_frontend=False), raise_server_exceptions=False) as c:
        yield c


def _events(name: str | None = None) -> list[dict]:
    with store.connect() as conn:
        rows = conn.execute("SELECT * FROM events" + (" WHERE name = ?" if name else "") + " ORDER BY ts_ms",
                            (name,) if name else ()).fetchall()
        out = []
        for r in rows:
            props = {p["key"]: p["value"] for p in conn.execute("SELECT key, value FROM event_props WHERE event_id = ?", (r["event_id"],))}
            out.append(dict(r) | {"props": props})
        return out


# ---------- catalog ----------

def test_catalog_parses_and_every_event_is_documented():
    cat = catalog.load()
    assert {"api.error", "job.failed", "client.error", "companion.error", "page.viewed"} <= set(cat.events)
    doc = (ROOT / "docs" / "analytics.md").read_text()
    for e in cat.events.values():
        assert e.owner and len(e.purpose) > 20, e.name
        assert f"`{e.name}`" in doc, f"{e.name} missing from docs/analytics.md § Catalog"


def test_catalog_rejects_malformed_entries():
    base = {"retention": {"error_days": 1, "usage_days": 1, "aggregate_days": 1}, "views": {"values": ["x"]}}
    with pytest.raises(catalog.CatalogError, match="unknown type"):
        catalog.parse(base | {"events": {"a.b": {"version": 1, "category": "error", "source": "server", "owner": "o",
                                                   "purpose": "p", "props": {"t": {"type": "string"}}}}})
    with pytest.raises(catalog.CatalogError, match="dim"):
        catalog.parse(base | {"events": {"a.b": {"version": 1, "category": "error", "source": "server", "owner": "o",
                                                   "purpose": "p", "dims": ["nope"]}}})
    with pytest.raises(catalog.CatalogError, match="trigger"):
        catalog.parse(base | {"events": {"a.b": {"version": 1, "category": "usage", "source": "server", "owner": "o",
                                                   "purpose": "p", "props": {"k": {"type": "enum", "values": ["a"]}},
                                                   "triggers": {"r": {"k": "zzz"}}}}})


def test_route_triggers_name_real_routes_and_job_names_are_codes():
    app = create_app(serve_frontend=False)
    names = {getattr(r, "name", None) for r in app.routes}
    for e in catalog.load().events.values():
        for route in e.triggers:
            assert route in names, f"{e.name}: trigger {route!r} is not an API route"
    for spec in jobs_api.all_specs():
        assert catalog.check_value(catalog.Prop("job", "code"), spec.name, ()) == spec.name


# ---------- no-PII guard ----------

PII_NAME = re.compile(r"email|e_mail|name$|^name|user(name)?$|ip(_?addr)?$|agent|url|uri|card|price|cost|text|message|"
                      r"note|title|query|search|address|phone|token|password|secret|deck_name|slug", re.I)
PII_VALUES = ["owner@example.com", "192.168.1.20", "https://evil.example/x?q=1", "+1 415 555 0100",
              "4155550100", "Sol Ring", "Lightning Bolt (2XM) 117", "11111111-1111-4111-8111-111111111111",
              "Mozilla/5.0 (Macintosh)", "a" * 65, "drop table events;", "user.12345678"]


def test_no_catalog_property_is_free_text_or_pii_named():
    cat = catalog.load()
    for e in cat.events.values():
        for p in e.props.values():
            assert p.type in catalog.TYPES and p.type != "string", (e.name, p.name)
            assert not PII_NAME.search(p.name), f"{e.name}.{p.name} looks like personal data"


def test_every_string_property_refuses_pii_shaped_values():
    cat = catalog.load()
    for e in cat.events.values():
        for p in e.props.values():
            if p.type == "int":
                continue
            for v in PII_VALUES:
                assert catalog.check_value(p, v, cat.views) is None, f"{e.name}.{p.name} accepted {v!r}"


def test_validate_drops_unknown_props_and_rejects_bad_events():
    ok = catalog.validate("page.viewed", {"view": "decks", "viewport": "narrow", "email": "a@b.c"}, source="client")
    assert ok.props == {"view": "decks", "viewport": "narrow"} and ok.dropped == ["email"]
    with pytest.raises(ValueError, match="unknown event"):
        catalog.validate("nope.event", {}, source="client")
    with pytest.raises(ValueError, match="server event"):
        catalog.validate("api.error", {}, source="client")
    with pytest.raises(ValueError, match="missing or invalid view"):
        catalog.validate("page.viewed", {"view": "Sol Ring", "viewport": "wide"}, source="client")
    assert catalog.to_code("StaleCounts") == "stale_counts"
    assert catalog.to_code("HTTPException") == "http_exception"


# ---------- consent ----------

def test_local_defaults_record_both_and_opt_out_is_honored(on):
    c = consent.get()
    assert (c.mode, c.errors, c.usage, c.asked) == ("local", True, True, True)
    assert analytics.record("job.started", {"job": "edhrec.sync_bulk"})
    consent.update(usage=False)
    assert not analytics.record("job.started", {"job": "edhrec.sync_bulk"})
    assert analytics.record("job.failed", {"job": "edhrec.sync_bulk", "code": "key_error"})
    consent.update(errors=False)
    assert not analytics.record("job.failed", {"job": "edhrec.sync_bulk", "code": "key_error"})
    r = analytics.ingest_client([{"name": "page.viewed", "props": {"view": "decks", "viewport": "wide"}}], session_id=SID)
    assert r.accepted == 0 and r.skipped_by_consent == 1
    assert [e["name"] for e in _events()] == ["job.started", "job.failed"]


def test_hosted_usage_is_opt_in(on, monkeypatch):
    monkeypatch.setenv("MM_MODE", "hosted")
    c = consent.get(fresh=True)
    assert (c.errors, c.usage, c.asked) == (True, False, False)
    assert not analytics.record("job.started", {"job": "edhrec.sync_bulk"})
    c = consent.update(usage=True)
    assert c.usage and c.asked
    assert analytics.record("job.started", {"job": "edhrec.sync_bulk"})


def test_kill_switch_records_nothing(tmp_db):
    assert consent.get(fresh=True).disabled  # the suite default
    assert not analytics.record("job.failed", {"job": "x", "code": "y"})
    assert analytics.ingest_client([{"name": "page.viewed", "props": {}}], session_id=None).accepted == 0


# ---------- store: retention, forget, separation ----------

def _insert(name: str, props: dict, at: datetime, user: str = identity.LOCAL_USER) -> None:
    checked = catalog.validate(name, props, source=catalog.load().events[name].source)
    store.insert([store.Row(checked, at=at, user_key=identity.user_key(user), key_version=identity.key_version())])


def test_retention_prunes_by_category_and_keeps_aggregates_13_months(on):
    now = datetime(2026, 10, 7, 12, tzinfo=UTC)
    err = {"job": "j.x", "code": "boom"}
    use = {"job": "j.x"}
    _insert("job.failed", err, now - timedelta(days=29))
    _insert("job.failed", err, now - timedelta(days=31))
    _insert("job.started", use, now - timedelta(days=89))
    _insert("job.started", use, now - timedelta(days=91))
    _insert("job.started", use, now - timedelta(days=400))
    got = store.prune(now=now)
    assert got == {"errors": 1, "usage": 2, "aggregates": 1}
    with store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM event_props WHERE event_id NOT IN (SELECT event_id FROM events)").fetchone()[0] == 0
        assert conn.execute("SELECT SUM(n) FROM daily_counts").fetchone()[0] == 4


def test_forget_deletes_only_that_users_raw_events(on):
    now = datetime.now(UTC)
    _insert("job.started", {"job": "j.x"}, now)
    _insert("job.started", {"job": "j.x"}, now, user="someone-else")
    assert analytics.forget_user() == 1
    rows = _events()
    assert len(rows) == 1 and rows[0]["user_key"] == identity.user_key("someone-else")
    with store.connect() as conn:  # the aggregate has no user key and stays
        assert conn.execute("SELECT SUM(n) FROM daily_counts").fetchone()[0] == 2


def test_user_key_is_a_one_way_hmac_that_rotates_with_the_secret(on, monkeypatch):
    k = identity.user_key("alice")
    assert len(k) == 32 and "alice" not in k and k != identity.user_key("bob")
    monkeypatch.setenv("MM_ANALYTICS_SECRET", "rotated")
    assert identity.user_key("alice") != k


def test_store_is_separate_from_the_collection_db_and_its_backups(on):
    analytics.record("job.failed", {"job": "j.x", "code": "boom"})
    assert store.path() != on and store.path().exists()
    coll = {r[0] for r in sqlite3.connect(on).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not coll & {"events", "event_props", "daily_counts"}
    assert not set(undo.USER_TABLES) & {"events", "event_props", "daily_counts"}


# ---------- dashboard (portable saved SQL) ----------

def test_summary_trends_sessions_funnel_and_trace(on):
    ctx = analytics.Context(request_id="abcdef0123456789abcdef0123456789", session_id=SID)
    analytics.record("api.error", {"route": "deck_save", "method": "POST", "status": 409, "code": "stale_draft"}, ctx=ctx)
    analytics.ingest_client([{"name": "page.viewed", "props": {"view": "collection", "viewport": "narrow"}}], session_id=SID)
    analytics.record_response("collection_buy_list", "POST", 200, None, ctx=ctx)
    s = dashboard.summary(7)
    assert s["totals"]["errors"] == 1 and s["totals"]["sessions"] == 1 and s["totals"]["sessions_with_errors"] == 1
    assert s["top_errors"][0]["dims"] == {"route": "deck_save", "method": "POST", "status": "409", "code": "stale_draft"}
    assert s["views"] == [{"view": "collection", "narrow": 1, "wide": 0, "n": 1}]
    assert [f["sessions"] for f in s["funnel"]] == [1, 1]
    assert len(s["error_trend"]) == 7
    assert dashboard.trace("abcdef01")[0]["props"]["code"] == "stale_draft"
    with pytest.raises(ValueError):
        dashboard.trace("zz")


def test_saved_queries_are_portable_sql():
    banned = re.compile(r"julianday|strftime|json_extract|datetime\(|date\(|ifnull|group_concat", re.I)
    for name in dashboard.query_names():
        assert not banned.search(dashboard.sql(name)), f"{name}.sql uses SQLite-only functions"


# ---------- web wiring ----------

def test_errors_carry_a_code_and_request_id(client):
    r = client.get("/api/decks/nope", headers={"X-MM-Session": SID})
    assert r.status_code == 404
    body = r.json()
    assert body["request_id"] == r.headers["x-request-id"] and len(body["request_id"]) == 32
    assert body["code"] and isinstance(body["detail"], str)
    ev = _events("api.error")[-1]
    assert ev["props"]["route"] == "deck_detail" and ev["props"]["status"] == "404"
    assert ev["request_id"] == body["request_id"] and ev["session_id"] == SID
    r = client.get("/api/ingest/search", params={"q": "x"})
    assert r.status_code == 422 and r.json()["code"] == "request_validation"


def test_unhandled_exception_is_a_coded_500(client, monkeypatch):
    from magic_manager.api import history as history_api

    def boom():
        raise KeyError("missing piece")
    monkeypatch.setattr(history_api, "history", boom)
    r = client.get("/api/history")
    assert r.status_code == 500
    assert r.json()["code"] == "key_error" and "KeyError" in r.json()["detail"]
    assert r.json()["request_id"] == r.headers["x-request-id"]
    assert _events("api.error")[-1]["props"]["code"] == "key_error"


def test_client_ingest_endpoint_validates_and_reports_rejections(client):
    r = client.post("/api/analytics/events", headers={"X-MM-Session": SID}, json={"events": [
        {"name": "page.viewed", "props": {"view": "decks", "viewport": "wide", "path": "/decks/secret-deck"}},
        {"name": "client.error", "props": {"view": "decks", "kind": "uncaught", "code": "type_error"}},
        {"name": "job.failed", "props": {}},
    ]})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["accepted"] == 2 and out["dropped_props"] == 1
    assert out["rejected"] == [{"index": 2, "reason": "event 'job.failed' is a server event"}]
    assert client.post("/api/analytics/events", json={"events": [{"name": "x"}] * 51}).status_code == 422
    assert all(e["session_id"] == SID for e in _events() if e["source"] == "client")
    assert _events("api.error")[-1]["props"]["route"] == "analytics_events"


def test_consent_and_forget_endpoints(client):
    assert client.get("/api/analytics/consent").json()["usage"] is True
    assert client.put("/api/analytics/consent", json={"usage": False}).json()["usage"] is False
    client.post("/api/analytics/events", json={"events": [{"name": "page.viewed", "props": {"view": "decks", "viewport": "wide"}}]})
    assert _events("page.viewed") == []
    client.post("/api/analytics/events", json={"events": [{"name": "companion.error", "props": {"code": "cart.page_changed"}}]})
    assert client.delete("/api/analytics/my-data").json() == {"deleted": 1}


def test_dashboard_is_behind_the_flag(client, monkeypatch):
    assert client.get("/api/analytics/summary").status_code == 403
    monkeypatch.setenv("MM_FEATURES", "analytics")
    s = client.get("/api/analytics/summary", params={"days": 7})
    assert s.status_code == 200 and s.json()["days"] == 7
    assert client.get("/api/analytics/trace/abcdef").json() == []
    assert client.get("/api/analytics/catalog").status_code == 200


def test_route_trigger_records_a_usage_event(client, monkeypatch):
    from magic_manager.api import collection as collection_api
    monkeypatch.setattr(collection_api, "buy_list", lambda body: collection_api.BuyListOut(text="", lines=0))
    r = client.post("/api/collection/buy-list", json={"target": "manapool", "items": []})
    assert r.status_code == 200, r.text
    assert _events("buylist.exported")[0]["props"] == {"surface": "collection"}


def test_failed_job_records_a_coded_failure(client, monkeypatch):
    def boom(**k):
        raise RuntimeError("kaput")
    monkeypatch.setattr(edhrec, "names_for_bulk", boom)
    job_id = client.post("/api/jobs/edhrec.sync_bulk", json={"selector": "inventory"}).json()["id"]
    with client.stream("GET", f"/api/jobs/{job_id}/events") as r:
        for _ in r.iter_lines():
            pass
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "failed" and job["error_code"] == "runtime_error"
    failed = _events("job.failed")[0]
    assert failed["props"]["code"] == "runtime_error" and failed["props"]["job_id"] == job_id
    assert _events("job.started")[0]["props"]["job"] == "edhrec.sync_bulk"


def test_catalog_file_has_no_secrets_or_free_text_fields():
    data = tomllib.loads((ROOT / "config" / "analytics_events.toml").read_text())
    assert json.dumps(data).count('"type": "string"') == 0
