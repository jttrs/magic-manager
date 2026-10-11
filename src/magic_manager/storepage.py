"""Read a store product page into a listing: price, currency, stock, title.

Pure parsers (no network) so every recipe is testable against saved fixture
pages. Signals, most authoritative first (see docs/deals-scraping.md):

* ``shopify``  — Shopify's storefront ``<product-url>.js``: ``variants[].price``
  (cents) / ``available`` (the cheapest available variant).
* ``meta``     — ``product:price:amount`` / ``og:price:amount`` (+ currency,
  ``og:availability`` / ``product:availability``); then schema.org JSON-LD
  ``Product.offers``; then schema.org microdata ``itemprop="price"``.
* ``text``     — a recipe-specific regex over the HTML (last resort, fragile).

Bot walls ("Just a moment…", "Robot or human?", "Attention Required!") are
recognized so a blocked read says so instead of returning a wrong price.

JSON-LD offers also say WHO sells the offer and in what condition; a recipe
may refuse to count a listing (marketplace seller, used offer) — the listing
then carries ``skipped`` (a plain note) and the read raises :class:`NotCounted`.
"""
from __future__ import annotations

import html as htmllib
import json
import re
from collections import deque
from dataclasses import dataclass

_BLOCK_TITLES = ("just a moment", "robot or human", "attention required", "access denied", "are you a robot", "pardon our interruption")


@dataclass
class Listing:
    price: float | None
    currency: str | None = None
    available: bool | None = None       # None = the page doesn't say
    title: str | None = None
    signal: str = ""                    # which signal produced the price
    seller: str | None = None           # who sells the main offer, when the page says
    condition: str | None = None        # the main offer's condition ("new", "used", "Pre-owned"…)
    skipped: str | None = None          # why the store's recipe doesn't count this listing


class Blocked(RuntimeError):
    """The store served a bot wall or refused the request."""


class NotCounted(LookupError):
    """The page's main offer isn't one Deals counts (a marketplace seller, a
    used offer, no offer at all) — the message says which, in plain words."""


def _num(v) -> float | None:
    if v is None:
        return None
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(v))
    return float(m.group(0).replace(",", "")) if m else None


def _avail(v) -> bool | None:
    s = str(v or "").lower()
    if not s:
        return None
    if any(k in s for k in ("outofstock", "out of stock", "out_of_stock", "soldout", "sold out", "discontinued")):
        return False
    if any(k in s for k in ("instock", "in stock", "in_stock", "preorder", "pre-order", "presale", "onlineonly", "limitedavailability", "true")):
        return True
    return None


def title_of(page: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    return htmllib.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else None


def check_blocked(page: str, status: int = 200) -> None:
    t = (title_of(page) or "").lower()
    if status in (401, 403, 429) or any(b in t for b in _BLOCK_TITLES):
        raise Blocked(f"the store blocked the request ({status}{', ' + t if t else ''})")
    if status not in (200, 404):
        raise Blocked(f"the store’s site is unavailable right now (HTTP {status})")


def _meta(page: str, *names: str) -> str | None:
    for name in names:
        for pat in (rf'<meta[^>]+(?:property|name|itemprop)=["\']{re.escape(name)}["\'][^>]*content=(["\'])(.*?)\1',
                    rf'<meta[^>]+content=(["\'])(.*?)\1[^>]*(?:property|name|itemprop)=["\']{re.escape(name)}["\']'):
            m = re.search(pat, page, re.I)
            if m:
                return htmllib.unescape(m.group(2)).strip()
    return None


def _ld_name(v) -> str | None:
    if isinstance(v, dict):
        v = v.get("name")
    return str(v).strip() if isinstance(v, str) and v.strip() else None


def condition_of(v) -> str | None:
    """A condition as the page states it; schema.org URLs → ``new`` / ``used``
    / ``refurbished`` / ``damaged``."""
    s = str(v or "").strip()
    if not s:
        return None
    m = re.fullmatch(r"(?:https?://schema\.org/)?(\w+?)Condition", s, re.I)
    return m.group(1).lower() if m else s


def is_new(condition: str | None) -> bool:
    return bool(re.fullmatch(r"(?:brand[\s-]+)?new(?:condition)?", (condition or "").strip(), re.I))


def _jsonld_offers(page: str):
    """Yield (price, currency, availability, name, seller, condition) from
    schema.org JSON-LD."""
    for block in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        stack = deque([data])
        while stack:
            node = stack.popleft()
            if isinstance(node, list):
                stack.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            stack.extend(v for k, v in node.items() if k in ("@graph", "mainEntity", "itemListElement"))
            t = node.get("@type")
            types = t if isinstance(t, list) else [t]
            if "Product" in types or "ProductGroup" in types:
                offers = node.get("offers")
                for o in offers if isinstance(offers, list) else [offers] if offers else []:
                    if isinstance(o, dict):
                        price = o.get("price", o.get("lowPrice"))
                        yield (_num(price), o.get("priceCurrency"), o.get("availability"), node.get("name"),
                               _ld_name(o.get("seller")), condition_of(o.get("itemCondition")))


def read_meta(page: str) -> Listing:
    """Price from page tags: product/og meta → JSON-LD offers → microdata."""
    title = _meta(page, "og:title") or title_of(page)
    price = _num(_meta(page, "product:price:amount", "og:price:amount"))
    if price is not None:
        avail = _avail(_meta(page, "product:availability", "og:availability"))
        if avail is None:
            avail = next((_avail(o[2]) for o in _jsonld_offers(page) if o[2]), None)
        if avail is None:
            m = re.search(r'itemprop=["\']availability["\'][^>]*(?:href|content)=["\']([^"\']+)["\']', page, re.I)
            avail = _avail(m.group(1)) if m else None
        return Listing(price, _meta(page, "product:price:currency", "og:price:currency"), avail, title, "meta")
    for p, cur, av, name, seller, cond in _jsonld_offers(page):
        if p is not None:
            return Listing(p, cur, _avail(av), name or title, "json-ld", seller=seller, condition=cond)
    m = re.search(r'itemprop=["\']price["\'][^>]*content=(["\'])(.+?)\1', page, re.I) or \
        re.search(r'content=(["\'])(.+?)\1[^>]*itemprop=["\']price["\']', page, re.I)
    if m:
        av = re.search(r'itemprop=["\']availability["\'][^>]*(?:href|content)=["\']([^"\']+)["\']', page, re.I)
        cur = re.search(r'itemprop=["\']priceCurrency["\'][^>]*content=(["\'])(.+?)\1', page, re.I)
        return Listing(_num(m.group(2)), cur.group(2) if cur else None, _avail(av.group(1)) if av else None, title, "microdata")
    return Listing(None, title=title)


def _variant_for(variants: list[dict], want: str) -> dict | None:
    """The variant a ``?variant=`` link names: its numeric id, else a variant
    whose title contains the value (stores also use names, e.g. ``lorehold``)."""
    want = want.strip().lower()
    for v in variants:
        if str(v.get("id")) == want:
            return v
    key = re.sub(r"[^a-z0-9]+", " ", want).strip()
    hits = [v for v in variants if key and key in re.sub(r"[^a-z0-9]+", " ", str(v.get("title") or "").lower())]
    return hits[0] if len(hits) == 1 else None


def read_shopify(product: dict, variant: str | None = None) -> Listing:
    """Shopify storefront ``<product-url>.js``: prices in cents, per-variant and
    product-level ``available``. A ``variant`` (from the link's ``?variant=``)
    reads that variant — a multi-deck page's links each name one deck — and
    its title joins the product's; otherwise the cheapest available variant
    wins (else the cheapest overall, marked unavailable). A requested variant
    that can't be found raises ``LookupError`` (like a 404 product) — never
    another variant's price, and not a "page changed" recipe failure."""
    variants = product.get("variants") or []
    title = product.get("title")
    chosen = _variant_for(variants, variant) if variant else None
    if chosen is not None:
        pick, available = chosen, bool(chosen.get("available"))
        vt = str(chosen.get("title") or "")
        if vt and vt.lower() != "default title":
            title = f"{title} — {vt}"
    elif variant:
        raise LookupError("the store no longer has this variant")
    else:
        live = [v for v in variants if v.get("available")]
        pick = min(live or variants, key=lambda v: v.get("price") or 0, default=None)
        available = bool(live) if variants else product.get("available")
    if pick is None or pick.get("price") is None:
        return Listing(None, title=title)
    cents = pick["price"]
    price = cents / 100 if isinstance(cents, int) else _num(cents)
    return Listing(round(price, 2), "USD", available, title, "shopify")
