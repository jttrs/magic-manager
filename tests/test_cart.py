"""cart — the Mana Pool cart audit engine, and its web route behind the
cart_check flag. Offline: seeded cards/inventory; the Mana Pool catalog is never
hit (set+number lines map locally; a uuid-only line uses a stub)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from magic_manager import cart, config, manapool

A, B, C = (f"cccc0000-0000-0000-0000-00000000000{i}" for i in (1, 2, 3))


@pytest.fixture
def cards(tmp_db, seed_cards, make_card):
    seed_cards([
        make_card(id=A, oracle_id="oa", set="tst", collector_number="1", name="Alpha", prices={"usd": "2.00", "usd_foil": "5.00"}),
        make_card(id=B, oracle_id="ob", set="tst", collector_number="2", name="Beta", prices={"usd": "1.00", "usd_foil": None}),
        make_card(id=C, oracle_id="oc", set="tst", collector_number="3", name="Gamma", prices={"usd": "10.00", "usd_foil": None}),
    ])
    from magic_manager import db
    with db.connect() as conn:
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) VALUES (?, 'nonfoil', 1, '2025-01-01')", (B,))


def test_map_cart_local_first_then_catalog(cards, monkeypatch):
    called = []
    lines = cart.map_cart([
        {"set": "TST", "number": "1", "quantity": 2, "price": 3.0, "finish": "foil"},
        {"scryfall_id": B, "price_cents": 150},
        {"card_id": "uuid-c", "finish_id": "NF"},
        {"set": "zzz", "number": "9", "name": "Mystery"},
    ], product_fn=lambda u: called.append(u) or {"scryfall_id": C, "name": "Gamma", "set_code": "tst", "number": "3"})
    assert [m.scryfall_id for m in lines] == [A, B, C, None]
    assert (lines[0].foil, lines[0].quantity, lines[0].price_cents, lines[0].set_code) == (True, 2, 300, "TST")
    assert called == ["uuid-c"]
    assert lines[3].name == "Mystery"


def test_map_cart_stops_asking_without_credentials(cards):
    calls = []

    def unconfigured(u):
        calls.append(u)
        raise manapool.ManapoolUnconfigured("no creds")
    lines = cart.map_cart([{"card_id": "u1"}, {"card_id": "u2"}], product_fn=unconfigured)
    assert calls == ["u1"] and all(m.scryfall_id is None for m in lines)


def test_audit_finds_dupes_owned_and_overpay(cards, monkeypatch):
    monkeypatch.setattr(cart, "infer_set_anchors", lambda mapped: [])
    out = cart.audit([
        {"set": "tst", "number": "1", "price": 2.10},
        {"set": "tst", "number": "1", "price": 6.00, "finish": "foil"},
        {"set": "tst", "number": "2", "price": 1.00},
        {"set": "tst", "number": "3", "price": 14.00, "quantity": 2},
    ], remote=False)
    assert (out["lines"], out["copies"], out["total"]) == (4, 5, 37.1)
    dupes = {d["name"]: d for d in out["dupes"]}
    assert set(dupes) == {"Alpha", "Gamma"}                      # foil+nonfoil · ×2 one finish
    assert dupes["Alpha"]["cheaper"] == 2.10 and dupes["Gamma"]["note"] == "×2 nonfoil"
    assert [o["name"] for o in out["owned"]] == ["Beta"]
    assert [o["name"] for o in out["overpay"]] == ["Gamma"]      # +40%, +$4 — Alpha's +$1 foil isn't > $1
    assert out["family"] is None and out["missing"] == []


def test_parse_rejects_non_carts():
    with pytest.raises(cart.CartFormatError):
        cart.parse("hello")
    assert cart.parse('{"items": [{"set": "x"}]}') == [{"set": "x"}]


@pytest.fixture
def client(cards, tmp_path, monkeypatch, copy_real_config):
    monkeypatch.setenv("MAGIC_MANAGER_CONFIG_DIR", str(tmp_path))
    (tmp_path / "features.toml").write_text("[features]\ncart_check = false\n")
    copy_real_config(tmp_path)  # every other config file the routes read
    monkeypatch.delenv("MM_FEATURES", raising=False)
    monkeypatch.setattr(cart, "infer_set_anchors", lambda mapped: [])
    config._cached_toml.cache_clear()
    from magic_manager.web.app import create_app
    yield TestClient(create_app())
    config._cached_toml.cache_clear()


def test_cart_route_is_gated_by_the_flag(client, monkeypatch):
    from magic_manager.api import cart as cart_api
    fetched = {"items": [{"scryfall_id": B, "price_cents": 100}]}

    class FakeScript:
        _load_env = staticmethod(lambda: {})
        fetch_headless = staticmethod(lambda env: fetched["items"])
    monkeypatch.setattr(cart_api, "_cart_script", lambda: FakeScript)
    assert client.get("/api/features").json()["flags"] == {"cart_check": False}
    assert client.post("/api/cart/check", json={}).status_code == 403
    monkeypatch.setenv("MM_FEATURES", "cart_check")
    r = client.post("/api/cart/check", json={})
    assert r.status_code == 200 and r.json()["owned"][0]["name"] == "Beta"
    fetched["items"] = None
    assert client.post("/api/cart/check", json={}).status_code == 422


@pytest.mark.parametrize("line", [
    {"quantity": "2x"}, {"price": float("nan")}, {"price": "3"}, {"scryfall_id": []},
    {"set": {"a": 1}}, {"tcgplayer_product_id": "abc"}, {"quantity": -1}, {"quantity": True},
])
def test_parse_rejects_malformed_line_values(line):
    with pytest.raises(cart.CartFormatError, match="line 2"):
        cart.parse([{"set": "tst", "number": "1"}, line])


def test_parse_accepts_numeric_strings_and_ints():
    items = [{"set": "tst", "number": 7, "quantity": "2", "tcgplayer_product_id": "123", "price": 1}]
    assert cart.parse(items) == items


def test_map_cart_catalog_all_fetches_product_for_local_lines(cards):
    prod = {"scryfall_id": A, "name": "Alpha", "variants": [{"finish_id": "NF", "condition_id": "NM", "low_price": 180}]}
    line = {"set": "tst", "number": "1", "card_id": "uuid-a", "price": 3.0}
    assert cart.map_cart([line], product_fn=lambda u: prod)[0].prod is None        # web: local wins, no catalog call
    (m,) = cart.map_cart([line], catalog_all=True, product_fn=lambda u: prod)
    assert m.scryfall_id == A and m.prod is prod
    assert cart.overpay_rows([m], prices_fn=cart.local_prices)["rows"][0]["mp_cheap"] == 1.8
