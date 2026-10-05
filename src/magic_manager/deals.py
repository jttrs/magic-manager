"""Deals: open shopping tabs → vendor product pages (prices come with the recipes).

Composes :mod:`tabs` (read the browser) and :mod:`vendors` (the recipe book).
"""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import urlsplit

from . import tabs as tabs_mod, vendors


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
    order = [v.key for v in vendors.VENDORS]
    return {
        "browser": read.browser, "windows": read.windows, "windows_read": read.windows_read,
        "warnings": read.warnings,
        "stores": sorted(stores.values(), key=lambda s: order.index(s["key"])),
        "uncatalogued": [{"host": h, "tabs": ts} for h, ts in sorted(candidates.items(), key=lambda kv: -len(kv[1]))],
        "store_pages": store_pages, "other": other,
        "dropped_local": read.dropped_local, "duplicates": read.duplicates,
    }
