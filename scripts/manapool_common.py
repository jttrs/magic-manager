"""Shared Mana Pool cart plumbing — the DRY core for the cart tools.

Houses the three things every cart tool needs, so `manapool_price_check.py`
(overpay check) and `manapool_cart_check.py` (owned / missing / overpay audit)
share one implementation instead of each re-deriving it:

  1. `load_cart(file, method)`      — obtain normalized cart line dicts.
  2. `map_cart(cart) -> [CartLine]` — ONE mtgjson-uuid → ManaPool product →
        scryfall_id resolution pass (24h-cached). The scryfall_id it yields is
        the join key for BOTH inventory-ownership and Scryfall-market lookups,
        so this pass is load-bearing for all downstream checks.
  3. `overpay_rows(mapped) -> {...}` — the "priced over true market" comparison
        buckets (rows / no_market / unmapped), ready for a caller to render.

Cart line dict shape (from scripts/manapool_cart.py): {inventory_id, price_cents,
seller_id, quantity, card_id (mtgjson uuid), condition_id, finish_id,
unique_product_id}. Headless carries no name/set — those come from the product row.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))  # so we can import sibling manapool_cart

from magic_manager import scryfall  # noqa: E402

MANAPOOL_SH = ROOT / ".claude" / "skills" / "manapool-search" / "manapool.sh"

# ManaPool finish_id -> is_foil. FO=foil, NF/FN=nonfoil, ET=etched (foil-like).
FINISH_FOIL = {"FO": True, "NF": False, "FN": False, "ET": True}


# ---------- cart loading ----------

def _read_json_cart(src: str | None) -> list[dict]:
    """Read a normalized cart JSON from a file path, or stdin when src is
    None/'-'. Accepts either a raw array or a {"items": [...]} envelope."""
    if src and src != "-":
        text = Path(src).read_text()
    else:
        text = sys.stdin.read()
    data = json.loads(text)
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise SystemExit("input is not a cart JSON array (or {items:[...]})")
    return items


def load_cart(file: str | None, method: str | None = None) -> list[dict]:
    """Obtain normalized cart line dicts.

    - ``file`` given (path or '-') → read that JSON (a saved/piped cart or a
      bookmarklet paste). Takes precedence over ``method``.
    - ``method == "bookmarklet"`` → read stdin. (This is how
      ``manapool_price_check.py`` invokes it, preserving its
      ``manapool_cart.py | manapool_price_check.py`` pipe contract.)
    - otherwise (``method`` None or "headless") → live headless fetch via
      ``manapool_cart.fetch_headless``; if that fails and headless wasn't
      forced, fall back to reading stdin.
    """
    if file is not None:
        return _read_json_cart(file)
    if method == "bookmarklet":
        return _read_json_cart("-")

    import manapool_cart as mc  # sibling script; scripts/ is on sys.path
    env = mc._load_env()
    items = mc.fetch_headless(env)
    if items is not None:
        return items
    if method == "headless":
        raise SystemExit("headless cart fetch failed (and no fallback requested).")
    return _read_json_cart("-")


# ---------- cart -> card mapping ----------

@dataclass
class CartLine:
    # raw cart fields
    card_id: str | None            # mtgjson uuid
    price_cents: int | None
    finish_id: str | None
    condition_id: str | None
    quantity: int
    # resolved via _mp_product (None when the uuid didn't map)
    scryfall_id: str | None
    name: str | None
    set_code: str | None           # upper-cased
    number: str | None
    foil: bool
    prod: dict | None              # raw ManaPool product row (for _variant_low)


def _mp_product(uuid: str) -> dict | None:
    """One Mana Pool product row for an mtgjson uuid (scryfall_id + variants).
    Per-uuid because the response doesn't echo which uuid produced each row;
    the wrapper's 24h cache makes repeat single lookups cheap."""
    import urllib.parse
    qs = "mtgjson_uuids=" + urllib.parse.quote(uuid)
    res = subprocess.run(
        [str(MANAPOOL_SH), "raw", "GET", "/products/singles", qs],
        capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        return None
    data = json.loads(res.stdout).get("data", [])
    return data[0] if data else None


def map_cart(cart: list[dict]) -> list[CartLine]:
    """ONE mapping pass: resolve each cart line's mtgjson uuid to a ManaPool
    product (hence scryfall_id) exactly once per unique uuid (24h-cached).
    Unmapped lines are carried through with scryfall_id/prod=None so callers
    can report skips. Deterministic: preserves cart order; one lookup per uuid."""
    uuids = [c["card_id"] for c in cart if c.get("card_id")]
    prod_by_uuid: dict[str, dict] = {}
    for u in dict.fromkeys(uuids):  # dedup, preserve order
        p = _mp_product(u)
        if p:
            prod_by_uuid[u] = p

    out: list[CartLine] = []
    for c in cart:
        prod = prod_by_uuid.get(c.get("card_id"))
        foil = FINISH_FOIL.get(c.get("finish_id"), False)
        out.append(CartLine(
            card_id=c.get("card_id"),
            price_cents=c.get("price_cents"),
            finish_id=c.get("finish_id"),
            condition_id=c.get("condition_id"),
            quantity=c.get("quantity") or 1,
            scryfall_id=(prod or {}).get("scryfall_id"),
            name=(prod or {}).get("name"),
            set_code=((prod or {}).get("set_code") or "").upper() or None,
            number=(str((prod or {}).get("number")) if prod and prod.get("number") is not None else None),
            foil=foil,
            prod=prod,
        ))
    return out


# ---------- pricing ----------

def _variant_low(prod: dict, foil: bool, condition: str) -> int | None:
    """low_price (cents) for the finish+condition variant; falls back to the
    finish-matched cheapest across conditions, then the top-level nm field."""
    want_fin = {"FO"} if foil else {"NF", "FN"}
    cands = [v for v in prod.get("variants", [])
             if v.get("finish_id") in want_fin and v.get("low_price")]
    if not cands:
        # top-level fallback
        return prod.get("price_cents_nm_foil") if foil else prod.get("price_cents_nm")
    # prefer exact condition, else cheapest of the finish
    exact = [v for v in cands if v.get("condition_id") == condition]
    pool = exact or cands
    return min(v["low_price"] for v in pool)


def _usd(cents) -> float | None:
    return round(cents / 100.0, 2) if isinstance(cents, (int, float)) else None


def _fmt(v: float | None) -> str:
    return f"${v:.2f}" if v is not None else "—"


def overpay_rows(mapped: list[CartLine]) -> dict:
    """The "priced over true market" comparison over already-mapped lines.

    Fetches Scryfall market once via ``scryfall.collection`` for all mapped
    scryfall_ids, then per line computes your / MP-cheapest / market / over / pct.
    Returns the three buckets the renderers consume:

        {"rows": [...],        # judged lines, sorted by (-pct, name, set, num)
         "no_market": [...],   # lines with no Scryfall market price (unjudgeable)
         "unmapped": int}      # cart lines that didn't map to a product

    Threshold/flagging is a rendering concern (the caller applies
    ``--over-market-pct``), so this function doesn't take it.
    """
    scryfall_ids = sorted({m.scryfall_id for m in mapped if m.scryfall_id})
    scry: dict[str, dict] = {}
    if scryfall_ids:
        found, _ = scryfall.collection([{"id": s} for s in scryfall_ids])
        for c in found:
            scry[c["id"]] = c.get("prices") or {}

    rows: list[dict] = []
    no_market: list[dict] = []
    unmapped = 0
    for m in mapped:
        if not m.prod:
            unmapped += 1
            continue
        cond = m.condition_id or "NM"
        your = _usd(m.price_cents)
        mp_cheap = _usd(_variant_low(m.prod, m.foil, cond))
        sp = scry.get(m.scryfall_id, {})
        val = sp.get("usd_foil") if m.foil else sp.get("usd")
        market = float(val) if val not in (None, "") else None
        rec = {
            "name": m.name or "?",
            "set": (m.set_code or ""),
            "num": m.number or "",
            "fin": "foil" if m.foil else "nonfoil",
            "your": your, "mp_cheap": mp_cheap, "market": market,
        }
        if market is None or your is None:
            no_market.append(rec)
            continue
        over = your - market
        rec["over"] = over
        rec["pct"] = (over / market * 100) if market else 0.0
        rows.append(rec)

    rows.sort(key=lambda r: (-r["pct"], r["name"], r["set"], r["num"]))
    return {"rows": rows, "no_market": no_market, "unmapped": unmapped}
