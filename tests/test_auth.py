"""Hosted sign-in (§25.4 step 4): auth.db, invite-only OAuth, sessions, CSRF, the gate.

Offline: provider HTTP goes through an httpx MockTransport; Google ID tokens are
signed with a throwaway RSA key."""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey
from typer.testing import CliRunner

from magic_manager import analytics, auth, secrets as secrets_mod
from magic_manager.analytics import identity
from magic_manager.auth import oauth, store
from magic_manager.cli import app as cli_app
from magic_manager.web import auth_routes
from magic_manager.web.app import create_app

ORIGIN = "http://localhost:8784"
GOOGLE_CID = "google-client.apps.example"


# ---------- auth.db ----------

def test_invite_is_single_use_and_stored_hashed():
    inv = store.create_invite(is_admin=True)
    raw = sqlite3.connect(store.path()).execute("SELECT code_hash FROM invites").fetchall()
    assert raw == [(store.hash_secret(inv.code),)]
    user = store.redeem_invite(inv.code, "discord", "123", "Owner", "o@example.com")
    assert user.is_admin and len(user.id) == 16 and user.id.isalnum() and user.id == user.id.lower()
    with pytest.raises(store.InviteInvalid):
        store.redeem_invite(inv.code, "google", "456", "Other", None)
    assert store.user_for_identity("discord", "123") == user


def test_expired_and_unknown_invites_refused(monkeypatch):
    with pytest.raises(store.InviteInvalid):
        store.invite_is_admin("nope")
    inv = store.create_invite(is_admin=True, expires_in=timedelta(minutes=1))
    later = store._now() + timedelta(minutes=2)
    monkeypatch.setattr(store, "_now", lambda: later)
    with pytest.raises(store.InviteInvalid):
        store.redeem_invite(inv.code, "discord", "1", "X", None)


def test_sessions_hash_rotate_expire_and_die_with_disable(monkeypatch):
    user = store.redeem_invite(store.create_invite(is_admin=True).code, "discord", "1", "A", None)
    s1 = store.create_session(user.id)
    stored = sqlite3.connect(store.path()).execute("SELECT token_hash FROM sessions").fetchall()
    assert stored == [(store.hash_secret(s1.token),)]  # never the token itself
    got = store.session_for(s1.token)
    assert got and got.user.id == user.id and store.csrf_matches(got, s1.csrf_token)
    assert not store.csrf_matches(got, "wrong") and not store.csrf_matches(got, None)
    # rotation: a new sign-in replaces the presented session
    s2 = store.create_session(user.id, replaces=s1.token)
    assert store.session_for(s1.token) is None and store.session_for(s2.token)
    # idle expiry
    now = store._now()
    monkeypatch.setattr(store, "_now", lambda: now + store.SESSION_IDLE + timedelta(seconds=1))
    assert store.session_for(s2.token) is None
    monkeypatch.setattr(store, "_now", lambda: now)
    # absolute expiry, even when active
    s3 = store.create_session(user.id)
    t = now
    for _ in range(4):  # touch every 10 days, never idle
        t += timedelta(days=10)
        monkeypatch.setattr(store, "_now", lambda t=t: t)
        alive = store.session_for(s3.token)
    assert alive is None  # day 40 > 30-day absolute cap
    monkeypatch.setattr(store, "_now", lambda: now)
    # disabled users' sessions die
    s4 = store.create_session(user.id)
    assert store.revoke(user.id, disable=True) >= 1
    assert store.session_for(s4.token) is None
    s5 = store.create_session(user.id)
    assert store.session_for(s5.token) is None  # disabled: refused on sight


def test_end_session_and_prune():
    user = store.redeem_invite(store.create_invite(is_admin=True).code, "google", "g", "B", None)
    s = store.create_session(user.id)
    assert store.end_session(s.token) and store.session_for(s.token) is None
    assert store.prune_sessions() == 0


def test_auth_db_lives_in_the_data_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("MM_AUTH_DB")
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(tmp_path / "x" / "magic_manager.db"))
    assert store.path() == tmp_path / "x" / "auth.db"
    monkeypatch.delenv("MAGIC_MANAGER_DB")
    monkeypatch.setenv("MM_LAYOUT", "split")
    monkeypatch.setenv("MM_DATA_DIR", str(tmp_path / "data"))
    assert store.path() == tmp_path / "data" / "auth.db"


# ---------- config ----------

@pytest.mark.parametrize("value,ok", [
    ("http://localhost:8784", True), ("https://cards.example.com/", True),
    ("http://cards.example.com", False), ("https://x.com/path", False), ("ftp://x", False),
])
def test_public_origin_validation(monkeypatch, value, ok):
    monkeypatch.setenv("MM_PUBLIC_ORIGIN", value)
    if ok:
        assert auth.public_origin() == value.rstrip("/")
    else:
        with pytest.raises(auth.HostedConfigError):
            auth.public_origin()


def test_hosted_refuses_to_start_without_origin_or_provider(monkeypatch, tmp_db):
    monkeypatch.setattr(secrets_mod, "_dotenv_get", lambda name: None)
    monkeypatch.setenv("MM_MODE", "hosted")
    with pytest.raises(auth.HostedConfigError, match="MM_PUBLIC_ORIGIN"):
        create_app(serve_frontend=False)
    monkeypatch.setenv("MM_PUBLIC_ORIGIN", ORIGIN)
    with pytest.raises(auth.HostedConfigError, match="provider"):
        create_app(serve_frontend=False)
    result = CliRunner().invoke(cli_app, ["serve", "--port", "1"])
    assert result.exit_code == 2 and "provider" in result.output


# ---------- local mode: today exactly ----------

def test_local_mode_has_no_login(tmp_db):
    c = TestClient(create_app(serve_frontend=False))
    assert c.get("/api/auth/me").status_code == 404
    assert c.get("/api/undo").status_code == 200
    assert c.post("/api/auth/logout").status_code in (404, 405)
    assert not any(r.path.startswith("/api/auth") for r in api_routes(create_app(serve_frontend=False)))


# ---------- hosted ----------

@pytest.fixture
def hosted(monkeypatch, tmp_db):
    monkeypatch.setattr(secrets_mod, "_dotenv_get", lambda name: None)
    monkeypatch.setenv("MM_MODE", "hosted")
    monkeypatch.setenv("MM_PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.setenv("MM_OAUTH_DISCORD_CLIENT_ID", "discord-cid")
    monkeypatch.setenv("MM_OAUTH_DISCORD_CLIENT_SECRET", "discord-secret")
    monkeypatch.setenv("MM_OAUTH_GOOGLE_CLIENT_ID", GOOGLE_CID)
    monkeypatch.setenv("MM_OAUTH_GOOGLE_CLIENT_SECRET", "google-secret")
    oauth.reset()
    auth_routes.login_limiter.reset()
    auth_routes.write_limiter.reset()
    app = create_app(serve_frontend=False)
    yield app
    oauth.reset()


class Provider:
    """Fake Discord + Google endpoints."""

    def __init__(self) -> None:
        self.key = RSAKey.generate_key(2048, parameters={"kid": "k1"})
        self.discord_user = {"id": "d-1", "username": "owner", "global_name": "The Owner",
                             "email": "owner@example.com", "verified": True}
        self.google_claims: dict = {"sub": "g-1", "name": "G Owner", "email": "g@example.com", "email_verified": True}
        self.nonce: str | None = None
        self.token_requests: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == oauth.DISCORD.token_url:
            self.token_requests.append(parse_qs(request.content.decode()))
            return httpx.Response(200, json={"access_token": "at", "token_type": "Bearer"})
        if url == oauth.DISCORD_ME:
            assert request.headers["authorization"] == "Bearer at"
            return httpx.Response(200, json=self.discord_user)
        if url == oauth.GOOGLE.token_url:
            self.token_requests.append(parse_qs(request.content.decode()))
            claims = {"iss": "https://accounts.google.com", "aud": GOOGLE_CID, "exp": 4_000_000_000,
                      "iat": 1_700_000_000, "nonce": self.nonce, **self.google_claims}
            return httpx.Response(200, json={"access_token": "at", "id_token": jwt.encode({"alg": "RS256", "kid": "k1"}, claims, self.key)})
        if url == oauth.GOOGLE_JWKS:
            return httpx.Response(200, json=KeySet([self.key]).as_dict(private=False))
        return httpx.Response(404)


@pytest.fixture
def provider(monkeypatch):
    p = Provider()
    monkeypatch.setattr(oauth, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(p.handler)))
    return p


def _client(app) -> TestClient:
    return TestClient(app, base_url=ORIGIN)


def sign_in(c: TestClient, provider: Provider, name: str, invite: str | None = None, next_path: str | None = None):
    params = {k: v for k, v in (("invite", invite), ("next", next_path)) if v}
    r = c.get(f"/api/auth/login/{name}", params=params, follow_redirects=False)
    assert r.status_code == 303, r.text
    loc = urlsplit(r.headers["location"])
    if loc.path == "/":  # refused before reaching the provider
        return r
    q = {k: v[0] for k, v in parse_qs(loc.query).items()}
    assert q["code_challenge_method"] == "S256" and q["redirect_uri"] == f"{ORIGIN}/api/auth/callback/{name}"
    assert "invite" not in r.headers["location"]  # the invite never goes to the provider
    provider.nonce = q.get("nonce")
    return c.get(f"/api/auth/callback/{name}", params={"code": "the-code", "state": q["state"]}, follow_redirects=False)


def _error(r) -> str | None:
    q = parse_qs(urlsplit(r.headers["location"]).query)
    return q.get("auth_error", [None])[0]


def me(c: TestClient) -> dict:
    return c.get("/api/auth/me").json()


@pytest.mark.parametrize("name", ["discord", "google"])
def test_invite_sign_in_creates_admin_then_signs_in_without_invite(hosted, provider, name):
    c = _client(hosted)
    assert me(c)["user"] is None
    inv = store.create_invite(is_admin=True)
    r = sign_in(c, provider, name, invite=inv.code, next_path="/decks")
    assert r.status_code == 303 and r.headers["location"] == "/decks"
    body = me(c)
    assert body["user"]["is_admin"] and body["csrf_token"]
    assert body["user"]["display_name"] in ("The Owner", "G Owner")
    # PKCE verifier was sent with the code; no token is stored anywhere
    assert provider.token_requests[-1]["code_verifier"][0]
    dump = "\n".join(sqlite3.connect(store.path()).iterdump())
    assert "the-code" not in dump and '"at"' not in dump and "'at'" not in dump
    # known identity: no invite needed; the session rotates
    old_cookie = c.cookies.get("mm_session")
    r = sign_in(c, provider, name)
    assert r.headers["location"] == "/" and c.cookies.get("mm_session") != old_cookie
    assert me(c)["user"]["id"] == body["user"]["id"]
    assert store.session_for(old_cookie) is None


def test_session_cookie_attributes(hosted, provider):
    c = _client(hosted)
    r = sign_in(c, provider, "discord", invite=store.create_invite(is_admin=True).code)
    cookie = [h for h in r.headers.get_list("set-cookie") if h.startswith("mm_session=")][0].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie


def test_https_origin_uses_host_prefix_and_secure(monkeypatch):
    monkeypatch.setenv("MM_PUBLIC_ORIGIN", "https://cards.example.com")
    assert auth_routes.cookie_name() == "__Host-mm_session" and auth.secure_cookies()


def test_unknown_identity_without_invite_is_refused(hosted, provider):
    c = _client(hosted)
    r = sign_in(c, provider, "discord")
    assert _error(r) == "not_invited" and me(c)["user"] is None
    assert store.users() == []


def test_bad_and_used_invites_refused(hosted, provider):
    c = _client(hosted)
    assert _error(sign_in(c, provider, "discord", invite="garbage")) == "invite_invalid"
    inv = store.create_invite(is_admin=True)
    sign_in(c, provider, "discord", invite=inv.code)
    provider.discord_user = {**provider.discord_user, "id": "d-2"}
    c2 = _client(hosted)
    assert _error(sign_in(c2, provider, "discord", invite=inv.code)) == "invite_invalid"


def test_state_must_match_this_browser(hosted, provider):
    c = _client(hosted)
    r = c.get("/api/auth/login/discord", follow_redirects=False)
    state = parse_qs(urlsplit(r.headers["location"]).query)["state"][0]
    other = _client(hosted)  # the victim's browser: no state cookie (login CSRF)
    r2 = other.get("/api/auth/callback/discord", params={"code": "x", "state": state}, follow_redirects=False)
    assert _error(r2) == "state"
    # and a state is single use
    r3 = c.get("/api/auth/callback/discord", params={"code": "x", "state": "forged"}, follow_redirects=False)
    assert _error(r3) == "state"


def test_provider_denial_and_failures(hosted, provider, monkeypatch):
    c = _client(hosted)
    r = c.get("/api/auth/login/discord", follow_redirects=False)
    state = parse_qs(urlsplit(r.headers["location"]).query)["state"][0]
    r = c.get("/api/auth/callback/discord", params={"error": "access_denied", "state": state}, follow_redirects=False)
    assert _error(r) == "denied"
    assert _error(c.get("/api/auth/login/github", follow_redirects=False)) == "provider_unavailable"
    monkeypatch.delenv("MM_OAUTH_GOOGLE_CLIENT_SECRET")
    assert _error(c.get("/api/auth/login/google", follow_redirects=False)) == "provider_unavailable"


def test_google_id_token_checks(hosted, provider):
    inv = store.create_invite(is_admin=True)
    c = _client(hosted)
    # wrong nonce (a replayed token)
    r = c.get("/api/auth/login/google", params={"invite": inv.code}, follow_redirects=False)
    state = parse_qs(urlsplit(r.headers["location"]).query)["state"][0]
    provider.nonce = "someone-elses-nonce"
    r = c.get("/api/auth/callback/google", params={"code": "c", "state": state}, follow_redirects=False)
    assert _error(r) == "id_token"
    # wrong audience
    provider.google_claims = {**provider.google_claims, "aud": "another-app"}
    assert _error(sign_in(c, provider, "google", invite=inv.code)) == "id_token"
    assert store.users() == []
    # unverified email is not stored
    provider.google_claims = {"sub": "g-9", "name": "N", "email": "x@example.com", "email_verified": False}
    sign_in(c, provider, "google", invite=inv.code)
    assert me(c)["user"]["email"] is None


def test_google_bad_signature_refused(hosted, provider):
    inv = store.create_invite(is_admin=True)
    real = provider.key
    provider.key = RSAKey.generate_key(2048, parameters={"kid": "k1"})  # signs with a key Google doesn't publish
    published = KeySet([real]).as_dict(private=False)
    orig = provider.handler

    def handler(request):
        if str(request.url) == oauth.GOOGLE_JWKS:
            return httpx.Response(200, json=published)
        return orig(request)
    provider.handler = handler
    c = _client(hosted)
    assert _error(sign_in(c, provider, "google", invite=inv.code)) == "id_token"


# ---------- step-5 rail: admins only ----------

def test_non_admin_invites_cannot_be_minted():
    r = CliRunner().invoke(cli_app, ["auth", "invite"])
    assert r.exit_code == 2 and "Profiles open soon" in r.output


def test_non_admin_can_never_reach_a_collection(hosted, provider):
    member = store.create_invite(is_admin=False)  # minted below the CLI (it refuses)
    c = _client(hosted)
    r = sign_in(c, provider, "discord", invite=member.code)
    assert _error(r) == "profiles_soon" and store.users() == []
    # even a member that somehow exists with a session is treated as signed out
    user = store.redeem_invite(store.create_invite(is_admin=False).code, "google", "m", "Member", None)
    s = store.create_session(user.id)
    c.cookies.set("mm_session", s.token)
    assert me(c)["user"] is None
    for path in ("/api/undo", "/api/collection", "/api/history", "/api/jobs"):
        assert c.get(path).status_code == 401
    assert c.post("/api/ingest/commit", json={}, headers={"Origin": ORIGIN, "X-CSRF-Token": s.csrf_token}).status_code == 401
    # and an existing member signing in through a provider is refused too
    provider.google_claims = {"sub": "m", "name": "Member", "email_verified": False}
    assert _error(sign_in(c, provider, "google")) == "profiles_soon"


def test_disabled_admin_refused_at_sign_in(hosted, provider):
    c = _client(hosted)
    sign_in(c, provider, "discord", invite=store.create_invite(is_admin=True).code)
    uid = me(c)["user"]["id"]
    store.revoke(uid, disable=True)
    assert me(c)["user"] is None
    assert _error(sign_in(c, provider, "discord")) == "disabled"


# ---------- the gate ----------

def api_routes(app) -> list[APIRoute]:
    """Every APIRoute, including those in included routers (FastAPI keeps them lazily)."""
    out: list[APIRoute] = []

    def walk(routes):
        for r in routes:
            if isinstance(r, APIRoute):
                out.append(r)  # an included router's paths already carry its prefix
            elif hasattr(r, "original_router"):
                walk(r.original_router.routes)
    walk(app.routes)
    return out


def _concrete(path: str) -> str:
    import re
    return re.sub(r"\{[^}]+\}", "x", path)


def test_every_api_route_needs_a_session_except_the_public_ones(hosted):
    c = _client(hosted)
    seen = 0
    routes = api_routes(hosted)
    assert {r.path for r in routes} >= {"/api/analytics/consent", "/api/scrapers/health", "/api/auth/me"}
    for route in routes:
        if not route.path.startswith("/api/"):
            continue
        if route.path in auth_routes.PUBLIC_ROUTES:
            continue
        for method in route.methods:
            r = c.request(method, _concrete(route.path), headers={"Origin": ORIGIN}, json={})
            assert r.status_code == 401, (method, route.path, r.status_code)
            assert r.json()["code"] == "auth.required" and r.json()["request_id"]
            seen += 1
    assert seen > 50
    # the allowlist is exactly the auth routes + features
    public = {r.path for r in routes if r.path in auth_routes.PUBLIC_ROUTES}
    assert public == set(auth_routes.PUBLIC_ROUTES)


@pytest.fixture
def admin(hosted, provider):
    c = _client(hosted)
    sign_in(c, provider, "discord", invite=store.create_invite(is_admin=True).code)
    return c, me(c)["csrf_token"]


def test_admin_reads_and_writes_with_csrf_and_origin(admin):
    c, csrf = admin
    assert c.get("/api/undo").status_code == 200
    ok = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
    r = c.put("/api/analytics/consent", json={"errors": True, "usage": False}, headers=ok)
    assert r.status_code == 200
    r = c.put("/api/analytics/consent", json={"errors": True, "usage": False}, headers={"Origin": ORIGIN})
    assert r.status_code == 403 and r.json()["code"] == "auth.csrf"
    r = c.put("/api/analytics/consent", json={"errors": True, "usage": False}, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf + "x"})
    assert r.json()["code"] == "auth.csrf"
    for origin in (None, "http://evil.example", "http://localhost:5173"):
        h = {"X-CSRF-Token": csrf} | ({"Origin": origin} if origin else {})
        r = c.put("/api/analytics/consent", json={"errors": True, "usage": False}, headers=h)
        assert r.status_code == 403 and r.json()["code"] == "auth.origin"
    # the Sec-Fetch-Site guard still applies
    r = c.put("/api/analytics/consent", json={"errors": True, "usage": False}, headers=ok | {"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403 and r.json()["code"] == "request.cross_site"


def test_sign_out_ends_the_session(admin):
    c, csrf = admin
    token = c.cookies.get("mm_session")
    assert c.post("/api/auth/logout", headers={"Origin": ORIGIN}).json()["code"] == "auth.csrf"
    assert c.post("/api/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}).status_code == 204
    assert store.session_for(token) is None
    c.cookies.set("mm_session", token)
    assert c.get("/api/undo").status_code == 401


def test_write_rate_limit(admin, monkeypatch):
    c, csrf = admin
    monkeypatch.setattr(auth_routes, "write_limiter", auth_routes.ratelimit.Limiter(2))
    h = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
    codes = [c.put("/api/analytics/consent", json={"errors": True, "usage": False}, headers=h).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_login_rate_limit_per_ip(hosted, monkeypatch):
    monkeypatch.setattr(auth_routes, "login_limiter", auth_routes.ratelimit.Limiter(3))
    c = _client(hosted)
    errs = [_error(c.get("/api/auth/login/discord", follow_redirects=False)) for _ in range(4)]
    assert errs == [None, None, None, "rate_limited"]


def test_me_lists_configured_providers_without_secrets(hosted, monkeypatch):
    monkeypatch.delenv("MM_OAUTH_GOOGLE_CLIENT_ID")
    body = me(_client(hosted))
    assert [p["name"] for p in body["providers"]] == ["discord"]
    assert body["profiles_open"] is False
    assert "secret" not in json.dumps(body)


def test_safe_next_only_same_origin_paths():
    assert oauth.safe_next("/decks?x=1") == "/decks?x=1"
    for bad in ("https://evil.example", "//evil.example", "/\\evil", "decks", None, "/a\nb"):
        assert oauth.safe_next(bad) == "/"


def test_access_log_redacts_query_strings():
    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                            ("1.2.3.4", "GET", "/api/auth/callback/discord?code=SECRET&state=S", "1.1", 303), None)
    auth_routes._redactor.filter(rec)
    assert "SECRET" not in rec.getMessage() and "/api/auth/callback/discord" in rec.getMessage()


def test_analytics_key_is_the_signed_in_user(admin, monkeypatch):
    c, csrf = admin
    uid = me(c)["user"]["id"]
    seen = {}
    monkeypatch.setattr(analytics, "forget_user", lambda user_id=None: seen.setdefault("uid", analytics.current().user_id) and 0)
    r = c.delete("/api/analytics/my-data", headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})
    assert r.status_code == 200 and seen["uid"] == uid
    assert identity.user_key(uid) != identity.user_key()
