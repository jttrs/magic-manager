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


# ---------- per-family rule switches ----------

def _rule_fixture(monkeypatch):
    import magic_manager.scryfall as scry
    from magic_manager import config, selectors
    monkeypatch.setattr(scry, "all_sets", lambda: [])
    hard = {"promo_types_any_of": frozenset({"zzstamp"}), "tier": "hard"}
    prop = {"set_codes": frozenset({"tla"}), "collector_numbers": frozenset({"9"}), "note": "n"}
    monkeypatch.setattr(selectors, "FAMILY_UNOBTAINABLE_RULES", {"tla": [hard]})
    monkeypatch.setattr(selectors, "FAMILY_PROPOSED_RULES", {"tla": [prop]})
    return config.rule_id(hard), config.rule_id(prop)


def test_family_rules_shape_put_reset_and_errors(tmp_db, monkeypatch):
    hid, pro = _rule_fixture(monkeypatch)
    c = TestClient(create_app(serve_frontend=False))
    fams = c.get(f"{URL}/families").json()["families"]
    assert (fams[0]["code"], fams[0]["rules"], fams[0]["changed"]) == ("tla", 2, 0)
    body = c.get(f"{URL}/families/tla").json()
    assert body["code"] == "tla" and [r["id"] for r in body["rules"]] == [hid, pro]
    r0 = body["rules"][1]
    assert r0["default"] == "count" and r0["state"] == "count" and r0["changed"] is False and r0["note"] == "n"
    assert r0["prints"] is None and "Set: tla" in r0["description"]
    r = c.put(f"{URL}/families/tla/rules/{pro}", json={"state": "hide"})
    assert r.status_code == 200, r.text
    assert next(x for x in r.json()["rules"] if x["id"] == pro)["changed"] is True
    assert c.get(f"{URL}/families").json()["families"][0]["changed"] == 1
    assert c.put(f"{URL}/families/tla/rules/{pro}", json={"state": "maybe"}).status_code == 422
    assert c.put(f"{URL}/families/tla/rules/{pro}", json={"state": "hide", "x": 1}).status_code == 422
    assert c.put(f"{URL}/families/nope/rules/{pro}", json={"state": "hide"}).status_code == 404
    assert c.put(f"{URL}/families/tla/rules/deadbeef00", json={"state": "hide"}).status_code == 404
    assert c.get(f"{URL}/families/nope").status_code == 404
    r = c.put(f"{URL}/families/tla/rules/{pro}", json={"state": None})
    assert next(x for x in r.json()["rules"] if x["id"] == pro)["changed"] is False


def test_hosted_family_rules_are_per_user(people, monkeypatch):
    hid, pro = _rule_fixture(monkeypatch)
    (ca, ha, _a), (cm, hm, _m) = people
    r = cm.put(f"{URL}/families/tla/rules/{pro}", json={"state": "chase"}, headers=hm)
    assert r.status_code == 200, r.text
    mine = next(x for x in cm.get(f"{URL}/families/tla").json()["rules"] if x["id"] == pro)
    admin = next(x for x in ca.get(f"{URL}/families/tla").json()["rules"] if x["id"] == pro)
    assert mine["state"] == "chase" and admin["state"] == "count"
