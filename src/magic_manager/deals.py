"""Deals: open shopping tabs → vendor product pages (prices come with the recipes).

Composes :mod:`tabs` (read the browser) and :mod:`vendors` (the recipe book).
"""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import urlsplit

from . import storefetch, storepage, tabs as tabs_mod, vendors


def open_tabs(browser: str = "chrome", **read_kw) -> dict:
    """Your open tabs sorted into: product pages per catalogued store, Shopify-
    shaped stores without a recipe yet, and a count of everything else."""
    read = tabs_mod.read_tabs(browser, **read_kw)
    stores: dict[str, dict] = {}
    candidates: dict[str, list[dict]] = defaultdict(list)
    store_pages = other = 0
    for t in read.tabs:
        m = vendors.classify(t.host, urlsplit(t.url).path)
        entry = {"url": t.url, "title": t.title, "window": t.window, "tab": t.tab}
        if m.kind == "product":
            v = m.vendor
            s = stores.setdefault(v.key, {"key": v.key, "name": v.name, "mode": v.mode,
                                          "no_sales_tax": v.no_sales_tax, "tabs": []})
            s["tabs"].append(entry)
        elif m.kind == "store_page":
            store_pages += 1
        elif m.kind == "maybe_shopify":
            candidates[t.host].append(entry)
        else:
            other += 1
    order = [v.key for v in vendors.catalog()]
    return {
        "browser": read.browser, "windows": read.windows, "windows_read": read.windows_read,
        "warnings": read.warnings,
        "stores": sorted(stores.values(), key=lambda s: order.index(s["key"])),
        "uncatalogued": [{"host": h, "tabs": ts} for h, ts in sorted(candidates.items(), key=lambda kv: -len(kv[1]))],
        "store_pages": store_pages, "other": other,
        "dropped_local": read.dropped_local, "duplicates": read.duplicates,
    }


def read_prices(urls: list[str], *, progress=None, fresh: bool = False) -> list[dict]:
    """Price + stock for each product URL with its store's recipe. Never raises
    per URL: each row carries ``error`` (blocked, tab closed, JS events off, …)
    so one bad page doesn't sink the batch. A ``JsEventsOff`` is reported once
    and the remaining open-tab reads are skipped with the same message."""
    rows: list[dict] = []
    js_off: str | None = None
    for i, url in enumerate(urls, 1):
        if progress:
            progress(i, len(urls), url)
        row: dict = {"url": url, "price": None, "currency": None, "available": None, "title": None, "signal": "", "error": None}
        try:
            parts = urlsplit(url)
            m = vendors.classify(parts.hostname or "", parts.path)
            if js_off and m.vendor and m.vendor.mode == "rendered":
                raise storefetch.JsEventsOff(js_off)
            v, listing = storefetch.read(url, fresh=fresh)
            row.update(vendor=v.key, price=listing.price, currency=listing.currency,
                       available=listing.available, title=listing.title, signal=listing.signal)
            if listing.price is None:
                row["error"] = "No price found on the page — the store’s page may have changed."
        except storefetch.JsEventsOff as e:
            js_off = str(e)
            row["error"] = js_off
        except (storepage.Blocked, storefetch.TabGone, LookupError) as e:
            row["error"] = str(e)[:1].upper() + str(e)[1:]
        except Exception as e:  # noqa: BLE001 — one store's surprise never sinks the batch
            row["error"] = f"Couldn’t read this page ({type(e).__name__})."
        rows.append(row)
    return rows
