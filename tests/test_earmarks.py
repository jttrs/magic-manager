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


# ---------- singles (V31) ----------

def _add_single(cn="5", finish="foil", url=URL_A, **kw):
    return earmarks.earmark_add(
        "tst", f"Test Card (#{cn}, {finish})", url, kind="single",
        scryfall_id="sid-" + cn, collector_number=cn, finish=finish,
        category="single", asking_price=3.0, **kw)


def test_single_add_and_readd_updates(tmp_db):
    assert _add_single()["product_action"] == "inserted"
    assert _add_single(url=URL_B)["product_action"] == "updated"
    (p,) = earmarks.earmark_list()
    assert (p.kind, p.finish, p.collector_number, p.scryfall_id) == ("single", "foil", "5", "sid-5")
    assert len(p.links) == 2


def test_single_different_finish_is_distinct(tmp_db):
    _add_single(finish="foil")
    _add_single(finish="nonfoil", url=URL_B)
    assert len(earmarks.earmark_list()) == 2


def test_single_and_sealed_coexist_and_sealed_defaults(tmp_db):
    _add_single()
    earmarks.earmark_add("tst", "Test Bundle", URL_B)
    by_kind = {p.kind: p for p in earmarks.earmark_list()}
    assert set(by_kind) == {"single", "sealed"}
    assert by_kind["sealed"].finish is None and by_kind["sealed"].scryfall_id is None


def test_single_validation(tmp_db):
    with pytest.raises(ValueError):
        earmarks.earmark_add("tst", "x", URL_A, kind="single", finish="foil")
    with pytest.raises(ValueError):
        earmarks.earmark_add("tst", "x", URL_A, kind="single", collector_number="1", finish="etched")
    with pytest.raises(ValueError):
        earmarks.earmark_add("tst", "x", URL_A, kind="bogus")


# ---------- resolve_single ----------

def test_resolve_single_local(tmp_db, seed_cards, make_card):
    seed_cards([make_card(id="sid-1", name="Front // Back", flavor_name="Flavorful",
                          set="tst", collector_number="7", rarity="mythic")])
    r = earmarks.resolve_single("TST", "7", "foil", name="front")
    assert r["scryfall_id"] == "sid-1" and r["finish"] == "foil"
    assert r["name"] == "Front // Back (#7, foil)" and r["subtype"] == "mythic"
    assert r["release_date"] == "2025-01-01" and r["kind"] == "single"
    # flavor name and full name are accepted too
    earmarks.resolve_single("tst", "7", "nonfoil", name="Flavorful")
    earmarks.resolve_single("tst", "7", "nonfoil", name="Front // Back")


def test_resolve_single_rejections(tmp_db, seed_cards, make_card, monkeypatch):
    seed_cards([make_card(id="sid-1", set="tst", collector_number="7", finishes=["nonfoil"])])
    with pytest.raises(LookupError, match="nonfoil"):
        earmarks.resolve_single("tst", "7", "foil")
    with pytest.raises(LookupError, match="not 'Other Card'"):
        earmarks.resolve_single("tst", "7", "nonfoil", name="Other Card")
    from magic_manager import scryfall
    monkeypatch.setattr(scryfall, "collection", lambda ids: ([], list(ids)))
    with pytest.raises(LookupError, match="no printing TST #99"):
        earmarks.resolve_single("tst", "99")


def test_resolve_single_etched_only_rejected_for_foil(tmp_db, seed_cards, make_card):
    seed_cards([make_card(id="sid-1", set="tst", collector_number="7", finishes=["etched"])])
    with pytest.raises(LookupError, match="etched-only"):
        earmarks.resolve_single("tst", "7", "foil")


def test_resolve_single_foil_and_etched_accepts_foil(tmp_db, seed_cards, make_card):
    seed_cards([make_card(id="sid-1", set="tst", collector_number="7", finishes=["foil", "etched"])])
    assert earmarks.resolve_single("tst", "7", "foil")["finish"] == "foil"


def test_resolve_single_scryfall_fill(tmp_db, make_card, monkeypatch):
    from magic_manager import db, scryfall
    card = make_card(id="sid-9", name="Remote Card", set="tst", collector_number="9")
    monkeypatch.setattr(scryfall, "collection", lambda ids: ([card], []))
    r = earmarks.resolve_single("tst", "9", "nonfoil", name="Remote Card")
    assert r["scryfall_id"] == "sid-9"
    with db.connect() as conn:
        assert conn.execute("SELECT name FROM cards WHERE scryfall_id='sid-9'").fetchone()[0] == "Remote Card"


# ---------- CLI singles ----------

def test_cli_single_add(tmp_db, seed_cards, make_card):
    from magic_manager import cli
    from typer.testing import CliRunner
    seed_cards([make_card(id="sid-1", name="Test Card", set="tst", collector_number="7")])
    runner = CliRunner()
    ok = runner.invoke(cli.app, ["earmark", "add", "tst", "--cn", "7", "--finish", "foil",
                                 "--name", "Test Card", "--url", URL_A, "--price", "2.5"])
    assert ok.exit_code == 0, ok.output
    (p,) = earmarks.earmark_list()
    assert (p.kind, p.finish, p.scryfall_id, p.category) == ("single", "foil", "sid-1", "single")
    assert p.product_name == "Test Card (#7, foil)"

    bad = runner.invoke(cli.app, ["earmark", "add", "tst", "--cn", "7", "--name", "Wrong",
                                  "--url", URL_B])
    assert bad.exit_code == 2
    assert len(earmarks.earmark_list()) == 1

    neither = runner.invoke(cli.app, ["earmark", "add", "tst", "--url", URL_B])
    assert neither.exit_code == 2

    lst = runner.invoke(cli.app, ["earmark", "list"])
    assert "[single · foil]" in lst.output


# ---------- V31 migration ----------

def test_v31_migration_from_v30(tmp_path, monkeypatch):
    import sqlite3
    from magic_manager import db as db_mod
    f = tmp_path / "v30.db"
    raw = sqlite3.connect(str(f))
    raw.executescript(db_mod.MIGRATIONS[0])
    for i in range(1, 30):
        raw.executescript(db_mod.MIGRATIONS[i])
    raw.execute("INSERT INTO schema_version (version) VALUES (30)")
    raw.execute("INSERT INTO earmarked_products (set_code, product_name, earmarked_at) "
                "VALUES ('c19', 'Old Deck', '2026-01-01')")
    raw.commit()
    raw.close()
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(f))
    with db_mod.connect() as conn:
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == db_mod.CURRENT_VERSION
        row = conn.execute("SELECT kind, finish FROM earmarked_products").fetchone()
        assert (row["kind"], row["finish"]) == ("sealed", None)
        ins = ("INSERT INTO earmarked_products (set_code, product_name, earmarked_at, kind, "
               "collector_number, finish) VALUES ('tst', ?, 'now', 'single', '5', 'foil')")
        conn.execute(ins, ("a",))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(ins, ("b",))
