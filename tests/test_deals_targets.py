"""V33 price targets on watched products: set/clear, met, and newly met by a read."""
from __future__ import annotations

import sqlite3

import pytest

from magic_manager import db, deals, earmarks, market, sealed, valuation


@pytest.fixture
def watched(tmp_db, monkeypatch):
    """One watched sealed product (market $80) at two stores; reads are stubbed per test."""
    monkeypatch.setattr(earmarks, "resolve_identity", lambda set_code, name: {
        "kind": "sealed", "set_code": set_code, "name": name, "uuid": "u-1", "category": "deck"})
    monkeypatch.setattr(valuation, "value_sealed_product", lambda set_code, name, **kw: sealed.ProductValuation(
        label=name, kind="sealed", sealed_market=80.0, intrinsic=95.0))
    monkeypatch.setattr(sealed, "identify_product", lambda set_code, name: {"name": name, "category": "deck"})
    market._cost_memo.clear()
    a, b = "https://a.example/products/deck", "https://b.example/products/deck"
    deals.watch(a, {"kind": "sealed", "set_code": "c18", "name": "Deck"}, price=75.0)
    deals.watch(b, {"kind": "sealed", "set_code": "c18", "name": "Deck"}, price=78.0)
    [p] = earmarks.earmark_list()
    yield {"pid": p.product_id, "a": a, "b": b}
    market._cost_memo.clear()


def _stub_reads(monkeypatch, prices: dict[str, tuple[float, bool | None]]):
    monkeypatch.setattr(deals, "read_prices", lambda urls, **kw: [
        {"url": u, "price": prices[u][0], "currency": "USD", "available": prices[u][1], "title": None,
         "signal": "shopify", "error": None} for u in urls])


def test_v33_creates_targets_table(tmp_db):
    with db.connect() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(earmark_targets)")]
        assert cols == ["product_id", "mode", "value", "set_at"]
        conn.execute("INSERT INTO earmarked_products (set_code, product_name, earmarked_at) VALUES ('x', 'P', 'now')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO earmark_targets VALUES (1, 'pct_under', 120, 'now')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO earmark_targets VALUES (1, 'bogus', 5, 'now')")


def test_set_replace_clear_and_cascade(watched):
    pid = watched["pid"]
    t = earmarks.set_target(pid, "price", 70)
    assert (t["mode"], t["value"]) == ("price", 70.0)
    earmarks.set_target(pid, "pct_under", 15)
    assert earmarks.targets() == {pid: {**earmarks.targets()[pid], "mode": "pct_under", "value": 15.0}}
    with pytest.raises(ValueError):
        earmarks.set_target(pid, "pct_under", 100)
    with pytest.raises(ValueError):
        earmarks.set_target(pid, "price", 0)
    with pytest.raises(LookupError):
        earmarks.set_target(999, "price", 5)
    assert earmarks.clear_target(pid) and earmarks.targets() == {}
    earmarks.set_target(pid, "price", 70)
    earmarks.earmark_remove_product("c18", "Deck")
    assert earmarks.targets() == {}                      # goes with its product


def test_threshold():
    assert earmarks.target_threshold(None, 80) is None
    assert earmarks.target_threshold({"mode": "price", "value": 70}, None) == 70
    assert earmarks.target_threshold({"mode": "pct_under", "value": 10}, None) is None
    assert earmarks.target_threshold({"mode": "pct_under", "value": 10}, 80) == 72.0


def test_watchlist_carries_target_and_store_range(watched):
    earmarks.set_target(watched["pid"], "price", 76)
    earmarks.record_reads([{"url": watched["a"], "price": 82.0, "available": True},
                           {"url": watched["a"], "price": 79.0, "available": True}])
    [w] = deals.watchlist(values=False)
    assert (w["product_id"], w["target"]["mode"], w["target_price"]) == (watched["pid"], "price", 76.0)
    a = next(s for s in w["stores"] if s["url"] == watched["a"])
    assert (a["first_price"], a["low"], a["high"], a["price"]) == (75.0, 75.0, 82.0, 79.0)
    assert w["target_met"] is False                     # best in stock: b at 78 (a now 79)


def test_sold_out_price_never_meets_a_target(watched):
    earmarks.set_target(watched["pid"], "price", 70)
    earmarks.record_reads([{"url": watched["a"], "price": 60.0, "available": False}])
    [w] = deals.watchlist(values=False)
    assert w["best_price"] == 78.0 and w["target_met"] is False


def test_pct_target_price_needs_the_market(watched):
    earmarks.set_target(watched["pid"], "pct_under", 10)   # 10% under $80 → $72
    [w] = deals.watchlist(values=False)
    assert w["target_price"] is None and w["target_met"] is None   # instant list has no sealed market
    [w] = deals._with_target_prices(deals.watchlist(values=False))
    assert (w["target_price"], w["target_met"]) == (72.0, False)


def test_read_reports_only_newly_met_targets(watched, monkeypatch):
    earmarks.set_target(watched["pid"], "pct_under", 10)
    _stub_reads(monkeypatch, {watched["a"]: (71.5, True), watched["b"]: (90.0, True)})
    res = deals.read_watched()
    [hit] = res["newly_met"]
    assert (hit["price"], hit["url"], hit["target_price"]) == (71.5, watched["a"], 72.0)
    assert res["rows"][0]["target_met"] is True
    assert deals.read_watched()["newly_met"] == []           # still met — not new again
    _stub_reads(monkeypatch, {watched["a"]: (74.0, True), watched["b"]: (90.0, True)})
    assert deals.read_watched()["newly_met"] == []           # no longer met
    _stub_reads(monkeypatch, {watched["a"]: (74.0, True), watched["b"]: (70.0, True)})
    assert [h["url"] for h in deals.read_watched()["newly_met"]] == [watched["b"]]


def test_no_target_no_notice(watched, monkeypatch):
    _stub_reads(monkeypatch, {watched["a"]: (1.0, True), watched["b"]: (1.0, True)})
    assert deals.read_watched()["newly_met"] == []


def test_target_routes(watched, monkeypatch):
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app
    monkeypatch.setenv("MM_FEATURES", "deals")
    client = TestClient(create_app(serve_frontend=False))
    pid = watched["pid"]
    r = client.put("/api/deals/target", json={"product_id": pid, "mode": "price", "value": 70})
    assert r.status_code == 200 and r.json()["value"] == 70.0
    assert client.get("/api/deals/watched").json()[0]["target_price"] == 70.0
    assert client.put("/api/deals/target", json={"product_id": pid, "mode": "pct_under", "value": 150}).status_code == 422
    assert client.put("/api/deals/target", json={"product_id": 999, "mode": "price", "value": 5}).status_code == 404
    assert client.delete(f"/api/deals/target?product_id={pid}").status_code == 204
    assert client.get("/api/deals/watched").json()[0]["target"] is None


@pytest.mark.parametrize("mode,value", [("pct_under", 99.996), ("price", 0.004)])
def test_target_rounds_before_validating(watched, monkeypatch, mode, value):
    with pytest.raises(ValueError):
        earmarks.set_target(watched["pid"], mode, value)
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app
    monkeypatch.setenv("MM_FEATURES", "deals")
    client = TestClient(create_app(serve_frontend=False))
    r = client.put("/api/deals/target", json={"product_id": watched["pid"], "mode": mode, "value": value})
    assert r.status_code == 422


def test_target_route_maps_integrity_error(watched, monkeypatch):
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app
    monkeypatch.setenv("MM_FEATURES", "deals")
    def boom(*a, **k):
        raise sqlite3.IntegrityError("CHECK failed")
    monkeypatch.setattr(earmarks, "set_target", boom)
    client = TestClient(create_app(serve_frontend=False))
    r = client.put("/api/deals/target", json={"product_id": watched["pid"], "mode": "price", "value": 5})
    assert r.status_code == 422


def test_unexpected_target_price_error_is_logged_not_hidden(watched, monkeypatch, caplog):
    earmarks.set_target(watched["pid"], "pct_under", 10)
    market._cost_memo.clear()
    def bug(*a, **k):
        raise AttributeError("oops")
    monkeypatch.setattr(valuation, "value_sealed_product", bug)
    with caplog.at_level("ERROR"):
        rows = deals._with_target_prices(deals.watchlist(values=False))
    assert rows[0]["target_price"] is None
    assert "BUG" in caplog.text
