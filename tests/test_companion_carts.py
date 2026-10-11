"""TCGplayer + Card Kingdom carts: reader goldens → strict API models → ``cart.audit``.

The ``tests/fixtures/companion/{tcgplayer,cardkingdom}-cart.expected.json`` goldens are
written by ``web/e2e/companion-cart-readers.spec.ts`` (the real readers in Chromium
against guest carts saved from the live sites), so reader → app → engine stays one chain.
Offline: Scryfall's TCGplayer lookup and MTGJSON's set files are faked.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from magic_manager import addcards, cart, config, db, mtgjson, scraper_health, scryfall, store_ids
from magic_manager.api import companion as companion_api

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "companion"


def _golden(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def sid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


# The printings behind the two saved carts (ids from MTGJSON / Scryfall, checked by hand).
TCG = {563893: ("Vengeful Bloodwitch", "fdn", "76", 1), 630864: ("Aerith Gainsborough", "fin", "4", 2),
       487805: ("The One Ring", "ltr", "246", 3), 630958: ("Ardyn, the Usurper", "fin", "315", 4),
       577866: ("Sol Ring", "dsc", "94", 5)}
SETS = [{"code": "fin", "name": "Final Fantasy", "set_type": "expansion"},
        {"code": "fdc", "name": "Foundations Commander", "set_type": "commander"},
        {"code": "3ed", "name": "Revised Edition", "set_type": "core"},
        {"code": "ltr", "name": "The Lord of the Rings: Tales of Middle-earth", "set_type": "expansion"},
        {"code": "pltr", "name": "Tales of Middle-earth Promos", "set_type": "promo"},
        {"code": "dsc", "name": "Duskmourn: House of Horror Commander", "set_type": "commander"},
        {"code": "fdn", "name": "Foundations", "set_type": "expansion"}]
# Card Kingdom product id → (set, cn, MTGJSON identifier key, our id number)
CK = {313555: ("fin", "4", "cardKingdomId", 2), 313885: ("fin", "524", "cardKingdomFoilId", 6),
      26242: ("3ed", "274", "cardKingdomId", 7), 333767: ("fdc", "286", "cardKingdomId", 8),
      279381: ("ltr", "451", "cardKingdomFoilId", 9)}
NAMES = {2: "Aerith Gainsborough", 6: "Ardyn, the Usurper", 7: "Sol Ring", 8: "Sol Ring", 9: "The One Ring"}


@pytest.fixture
def carts(tmp_db, seed_cards, make_card, monkeypatch):
    cards = [make_card(id=sid(n), name=name, set=s, collector_number=cn, prices={"usd": "1.00", "usd_foil": "2.00"})
             for name, s, cn, n in TCG.values()]
    cards += [make_card(id=sid(n), name=NAMES[n], set=s, collector_number=cn, prices={"usd": "1.00", "usd_foil": "2.00"})
              for s, cn, _, n in CK.values() if n != 2]
    # Decoys: other printings of the same names in sets that DON'T carry the id.
    cards += [make_card(id=sid(90), name="Sol Ring", set="dsc", collector_number="95"),
              make_card(id=sid(91), name="The One Ring", set="pltr", collector_number="246s")]
    seed_cards(cards)
    def by_tcg(pid):   # Scryfall's answer carries today's price, like the row it upserts over
        if pid not in TCG:
            return None
        name, s, cn, n = TCG[pid]
        with db.connect() as conn:
            usd, foil = conn.execute("SELECT prices_usd, prices_usd_foil FROM cards WHERE scryfall_id = ?", (sid(n),)).fetchone()
        return make_card(id=sid(n), name=name, set=s, collector_number=cn, prices={"usd": usd, "usd_foil": foil})
    monkeypatch.setattr(scryfall, "by_tcgplayer_id", by_tcg)
    monkeypatch.setattr(scryfall, "all_sets", lambda: SETS)
    reads: list[str] = []

    def set_file(code):
        reads.append(code.lower())
        rows = [{"name": NAMES[n], "number": cn, "identifiers": {"scryfallId": sid(n), key: str(pid)}}
                for pid, (s, cn, key, n) in CK.items() if s == code.lower()]
        return {"data": {"cards": rows, "tokens": []}}

    monkeypatch.setattr(mtgjson, "set_file", set_file)
    monkeypatch.setattr(scryfall, "search", lambda *a, **k: iter(()))
    monkeypatch.setattr(addcards, "ensure_printings", lambda ids: [])
    monkeypatch.setattr(cart, "infer_set_anchors", lambda mapped: [])
    store_ids._ck_index.cache_clear()
    yield reads
    store_ids._ck_index.cache_clear()


def _price(n: int, usd: str, usd_foil: str | None = None):
    with db.connect() as conn:
        conn.execute("UPDATE cards SET prices_usd = ?, prices_usd_foil = ? WHERE scryfall_id = ?", (usd, usd_foil, sid(n)))


def _own(n: int, qty: int = 1, finish: str = "nonfoil"):
    from magic_manager import inventory
    inventory.inventory_add(sid(n), finish, qty)


def test_tcgplayer_cart_from_the_reader_golden(carts):
    out = _golden("tcgplayer-cart.expected.json")
    req = companion_api.CartLinesIn(items=out["items"], source="extension", store="tcgplayer")
    _price(5, "0.50")          # Sol Ring NM English at $1.85 vs $0.50 → over market
    _price(3, "50.00")         # The One Ring LP at $108.15 vs NM $50 → played: shown, never flagged
    _price(2, "1.50")          # Aerith NM English at $1.75 — under the $1 floor
    _price(4, "1.00", "6.00")  # Ardyn foil at $5.49 — under market
    _own(2)                    # an Aerith Gainsborough already owned
    r = cart.audit([i.model_dump() for i in req.items])
    assert (r["lines"], r["copies"], r["total"]) == (7, 8, 126.69)
    assert r["unidentified"] == []
    assert [(n["name"], n["kind"]) for n in r["not_cards"]] == [("FINAL FANTASY - Play Booster Pack", "sealed")]
    # Japanese + English Aerith = the same printing: bought twice, and already owned (both lines).
    assert {(d["name"], d["note"]) for d in r["dupes"]} == {("Aerith Gainsborough", "×2 nonfoil"), ("Vengeful Bloodwitch", "×2 nonfoil")}
    assert {(o["name"], o["language"]) for o in r["owned"]} == {("Aerith Gainsborough", "Japanese"), ("Aerith Gainsborough", "English")}
    assert [(o["name"], o["condition"]) for o in r["overpay"]] == [("Sol Ring", "NM")]
    assert r["not_compared"] == 2            # the LP One Ring + the Japanese Aerith
    foil = next(m for m in cart.map_cart([i.model_dump() for i in req.items]) if m.name == "Ardyn, the Usurper")
    assert (foil.scryfall_id, foil.foil) == (sid(4), True)


def test_cardkingdom_cart_from_the_reader_golden(carts):
    out = _golden("cardkingdom-cart.expected.json")
    req = companion_api.CartLinesIn(items=out["items"], source="extension", store="cardkingdom")
    _price(8, "0.75")           # Sol Ring FDC NM at $2.99 vs $0.75 → over market
    _price(2, "4.50")           # Aerith NM at $4.49 — at market
    _price(6, "1.00", "17.00")  # Ardyn foil at $16.99 — at market
    _price(7, "2.00")           # Sol Ring 3ED VG at $17.49 — played grade: never flagged
    _price(9, "10.00", "40.00")  # The One Ring EX foil at $125.99 — EX is a played grade
    mapped = cart.map_cart([i.model_dump() for i in req.items])
    assert [(m.name, m.scryfall_id, m.foil, m.condition_id) for m in mapped] == [
        ("Aerith Gainsborough", sid(2), False, "NM"),
        ("Ardyn, the Usurper", sid(6), True, "NM"),           # Card Kingdom's foil product → the foil printing
        ("Sol Ring", sid(7), False, "VG"),                    # "3rd Edition" is Scryfall's Revised Edition
        ("Sol Ring", sid(8), False, "NM"),
        ("The One Ring", sid(9), True, "EX"),                 # "Promotional": the bundle promo lives in LTR
        ("The Hobbit Gift Bundle", None, False, None),
    ]
    store_ids._ck_index.cache_clear()
    r = cart.audit([i.model_dump() for i in req.items])
    assert [(o["name"], o["set"], o["condition"]) for o in r["overpay"]] == [("Sol Ring", "FDC", "NM")]
    assert r["unidentified"] == [] and [n["name"] for n in r["not_cards"]] == ["The Hobbit Gift Bundle"]


def test_cardkingdom_edition_ranking_reads_the_likeliest_set_first(carts):
    rows = [{"set_code": s, "collector_number": "1"} for s in ("dsc", "fdc", "3ed", "fdn")]
    assert store_ids._ranked_sets(rows, store_ids.CkLine(1, "Sol Ring", "3rd Edition"))[0] == "3ed"
    assert store_ids._ranked_sets(rows, store_ids.CkLine(1, "Sol Ring", "Foundations Commander"))[0] == "fdc"
    rows = [{"set_code": "fin", "collector_number": "524"}, {"set_code": "fdn", "collector_number": "9"}]
    assert store_ids._ranked_sets(rows, store_ids.CkLine(1, "Ardyn, the Usurper", "Final Fantasy Variants Foil", "524"))[0] == "fin"


def test_cardkingdom_unknown_id_stays_unidentified_never_guessed(carts):
    found = store_ids.cardkingdom_printings([store_ids.CkLine(999999, "Sol Ring", "Foundations Commander")])
    assert found == {}
    assert len(carts) <= store_ids.CK_SCAN_LIMIT


def test_offline_store_lookups_leave_lines_named_not_dropped(carts, monkeypatch):
    def boom(*a, **k):
        raise scryfall.ScryfallError("offline")
    monkeypatch.setattr(scryfall, "by_tcgplayer_id", boom)
    r = cart.audit([{"tcgplayer_product_id": 999, "name": "Mystery", "quantity": 1, "price": 1.0}])
    assert r["unidentified"] == [{"name": "Mystery", "set": None, "num": None}]


# ---------- API ----------

@pytest.fixture
def client(carts, tmp_path, monkeypatch, copy_real_config):
    monkeypatch.setenv("MAGIC_MANAGER_CONFIG_DIR", str(tmp_path))
    copy_real_config(tmp_path)  # every other config file the routes read
    (tmp_path / "features.toml").write_text("[features]\ncart_check = false\n")
    monkeypatch.setenv("MM_FEATURES", "cart_check")
    monkeypatch.setenv("MM_SCRAPER_HEALTH", str(tmp_path / "health.json"))
    config._cached_toml.cache_clear()
    from magic_manager.web.app import create_app
    yield TestClient(create_app(serve_frontend=False))
    config._cached_toml.cache_clear()


def test_cart_lines_route_takes_each_store_and_refuses_extras(client):
    items = _golden("tcgplayer-cart.expected.json")["items"]
    r = client.post("/api/cart/lines", json={"items": items, "source": "extension", "store": "tcgplayer"})
    assert r.status_code == 200 and r.json()["copies"] == 8 and r.json()["not_cards"][0]["kind"] == "sealed"
    assert next(h for h in scraper_health.health() if h.scraper.key == "companion-cart/tcgplayer").status == "ok"
    ck = _golden("cardkingdom-cart.expected.json")["items"]
    assert client.post("/api/cart/lines", json={"items": ck, "source": "extension", "store": "cardkingdom"}).status_code == 200
    assert client.post("/api/cart/lines", json={"items": items, "source": "bookmarklet", "store": "tcgplayer"}).status_code == 422
    assert client.post("/api/cart/lines", json={"items": items, "source": "extension", "store": "ebay"}).status_code == 422
    assert client.post("/api/cart/lines", json={"items": [{**items[0], "seller": "x"}], "source": "extension", "store": "tcgplayer"}).status_code == 422
