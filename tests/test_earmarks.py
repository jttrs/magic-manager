"""Tests for the earmark watchlist (magic_manager.earmarks) + CLI identity guard.

Offline + deterministic via conftest's tmp_db. The CRUD is pure DB; the only
MTGJSON touch is the CLI `add` command's identity validation, which we exercise
by monkeypatching mtgjson.set_file to serve a canned sealedProduct list.
"""

from __future__ import annotations

import pytest

from magic_manager import earmarks


URL_A = "https://cashcardsunlimited.com/products/2019-commander-deck?variant=1"
URL_B = "https://www.tcgplayer.com/product/198267"


def test_store_name_from_url():
    assert earmarks.store_name_from_url(URL_A) == "cashcardsunlimited.com"
    assert earmarks.store_name_from_url(URL_B) == "tcgplayer.com"  # www. stripped
    assert earmarks.store_name_from_url("not a url") is None


def test_add_creates_product_and_link(tmp_db):
    res = earmarks.earmark_add(
        "c19", "Faceless Menace", URL_A,
        category="deck", asking_price=50.0,
    )
    assert res["product_action"] == "inserted"
    assert res["link_action"] == "inserted"
    products = earmarks.earmark_list()
    assert len(products) == 1
    p = products[0]
    assert p.set_code == "c19"
    assert p.product_name == "Faceless Menace"
    assert len(p.links) == 1
    assert p.links[0].store_name == "cashcardsunlimited.com"
    assert p.links[0].asking_price == 50.0
    assert p.best_asking == 50.0


def test_same_product_two_stores_collates(tmp_db):
    """Adding the SAME product on a second storefront → still ONE product, TWO
    links. best_asking reflects the cheaper store."""
    earmarks.earmark_add("c19", "Faceless Menace", URL_A, asking_price=50.0)
    res = earmarks.earmark_add("c19", "Faceless Menace", URL_B, asking_price=46.5)
    assert res["product_action"] == "updated"   # product already existed
    assert res["link_action"] == "inserted"     # new storefront link

    products = earmarks.earmark_list()
    assert len(products) == 1
    p = products[0]
    assert len(p.links) == 2
    assert p.best_asking == 46.5
    # links sort cheapest-first
    assert [l.asking_price for l in p.links] == [46.5, 50.0]


def test_readd_same_url_updates_snapshot(tmp_db):
    earmarks.earmark_add("c19", "Faceless Menace", URL_A, asking_price=50.0)
    res = earmarks.earmark_add("c19", "Faceless Menace", URL_A, asking_price=42.0)
    assert res["link_action"] == "updated"
    p = earmarks.earmark_list()[0]
    assert len(p.links) == 1                    # no duplicate link
    assert p.links[0].asking_price == 42.0      # snapshot refreshed


def test_metadata_coalesces_on_readd(tmp_db):
    """A later add fills in metadata an earlier one lacked, without clobbering
    already-set values with None."""
    earmarks.earmark_add("c19", "Faceless Menace", URL_A, category="deck")
    earmarks.earmark_add("c19", "Faceless Menace", URL_B, release_date="2019-08-23")
    p = earmarks.earmark_list()[0]
    assert p.category == "deck"            # preserved
    assert p.release_date == "2019-08-23"  # filled in


def test_rm_link_keeps_product(tmp_db):
    earmarks.earmark_add("c19", "Faceless Menace", URL_A, asking_price=50.0)
    earmarks.earmark_add("c19", "Faceless Menace", URL_B, asking_price=46.5)
    res = earmarks.earmark_remove_link(URL_A)
    assert res["removed"] is True
    p = earmarks.earmark_list()[0]
    assert len(p.links) == 1
    assert p.links[0].store_url == URL_B


def test_rm_product_cascades_links(tmp_db):
    earmarks.earmark_add("c19", "Faceless Menace", URL_A, asking_price=50.0)
    earmarks.earmark_add("c19", "Faceless Menace", URL_B, asking_price=46.5)
    res = earmarks.earmark_remove_product("c19", "Faceless Menace")
    assert res["removed"] is True
    assert earmarks.earmark_list() == []
    # links gone too (ON DELETE CASCADE)
    from magic_manager import db
    with db.connect() as conn:
        n = conn.execute("SELECT COUNT(*) FROM earmark_links").fetchone()[0]
    assert n == 0


def test_rm_missing_returns_false(tmp_db):
    assert earmarks.earmark_remove_link("https://nope.example/x")["removed"] is False
    assert earmarks.earmark_remove_product("zzz", "Nope")["removed"] is False


# ---------- CLI identity guard ----------

def _fake_set_file(products):
    def _f(code):
        return {"sealedProduct": products}
    return _f


def test_cli_add_requires_resolvable_identity(tmp_db, monkeypatch):
    """`mm earmark add` must exit 2 when the product can't be resolved in MTGJSON,
    and must NOT write anything."""
    from magic_manager import cli, mtgjson
    from typer.testing import CliRunner

    monkeypatch.setattr(mtgjson, "set_file", _fake_set_file([
        {"name": "Commander 2019 Commander Deck Faceless Menace", "category": "deck",
         "uuid": "u1", "releaseDate": "2019-08-23", "cardCount": 100},
    ]))
    runner = CliRunner()

    # Unresolvable name → exit 2, nothing written.
    bad = runner.invoke(cli.app, ["earmark", "add", "c19",
                                  "--name", "nonexistent widget", "--url", URL_A])
    assert bad.exit_code == 2
    assert earmarks.earmark_list() == []

    # Resolvable substring → success, one product.
    good = runner.invoke(cli.app, ["earmark", "add", "c19",
                                   "--name", "faceless menace", "--url", URL_A,
                                   "--price", "50"])
    assert good.exit_code == 0
    products = earmarks.earmark_list()
    assert len(products) == 1
    # product name is the FULL MTGJSON name, not the substring the user typed
    assert products[0].product_name == "Commander 2019 Commander Deck Faceless Menace"
    assert products[0].product_uuid == "u1"
