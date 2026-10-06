"""The vendor recipe book — every recipe parses its saved store page.

Fixtures in tests/fixtures/vendors/ are real pages captured 2026-10-05
(``<key>.html.gz`` for page-tag stores, ``<key>.js.json.gz`` for Shopify). When a
store changes its markup, re-capture the page and update the expectation —
the nightly canary (scripts/vendor_canary.py) flags it live first.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from magic_manager import deals, storefetch, storepage, vendors

FIX = Path(__file__).parent / "fixtures" / "vendors"

# key -> (price, available, title starts with)
EXPECT = {
    "manyrealms": (180.99, True, "Magic the Gathering - Foundations"),
    "pokebox": (117.99, True, "Marvel Super Heroes"),
    "stompinggrounds": (179.0, True, "Magic: The Gathering Foundations"),
    "doubleinfinity": (169.99, True, "Magic the Gathering: Edge of Eternities"),
    "gamersguild": (142.28, False, "Magic: The Gathering | Reality Fracture"),
    "forgeandfire": (249.95, True, "Final Fantasy - Play Booster Box"),
    "coolstuff": (44.99, True, "MTG - Universes Beyond: Final Fantasy"),
    "starcity": (249.99, False, "Final Fantasy Play Booster Box"),
    "miniaturemarket": (179.99, False, "MtG Universes Beyond: Final Fantasy"),
    "gamenerdz": (129.97, True, "Riftbound"),
    "nobleknight": (159.95, False, "Edge of Eternities - Play Booster Display"),
    "dragonslair": (189.99, True, "Magic the Gathering: Teenage Mutant Ninja Turtles"),
    "costco": (46.99, False, "Magic: The Gathering Bloomburrow Commander Kit"),
    "cardkingdom": (274.99, True, "Edge of Eternities Play Booster Box"),
}


def _page(key: str):
    js = FIX / f"{key}.js.json.gz"
    if js.exists():
        return json.loads(gzip.decompress(js.read_bytes()))
    return gzip.decompress((FIX / f"{key}.html.gz").read_bytes()).decode()


@pytest.mark.parametrize("key", sorted(EXPECT))
def test_recipe_reads_its_saved_page(key):
    price, available, title = EXPECT[key]
    listing = vendors.read_listing(vendors.by_key(key), _page(key))
    assert listing.price == pytest.approx(price)
    assert listing.available is available
    assert (listing.title or "").startswith(title)


def test_every_vendor_is_catalogued_tested_and_its_sample_is_a_product_page():
    keys = {v.key for v in vendors.catalog()}
    rendered = {v.key for v in vendors.catalog() if v.mode == "rendered"}
    assert keys - rendered == set(EXPECT), "every server-read vendor needs a fixture + expectation"
    for v in vendors.catalog():
        if v.sample_url:
            assert v.is_product(urlsplit(v.sample_url).path), v.key
        else:
            assert v.mode == "rendered", f"{v.key}: server-read vendors need a sample_url for the canary"


@pytest.mark.parametrize("key,text,price,available", [
    # Best Buy: the first $ amount is the price; the second is the ÷4 installment.
    ("bestbuy", "Magic Foundations Play Booster Box\n$159.99\nor $39.99/mo. for 4 months\nAdd to Cart", 159.99, None),
    ("bestbuy", "Commander Deck\n$44.99\nSold Out", 44.99, False),
    # eBay: the first US $ amount; installments and shipping come later.
    ("ebay", "Final Fantasy Collector Box\nUS $529.99\nor 4 interest-free payments of US $132.50\nShipping: US $20.00", 529.99, None),
    ("ebay", "This listing was ended by the seller.\nUS $99.00", 99.0, False),
    ("target", "MTG Foundations Bundle\n$59.99\nOut of stock at your store", 59.99, False),
])
def test_rendered_recipes_pick_the_right_price(key, text, price, available):
    listing = vendors.read_listing(vendors.by_key(key), "<html><head><title>x</title></head></html>", text=text)
    assert listing.price == pytest.approx(price)
    assert listing.available is available


def test_page_tags_beat_text_patterns_for_rendered_stores():
    head = '<html><head><meta property="product:price:amount" content="149.99"></head></html>'
    listing = vendors.read_listing(vendors.by_key("bestbuy"), head, text="$12.50 promo\n$149.99")
    assert (listing.price, listing.signal) == (149.99, "meta")


@pytest.mark.parametrize("title", ["Just a moment...", "Robot or human?", "Attention Required! | Cloudflare"])
def test_bot_walls_are_recognized(title):
    with pytest.raises(storepage.Blocked):
        storepage.check_blocked(f"<html><head><title>{title}</title></head></html>")
    with pytest.raises(storepage.Blocked):
        storepage.check_blocked("", 403)


def test_shopify_js_url_handles_collection_scoped_links():
    assert storefetch.shopify_js_url("https://manyrealms.com/collections/sealed/products/fdn-box?variant=1") == \
        "https://manyrealms.com/products/fdn-box.js"


def test_read_tab_parses_the_tab_payload_and_detects_closed_tabs():
    payload = json.dumps({"head": '<meta property="og:title" content="Box">', "ld": ['{"@type":"Product","offers":{"price":"10.00"}}'],
                          "text": "Box $10.00", "title": "Box"})
    html, text = storefetch.read_tab("https://www.bestbuy.com/product/x/1", runner=lambda s: payload)
    assert 'application/ld+json' in html and text == "Box $10.00"
    with pytest.raises(storefetch.TabGone):
        storefetch.read_tab("https://www.bestbuy.com/product/x/1", runner=lambda s: "__GONE__")


def test_read_prices_reports_per_url_errors_and_stops_tab_reads_once_js_is_off(monkeypatch):
    calls = []

    def fake_read(url, fresh=False):
        calls.append(url)
        if "bestbuy" in url:
            raise storefetch.JsEventsOff("Turn on Allow JavaScript from Apple Events")
        if "costco" in url:
            raise storepage.Blocked("the store blocked the request (403)")
        return vendors.by_key("manyrealms"), storepage.Listing(10.0, "USD", True, "Box", "shopify")
    monkeypatch.setattr(storefetch, "read", fake_read)
    rows = deals.read_prices([
        "https://manyrealms.com/products/a",
        "https://www.bestbuy.com/product/x/1",
        "https://www.bestbuy.com/product/y/2",
        "https://www.costco.com/p/-/x/123",
    ])
    assert [r["price"] for r in rows] == [10.0, None, None, None]
    assert rows[1]["error"] == rows[2]["error"] == "Turn on Allow JavaScript from Apple Events"
    assert "https://www.bestbuy.com/product/y/2" not in calls          # skipped after the first JS-off
    assert rows[3]["error"].startswith("The store blocked")
