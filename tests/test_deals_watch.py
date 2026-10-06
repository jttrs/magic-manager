"""V32 earmark price history + Deals watching (watch, record reads, watchlist)."""
from __future__ import annotations

import sqlite3

import pytest

from magic_manager import db, deals, earmarks, sealed, valuation


@pytest.fixture
def stub_identity(monkeypatch):
    monkeypatch.setattr(earmarks, "resolve_identity", lambda set_code, name: {
        "kind": "sealed", "set_code": set_code, "name": name, "uuid": "u-1", "category": "deck"})
    monkeypatch.setattr(valuation, "value_sealed_product", lambda set_code, name, **kw: sealed.ProductValuation(
        label=name, kind="sealed", sealed_market=80.0, intrinsic=95.0))
    deals._value_memo.clear()
    yield
    deals._value_memo.clear()


def test_v32_seeds_history_from_existing_asking_prices(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(path))
    with db.connect():
        pass
    with sqlite3.connect(path) as c:      # pretend the DB predates V32, with one priced + one unpriced link
        c.execute("DROP TABLE earmark_prices")
        c.execute("UPDATE schema_version SET version = 31")
        c.execute("INSERT INTO earmarked_products (set_code, product_name, earmarked_at) VALUES ('c13', 'Deck', '2026-09-05T00:00:00+00:00')")
        c.execute("INSERT INTO earmark_links (product_id, store_url, asking_price, captured_at) VALUES (1, 'https://a/x', 59.99, '2026-09-05T19:04:29+00:00')")
        c.execute("INSERT INTO earmark_links (product_id, store_url, asking_price, captured_at) VALUES (1, 'https://b/y', NULL, '2026-09-05T19:04:29+00:00')")
    with db.connect() as conn:
        rows = conn.execute("SELECT link_id, price, read_at, source FROM earmark_prices").fetchall()
        assert [tuple(r) for r in rows] == [(1, 59.99, "2026-09-05T19:04:29+00:00", "snapshot")]
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == db.CURRENT_VERSION
        # Concurrent first connections can each run the script before the version
        # bump lands; a second run must not duplicate the seed.
        conn.executescript(db.SCHEMA_V32)
        assert conn.execute("SELECT COUNT(*) FROM earmark_prices").fetchone()[0] == 1


def test_watch_records_history_and_reads_append(tmp_db, stub_identity):
    url = "https://cashcardsunlimited.com/products/2018-commander-deck?variant=1"
    deals.watch(url, {"kind": "sealed", "set_code": "c18", "name": "Commander 2018 Commander Deck Adaptive Enchantment"}, price=69.99)
    assert earmarks.record_reads([{"url": url, "price": 64.99, "currency": "USD", "available": True},
                                  {"url": "https://elsewhere/x", "price": 1.0}]) == 1
    w = deals.watchlist()
    assert len(w) == 1
    store = w[0]["stores"][0]
    assert (store["price"], store["first_price"], store["change"], store["read"], store["available"]) == (64.99, 69.99, -5.0, True, True)
    assert (w[0]["best_price"], w[0]["market"], w[0]["delta"], w[0]["pct"]) == (64.99, 80.0, -15.01, -18.8)
    assert [h["price"] for h in store["history"]] == [69.99, 64.99]
    deals.unwatch(url)
    with db.connect() as conn:                           # history goes with its link
        assert conn.execute("SELECT COUNT(*) FROM earmark_prices").fetchone()[0] == 0


def test_watching_is_sealed_and_secret_lair_only(tmp_db):
    with pytest.raises(deals.NotWatchable):
        deals.watch("https://x/p", {"kind": "single", "set_code": "fdn", "name": "Card"}, price=1.0)


def test_watched_links_count_as_confirmed(tmp_db, stub_identity):
    url = "https://manyrealms.com/products/x"
    deals.watch(url, {"kind": "sealed", "set_code": "hob", "name": "The Hobbit Bundle"}, price=50.0)
    assert deals.watched_identities([url, "https://other"]) == {url: {"kind": "sealed", "set_code": "hob", "name": "The Hobbit Bundle"}}
    assert deals._earmark_choice("sld", "Goblingram (Foil Edition)", "foil") == {"kind": "sld", "set_code": "sld", "name": "Goblingram", "finish": "foil"}
