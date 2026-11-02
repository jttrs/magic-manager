"""Phase 3 step 9 (H12, hosted): the browser companion holds NO credential for our API.

It hands approved lines to the paired app PAGE (postMessage); the page posts them with the
signed-in user's session cookie + CSRF header. So every companion-fed route is an ordinary
gated write: no session → 401, no/bad CSRF or a foreign origin → 403, and with both it writes
only the signed-in user's own collection file.
"""
from __future__ import annotations

import subprocess

import pytest

from magic_manager import db, features, layout, owner_machine
from magic_manager.auth import admin as admin_engine
from magic_manager.web import auth_routes

from test_auth import ORIGIN, hosted, me, provider, sign_in  # noqa: F401 — fixtures
from test_user_connections import B_ID, _as, _copies, _sha, owner_split, two_users  # noqa: F401 — fixtures

# Every route the companion's reads land on (via the app page), with a valid body.
COMPANION_ROUTES = [
    ("/api/cart/lines", {"items": [{"scryfall_id": B_ID, "name": "Beta", "quantity": 1}], "source": "extension"}),
    ("/api/deals/tabs", {"tabs": [{"url": "https://www.coolstuffinc.com/p/1", "title": "x"}]}),
    ("/api/ingest/deck-from-browser", {"source": "archidekt", "deck": {"id": 1, "name": "D", "cards": [
        {"quantity": 1, "card": {"uid": B_ID, "oracleCard": {"name": "Beta"}}}]}}),
    ("/api/collection/import/preview", {"source": "moxfield", "scope": "collection", "lines": [
        {"quantity": 3, "finish": "nonfoil", "scryfall_id": B_ID}]}),
    ("/api/collection/import/apply", {"source": "moxfield", "scope": "collection", "mode": "add", "lines": [
        {"quantity": 3, "finish": "nonfoil", "scryfall_id": B_ID}]}),
    ("/api/purchases/orders", {"store": "manapool", "orders": [{"order_id": "MP-1", "ordered_at": "2026-10-01", "lines": [
        {"name": "Beta", "scryfall_id": B_ID, "quantity": 2, "price": 1.5}]}]}),
    ("/api/jobs/deals.watchlist", {"refresh": True, "in_browser": True, "pages": {}}),
]


@pytest.fixture
def member(two_users, monkeypatch):
    """Member B with every flag on (an admin's override), the network and subprocesses off."""
    c, data, (a, ta), (b, tb) = two_users
    for flag in features.base_flags():
        admin_engine.set_flag(b, flag, True, actor=a)

    def offline(*_a, **_k):
        raise OSError("offline in this test")
    for name in ("run", "Popen", "check_output", "check_call"):
        monkeypatch.setattr(subprocess, name, offline)
    from magic_manager import scryfall

    def scryfall_offline(*_a, **_k):
        raise scryfall.ScryfallError("offline in this test")
    monkeypatch.setattr(scryfall, "_run", scryfall_offline)
    from magic_manager import cart
    monkeypatch.setattr(cart, "infer_set_anchors", lambda mapped: [])
    monkeypatch.setattr(auth_routes, "write_limiter", auth_routes.ratelimit.Limiter(100_000))
    return two_users


def _route_ok(r) -> bool:
    return 200 <= r.status_code < 300


@pytest.mark.parametrize(("path", "body"), COMPANION_ROUTES, ids=[p for p, _ in COMPANION_ROUTES])
def test_companion_routes_need_a_session_csrf_and_the_apps_origin(member, path, body):
    c, data, (a, ta), (b, tb) = member
    good = _as(c, tb)
    csrf = good["X-CSRF-Token"]
    c.cookies.clear()
    r = c.post(path, json=body, headers=good)
    assert r.status_code == 401 and r.json()["code"] == "auth.required", r.text
    c.cookies.set("mm_session", tb)
    r = c.post(path, json=body, headers={"Origin": ORIGIN})
    assert r.status_code == 403 and r.json()["code"] == "auth.csrf"
    r = c.post(path, json=body, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf + "x"})
    assert r.status_code == 403 and r.json()["code"] == "auth.csrf"
    for origin in ("https://evil.example", "http://localhost:5173"):
        r = c.post(path, json=body, headers={"Origin": origin, "X-CSRF-Token": csrf})
        assert r.status_code == 403 and r.json()["code"] == "auth.origin"
    r = c.post(path, json=body, headers=good | {"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403 and r.json()["code"] == "request.cross_site"
    # A's session token + B's CSRF token: refused (the CSRF token is bound to the session)
    c.cookies.set("mm_session", ta)
    r = c.post(path, json=body, headers=good)
    assert r.status_code == 403 and r.json()["code"] == "auth.csrf"
    c.cookies.set("mm_session", tb)
    r = c.post(path, json=body, headers=good)
    assert _route_ok(r), (path, r.status_code, r.text)


def test_companion_writes_land_only_in_the_signed_in_users_file(member, monkeypatch):
    c, data, (a, ta), (b, tb) = member
    a_files = [data / "users" / f"{a}.db", data / "users" / f"{a}.undo.db"]
    _as(c, ta)  # make sure A's restore point exists before the sweep
    before = [_sha(p) for p in a_files]
    opened: list = []
    real_open = db._open_split
    monkeypatch.setattr(db, "_open_split", lambda lay: opened.append(lay.path) or real_open(lay))
    with layout.as_user(b):
        b_before = _copies()
    h = _as(c, tb)
    results = {path: c.post(path, json=body, headers=h) for path, body in COMPANION_ROUTES}
    assert all(_route_ok(r) for r in results.values()), {p: (r.status_code, r.text[:200]) for p, r in results.items()}
    assert results["/api/collection/import/apply"].status_code == 200, results["/api/collection/import/apply"].text
    assert results["/api/purchases/orders"].json()["saved"] == 1
    job = results["/api/jobs/deals.watchlist"].json()["id"]
    with layout.as_user(b):
        assert _copies() == b_before + 3
        with db.connect() as conn:
            assert conn.execute("SELECT COUNT(*) FROM purchases").fetchone()[0] == 1
    assert set(opened) == {data / "users" / f"{b}.db"}, sorted(set(opened))
    assert [_sha(p) for p in a_files] == before
    with layout.as_user(a), db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM purchases").fetchone()[0] == 0
    # the watched-page read runs as B: A can't even see the job
    assert c.get(f"/api/jobs/{job}").status_code == 200
    _as(c, ta)
    assert c.get(f"/api/jobs/{job}").status_code == 404


def test_member_moxfield_import_never_reaches_a_server_browser(member, monkeypatch):
    """A member's Moxfield link: refused before any process starts (the companion reads it);
    the job fails with the coded refusal and a 'use the companion' hint."""
    from magic_manager import addcards, browser_launch
    c, data, (a, ta), (b, tb) = member
    started: list = []
    monkeypatch.setattr(addcards.subprocess, "Popen", lambda *a, **k: started.append(a) or (_ for _ in ()).throw(AssertionError("spawned")))
    with layout.as_user(b):
        with pytest.raises(owner_machine.OwnerOnly) as e:
            addcards.fetch_deck_lines("https://www.moxfield.com/decks/abcdef")
        assert e.value.error_code == "auth.admin_only" and "browser companion" in str(e.value)
    assert started == []
    # the launch seam itself refuses in a process started for a member
    monkeypatch.setenv(browser_launch.NO_SERVER_BROWSER_ENV, "1")
    with pytest.raises(browser_launch.ServerBrowserRefused):
        browser_launch.launch(object(), headless=True)


def test_a_deck_url_is_never_read_as_an_option(member, monkeypatch):
    """`--file=<server path>` as the "URL" can't make import_deck.py read a server file."""
    from magic_manager import addcards
    from magic_manager.api import ingest as ingest_api
    with pytest.raises(ValueError):
        ingest_api.FetchDeckInput(url="--file=/etc/passwd")
    assert ingest_api.FetchDeckInput(url="Https://archidekt.com/decks/1").url   # a capitalised scheme still reads
    with pytest.raises(RuntimeError):
        addcards.fetch_deck_payload("--file=/etc/passwd")
    from test_user_connections import _fetch_args
    args = _fetch_args(monkeypatch, "https://archidekt.com/decks/1")
    assert args["argv"][-2:] == ["--", "https://archidekt.com/decks/1"]


def test_subprocess_seams_refuse_a_server_browser(monkeypatch):
    """The fetcher's own guards (behind the pre-spawn refusal): --no-browser / MM_NO_SERVER_BROWSER
    stop Moxfield in import_deck.py and any MoxfieldSession, anonymous included."""
    from magic_manager import browser_launch
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    import import_deck
    import moxfield_session
    monkeypatch.setenv(browser_launch.NO_SERVER_BROWSER_ENV, "1")
    with pytest.raises(RuntimeError, match="browser companion"):
        import_deck.fetch_moxfield("abcdef", fresh=False)
    for kw in ({"anonymous": True}, {"anonymous": False}):
        with pytest.raises(RuntimeError, match="browser companion"):
            moxfield_session.MoxfieldSession(**kw)
