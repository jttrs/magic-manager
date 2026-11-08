"""/api/preferences/collection — GET shape, PUT ok / 422 / 404, null resets, per-user in hosted."""
from __future__ import annotations

from fastapi.testclient import TestClient

from magic_manager.web.app import create_app

from test_auth import ORIGIN, hosted, me, provider, sign_in  # noqa: F401 — fixtures
from test_admin import people  # noqa: F401 — fixture

URL = "/api/preferences/collection"


def test_get_shape(tmp_db):
    c = TestClient(create_app(serve_frontend=False))
    body = c.get(URL).json()
    assert [p["key"] for p in body["prefs"]][0] == "set_types"
    p = next(p for p in body["prefs"] if p["key"] == "datestamped")
    assert p["kind"] == "choice" and p["value"] == "hide" and p["default"] == "hide" and p["changed"] is False
    assert p["choices"] == [{"value": "hide", "label": "Leave out"}, {"value": "show", "label": "Include"}]
    m = next(p for p in body["prefs"] if p["key"] == "missing_rarities")
    assert m["kind"] == "multi" and m["value"] == ["rare", "mythic", "uncommon_chase"]


def test_put_ok_422_404_and_reset(tmp_db):
    c = TestClient(create_app(serve_frontend=False))
    r = c.put(f"{URL}/datestamped", json={"value": "show"})
    assert r.status_code == 200, r.text
    p = next(p for p in r.json()["prefs"] if p["key"] == "datestamped")
    assert p["value"] == "show" and p["changed"] is True
    assert c.put(f"{URL}/datestamped", json={"value": "maybe"}).status_code == 422
    assert c.put(f"{URL}/missing_rarities", json={"value": []}).status_code == 422
    assert c.put(f"{URL}/nope", json={"value": "x"}).status_code == 404
    assert c.put(f"{URL}/datestamped", json={"value": "show", "extra": 1}).status_code == 422
    r = c.put(f"{URL}/datestamped", json={"value": None})
    assert next(p for p in r.json()["prefs"] if p["key"] == "datestamped")["changed"] is False
    r = c.put(f"{URL}/missing_rarities", json={"value": ["common", "rare"]})
    assert next(p for p in r.json()["prefs"] if p["key"] == "missing_rarities")["value"] == ["rare", "common"]


def test_hosted_prefs_are_per_user(people):
    (ca, ha, _a), (cm, hm, _m) = people
    r = cm.put(f"{URL}/foil_twins", json={"value": "once"}, headers=hm)   # a member may set their own
    assert r.status_code == 200, r.text
    mine = next(p for p in cm.get(URL).json()["prefs"] if p["key"] == "foil_twins")
    admin = next(p for p in ca.get(URL).json()["prefs"] if p["key"] == "foil_twins")
    assert mine["value"] == "once" and admin["value"] == "each"
