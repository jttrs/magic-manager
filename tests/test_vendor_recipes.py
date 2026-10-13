"""The vendor recipe book — every recipe parses its saved store page.

Fixtures in tests/fixtures/vendors/ are real pages captured 2026-10-05
(``<key>.html.gz`` for page-tag stores, ``<key>.js.json.gz`` for Shopify). When a
store changes its markup, re-capture the page and update the expectation —
the nightly canary (scripts/vendor_canary.py) flags it live first.

Open-tab (``rendered``) marketplaces keep real tab reads under
``rendered/<key>-<case>.json.gz`` (scripts/capture_store_tab.py, 2026-10-10):
each holds BOTH read paths — the browser companion's extract and the AppleScript
tab read — and every recipe expectation is checked against each. Best Buy and
Target tabs (2026-10-12) were read in a throwaway browser profile (guest, no
account), location text redacted.
"""
from __future__ import annotations

import gzip
import json
import re
import subprocess
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
    "cashcards": (69.99, True, "2018 Commander Deck"),        # no ?variant= → cheapest in-stock variant
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


# fixture -> (price, available, title starts with, seller, why not counted (substring) or None)
RENDERED = {
    "amazon-1p": (129.42, True, "Magic: the Gathering Lorwyn Eclipsed - Play Booster Box", "Amazon.com", None),
    "amazon-preorder": (224.97, True, "Magic: The Gathering | Star Trek Commander Deck Bundle", "Amazon.com", None),
    "amazon-third-party": (129.99, True, "Magic: The Gathering Secrets of Strixhaven", "Bigg Time Sales", "third-party seller (Bigg Time Sales)"),
    "amazon-merchant-fulfilled": (109.97, None, "Magic: The Gathering Fallout Commander Deck", "EmpireGameCenter", "third-party seller (EmpireGameCenter)"),
    "walmart-1p": (45.99, True, "Magic: The Gathering Tarkir Dragonstorm Commander Deck - Jeskai Striker", "Walmart.com", None),
    "walmart-third-party": (109.99, True, "Magic: The Gathering Lorwyn Eclipsed Play Booster Box", "CardsHQ", "third-party seller (CardsHQ)"),
    "gamestop-in-stock": (139.99, True, "Magic: The Gathering Marvel", "GameStop", None),
    "gamestop-sold-out": (159.99, False, "Magic: The Gathering Edge of Eternities", "GameStop", None),
    # Best Buy: JSON-LD says InStock on every page; the buy box decides.
    "bestbuy-in-stock": (174.99, True, "Wizards of The Coast - Magic: The Gathering Foundations Play Booster Box", "Best Buy", None),
    "bestbuy-sold-out": (39.99, False, "Wizards of The Coast - Magic: The Gathering Duskmourn", "Best Buy", None),
    "bestbuy-in-store-only": (41.99, False, "Wizards of The Coast - Magic: The Gathering  - The Hobbit Collector Booster", "Best Buy", None),
    "bestbuy-pickup-only": (29.99, True, "Wizards of The Coast - Magic: The Gathering Foundations Commander Deck", "Best Buy", None),
    # Target: no page tags; an in-stock page doesn't say so (unknown), a failed price module isn't counted.
    "target-in-stock": (39.99, None, "Magic The Gathering: FINAL FANTASY VI Commander Deck", None, None),
    "target-out-of-stock": (44.99, False, "Magic:The Gathering | Avatar:The Last Airbender Collector Booster", None, None),
    "target-no-offer": (None, None, "Magic The Gathering | Reality Fracture Play Booster Display", None, "no offer"),
}


def _rendered(name: str) -> dict:
    return json.loads(gzip.decompress((FIX / "rendered" / f"{name}.json.gz").read_bytes()))


@pytest.mark.parametrize("path", ["extract", "tab"])
@pytest.mark.parametrize("name", sorted(RENDERED))
def test_open_tab_recipe_reads_both_read_paths(name, path):
    price, available, title, seller, skipped = RENDERED[name]
    fixture = _rendered(name)
    v = vendors.by_key(name.split("-")[0])
    html, text = storefetch.page_from_extract(fixture[path])
    listing = vendors.read_listing(v, html, text=text)
    assert (listing.price, listing.available, listing.seller) == (
        pytest.approx(price) if price is not None else None, available, seller)
    assert (listing.title or "").startswith(title)
    assert not re.search(r"Amazon\.com:|Walmart\.com|\| GameStop|: Target$|- Best Buy$", listing.title)    # store noise stripped
    if skipped is None:
        assert listing.skipped is None
        assert storefetch.read(fixture["url"], rendered=fixture[path])[1].price == pytest.approx(price)
    else:
        assert skipped in listing.skipped
        with pytest.raises(storepage.NotCounted, match=re.escape(skipped)):
            storefetch.read(fixture["url"], rendered=fixture[path])


def test_every_rendered_fixture_has_an_expectation():
    assert {p.name.removesuffix(".json.gz") for p in (FIX / "rendered").glob("*.json.gz")} == set(RENDERED)
    marketplaces = {v.key for v in vendors.catalog() if v.mode == "rendered" and v.sellers}
    assert marketplaces == {"amazon", "walmart", "gamestop", "bestbuy"}
    assert marketplaces <= {n.split("-")[0] for n in RENDERED}, "every marketplace recipe needs a captured tab"


@pytest.mark.parametrize("key,text,skipped", [
    # Amazon: no buy box — the only prices on the page are other items'.
    ("amazon", "Under $10\n$74.95\nCurrently unavailable.\nWe don't know when or if this item will be back in stock.", "no offer"),
    ("amazon", "$54.99\nIn Stock\nShips from and sold by Amazon.com.", None),
    ("amazon", "$41.10\nIn Stock\nShips from\nAmazon\nSold by\nAmazon Resale", "third-party seller (Amazon Resale)"),
    ("amazon", "$54.99\nTemporarily out of stock.\nShipper / Seller\nAmazon.com", None),
    ("amazon", "Magic Booster Box\nNo featured offers available\n$95.00 (12 new offers)\nSee All Buying Options\n", "no offer"),
    # Seller-gated store with a price but no seller line: fail closed.
    ("walmart", "Current price is $45.99\nIn stock", "No seller shown"),
    # Walmart: a used / restored main offer.
    ("walmart", "Condition\nRestored: Like New\nCurrent price is Now $89.00\nSold and shipped by Walmart.com", "used / pre-owned offer (Restored: Like New)"),
    ("walmart", "$0.00\nCondition\nNew\nCurrent price is $45.99\nOut of stock\nSold and shipped by Walmart.com", None),
    # Best Buy Marketplace: the buy box's "Sold by" names the seller (JSON-LD wins when present).
    ("bestbuy", "Sold by\nBest Buy\n$29.99\nAdd to cart\nSold by\nReturn & Exchange Policy", None),
    ("bestbuy", "Sold by\nCardShop Direct\n$129.99\nAdd to cart\nSold by\nReturn & Exchange Policy", "third-party seller (CardShop Direct)"),
    ("bestbuy", "$29.99\nAdd to cart", "No seller shown"),
    # Target's price module failed: whatever $ is left on the page isn't this offer.
    ("target", "There was a temporary issue\nChoose delivery method in cart\nAdd to cart\n$19.99", "no offer"),
])
def test_marketplace_rules_on_page_text(key, text, skipped):
    listing = vendors.read_listing(vendors.by_key(key), "<html><head><title>x</title></head></html>", text=text)
    if skipped is None:
        assert listing.skipped is None and listing.price is not None
    else:
        assert skipped in listing.skipped


def test_amazon_and_walmart_text_rules_take_the_buy_box_not_the_cart_or_installments():
    amazon = vendors.read_listing(vendors.by_key("amazon"), "<title>x</title>", text="$54.99\nTemporarily out of stock.\nShipper / Seller\nAmazon.com")
    assert (amazon.price, amazon.available) == (54.99, False)
    walmart = vendors.read_listing(vendors.by_key("walmart"), "<title>x</title>",
                                   text="$0.00\nCurrent price is\nNow $109.99\nAs low as $20/mo\nOut of stock")
    assert (walmart.price, walmart.available) == (109.99, False)


def _ld(offer: dict) -> str:
    return ('<html><head><title>Box | GameStop</title><script type="application/ld+json">'
            + json.dumps({"@type": "Product", "name": "Box", "offers": [{"@type": "Offer", "price": "99.99", "priceCurrency": "USD",
                                                                          "availability": "https://schema.org/InStock", **offer}]})
            + "</script></head></html>")


@pytest.mark.parametrize("offer,skipped", [
    ({"seller": {"@type": "Organization", "name": "GameStop"}, "itemCondition": "https://schema.org/NewCondition"}, None),
    ({"seller": {"@type": "Organization", "name": "GameStop"}, "itemCondition": "https://schema.org/UsedCondition"}, "used / pre-owned offer (used)"),
    ({"seller": {"@type": "Organization", "name": "Card Shack"}, "itemCondition": "NewCondition"}, "third-party seller (Card Shack)"),
    ({}, "No seller shown"),                                        # the page doesn't say → fail closed
])
def test_json_ld_seller_and_condition_decide_for_gamestop(offer, skipped):
    listing = vendors.read_listing(vendors.by_key("gamestop"), _ld(offer), text="")
    assert listing.price == 99.99 and listing.title == "Box"
    assert listing.skipped is None if skipped is None else skipped in listing.skipped


def test_seller_and_condition_rules_are_opt_in():
    """Other stores keep reading used / marketplace offers (eBay singles are often 'Used')."""
    listing = vendors.read_listing(vendors.by_key("ebay"), _ld({"seller": {"name": "someone"}, "itemCondition": "https://schema.org/UsedCondition"}), text="")
    assert (listing.price, listing.seller, listing.condition, listing.skipped) == (99.99, "someone", "used", None)


@pytest.mark.parametrize("value,cond,new", [
    ("https://schema.org/NewCondition", "new", True), ("http://schema.org/RefurbishedCondition", "refurbished", False),
    ("UsedCondition", "used", False), ("New", "New", True), ("Brand New", "Brand New", True), ("Pre-owned", "Pre-owned", False), (None, None, False),
])
def test_condition_of(value, cond, new):
    assert storepage.condition_of(value) == cond
    assert storepage.is_new(cond) is new


@pytest.mark.parametrize("url,key", [
    ("https://www.amazon.com/Magic-Gathering-Lorwyn-Eclipsed-Booster/dp/B0FP42WVL7/ref=sr_1_2", "amazon"),
    ("https://www.amazon.com/dp/B0FP42WVL7", "amazon"),
    ("https://www.amazon.com/gp/product/B0FP42WVL7", "amazon"),
    ("https://www.walmart.com/ip/Magic-The-Gathering-Lorwyn-Eclipsed-Play-Booster-Box-30-Packs/18433274568", "walmart"),
    ("https://www.walmart.com/ip/18433274568", "walmart"),
    ("https://www.gamestop.com/toys-games/trading-cards/products/magic-the-gathering-edge-of-eternities-play-booster-box/425777.html", "gamestop"),
])
def test_marketplace_product_urls(url, key):
    parts = urlsplit(url)
    m = vendors.classify(parts.hostname, parts.path)
    assert (m.kind, m.vendor.key) == ("product", key)


@pytest.mark.parametrize("url", ["https://www.amazon.com/s?k=magic", "https://www.amazon.com/gp/cart/view.html",
                                 "https://www.walmart.com/search?q=magic", "https://www.walmart.com/cart",
                                 "https://www.gamestop.com/toys-games/trading-cards", "https://www.gamestop.com/search/?q=magic"])
def test_marketplace_other_pages_arent_products(url):
    parts = urlsplit(url)
    assert vendors.classify(parts.hostname, parts.path).kind == "store_page"


def test_read_prices_says_why_a_marketplace_offer_isnt_counted():
    fixture = _rendered("walmart-third-party")
    rows = deals.read_prices([fixture["url"]], pages={fixture["url"]: fixture["extract"]})
    assert rows[0]["price"] is None
    assert rows[0]["error"] == "Sold by a third-party seller (CardsHQ) — Deals only counts Walmart itself."


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
    # Best Buy: the first whole-line $ amount is the price; installments come later.
    ("bestbuy", "Magic Foundations Play Booster Box\n$159.99\nor $39.99/mo. for 4 months\nAdd to Cart", 159.99, None),
    ("bestbuy", "Commander Deck\n$44.99\nSold Out", 44.99, False),
    # eBay: the first US $ amount; installments and shipping come later.
    ("ebay", "Final Fantasy Collector Box\nUS $529.99\nor 4 interest-free payments of US $132.50\nShipping: US $20.00", 529.99, None),
    ("ebay", "This listing was ended by the seller.\nUS $99.00", 99.0, False),
    ("target", "MTG Foundations Bundle\n$59.99\nOut of stock at your store", 59.99, False),
    ("target", "Pay in 4 interest-free payments of $10.00\n$39.99 was $43.99", 39.99, None),
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


def test_shopify_variant_links_read_that_variant():
    page = _page("cashcards")
    v = vendors.by_key("cashcards")
    by_id = vendors.read_listing(v, page, variant="46755709747427")
    assert (by_id.price, by_id.available, by_id.title) == (69.99, True, "2018 Commander Deck — Adaptive Enchantment")
    by_name = vendors.read_listing(v, page, variant="subjective")
    assert (by_name.price, by_name.title) == (59.99, "2018 Commander Deck — Subjective Reality")


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

    def fake_read(url, fresh=False, rendered=None):
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


# ---------- retro review B: store reads ----------

def test_osascript_times_out_with_a_plain_message(monkeypatch):
    seen = {}

    def boom(*a, **kw):
        seen.update(kw)
        raise subprocess.TimeoutExpired("osascript", kw["timeout"])

    monkeypatch.setattr(storefetch.subprocess, "run", boom)
    with pytest.raises(storefetch.TabUnreadable, match="Chrome didn’t answer in 30 s"):
        storefetch._osascript("x")
    assert seen["timeout"] == 30


def test_osascript_failure_is_tab_unreadable_but_js_off_is_kept(monkeypatch):
    def fake(err):
        return lambda *a, **kw: subprocess.CompletedProcess(a, 1, "", err)

    monkeypatch.setattr(storefetch.subprocess, "run", fake("execution error: boom"))
    with pytest.raises(storefetch.TabUnreadable):
        storefetch._osascript("x")
    monkeypatch.setattr(storefetch.subprocess, "run", fake("Allow JavaScript from Apple Events is turned off"))
    with pytest.raises(storefetch.JsEventsOff):
        storefetch._osascript("x")


def test_read_prices_shows_the_tab_unreadable_message(monkeypatch):
    def fake_read(url, fresh=False, rendered=None):
        raise storefetch.TabUnreadable("Chrome didn’t answer in 30 s — close any open Chrome dialog and read again")

    monkeypatch.setattr(storefetch, "read", fake_read)
    monkeypatch.setattr(deals, "_record_store_health", lambda rows: None)
    rows = deals.read_prices(["https://www.bestbuy.com/product/x/1"], pages={"https://www.bestbuy.com/product/x/1": {}})
    assert rows[0]["error"].startswith("Chrome didn’t answer")


class _Resp:
    def __init__(self, status, text="body"):
        self.status_code, self.text = status, text


class _Client:
    def __init__(self, status):
        self.status, self.calls = status, 0

    def get(self, *a, **kw):
        self.calls += 1
        return _Resp(self.status)


@pytest.mark.parametrize("status,cached", [(200, True), (404, True), (403, False), (429, False), (401, False), (500, False), (503, False)])
def test_only_200_and_404_are_cached(monkeypatch, tmp_path, status, cached):
    monkeypatch.setenv("MM_VENDOR_CACHE", str(tmp_path))
    monkeypatch.setattr(storefetch, "_pace", lambda host: None)
    c = _Client(status)
    storefetch._get("https://x.example/p", client=c)
    storefetch._get("https://x.example/p", client=c)
    assert c.calls == (1 if cached else 2)


def test_server_errors_say_the_site_is_unavailable():
    with pytest.raises(storepage.Blocked, match=r"unavailable right now \(HTTP 503\)"):
        storepage.check_blocked("", 503)
    storepage.check_blocked("<html></html>", 200)
    with pytest.raises(storepage.Blocked, match="blocked the request"):
        storepage.check_blocked("", 429)


@pytest.mark.parametrize("key,text", [
    ("bestbuy", "Box\n$159.99\nAdd to Cart\nPickup not available at Springfield\nShipping: sold out of express"),
    ("target", "Box\n$59.99\nAdd to cart\nShip it\nPickup not available\nNot available at your store"),
    # Carousels below the buy box carry their own buttons: the main offer's state comes first.
    ("bestbuy", "Sold by\nBest Buy\n$174.99\nAdd to cart\nSold by\nReturn & Exchange Policy\n$29.99\nSold Out\n$59.99\nIn Store Only"),
    ("bestbuy", "$29.99\nShipping not available for this item\nAdd to cart"),
    ("target", "$39.99 was $43.99\nAdd to cart\nFrequently bought together\n$24.99\nOut of stock"),
])
def test_buy_box_sold_out_patterns_ignore_stray_wording(key, text):
    listing = vendors.read_listing(vendors.by_key(key), "<html><head><title>x</title></head></html>", text=text)
    assert listing.available is not False


def test_jsonld_first_product_in_document_order_wins():
    ld = json.dumps([{"@type": "Product", "name": "Main", "offers": {"price": "100"}},
                     {"@type": "Product", "name": "Related", "offers": {"price": "5"}}])
    page = f'<html><head><script type="application/ld+json">{ld}</script></head></html>'
    listing = storepage.read_meta(page)
    assert (listing.price, listing.title) == (100.0, "Main")


def test_meta_content_may_contain_apostrophes():
    page = '<meta property="og:title" content="Tarkir Collector\'s Booster Box"><meta property="product:price:amount" content="9.99">'
    assert storepage.read_meta(page).title == "Tarkir Collector's Booster Box"
    page = '<meta content="Collector\'s Box" property="og:title">'
    assert storepage._meta(page, "og:title") == "Collector's Box"


def test_content_values_never_run_across_tags():
    viewport = '<meta name="viewport" content="width=device-width, initial-scale=1">'
    page = f'{viewport}<title>X</title><div class="a" itemprop="price">$49.99</div>'
    assert storepage.read_meta(page).price is None
    page = f'{viewport}<meta content="Real Box" property="og:title">'
    assert storepage._meta(page, "og:title") == "Real Box"
    page = f'{viewport}<span content=\'Collector"s\' itemprop="price">x</span><span itemprop="price" content="12.50">'
    assert storepage.read_meta(page).price == 12.50


@pytest.mark.parametrize("key,text", [
    ("bestbuy", "Box\n$159.99\nSold Out\nPickup not available"),
    ("bestbuy", "Box\n$159.99\ncoming soon"),
    ("bestbuy", "$29.99\nUnavailable Nearby\nSold by\nReturn & Exchange Policy\n$19.99\nAdd to cart"),
    ("bestbuy", "$41.99\nIn Store Only\nSold by\nReturn & Exchange Policy\nMost likely in store only\nAdd to cart"),
    ("target", "$44.99\nPickup\nNot available\nShipping\nNot available\nOut of stock\nNotify me when available\nAdd to cart"),
    ("target", "Box\n$59.99\nOut of stock at your store\nShip it"),
    ("target", "Box\n$59.99\nSold out"),
])
def test_buy_box_sold_out_patterns_still_catch_sold_out(key, text):
    listing = vendors.read_listing(vendors.by_key(key), "<html><head><title>x</title></head></html>", text=text)
    assert listing.available is False
