"""Deals: open shopping tabs → store prices → what each listing is → vs market.

Composes :mod:`tabs` (read the browser), :mod:`vendors` + :mod:`storefetch`
(the recipe book), :mod:`listing_match` (what a listing is) and :mod:`valuation`
(what it is worth). Deltas are at FACE price — no-tax is a tiebreaker only.
"""
from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from urllib.parse import urlsplit

from . import db, earmarks, listing_match, market, sld, storefetch, storepage, tabs as tabs_mod, vendors


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


# A TCGplayer product page (what Market → Secret Lair's Watch saves). TCGplayer
# has no store recipe (rendered + bot-walled); a watched one is priced from its
# TCGplayer MARKET price instead of reading the page.
_TCGPLAYER_PRODUCT = re.compile(r"^https://(?:www\.)?tcgplayer\.com/product/\d+")
TCGPLAYER_MARKET = "TCGplayer market"


def is_market_link(url: str) -> bool:
    return bool(_TCGPLAYER_PRODUCT.match(url or ""))


def _market_read(row: dict, choice: dict | None) -> None:
    """Fill a TCGplayer-product row from the market price of the product it is watched as."""
    if choice is None or choice.get("kind") == "single":
        row["error"] = "Not a product page of a catalogued store."
        return
    c = market.product_cost(choice["kind"], choice["set_code"], choice["name"], choice.get("finish"))
    row.update(vendor="tcgplayer", price=c["market"], currency="USD", title=choice["name"], signal="market")
    if c["market"] is None:
        row["error"] = "TCGplayer has no market price for this yet."


def read_prices(urls: list[str], *, progress=None, fresh: bool = False) -> list[dict]:
    """Price + stock for each product URL with its store's recipe. Never raises
    per URL: each row carries ``error`` (blocked, tab closed, JS events off, …)
    so one bad page doesn't sink the batch. A ``JsEventsOff`` is reported once
    and the remaining open-tab reads are skipped with the same message. A
    watched TCGplayer product link reads its product's TCGplayer market price."""
    rows: list[dict] = []
    js_off: str | None = None
    market_ids = watched_identities([u for u in urls if is_market_link(u)])
    for i, url in enumerate(urls, 1):
        if progress:
            progress(i, len(urls), url)
        row: dict = {"url": url, "price": None, "currency": None, "available": None, "title": None, "signal": "", "error": None}
        try:
            if is_market_link(url):
                _market_read(row, market_ids.get(url))
                rows.append(row)
                continue
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


def _value(choice: dict, cache: dict | None = None) -> dict:
    """Market + contents for a matched listing. Sealed products and Secret Lair
    drops go through ``market.product_cost`` (memoized 30 min — the same figures
    the product inspector shows); a single is its printing's price."""
    if choice["kind"] == "single":
        price = choice.get("price")
        if price is None and choice.get("scryfall_id"):
            with db.connect() as conn:
                r = conn.execute("SELECT prices_usd, prices_usd_foil FROM cards WHERE scryfall_id = ?", (choice["scryfall_id"],)).fetchone()
            if r:
                price = r[1] if choice.get("finish") == "foil" else r[0]
        return {"market": price, "contents": None, "partial": False}
    c = market.product_cost(choice["kind"], choice["set_code"], choice["name"], choice.get("finish"))
    return {"market": c["market"], "contents": c["contents"], "partial": bool(c["unpriced"])}


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


def watched_identities(urls: list[str]) -> dict[str, dict]:
    """Watched (earmarked) links → the product you watch them as (a confirmation)."""
    if not urls:
        return {}
    with db.connect() as conn:
        rows = conn.execute(
            f"SELECT l.store_url, p.set_code, p.product_name, p.subtype, p.kind, p.scryfall_id, p.finish FROM earmark_links l "
            f"JOIN earmarked_products p USING (product_id) WHERE l.store_url IN ({','.join('?' * len(urls))})", urls).fetchall()
    return {r[0]: _earmark_choice(r[1], r[2], r[3], kind=r[4], scryfall_id=r[5], finish=r[6]) for r in rows}


def _earmark_choice(set_code: str, name: str, subtype: str | None, *, kind: str = "sealed",
                    scryfall_id: str | None = None, finish: str | None = None) -> dict:
    if kind == "single":
        return {"kind": "single", "set_code": set_code, "name": name, "scryfall_id": scryfall_id,
                "finish": finish or "nonfoil", "price": None}
    if set_code == "sld":
        return {"kind": "sld", "set_code": "sld", "name": sld.strip_foil_edition(name.replace(" (Foil Edition)", "")),
                "finish": subtype or "nonfoil"}
    return {"kind": "sealed", "set_code": set_code, "name": name}


def read_and_compare(urls: list[str], *, progress=None, fresh: bool = False) -> list[dict]:
    """Read every product page's price, then what it is and what it's worth.
    Prices of watched links are added to their history."""
    rows = read_prices(urls, progress=progress, fresh=fresh)
    earmarks.record_reads(rows)
    watched = watched_identities(urls)
    confirmed = {**watched, **confirmed_matches(urls)}
    cache: dict = {}
    out = []
    for i, r in enumerate(rows, 1):
        if progress:
            progress(i, len(rows), f"valuing {r.get('title') or r['url']}")
        out.append({**compare(r, confirmed=confirmed.get(r["url"]), cache=cache), "watching": r["url"] in watched})
    return out



# ---------- watching (earmarks + price history) ----------

class NotWatchable(ValueError):
    """Only sealed products, Secret Lair drops and single printings can be watched."""


def watch(url: str, choice: dict, *, price: float | None, currency: str | None = "USD") -> dict:
    """Earmark the product a listing sells at that store (validated through
    :func:`earmarks.resolve_identity`); the asking price starts its history."""
    kind = choice.get("kind")
    if kind == "single":
        return _watch_single(url, choice, price=price, currency=currency)
    if kind not in ("sealed", "sld"):
        raise NotWatchable("Only sealed products, Secret Lair drops and single cards can be watched.")
    name = choice["name"]
    if kind == "sld" and choice.get("finish") == "foil":
        name += " Foil Edition"
    ident = earmarks.resolve_identity(choice["set_code"], name)
    return earmarks.earmark_add(
        ident["set_code"], ident["name"], url, product_uuid=ident.get("uuid"), category=ident.get("category"),
        subtype=ident.get("subtype"), release_date=ident.get("release_date"), card_count=ident.get("card_count"),
        asking_price=price, currency=currency or "USD")


def _watch_single(url: str, choice: dict, *, price: float | None, currency: str | None) -> dict:
    """Earmark one printing (V31 single earmark), validated by ``earmarks.resolve_single``."""
    with db.connect() as conn:
        row = conn.execute("SELECT set_code, collector_number FROM cards WHERE scryfall_id = ?",
                           (choice.get("scryfall_id"),)).fetchone()
    if row is None:
        raise NotWatchable("Pick the exact printing first, then watch it.")
    ident = earmarks.resolve_identity(row[0], None, collector_number=row[1], finish=choice.get("finish") or "nonfoil")
    return earmarks.earmark_add(
        ident["set_code"], ident["name"], url, category=ident.get("category"), subtype=ident.get("subtype"),
        release_date=ident.get("release_date"), asking_price=price, currency=currency or "USD", kind="single",
        scryfall_id=ident["scryfall_id"], collector_number=ident["collector_number"], finish=ident["finish"])


def unwatch(url: str) -> dict:
    return earmarks.earmark_remove_link(url)


def _store_name(url: str, saved: str | None) -> str | None:
    """The catalogue's store name for a link (earmarks saved before the catalogue keep a host)."""
    if is_market_link(url):
        return TCGPLAYER_MARKET
    parts = urlsplit(url)
    v = vendors.classify(parts.netloc, parts.path).vendor
    return v.name if v else saved


def watchlist(*, progress=None, values: bool = True) -> list[dict]:
    """Every watched product: each store's latest price + stock + when read, the
    first price seen there, the best current in-stock price, and — with
    ``values`` — market + cards inside and the face-price gap. Best deals first.
    ``values=False`` is instant (no valuation): the web app fills values per
    product from ``market.product_cost``."""
    products = earmarks.earmark_list()
    history = earmarks.price_history([l.link_id for p in products for l in p.links])
    cache: dict = {}
    out = []
    for i, p in enumerate(products, 1):
        if progress:
            progress(i, len(products), p.product_name)
        choice = _earmark_choice(p.set_code, p.product_name, p.subtype, kind=p.kind,
                                 scryfall_id=p.scryfall_id, finish=p.finish)
        try:
            value = _value(choice, cache) if values or choice["kind"] == "single" else {}
        except Exception as e:  # noqa: BLE001 — still show the prices
            value = {"market": None, "contents": None, "partial": False, "error": str(e)}
        stores = []
        for l in p.links:
            h = history.get(l.link_id) or []
            last = h[-1] if h else {"price": l.asking_price, "available": None, "read_at": l.captured_at, "source": "snapshot"}
            first = h[0] if h else last
            stores.append({
                "url": l.store_url, "store": _store_name(l.store_url, l.store_name), "price": last["price"], "available": last["available"],
                "read_at": last["read_at"], "read": last["source"] == "read",
                "first_price": first["price"], "first_at": first["read_at"],
                "change": None if last["price"] is None or first["price"] is None else round(last["price"] - first["price"], 2),
                "history": [{"price": x["price"], "at": x["read_at"]} for x in h],
            })
        live = [s for s in stores if s["price"] is not None and s["available"] is not False]
        best = min(live or [s for s in stores if s["price"] is not None], key=lambda s: s["price"], default=None)
        market = value.get("market")
        delta = None if best is None or market is None else round(best["price"] - market, 2)
        out.append({
            "set_code": choice["set_code"], "name": choice["name"], "kind": choice["kind"], "finish": choice.get("finish"),
            "scryfall_id": choice.get("scryfall_id"), "category": p.category, "subtype": p.subtype,
            "release_date": p.release_date, "market": market, "contents": value.get("contents"),
            "partial": value.get("partial", False), "best_price": best["price"] if best else None,
            "best_store": best["store"] if best else None, "best_url": best["url"] if best else None,
            "delta": delta, "pct": None if delta is None or not market else round(delta / market * 100, 1),
            "stores": sorted(stores, key=lambda s: (s["price"] is None, s["price"] or 0)),
            "error": value.get("error"),
        })
    return sorted(out, key=lambda r: (r["pct"] is None, r["pct"] if r["pct"] is not None else 0))


def watched_urls() -> list[str]:
    return [l.store_url for p in earmarks.earmark_list() for l in p.links]
