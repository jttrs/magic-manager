"""Order history → purchases: reader goldens → strict API models → engine → ledger.

The ``tests/fixtures/companion/*-order*.expected.json`` goldens are written by
``web/e2e/companion-order-readers.spec.ts`` (the real readers in Chromium against
saved, de-personalised store pages), so reader → app → engine stays one chain.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from magic_manager import addcards, config, db, ingest, purchases, scryfall

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "companion"


def _golden(name: str) -> dict:
    return json.loads((FIX / name).read_text())


@pytest.fixture
def client(tmp_db, tmp_path, monkeypatch, seed_cards, make_card, copy_real_config):
    monkeypatch.setenv("MAGIC_MANAGER_CONFIG_DIR", str(tmp_path))
    copy_real_config(tmp_path)  # every other config file the routes read
    (tmp_path / "features.toml").write_text("[features]\npurchases = false\n")
    monkeypatch.delenv("MM_FEATURES", raising=False)
    config._cached_toml.cache_clear()
    # Offline: the Mana Pool golden's printings + the TCGplayer products' printings.
    mp = _golden("manapool-order.expected.json")["order"]["lines"]
    seed_cards([make_card(id=ln["scryfall_id"], name=ln["name"], set=ln["set_code"], collector_number=ln["collector_number"],
                          prices={"usd": "1.00", "usd_foil": "2.00"}) for ln in mp if ln["scryfall_id"]])
    tcg = {ln["tcgplayer_product_id"]: ln for o in _golden("tcgplayer-orders.expected.json")["orders"] for ln in o["lines"]}
    fake = {pid: make_card(id=f"00000000-0000-4000-8000-{pid:012d}", name=ln["name"], set="tcg", collector_number=str(pid))
            for pid, ln in tcg.items() if ln["kind"] == "single"}
    monkeypatch.setattr(scryfall, "by_tcgplayer_id", lambda pid: fake.get(pid))
    monkeypatch.setattr(addcards, "ensure_printings", lambda ids: [])
    from magic_manager.web.app import create_app
    yield TestClient(create_app(serve_frontend=False))
    config._cached_toml.cache_clear()


def _orders(store: str) -> dict:
    if store == "manapool":
        o = _golden("manapool-order.expected.json")["order"]
        return {"store": "manapool", "orders": [{**o, "ordered_at": "2026-09-23T18:07:31Z"}]}
    if store == "tcgplayer":
        return {"store": "tcgplayer", "orders": _golden("tcgplayer-orders.expected.json")["orders"]}
    o = _golden("cardkingdom-invoice.expected.json")["order"]
    return {"store": "cardkingdom", "orders": [{**o, "ordered_at": "2026-09-04T16:49"}]}


def test_gated_by_the_purchases_flag(client, monkeypatch):
    assert client.get("/api/purchases").status_code == 403
    assert client.post("/api/purchases/orders", json=_orders("manapool")).status_code == 403
    monkeypatch.setenv("MM_FEATURES", "purchases")
    stores = {s["key"]: s["verification"] for s in client.get("/api/purchases/stores").json()}
    assert stores == {"manapool": "verified", "tcgplayer": "partial", "cardkingdom": "partial"}


def test_manapool_order_from_the_reader_golden(client, monkeypatch):
    monkeypatch.setenv("MM_FEATURES", "purchases")
    r = client.post("/api/purchases/orders", json=_orders("manapool")).json()
    assert (r["saved"], r["unresolved"], r["skipped"]) == (1, 0, [])
    (p,) = client.get("/api/purchases").json()["purchases"]
    assert (p["store_name"], p["order_id"], p["lines"], p["copies"], p["assignable"]) == ("Mana Pool", "100102", 7, 8, 7)
    assert (p["shipping_usd"], p["fees_usd"], p["credit_usd"], p["tax_usd"], p["total_usd"]) == (2.7, 23.85, 28.61, 51.93, 544.15)
    rv = client.get(f"/api/purchases/{p['purchase_id']}").json()
    sealed = [ln for ln in rv["lines"] if ln["kind"] == "sealed"]
    assert len(sealed) == 1 and sealed[0]["printing"] is None
    # Add everything assignable → one purchase event, ledger reconciles.
    dec = [{"line_no": ln["line_no"], "add": ln["remaining"]} for ln in rv["lines"] if ln["printing"]]
    out = client.post(f"/api/purchases/{p['purchase_id']}/apply", json={"lines": dec}).json()
    assert out["added"] == 7
    with db.connect() as conn:
        assert ingest.reconcile_inventory_ledger(conn) == []
    again = client.post(f"/api/purchases/{p['purchase_id']}/apply", json={"lines": dec[:1]})
    assert again.status_code == 409
    assert client.post("/api/purchases/orders", json=_orders("manapool")).json()["skipped"] == ["100102"]
    hist = [e for e in client.get("/api/history").json()["entries"] if e["kind"] == "purchase"]
    assert hist[0]["title"] == "Mana Pool order #100102" and hist[0]["paid_usd"] is not None


def test_tcgplayer_orders_resolve_by_product_id(client, monkeypatch):
    monkeypatch.setenv("MM_FEATURES", "purchases")
    r = client.post("/api/purchases/orders", json=_orders("tcgplayer")).json()
    assert (r["saved"], r["unresolved"]) == (3, 0)
    ps = {p["order_id"]: p for p in client.get("/api/purchases").json()["purchases"]}
    assert ps["AAAA0001-000001-00001"]["status"] == "nothing"      # a sealed display: recorded only
    rv = client.get(f"/api/purchases/{ps['AAAA0003-000003-00003']['purchase_id']}").json()
    assert [(ln["finish"], ln["printing"] is not None) for ln in rv["lines"]] == [("nonfoil", True), ("nonfoil", True), ("foil", True)]


def test_cardkingdom_unverified_lines_are_never_cards(client, monkeypatch):
    monkeypatch.setenv("MM_FEATURES", "purchases")
    body = _orders("cardkingdom")
    body["orders"][0]["lines"].append({"kind": "single", "name": "Sol Ring", "quantity": 1, "price": 1.5,
                                       "scryfall_id": _golden("manapool-order.expected.json")["order"]["lines"][0]["scryfall_id"]})
    client.post("/api/purchases/orders", json=body)
    (p,) = client.get("/api/purchases").json()["purchases"]
    rv = client.get(f"/api/purchases/{p['purchase_id']}").json()
    assert [ln["kind"] for ln in rv["lines"]] == ["sealed", "other"]
    assert all(ln["printing"] is None for ln in rv["lines"]) and p["status"] == "nothing"
    assert client.delete(f"/api/purchases/{p['purchase_id']}").status_code == 204
    assert client.get("/api/purchases").json()["purchases"] == []


def test_strict_models_refuse_extras(client, monkeypatch):
    monkeypatch.setenv("MM_FEATURES", "purchases")
    body = _orders("manapool")
    body["orders"][0]["address"] = "1 Main St"
    assert client.post("/api/purchases/orders", json=body).status_code == 422
    body = _orders("manapool")
    body["orders"][0]["lines"][0]["seller"] = "x"
    assert client.post("/api/purchases/orders", json=body).status_code == 422
    empty = client.post("/api/purchases/orders", json={"store": "manapool", "orders": []})
    assert empty.status_code == 422 and empty.json()["detail"]["code"] == "orders.no_lines"
    assert client.post("/api/purchases/orders", json={**_orders("manapool"), "store": "ebay"}).status_code == 422
    assert client.post("/api/purchases/orders", json=_orders("manapool"), headers={"sec-fetch-site": "cross-site"}).status_code == 403


def test_engine_rejects_card_lines_from_unverified_store_paths(tmp_db, monkeypatch):
    monkeypatch.setattr(addcards, "ensure_printings", lambda ids: [])
    r = purchases.save([purchases.Order(store="cardkingdom", order_id="1", ordered_at="2026-01-01",
                                        lines=[purchases.OrderLine(name="X", quantity=1, set_code="fin", collector_number="1")])])
    with db.connect() as conn:
        assert conn.execute("SELECT kind FROM purchase_lines WHERE purchase_id = ?", (r.saved[0],)).fetchone()[0] == "other"
