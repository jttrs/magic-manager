"""Shared Mana Pool cart plumbing — the DRY core for the cart tools.

Cart I/O for the CLI tools (the headless / stdin cart fetch). Mapping, pricing
and the checks live in :mod:`magic_manager.cart`; this module re-exports them so
 `manapool_price_check.py`
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


MANAPOOL_SH = ROOT / ".claude" / "skills" / "manapool-search" / "manapool.sh"


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


# ---------- mapping + pricing: the engine (magic_manager.cart) ----------

from magic_manager.cart import (  # noqa: E402,F401 — re-exported for the cart scripts
    FINISH_FOIL, CartLine, _usd, _variant_low, map_cart, overpay_rows,
)


def _fmt(v: float | None) -> str:
    return f"${v:.2f}" if v is not None else "—"
