"""Deals: open shopping tabs → store prices → what each listing is → vs market.

Composes :mod:`tabs` (read the browser), :mod:`vendors` + :mod:`storefetch`
(the recipe book), :mod:`listing_match` (what a listing is) and :mod:`valuation`
(what it is worth). Deltas are at FACE price — no-tax is a tiebreaker only.
"""
from __future__ import annotations

import json
from collections import defaultdict
from urllib.parse import urlsplit

from . import db, listing_match, storefetch, storepage, tabs as tabs_mod, valuation, vendors


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


# ---------- what each listing is, and what it's worth ----------

_MATCH_KEY = "deals.match:"


def confirmed_matches(urls: list[str]) -> dict[str, dict]:
    """Your confirmed matches (url → {kind, set_code, name, scryfall_id, finish})."""
    if not urls:
        return {}
    with db.connect() as conn:
        rows = conn.execute(f"SELECT key, value FROM settings WHERE key IN ({','.join('?' * len(urls))})",
                            [_MATCH_KEY + u for u in urls]).fetchall()
    return {r[0][len(_MATCH_KEY):]: json.loads(r[1]) for r in rows}


def confirm_match(url: str, choice: dict | None) -> None:
    """Remember (or, with ``None``, forget) what a listing is."""
    with db.connect() as conn:
        if choice is None:
            conn.execute("DELETE FROM settings WHERE key = ?", (_MATCH_KEY + url,))
        else:
            keep = {k: choice.get(k) for k in ("kind", "set_code", "name", "scryfall_id", "finish")}
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                         (_MATCH_KEY + url, json.dumps(keep)))


def _cand(c: listing_match.Candidate, kind: str) -> dict:
    return {"kind": kind, "set_code": c.set_code, "name": c.name, "scryfall_id": c.scryfall_id,
            "finish": c.finish, "price": c.price}


def _value(choice: dict, cache: dict) -> dict:
    """Market + contents for a matched listing (cached per product in a run)."""
    kind = choice["kind"]
    if kind == "single":
        price = choice.get("price")
        if price is None and choice.get("scryfall_id"):
            with db.connect() as conn:
                r = conn.execute("SELECT prices_usd, prices_usd_foil FROM cards WHERE scryfall_id = ?", (choice["scryfall_id"],)).fetchone()
            if r:
                price = r[1] if choice.get("finish") == "foil" else r[0]
        return {"market": price, "contents": None, "partial": False}
    key = (kind, choice["set_code"], choice["name"], choice.get("finish"))
    if key not in cache:
        if kind == "sld":
            v = valuation.value_sld_drop(choice["name"], edition=choice.get("finish") or "auto", floors=False)
            cache[key] = {"market": v.sealed_market, "contents": v.exact_singles, "partial": False}
        else:
            v = valuation.value_sealed_product(choice["set_code"], choice["name"], floors=False)
            cache[key] = {"market": v.sealed_market, "contents": v.intrinsic, "partial": bool(v.unpriced_cards)}
    return cache[key]


def compare(row: dict, *, confirmed: dict | None = None, cache: dict | None = None) -> dict:
    """Add what the listing is and what it's worth to a price row: ``kind``,
    ``status`` (matched | ambiguous | unmatched | skipped | confirmed), ``match``,
    ``candidates``, ``note``, ``market``, ``contents``, ``delta`` (face price −
    market; never pre-discounted for tax) and ``pct``."""
    cache = {} if cache is None else cache
    out = {**row, "kind": None, "status": None, "match": None, "candidates": [], "note": "",
           "market": None, "contents": None, "partial": False, "delta": None, "pct": None}
    if confirmed:
        out.update(kind=confirmed["kind"], status="confirmed", match=confirmed)
    elif row.get("title"):
        m = listing_match.match(row["title"], row.get("price"))
        out.update(kind=m.kind, status=m.status, note=m.note,
                   match=_cand(m.match, m.kind) if m.match else None,
                   candidates=[_cand(c, m.kind) for c in m.candidates])
    if out["match"]:
        try:
            out.update(_value(out["match"], cache))
        except Exception as e:  # noqa: BLE001 — a valuation miss shouldn't hide the price
            out["note"] = f"Couldn’t value it: {e}"
    if out["market"] is not None and row.get("price") is not None:
        out["delta"] = round(row["price"] - out["market"], 2)
        out["pct"] = round(out["delta"] / out["market"] * 100, 1) if out["market"] else None
    return out


def read_and_compare(urls: list[str], *, progress=None, fresh: bool = False) -> list[dict]:
    """Read every product page's price, then what it is and what it's worth."""
    rows = read_prices(urls, progress=progress, fresh=fresh)
    confirmed = confirmed_matches(urls)
    cache: dict = {}
    out = []
    for i, r in enumerate(rows, 1):
        if progress:
            progress(i, len(rows), f"valuing {r.get('title') or r['url']}")
        out.append(compare(r, confirmed=confirmed.get(r["url"]), cache=cache))
    return out
