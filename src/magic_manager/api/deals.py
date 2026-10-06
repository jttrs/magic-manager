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


class PriceOut(BaseModel):
    url: str
    vendor: str | None = None
    price: float | None
    currency: str | None
    available: bool | None = Field(description="None when the page doesn't say.")
    title: str | None
    signal: str = Field(description="Which signal gave the price: shopify, meta, json-ld, microdata, pattern.")
    error: str | None


class ReadPricesInput(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=300)
    fresh: bool = Field(False, description="Skip the 30-minute page cache.")


def _run_read_prices(inp: ReadPricesInput, progress: ProgressFn) -> JobResult:
    features.require("deals")
    rows = deals.read_prices(inp.urls, fresh=inp.fresh,
                             progress=lambda i, n, url: progress(ProgressEvent(i - 1, n, url)))
    out = [PriceOut(**r).model_dump() for r in rows]
    priced = sum(1 for r in out if r["price"] is not None)
    return JobResult(summary=f"{priced} of {len(out)} prices read",
                     artifacts=[Artifact(kind="json", label="prices", data=out)])


READ_PRICES = register(JobSpec(
    name="deals.read_prices",
    title="Read store prices",
    description="Read price and stock for store product pages (server-side, or from your open tab).",
    input_model=ReadPricesInput,
    run=_run_read_prices,
))
