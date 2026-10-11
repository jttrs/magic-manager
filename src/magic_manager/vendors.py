"""The vendor recipe book (``config/vendors.toml``): which store a URL belongs
to, and how its product pages are read.

Each :class:`Vendor` names the store, its hosts, how a product URL looks, the
read ``mode`` (``shopify`` | ``meta`` | ``rendered``, see docs/deals-scraping.md),
optional regex patterns for price / stock / title when page tags aren't
enough, a sample product for the nightly canary, and whether it charges sales
tax (a cross-store tiebreaker only — deal deltas are always at face price).

Marketplaces (Amazon, Walmart) also name the store's own seller names and
whether only new offers count: a listing sold by someone else, in a used
condition, or with no main offer at all is read but not counted
(``Listing.skipped`` → :class:`storepage.NotCounted` with a plain note).
"""
from __future__ import annotations

import html as htmllib
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from . import config, storepage

Mode = Literal["shopify", "meta", "rendered"]


@dataclass(frozen=True)
class Vendor:
    key: str
    name: str
    hosts: tuple[str, ...]
    mode: Mode
    product_path: str
    sample_url: str | None = None
    no_sales_tax: bool = False
    price_pattern: str | None = None
    stock_pattern: str | None = None
    sold_out_pattern: str | None = None
    title_pattern: str | None = None
    seller_pattern: str | None = None       # group 1 = the main offer's seller (visible text)
    sellers: tuple[str, ...] = ()           # the store's own seller names; others aren't counted
    condition_pattern: str | None = None    # group 1 = the main offer's condition (visible text)
    new_only: bool = False                  # a used / pre-owned / renewed offer isn't counted
    no_offer_pattern: str | None = None     # the page has no main offer (e.g. "Currently unavailable")
    title_strip: str | None = None          # removed from the title (store name / category noise)

    def is_product(self, path: str) -> bool:
        return re.search(self.product_path, path) is not None


@lru_cache(maxsize=1)
def catalog() -> tuple[Vendor, ...]:
    rows = config.load_toml("vendors.toml", required=True).get("vendor", [])
    out = []
    for r in rows:
        if r.get("mode") not in ("shopify", "meta", "rendered"):
            raise config.ConfigError(f"vendors.toml: {r.get('key')!r} has an unknown mode {r.get('mode')!r}")
        out.append(Vendor(**{**r, "hosts": tuple(h.lower().removeprefix("www.") for h in r["hosts"]),
                             "sellers": tuple(r.get("sellers", ()))}))
    return tuple(out)


def by_key(key: str) -> Vendor:
    for v in catalog():
        if v.key == key:
            return v
    raise KeyError(f"unknown vendor {key!r}")


_SHOPIFY_PRODUCT = r"/products/[^/?#]+"


@dataclass(frozen=True)
class Match:
    kind: Literal["product", "store_page", "maybe_shopify", "other"]
    vendor: Vendor | None = None


def classify(host: str, path: str) -> Match:
    """What a tab is: a product page of a catalogued store, another page of one
    (cart, collection…), a product page of an uncatalogued Shopify-shaped store
    (a recipe candidate), or not a store at all."""
    host = host.lower().removeprefix("www.")
    for v in catalog():
        if host in v.hosts:
            return Match("product" if v.is_product(path) else "store_page", v)
    if re.search(_SHOPIFY_PRODUCT, path):
        return Match("maybe_shopify")
    return Match("other")


def read_listing(vendor: Vendor, page: str | dict, *, text: str | None = None,
                 variant: str | None = None) -> storepage.Listing:
    """Apply ``vendor``'s recipe to a fetched page (``shopify``: the product
    JSON; ``meta``: the HTML; ``rendered``: the tab's head/JSON-LD HTML plus its
    visible ``text``). Patterns fill what page tags leave unknown; a sold-out
    pattern always wins (a page can carry stale "in stock" tags). Patterns
    are case-insensitive and ``^``/``$`` anchor a line;
    when the recipe doesn't count the main offer, ``skipped`` says why."""
    if vendor.mode == "shopify":
        return storepage.read_shopify(page if isinstance(page, dict) else {}, variant)
    html = page if isinstance(page, str) else ""
    listing = storepage.read_meta(html)
    hay = text if text is not None else html
    if listing.price is None and vendor.price_pattern:
        m = re.search(vendor.price_pattern, hay, re.S | re.I | re.M)
        if m:
            listing.price, listing.currency, listing.signal = storepage._num(m.group(1)), "USD", "pattern"
    if vendor.sold_out_pattern and re.search(vendor.sold_out_pattern, hay, re.I | re.M):
        listing.available = False
    elif listing.available is None and vendor.stock_pattern and re.search(vendor.stock_pattern, hay, re.I | re.M):
        listing.available = True
    if vendor.title_pattern:
        m = re.search(vendor.title_pattern, html, re.S | re.I)
        if m:
            listing.title = re.sub(r"<[^>]+>|\s+", " ", m.group(1)).strip()
    if listing.title:  # JSON-LD names can carry raw entities (eBay: "LEGEND&#039;S")
        listing.title = htmllib.unescape(listing.title)
        if vendor.title_strip:
            listing.title = re.sub(vendor.title_strip, "", listing.title, flags=re.I).strip() or listing.title
    for attr, pattern in (("seller", vendor.seller_pattern), ("condition", vendor.condition_pattern)):
        if pattern and getattr(listing, attr) is None:
            m = re.search(pattern, hay, re.I | re.M)
            if m:
                setattr(listing, attr, re.sub(r"\s+", " ", m.group(1)).strip() or None)
    listing.skipped = _not_counted(vendor, listing, hay)
    return listing


def _not_counted(vendor: Vendor, listing: storepage.Listing, hay: str) -> str | None:
    """Why ``vendor``'s recipe doesn't count this listing's main offer, or None."""
    if vendor.no_offer_pattern and re.search(vendor.no_offer_pattern, hay, re.I | re.M):
        return f"{vendor.name} has no offer on this page right now (it says it’s unavailable)."
    if vendor.new_only and listing.condition and not storepage.is_new(listing.condition):
        return f"A used / pre-owned offer ({listing.condition}) — Deals only counts new."
    own = {s.casefold() for s in vendor.sellers}
    if own and not listing.seller:
        return f"No seller shown for the main offer — Deals only counts {vendor.name} itself."
    if own and listing.seller.casefold() not in own:
        return f"Sold by a third-party seller ({listing.seller}) — Deals only counts {vendor.name} itself."
    return None
