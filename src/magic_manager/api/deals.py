"""Deals surface of the typed API (internal — ``deals`` feature flag)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import deals, features
from .jobs import Artifact, JobResult, JobSpec, ProgressEvent, ProgressFn, register


class TabOut(BaseModel):
    url: str
    title: str
    window: int
    tab: int


class StoreTabsOut(BaseModel):
    key: str
    name: str
    mode: Literal["shopify", "meta", "rendered"] = Field(description="How prices are read: shopify/meta server-side, rendered from your open tab.")
    no_sales_tax: bool
    tabs: list[TabOut]


class UncataloguedOut(BaseModel):
    host: str
    tabs: list[TabOut]


class OpenTabsOut(BaseModel):
    browser: str
    windows: int
    windows_read: int
    warnings: list[str]
    stores: list[StoreTabsOut] = Field(description="Product pages of catalogued stores.")
    uncatalogued: list[UncataloguedOut] = Field(description="Shopify-shaped product pages from stores without a recipe yet.")
    store_pages: int = Field(description="Other pages of catalogued stores (carts, collections).")
    other: int = Field(description="Tabs that aren't stores.")
    dropped_local: int
    duplicates: int


def open_tabs(browser: str = "chrome") -> OpenTabsOut:
    features.require("deals")
    return OpenTabsOut(**deals.open_tabs(browser))


class MatchOut(BaseModel):
    kind: Literal["sealed", "sld", "single"]
    set_code: str
    name: str
    scryfall_id: str | None = None
    finish: str | None = None
    price: float | None = Field(None, description="Singles: the printing's market at that finish.")


class PriceOut(BaseModel):
    url: str
    vendor: str | None = None
    price: float | None
    currency: str | None
    available: bool | None = Field(description="None when the page doesn't say.")
    title: str | None
    signal: str = Field(description="Which signal gave the price: shopify, meta, json-ld, microdata, pattern.")
    error: str | None
    kind: Literal["sealed", "sld", "single", "other_game", "unknown"] | None = None
    status: Literal["matched", "ambiguous", "unmatched", "skipped", "confirmed"] | None = None
    match: MatchOut | None = None
    candidates: list[MatchOut] = Field(default_factory=list)
    note: str = ""
    market: float | None = Field(None, description="Sealed market, Secret Lair market, or the single's price.")
    contents: float | None = Field(None, description="What the cards inside are worth (sealed / Secret Lair).")
    partial: bool = Field(False, description="Some cards inside have no price — contents undercounts.")
    delta: float | None = Field(None, description="Face price minus market (negative = below market).")
    pct: float | None = None
    watching: bool = Field(False, description="This link is on your watchlist (its price history is kept).")


class ReadPricesInput(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=300)
    fresh: bool = Field(False, description="Skip the 30-minute page cache.")


def _run_read_prices(inp: ReadPricesInput, progress: ProgressFn) -> JobResult:
    features.require("deals")
    rows = deals.read_and_compare(inp.urls, fresh=inp.fresh,
                                  progress=lambda i, n, msg: progress(ProgressEvent(i - 1, n, msg)))
    out = [PriceOut(**r).model_dump() for r in rows]
    priced = sum(1 for r in out if r["price"] is not None)
    valued = sum(1 for r in out if r["delta"] is not None)
    return JobResult(summary=f"{priced} of {len(out)} prices read · {valued} compared to market",
                     artifacts=[Artifact(kind="json", label="prices", data=out)])


READ_PRICES = register(JobSpec(
    name="deals.read_prices",
    title="Read store prices",
    description="Read price and stock for store product pages, identify each product, and compare it to market.",
    input_model=ReadPricesInput,
    run=_run_read_prices,
))


class ConfirmIn(BaseModel):
    url: str
    title: str | None = None
    price: float | None = None
    currency: str | None = None
    available: bool | None = None
    choice: MatchOut | None = Field(description="What the listing is; null forgets a confirmation.")


def confirm(req: ConfirmIn) -> PriceOut:
    """Remember what a listing is, then value it with that choice."""
    features.require("deals")
    deals.confirm_match(req.url, req.choice.model_dump() if req.choice else None)
    row = {"url": req.url, "vendor": None, "price": req.price, "currency": req.currency, "available": req.available,
           "title": req.title, "signal": "", "error": None}
    watched = deals.watched_identities([req.url])
    confirmed = deals.confirmed_matches([req.url]).get(req.url) or watched.get(req.url)
    return PriceOut(**deals.compare(row, confirmed=confirmed), watching=req.url in watched)


class WatchIn(BaseModel):
    url: str
    choice: MatchOut
    price: float | None = None
    currency: str | None = "USD"


class WatchOut(BaseModel):
    watching: bool
    message: str


def watch(req: WatchIn) -> WatchOut:
    features.require("deals")
    deals.watch(req.url, req.choice.model_dump(), price=req.price, currency=req.currency)
    return WatchOut(watching=True, message="Watching — its price is saved each time you read it.")


def unwatch(url: str) -> WatchOut:
    features.require("deals")
    deals.unwatch(url)
    return WatchOut(watching=False, message="No longer watching this link.")


class PricePointOut(BaseModel):
    price: float | None
    at: str


class WatchStoreOut(BaseModel):
    url: str
    store: str | None
    price: float | None
    available: bool | None
    read_at: str
    read: bool = Field(description="False when the latest price is still the earmark's saved asking price.")
    first_price: float | None
    first_at: str
    change: float | None = Field(description="Latest minus first price seen here.")
    history: list[PricePointOut]


class WatchedOut(BaseModel):
    set_code: str
    name: str
    kind: Literal["sealed", "sld"]
    finish: str | None = None
    category: str | None
    subtype: str | None = None
    release_date: str | None
    market: float | None = None
    contents: float | None = None
    partial: bool = False
    best_price: float | None
    best_store: str | None
    best_url: str | None
    delta: float | None = None
    pct: float | None = None
    stores: list[WatchStoreOut]
    error: str | None = None


def watched() -> list[WatchedOut]:
    """Every watched product with its stores' prices — instant (no valuation;
    values come per product from /api/market/product-cost)."""
    features.require("deals")
    return [WatchedOut(**r) for r in deals.watchlist(values=False)]


class WatchlistInput(BaseModel):
    refresh: bool = Field(False, description="Read every watched link's price first.")


def _run_watchlist(inp: WatchlistInput, progress: ProgressFn) -> JobResult:
    features.require("deals")
    read = []
    if inp.refresh:
        urls = deals.watched_urls()
        read = deals.read_and_compare(urls, progress=lambda i, n, msg: progress(ProgressEvent(i - 1, n, f"reading {msg}")))
    rows = deals.watchlist(values=False)
    out = [WatchedOut(**r).model_dump() for r in rows]
    errors = [PriceOut(**r).model_dump() for r in read if r.get("error")]
    summary = f"{len(out)} watched products" + (f" · {len(read) - len(errors)} of {len(read)} prices read" if inp.refresh else "")
    return JobResult(summary=summary, artifacts=[Artifact(kind="json", label="watchlist", data=out),
                                                 Artifact(kind="json", label="errors", data=errors)])


WATCHLIST = register(JobSpec(
    name="deals.watchlist",
    title="Read watched prices",
    description="Read every watched link's current price (history grows) and list what you watch.",
    input_model=WatchlistInput,
    run=_run_watchlist,
))
