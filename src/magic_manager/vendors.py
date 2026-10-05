"""The vendor recipe book: which store a URL belongs to and how to read it.

Each :class:`Vendor` names the store, the hosts it answers on, how a product
page's URL looks, how its price is read (``mode``, see docs/deals-scraping.md),
and whether it charges sales tax (a cross-store tiebreaker only — deal deltas
are always at face price).

Modes: ``shopify`` (server-side ``<product>.json``), ``meta`` (og:price /
JSON-LD from a plain GET), ``rendered`` (read the already-rendered tab via
AppleScript — bot-blocked, JS-priced retailers; never fetched server-side).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Mode = Literal["shopify", "meta", "rendered"]


@dataclass(frozen=True)
class Vendor:
    key: str
    name: str
    hosts: tuple[str, ...]
    mode: Mode
    product_path: str                # regex on the URL path
    no_sales_tax: bool = False

    def is_product(self, path: str) -> bool:
        return re.search(self.product_path, path) is not None


_SHOPIFY_PRODUCT = r"/products/[^/?#]+"

VENDORS: tuple[Vendor, ...] = (
    Vendor("manyrealms", "Many Realms", ("manyrealms.com",), "shopify", _SHOPIFY_PRODUCT, no_sales_tax=True),
    Vendor("pokebox", "PokeBox", ("pokeboxusa.com",), "shopify", _SHOPIFY_PRODUCT, no_sales_tax=True),
    Vendor("bestbuy", "Best Buy", ("bestbuy.com",), "rendered", r"^/(site|product)/.+"),
    Vendor("ebay", "eBay", ("ebay.com",), "rendered", r"^/itm/\d+"),
)

_BY_HOST = {h: v for v in VENDORS for h in v.hosts}


@dataclass(frozen=True)
class Match:
    kind: Literal["product", "store_page", "maybe_shopify", "other"]
    vendor: Vendor | None = None


def classify(host: str, path: str) -> Match:
    """What a tab is: a product page of a catalogued store, another page of one
    (cart, collection…), a product page of an uncatalogued Shopify-shaped store
    (a recipe candidate), or not a store at all."""
    host = host.lower().removeprefix("www.")
    v = _BY_HOST.get(host)
    if v:
        return Match("product" if v.is_product(path) else "store_page", v)
    if re.search(_SHOPIFY_PRODUCT, path):
        return Match("maybe_shopify")
    return Match("other")
