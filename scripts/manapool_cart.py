"""Fetch the current Mana Pool cart as normalized JSON.

Mana Pool's *sanctioned* public API (manapool.com/api/v1) exposes no cart
endpoint — the website cart lives in a Supabase/PostgREST backend
(sb-api.manapool.com) behind a per-user session JWT. This script gets the cart
by one of two paths, trying the automatic one first:

  headless — password-grant against Supabase auth → session JWT (in memory
             only, never written) → read the RLS-scoped `cart_items` table →
             enrich inventoryIds via the same `inventory?id=in.(...)` select the
             site uses. Requires MANAPOOL_PASSWORD in .env. Fully hands-off.
  bookmarklet — fallback that always works: click the cart-bookmarklet on the
             cart page; it copies normalized cart JSON to your clipboard; paste
             it here via --file - (stdin) or --file PATH.

Output (stdout): a JSON array of line items, each:
  {"inventory_id","price_cents","seller_id","card_id","condition_id",
   "finish_id","quantity", and optionally "name","set","number"}
The `name`/`set` fields are present only from the bookmarklet path (it scrapes
the rendered rows); headless carries ManaPool ids and relies on downstream
mtgjson-id mapping. Which path produced the output is reported on stderr.

SECURITY: the session JWT is short-lived and held in memory only — never
written to disk or logged. MANAPOOL_PASSWORD is read from the gitignored .env.

Usage:
    uv run python scripts/manapool_cart.py                    # headless, else stdin if piped
    uv run python scripts/manapool_cart.py --file cart.json   # bookmarklet JSON from a file
    pbpaste | uv run python scripts/manapool_cart.py --file - # bookmarklet via clipboard
    uv run python scripts/manapool_cart.py --method headless  # force one path
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---- Supabase backend constants (observed from the live site; undocumented) ----
SB_BASE = "https://sb-api.manapool.com"
SB_APIKEY = "sb_publishable_mwzveHhY-M-t19HCwYC1lw_pRUJyYZP"
# The inventory-enrich select the site uses (inventoryId -> price/seller/product).
INV_SELECT = (
    "inventoryId:id,priceCents:adjusted_price_cents_new,sellerId:seller_id,"
    "quantityAvailable:live_quantity,"
    "product:products!inner(id,type,"
    "single:products_mtg_single(cardId:card_id,languageId:language_id,"
    "conditionId:condition_id,finishId:finish_id,uniqueProductId:unique_product_id))"
)


def _load_env() -> dict:
    env = {}
    envfile = ROOT / ".env"
    if envfile.exists():
        for line in envfile.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    # environment overrides file
    for k in ("MANAPOOL_EMAIL", "MANAPOOL_PASSWORD", "MANAPOOL_ACCESS_TOKEN"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def _http_json(url: str, headers: dict, method: str = "GET", body: bytes | None = None):
    req = urllib.request.Request(url, headers=headers, method=method, data=body)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


# ---------- headless: password login → cart_items → enrich ----------

def fetch_headless(env: dict) -> list[dict] | None:
    email = env.get("MANAPOOL_EMAIL")
    password = env.get("MANAPOOL_PASSWORD")
    if not email or not password:
        print("headless: no MANAPOOL_PASSWORD in .env — skipping headless login", file=sys.stderr)
        return None
    try:
        # 1. password grant → JWT (in memory only)
        tok = _http_json(
            f"{SB_BASE}/auth/v1/token?grant_type=password",
            headers={"apikey": SB_APIKEY, "Content-Type": "application/json"},
            method="POST",
            body=json.dumps({"email": email, "password": password}).encode(),
        )
        jwt = tok.get("access_token")
        if not jwt:
            print(f"headless: login returned no access_token ({tok.get('error_description') or tok})", file=sys.stderr)
            return None
        auth = {"apikey": SB_APIKEY, "Authorization": f"Bearer {jwt}"}

        # 2. read the RLS-scoped cart. Column names are unknown a priori, so
        #    select * and discover the inventory-id field at runtime.
        cart = _http_json(f"{SB_BASE}/rest/v1/cart_items?select=*", headers=auth)
        if not isinstance(cart, list) or not cart:
            print("headless: cart_items empty (cart may be empty, or schema differs)", file=sys.stderr)
            return [] if isinstance(cart, list) else None

        inv_field = _guess_inventory_field(cart[0])
        if not inv_field:
            print(f"headless: could not find an inventory-id column in cart_items row keys={list(cart[0].keys())}", file=sys.stderr)
            return None
        qty_field = _guess_qty_field(cart[0])
        inv_ids = [row[inv_field] for row in cart if row.get(inv_field)]
        qty_by_inv = {row[inv_field]: (row.get(qty_field) or 1) for row in cart} if qty_field else {}

        # 3. enrich inventoryIds → price/seller/product (batch, id=in.(...))
        enriched = _enrich_inventory(inv_ids, auth)
        return _normalize(enriched, qty_by_inv)
    except urllib.error.HTTPError as e:
        print(f"headless: HTTP {e.code} {e.reason} — falling through", file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001 — any failure should fall through, not crash
        print(f"headless: {type(e).__name__}: {e} — falling through", file=sys.stderr)
        return None


def _guess_inventory_field(row: dict) -> str | None:
    for cand in ("inventory_id", "inventoryId", "listing_id", "listingId", "id"):
        if cand in row:
            return cand
    # any *_id key that looks like a uuid
    for k, v in row.items():
        if k.endswith(("_id", "Id")) and isinstance(v, str) and len(v) == 36:
            return k
    return None


def _guess_qty_field(row: dict) -> str | None:
    for cand in ("quantity", "qty", "count"):
        if cand in row:
            return cand
    return None


def _enrich_inventory(inv_ids: list[str], auth: dict) -> list[dict]:
    out: list[dict] = []
    for i in range(0, len(inv_ids), 100):
        chunk = inv_ids[i:i + 100]
        id_list = ",".join(chunk)
        qs = urllib.parse.urlencode({"select": INV_SELECT, "id": f"in.({id_list})"})
        rows = _http_json(f"{SB_BASE}/rest/v1/inventory?{qs}", headers=auth)
        if isinstance(rows, list):
            out.extend(rows)
    return out


def _normalize(enriched: list[dict], qty_by_inv: dict) -> list[dict]:
    out = []
    for r in enriched:
        inv = r.get("inventoryId")
        single = (r.get("product") or {}).get("single") or {}
        out.append({
            "inventory_id": inv,
            "price_cents": r.get("priceCents"),
            "seller_id": r.get("sellerId"),
            "quantity": qty_by_inv.get(inv, 1),
            "card_id": single.get("cardId"),
            "condition_id": single.get("conditionId"),
            "finish_id": single.get("finishId"),
            "unique_product_id": single.get("uniqueProductId"),
        })
    return out


# ---------- bookmarklet clipboard paste ----------

def fetch_bookmarklet(src: str | None) -> list[dict] | None:
    if src == "-" or src is None:
        if sys.stdin.isatty():
            print("bookmarklet: no piped input. Click the cart bookmarklet, then paste its JSON "
                  "via: pbpaste | uv run python scripts/manapool_cart.py --file -", file=sys.stderr)
            return None
        text = sys.stdin.read()
    else:
        text = Path(src).read_text()
    text = text.strip()
    if not text:
        return None
    data = json.loads(text)
    # Accept either our normalized shape or the bookmarklet's {items:[...]} shape.
    items = data.get("items") if isinstance(data, dict) else data
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch Mana Pool cart (headless, or bookmarklet paste).")
    ap.add_argument("--file", default=None,
                    help="Bookmarklet JSON: a path, or '-' for stdin.")
    ap.add_argument("--method", choices=["headless", "bookmarklet"], default=None,
                    help="Force one path instead of headless-then-bookmarklet.")
    args = ap.parse_args()
    env = _load_env()

    # If a file/stdin is provided, that's an explicit bookmarklet paste.
    order = ([args.method] if args.method
             else (["bookmarklet"] if args.file else ["headless", "bookmarklet"]))
    result = None
    used = None
    for m in order:
        if m == "headless":
            result = fetch_headless(env)
        elif m == "bookmarklet":
            result = fetch_bookmarklet(args.file)
        if result is not None:
            used = m
            break

    if result is None:
        print("cart fetch failed. Fallback: click the cart bookmarklet and "
              "`pbpaste | uv run python scripts/manapool_cart.py --file -`.", file=sys.stderr)
        return 1

    print(f"cart fetched via {used}: {len(result)} line items", file=sys.stderr)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
