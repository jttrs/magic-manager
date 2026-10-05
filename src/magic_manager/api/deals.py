"""Deals surface of the typed API (internal — ``deals`` feature flag)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import deals, features


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
