"""Phase 3 step 10: the whole-system security review's hardening list (§25.4 step 10).

Hosted-only unless a test says otherwise; local mode keeps today's behavior.
1 security headers + CSP (style nonce on the SPA page) · 2 API docs off · 3 scraper
health can't be poisoned by members, stores codes only · 4 set codes / deck file names
validated at one engine seam (+ the wrapper) · 5 store reads never follow a redirect off
the store · 6 job scopes, per-user job cap, live-read limit · 7 coded error bodies ·
9 the real client IP only behind a named proxy · 10 disabled/deleted users' jobs stop.
"""
from __future__ import annotations

import asyncio
import dataclasses
import importlib
import json
import pkgutil
import re
import sqlite3
import subprocess
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from magic_manager import api as api_pkg, layout, mtgjson, scraper_health, storefetch, storepage, vendors
from magic_manager.api import jobs as jobs_api
from magic_manager.auth import ratelimit, store
from magic_manager.web import app as app_mod, auth_routes, runtime, security, telemetry
from magic_manager.web.app import create_app
from magic_manager.web.runtime import JobManager, JobRecord

from test_auth import ORIGIN, _error, hosted, me, provider, sign_in  # noqa: F401 — fixtures
from test_companion_hosted import member  # noqa: F401 — fixture
from test_user_connections import B_ID, _as, owner_split, two_users  # noqa: F401 — fixtures

ROOT = Path(__file__).resolve().parents[1]
CATALOG_JOBS = {"scryfall.sync_tags", "edhrec.sync_bulk", "edhrec.rankings", "art.lookup"}


def _all_specs() -> list[jobs_api.JobSpec]:
    for m in pkgutil.iter_modules(api_pkg.__path__):
        importlib.import_module(f"magic_manager.api.{m.name}")
    return jobs_api.all_specs()


# ---------- 1. security headers ----------

def _assert_hardened(r, *, nonce: str | None = None) -> None:
    csp = r.headers["content-security-policy"]
    for d in ("default-src 'self'", "script-src 'self'", "frame-ancestors 'none'", "base-uri 'none'",
              "form-action 'self'", "object-src 'none'", "img-src 'self' data: https://*.scryfall.io"):
        assert d in csp, (d, csp)
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert ("'nonce-" in csp) == (nonce is not None)
    if nonce:
        assert f"style-src 'self' 'nonce-{nonce}'" in csp
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "same-origin"


def test_every_hosted_response_carries_the_security_headers(member):
    c, data, (a, ta), (b, tb) = member
    h = _as(c, tb)
    responses = [
        c.get("/api/undo"),                                             # ok
        c.get("/api/decks/no-such-deck"),                               # 404
        c.post("/api/ingest/commit", json={}, headers=h),               # 422
        c.post("/api/ingest/commit", json={}, headers={"Origin": "https://evil.example"}),  # gate refusal
        c.get("/docs"),                                                 # outside /api
    ]
    c.cookies.clear()
    responses.append(c.get("/api/undo"))                                # 401
    for r in responses:
        _assert_hardened(r)
    assert "strict-transport-security" not in responses[0].headers     # http://localhost origin


def test_hsts_only_for_an_https_origin():
    assert dict(security.response_headers("https://cards.example.com"))[b"strict-transport-security"] == b"max-age=31536000"
    assert b"strict-transport-security" not in dict(security.response_headers("http://localhost:8784"))


def test_the_spa_page_carries_a_fresh_style_nonce(hosted, tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<!doctype html><html><head><title>x</title></head><body></body></html>')
    (dist / "assets" / "a.js").write_text("console.log(1)")
    monkeypatch.setattr(app_mod, "DIST_DIR", dist)
    c = TestClient(create_app(), base_url=ORIGIN)
    nonces = []
    for path in ("/", "/collection", "/index.html"):
        r = c.get(path)
        m = re.search(r'<meta name="csp-nonce" content="([^"]+)" />', r.text)
        assert r.status_code == 200 and m, r.text
        _assert_hardened(r, nonce=m.group(1))
        assert r.headers["cache-control"] == "no-store"
        nonces.append(m.group(1))
    assert len(set(nonces)) == 3                                        # one per response
    asset = c.get("/assets/a.js")
    assert asset.status_code == 200
    _assert_hardened(asset)


def test_local_mode_sends_no_csp_and_keeps_docs(tmp_db):
    c = TestClient(create_app(serve_frontend=False))
    r = c.get("/api/undo")
    assert r.status_code == 200 and "content-security-policy" not in r.headers
    assert c.get("/docs").status_code == 200 and c.get("/openapi.json").status_code == 200


# ---------- 2. API docs ----------

def test_api_docs_and_schema_are_off_when_hosted(hosted):
    c = TestClient(hosted, base_url=ORIGIN)
    for path in ("/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"):
        assert c.get(path).status_code == 404, path
    assert hosted.openapi()["paths"]                                    # dump_openapi.py still works offline


# ---------- 3. scraper health ----------

@pytest.fixture
def health_file(tmp_path, monkeypatch):
    p = tmp_path / "scraper_health.json"
    monkeypatch.setenv("MM_SCRAPER_HEALTH", str(p))
    return p


def _status(c, key: str) -> dict:
    return next(s for s in c.get("/api/scrapers/health").json()["scrapers"] if s["key"] == key)


def test_a_members_report_flags_nothing_an_admins_does(member, health_file):
    c, data, (a, ta), (b, tb) = member
    key = scraper_health.reported_key("moxfield.changed")
    r = c.post("/api/scrapers/report", json={"code": "moxfield.changed"}, headers=_as(c, tb))
    assert r.status_code == 204 and not r.content
    assert _status(c, key)["status"] != "down"
    r = c.post("/api/scrapers/report", json={"code": "moxfield.changed"}, headers=_as(c, ta))
    assert r.status_code == 200 and r.json()["status"] == "down"


def test_only_an_admin_sees_a_checks_own_message(member, health_file):
    c, data, (a, ta), (b, tb) = member
    key = scraper_health.store_key("manyrealms")
    scraper_health.record([(key, "fail", "scrape.no_price", "raw: /Users/owner/x.html id=123", None)], via="canary")
    _as(c, tb)
    assert _status(c, key)["message"] == scraper_health.reason("scrape.no_price")
    _as(c, ta)
    assert _status(c, key)["message"] == "raw: /Users/owner/x.html id=123"


def test_real_use_stores_only_the_reason_code(health_file, tmp_db, monkeypatch):
    from magic_manager import addcards
    scraper_health.record_use("deck-import/archidekt", "fail", "scrape.no_cards")

    def broken(url, progress=None):
        raise RuntimeError("no cards parsed from https://archidekt.com/decks/987654 (secret-id) at /Users/x/y")
    monkeypatch.setattr(addcards, "fetch_deck_payload", broken)
    with pytest.raises(RuntimeError):
        addcards.fetch_deck_lines("https://archidekt.com/decks/987654/x")
    text = health_file.read_text()
    assert "987654" not in text and "secret-id" not in text and "/Users" not in text
    rec = json.loads(text)["scrapers"]["deck-import/archidekt"]
    assert rec["status"] == "down" and rec["code"] == "scrape.no_cards" and rec["message"] is None


# ---------- 4. identifiers ----------

@pytest.mark.parametrize("code,ok", [("fin", True), ("PLST", True), ("30a", True), ("pss3", True),
                                     ("f", False), ("toolongcode", False), ("../x", False), ("a/b", False),
                                     ("fin\n", False), ("", False), ("fi n", False)])
def test_set_codes(code, ok):
    if ok:
        assert mtgjson.valid_set_code(code) == code
    else:
        with pytest.raises(mtgjson.BadIdentifier):
            mtgjson.valid_set_code(code)


@pytest.mark.parametrize("name,ok", [("CounterBlitzFinalFantasyX_FIC", True), ("DandânDeck_SLD.json", True),
                                     ("OishiiTokensオイシイトークン_SLD", True), ("../etc/passwd", False),
                                     ("a/b", False), ("a.b", False), ("a-b", False), ("a b", False), ("", False),
                                     ("x\n", False)])
def test_deck_file_names(name, ok):
    if ok:
        assert mtgjson.valid_deck_name(name) == name.removesuffix(".json")
    else:
        with pytest.raises(mtgjson.BadIdentifier):
            mtgjson.valid_deck_name(name)


def test_the_engine_refuses_before_the_wrapper_or_a_cache_path(monkeypatch):
    def never(_args):
        raise AssertionError("the wrapper must not run")
    monkeypatch.setattr(mtgjson, "_run", never)
    for call in (lambda: mtgjson.set_file("../x"), lambda: mtgjson.deck("../../x"), lambda: mtgjson.cached_deck("a/b"),
                 lambda: mtgjson.cached_deck_mtime("a.b"), lambda: mtgjson.cache_path("../DeckList.json"),
                 lambda: mtgjson.is_stale("/etc/passwd"), lambda: mtgjson.refresh("decks/../x.json")):
        with pytest.raises(mtgjson.BadIdentifier):
            call()


@pytest.mark.parametrize("args", [["set", "../x"], ["set", "a/b"], ["deck", "../../etc/passwd"], ["deck", "a.b"],
                                  ["sealed", "x;y"], ["cache-path", "../a.json"], ["refresh", "/etc/passwd"],
                                  ["check-stale", "decks/../../x.json"]])
def test_the_wrapper_refuses_bad_names_too(args, tmp_path):
    r = subprocess.run([str(mtgjson.WRAPPER), *args], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "MTGJSON_CACHE_DIR": str(tmp_path), "TMPDIR": str(tmp_path)})
    assert r.returncode == 2, (args, r.stdout, r.stderr)
    assert not any(tmp_path.rglob("*.json"))


def test_api_inputs_refuse_bad_identifiers(tmp_db, monkeypatch):
    from magic_manager.api import market as market_api
    c = TestClient(create_app(serve_frontend=False))
    for path in ("/api/market/value?set=..%2Fx&name=a", "/api/market/products?code=a.b",
                 "/api/market/product-cost?kind=sealed&set=x%2Fy&name=a", "/api/market/cards?code=..",
                 "/api/recipes/a.b", "/api/jumpstart/a-b"):
        r = c.get(path)
        assert r.status_code == 422 and r.json()["code"] == "request_validation", (path, r.text)
    for job, body in (("decks.read_recipes", {"file_names": ["../x"]}), ("decks.read_recipes", {"set": "x/y"}),
                      ("ingest.precon", {"file_name": "a/b"}), ("market.value_family", {"code": "../"})):
        r = c.post(f"/api/jobs/{job}", json=body)
        assert r.status_code == 422, (job, r.text)
    # a bad name that reaches the engine some other way is a coded 422 too
    monkeypatch.setattr(market_api, "family_cards", lambda code: mtgjson.valid_set_code("x/y"))
    r = c.get("/api/market/cards?code=fin")
    assert r.status_code == 422 and r.json()["code"] == "input.bad_identifier"


# ---------- 5. store fetch redirects ----------

class _Resp:
    def __init__(self, status, location=None, text="body"):
        self.status_code, self.text = status, text
        self.headers = {"location": location} if location else {}


class _Client:
    def __init__(self, answers):
        self.answers, self.asked = answers, []

    def get(self, url, **kw):
        assert kw.get("follow_redirects") is False
        self.asked.append(url)
        return self.answers[url] if isinstance(self.answers, dict) else self.answers(url)


@pytest.fixture
def no_pace(monkeypatch, tmp_path):
    monkeypatch.setenv("MM_VENDOR_CACHE", str(tmp_path))
    monkeypatch.setattr(storefetch, "_pace", lambda host: None)


@pytest.mark.parametrize("location", ["https://evil.example/p", "http://www.coolstuffinc.com/p/2",
                                      "https://coolstuffinc.com.evil.example/p", "https://user:pw@coolstuffinc.com/p/2",
                                      "https://www.starcitygames.com/p"])
def test_a_redirect_off_the_store_or_https_is_not_followed(no_pace, location):
    start = "https://www.coolstuffinc.com/p/1"
    c = _Client({start: _Resp(302, location)})
    with pytest.raises(storefetch.OffStoreRedirect) as e:
        storefetch._get(start, client=c)
    assert c.asked == [start] and e.value.error_code == "store.redirect_refused"
    assert isinstance(e.value, storepage.Blocked)  # a per-URL read error in Deals, never a crash


def test_a_redirect_within_the_store_is_followed(no_pace):
    v = next(v for v in vendors.catalog() if len(v.hosts) > 1)
    start = f"https://{v.hosts[0]}/products/x"
    other = f"https://www.{v.hosts[1]}/products/y"
    c = _Client({start: _Resp(301, "/products/z"), f"https://{v.hosts[0]}/products/z": _Resp(302, other),
                 other: _Resp(200, text="<html>ok</html>")})
    assert storefetch._get(start, client=c) == (200, "<html>ok</html>")
    assert c.asked == [start, f"https://{v.hosts[0]}/products/z", other]


def test_an_uncatalogued_page_stays_on_its_host_and_loops_stop(no_pace):
    c = _Client({"https://x.example/a": _Resp(302, "https://x.example/b"), "https://x.example/b": _Resp(200, text="ok")})
    assert storefetch._get("https://x.example/a", client=c) == (200, "ok")
    with pytest.raises(storefetch.OffStoreRedirect):
        storefetch._get("https://x.example/c", client=_Client({"https://x.example/c": _Resp(302, "https://y.example/c")}))
    loop = _Client(lambda url: _Resp(302, url + "x"))
    with pytest.raises(storefetch.OffStoreRedirect, match="too many"):
        storefetch._get("https://x.example/l", client=loop)
    assert len(loop.asked) == storefetch.MAX_REDIRECTS + 1


# ---------- 6. job scopes, the per-user job cap, live reads ----------

def test_every_job_declares_its_scope_and_catalog_jobs_are_these():
    specs = _all_specs()
    assert len(specs) >= 12
    assert all(s.scope in ("user", "shared", "catalog") for s in specs)
    assert {s.name for s in specs if s.scope == "catalog"} == CATALOG_JOBS
    with pytest.raises(TypeError):  # a new job can't forget to say
        jobs_api.JobSpec(name="x", title="X", description="", input_model=dict, run=lambda i, p: None)  # type: ignore[call-arg]


def _quick(monkeypatch, name: str) -> None:
    spec = jobs_api.get(name)
    monkeypatch.setitem(jobs_api._REGISTRY, name, dataclasses.replace(spec, run=lambda i, p: jobs_api.JobResult("ok")))


def test_members_cant_start_catalog_jobs_admins_can(member, monkeypatch):
    c, data, (a, ta), (b, tb) = member
    _all_specs()
    for name in CATALOG_JOBS:
        _quick(monkeypatch, name)
    body = {"edhrec.sync_bulk": {"families": ["fin"]}, "art.lookup": {"tag": "x", "cards": []},
            "edhrec.rankings": {"scope": "salt"}}
    hb = _as(c, tb)
    assert c.get("/api/features").json()["jobs"] == {n: False for n in CATALOG_JOBS}
    for name in CATALOG_JOBS:
        r = c.post(f"/api/jobs/{name}", json=body.get(name, {}), headers=hb)
        assert r.status_code == 403 and r.json()["code"] == "jobs.admin_only", (name, r.text)
    ha = _as(c, ta)
    assert c.get("/api/features").json()["jobs"] == {n: True for n in CATALOG_JOBS}
    r = c.post("/api/jobs/scryfall.sync_tags", json={}, headers=ha)
    assert r.status_code == 202, r.text


def test_the_worker_rechecks_a_catalog_jobs_scope(member):
    c, data, (a, ta), (b, tb) = member
    _all_specs()
    m = JobManager()
    rec = JobRecord(id="j1", name="scryfall.sync_tags", title="Sync", inputs={"refresh": False}, user=b)
    m._jobs[rec.id] = rec
    asyncio.run(m._execute(rec.id))
    assert rec.status == "failed" and rec.error_code == "jobs.admin_only"


def test_a_user_may_have_three_jobs_queued_or_running(member, monkeypatch):
    c, data, (a, ta), (b, tb) = member
    _quick(monkeypatch, "decks.read_recipes")
    jobs = c.app.state.jobs
    for i in range(runtime.MAX_ACTIVE_PER_USER):
        jobs._jobs[f"q{i}"] = JobRecord(id=f"q{i}", name="decks.read_recipes", title="Read", inputs={}, status="queued", user=b)
    r = c.post("/api/jobs/decks.read_recipes", json={"set": "fin"}, headers=_as(c, tb))
    assert r.status_code == 429 and r.json()["code"] == "jobs.too_many"
    r = c.post("/api/jobs/decks.read_recipes", json={"set": "fin"}, headers=_as(c, ta))  # A has her own allowance
    assert r.status_code == 202, r.text


def test_live_reads_are_limited_per_user(member, monkeypatch):
    c, data, (a, ta), (b, tb) = member
    from magic_manager.api import cards as cards_api, market as market_api
    monkeypatch.setattr(security, "live_limiter", ratelimit.Limiter(2))

    def down(limit):
        raise RuntimeError("catalogue unreadable")
    monkeypatch.setattr(market_api, "sld_drops", down)
    monkeypatch.setattr(cards_api, "floors", lambda body: {"live": body.live, "floors": []})
    _as(c, tb)
    assert [c.get("/api/market/secret-lair").status_code for _ in range(3)] == [502, 502, 429]
    hb = _as(c, tb)
    floors = [c.post("/api/cards/floors", json={"scryfall_ids": [B_ID]}, headers=hb).status_code for _ in range(3)]
    assert floors == [200, 200, 200]                                    # local floors: no limit
    assert c.post("/api/cards/floors", json={"scryfall_ids": [B_ID], "live": True}, headers=hb).status_code == 429
    _as(c, ta)
    assert c.get("/api/market/secret-lair").status_code == 502          # A's own allowance


# ---------- 7. coded error bodies ----------

_LEAK = re.compile(r"/Users/|/var/|/data/users|sqlite|SQLITE|mtgjson\.sh|constraint|no such table", re.I)


def test_hosted_error_bodies_never_carry_paths_or_sql(member, monkeypatch):
    c, data, (a, ta), (b, tb) = member
    from magic_manager.api import decks as decks_api, deals as deals_api, history as history_api, market as market_api

    def raise_(e):
        def f(*_a, **_k):
            raise e
        return f
    monkeypatch.setattr(decks_api, "detail", raise_(LookupError("deck 'x' not in /Users/torre/data/users/abcd.db")))
    monkeypatch.setattr(market_api, "family_products", raise_(mtgjson.MtgJsonError(
        "mtgjson.sh set FIN exited 6: HTTP 500 from https://mtgjson.com/api/v5/FIN.json (cache /var/folders/x/FIN.json)")))
    monkeypatch.setattr(history_api, "event", raise_(LookupError("sqlite3.OperationalError: no such table: ingest_events")))
    monkeypatch.setattr(deals_api, "set_target", raise_(sqlite3.IntegrityError("UNIQUE constraint failed: earmark_targets.product_id")))
    h = _as(c, tb)
    responses = [
        c.get("/api/decks/x"),
        c.get("/api/market/products?code=fin"),
        c.get("/api/history/1"),
        c.put("/api/deals/target", json={"product_id": 1, "mode": "price", "value": 5}, headers=h),
    ]
    for r in responses:
        body = r.json()
        assert 400 <= r.status_code < 600 and body["code"] and body["request_id"], r.text
        assert not _LEAK.search(r.text), r.text
    assert [r.status_code for r in responses] == [404, 502, 404, 422]


def test_local_mode_keeps_the_detail(tmp_db, monkeypatch):
    from magic_manager.api import decks as decks_api

    def gone(slug):
        raise LookupError("deck 'x' not in /Users/torre/db/magic_manager.db")
    monkeypatch.setattr(decks_api, "detail", gone)
    r = TestClient(create_app(serve_frontend=False)).get("/api/decks/x")
    assert r.status_code == 404 and "/Users/torre" in r.json()["detail"]


def test_public_detail_scrubs_nested_messages_and_keeps_plain_ones(monkeypatch):
    monkeypatch.setenv("MM_MODE", "hosted")
    assert telemetry.public_detail("Unknown deck 'abc'", None, 404) == "Unknown deck 'abc'"
    assert telemetry.public_detail("see https://x.com/a/b/c", None, 404) == "see https://x.com/a/b/c"
    scrubbed = telemetry.public_detail({"message": "at /data/users/x.db", "stale": [{"n": 1}]}, None, 409)
    assert scrubbed == {"message": telemetry.PLAIN_DEFAULT, "stale": [{"n": 1}]}
    assert telemetry.public_detail("anything", OSError("x"), 422) == telemetry.PLAIN_DEFAULT


# ---------- 9. client IP behind a proxy ----------

def _req(peer: str, **headers: str) -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "client": (peer, 5000),
                    "headers": [(k.replace("_", "-").lower().encode(), v.encode()) for k, v in headers.items()]})


def test_proxy_headers_are_ignored_unless_named(monkeypatch):
    monkeypatch.delenv("MM_TRUSTED_PROXY", raising=False)
    spoof = {"cf_connecting_ip": "1.1.1.1", "x_forwarded_for": "2.2.2.2"}
    assert security.client_ip(_req("127.0.0.1", **spoof)) == "127.0.0.1"
    monkeypatch.setenv("MM_TRUSTED_PROXY", "cloudflare")
    assert security.client_ip(_req("127.0.0.1", **spoof)) == "1.1.1.1"
    assert security.client_ip(_req("::1", cf_connecting_ip="2001:db8::1")) == "2001:db8::1"
    assert security.client_ip(_req("203.0.113.9", **spoof)) == "203.0.113.9"      # not from the proxy
    assert security.client_ip(_req("127.0.0.1", cf_connecting_ip="not an ip")) == "127.0.0.1"
    monkeypatch.setenv("MM_TRUSTED_PROXY", "tailscale")
    assert security.client_ip(_req("127.0.0.1", x_forwarded_for="9.9.9.9, 100.64.0.7")) == "100.64.0.7"
    assert security.client_ip(_req("127.0.0.1", cf_connecting_ip="1.1.1.1")) == "127.0.0.1"
    monkeypatch.setenv("MM_TRUSTED_PROXY", "nginx")
    with pytest.raises(security.ProxyConfigError):
        security.client_ip(_req("127.0.0.1"))


def test_a_misspelt_proxy_setting_refuses_to_start(hosted, monkeypatch):
    monkeypatch.setenv("MM_TRUSTED_PROXY", "cloudfare")
    with pytest.raises(security.ProxyConfigError):
        create_app(serve_frontend=False)


@pytest.mark.parametrize("proxy,limited", [(None, True), ("cloudflare", False)])
def test_sign_in_limit_keys_on_the_real_client_only_behind_a_named_proxy(hosted, monkeypatch, proxy, limited):
    if proxy:
        monkeypatch.setenv("MM_TRUSTED_PROXY", proxy)
    else:
        monkeypatch.delenv("MM_TRUSTED_PROXY", raising=False)
    monkeypatch.setattr(auth_routes, "login_limiter", ratelimit.Limiter(2))
    c = TestClient(create_app(serve_frontend=False), base_url=ORIGIN, client=("127.0.0.1", 40000))
    errs = [_error(c.get("/api/auth/login/discord", headers={"CF-Connecting-IP": ip}, follow_redirects=False))
            for ip in ("1.1.1.1", "1.1.1.1", "2.2.2.2")]
    assert errs == [None, None, "rate_limited" if limited else None]


def test_mm_serve_turns_off_uvicorns_own_proxy_header_rewrite(monkeypatch):
    import uvicorn
    from typer.testing import CliRunner
    from magic_manager.cli import app as cli_app
    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: seen.update(kw))
    CliRunner().invoke(cli_app, ["serve", "--port", "8790"])
    assert seen.get("proxy_headers") is False


# ---------- 10. disabled / deleted users' jobs ----------

def _ticking_spec(started: threading.Event, go: threading.Event, after: list) -> jobs_api.JobSpec:
    from pydantic import BaseModel

    class In(BaseModel):
        pass

    def run(_inputs, progress):
        progress(jobs_api.ProgressEvent(1, 3, "one"))
        started.set()
        go.wait(5)
        progress(jobs_api.ProgressEvent(2, 3, "two"))   # cooperative cancel point
        after.append(True)
        return jobs_api.JobResult("done")
    return jobs_api.JobSpec(name="test.ticks", title="Ticks", description="", input_model=In, run=run,
                            mutates=True, scope="user")


def test_disabling_a_user_stops_their_running_and_queued_jobs(member, monkeypatch):
    c, data, (a, ta), (b, tb) = member
    started, go, after = threading.Event(), threading.Event(), []
    monkeypatch.setitem(jobs_api._REGISTRY, "test.ticks", _ticking_spec(started, go, after))
    jobs = c.app.state.jobs
    running = JobRecord(id="r1", name="test.ticks", title="Ticks", inputs={}, user=b)
    queued = JobRecord(id="q1", name="test.ticks", title="Ticks", inputs={}, user=b)
    mine = JobRecord(id="a1", name="test.ticks", title="Ticks", inputs={}, status="queued", user=a)
    jobs._jobs.update({r.id: r for r in (running, queued, mine)})

    t = threading.Thread(target=lambda: asyncio.run(jobs._execute("r1")))
    t.start()
    assert started.wait(5)
    r = c.post(f"/api/admin/users/{b}/disable", headers=_as(c, ta))
    assert r.status_code == 200, r.text
    go.set()
    t.join(10)
    assert running.status == "failed" and running.error_code == "jobs.cancelled" and after == []
    assert queued.cancelled and not mine.cancelled
    calls = []
    monkeypatch.setitem(jobs_api._REGISTRY, "test.ticks", dataclasses.replace(
        jobs_api.get("test.ticks"), run=lambda i, p: calls.append(1) or jobs_api.JobResult("x")))
    asyncio.run(jobs._execute("q1"))
    assert queued.status == "failed" and queued.error_code == "jobs.cancelled" and calls == []


def test_a_job_whose_user_was_disabled_elsewhere_never_starts(member, monkeypatch):
    """e.g. `mm auth revoke --disable` or `mm auth delete-user` from another process."""
    c, data, (a, ta), (b, tb) = member
    calls = []
    from pydantic import BaseModel

    class In(BaseModel):
        pass
    monkeypatch.setitem(jobs_api._REGISTRY, "test.write", jobs_api.JobSpec(
        name="test.write", title="Write", description="", input_model=In, mutates=True, scope="user",
        run=lambda i, p: calls.append(1) or jobs_api.JobResult("x")))
    m = JobManager()
    store.revoke(b, disable=True)
    rec = JobRecord(id="w1", name="test.write", title="Write", inputs={}, user=b)
    m._jobs[rec.id] = rec
    asyncio.run(m._execute(rec.id))
    assert rec.status == "failed" and rec.error_code == "jobs.cancelled" and calls == []
    with layout.as_user(a):
        ok = JobRecord(id="w2", name="test.write", title="Write", inputs={}, user=a)
        m._jobs[ok.id] = ok
    asyncio.run(m._execute(ok.id))
    assert ok.status == "succeeded" and calls == [1]


def test_cancel_user_marks_only_their_unfinished_jobs():
    m = JobManager()
    for rid, user, status in (("1", "u", "queued"), ("2", "u", "running"), ("3", "u", "succeeded"), ("4", "v", "queued")):
        m._jobs[rid] = JobRecord(id=rid, name="x", title="X", inputs={}, status=status, user=user)
    assert m.cancel_user("u") == 2
    assert [m._jobs[i].cancelled for i in "1234"] == [True, True, False, False]
    assert "cancelled" not in m._jobs["1"].public()
    assert m.wait_idle("v", 0.05) is False and m.wait_idle("w", 0.05) is True


# ---------- 8. supply chain ----------

def test_base_images_and_actions_are_pinned():
    froms = re.findall(r"^FROM\s+(\S+)", (ROOT / "Dockerfile").read_text(), re.M)
    assert froms and all(re.search(r"@sha256:[0-9a-f]{64}$", f) for f in froms), froms
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        for uses in re.findall(r"uses:\s*(\S+)", wf.read_text()):
            if uses.startswith("./"):
                continue
            assert re.search(r"@[0-9a-f]{40}$", uses), f"{wf.name}: {uses} isn't pinned to a commit SHA"


def test_deploys_run_no_install_hooks_and_verify_commits():
    kit = ROOT / "deploy" / "macos"
    for script in (kit / "bin" / "deploy.sh", kit / "bin" / "upgrade.sh", ROOT / "Dockerfile"):
        text = script.read_text()
        assert re.findall(r"npm (?:--prefix web )?ci\b", text), script
        assert all("--ignore-scripts" in line for line in text.splitlines() if re.search(r"npm (?:--prefix web )?ci\b", line)), script
    assert "verify_main" in (kit / "bin" / "deploy.sh").read_text() and "verify_main" in (kit / "bin" / "upgrade.sh").read_text()
    fpr = re.search(r"^MM_WEBFLOW_FPR=([0-9A-F]{40})$", (kit / "bin" / "common.sh").read_text(), re.M).group(1)
    assert fpr == "968479A1AFF927E37D1A566BB5690EEEBB952194"
    assert "BEGIN PGP PUBLIC KEY BLOCK" in (kit / "web-flow.gpg").read_text()


def test_a_members_reads_neither_flag_nor_clear_a_scraper(member, health_file):
    c, data, (a, ta), (b, tb) = member
    key = scraper_health.store_key("bestbuy")
    with layout.as_user(b):
        scraper_health.record_use(key, "fail", "scrape.no_price")      # e.g. an empty companion extract
    assert key not in json.loads(health_file.read_text() if health_file.exists() else '{"scrapers": {}}')["scrapers"]
    with layout.as_user(a):
        scraper_health.record_use(key, "fail", "scrape.no_price")
    with layout.as_user(b):
        scraper_health.record_use(key, "ok")                            # a member can't hide it either
    assert json.loads(health_file.read_text())["scrapers"][key]["status"] == "down"
