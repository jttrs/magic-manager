"""Flag Mana Pool cart lines priced well over true market — the swindle check.

Purpose: before a large Mana Pool order, catch any card you're about to pay
X%+ over true market for — usually because ManaPool is thin on that specific
card (limited availability), sometimes a byproduct of the optimizer. This is
NOT an optimizer-efficiency verdict; it's a per-card "is this price sane vs the
broader market" check.

INPUT: normalized cart JSON from scripts/manapool_cart.py, via stdin or --file.
Each line needs {card_id (mtgjson uuid), price_cents, finish_id, condition_id}.

PIPELINE (deterministic):
  1. Map each cart line's mtgjson `card_id` -> a Mana Pool product row via the
     sanctioned /products/singles (mtgjson_uuids). That row carries the
     scryfall_id (encodes set+collector-number+treatment) AND the per-variant
     `low_price` (the SAME price basis as the cart's adjusted price — verified
     to match to the cent). Match the variant on finish (NF/FO) + condition (NM).
  2. Refresh true market via scryfall.collection(scryfall_ids) — Scryfall's
     prices_usd / prices_usd_foil are TCGplayer-derived. This is the market
     benchmark. (ManaPool's own price_market corroborates it but we lead with
     Scryfall.)
  3. Per line, finish-matched:
       your price   = cart price_cents
       MP cheapest  = variants[].low_price for finish+NM (corroboration:
                      "even MP's own floor is this high")
       market       = Scryfall prices_usd[_foil]
     Flag when your price >= market * (1 + threshold%).  Default 50%.
  4. Render markdown, sorted by % over market (worst first). Cards with no
     market price are listed separately (can't judge).

Matching is by scryfall_id + finish ONLY — never by name — so a borderless /
foil / etched variant is always compared to its own market number.

Usage:
    uv run python scripts/manapool_cart.py | uv run python scripts/manapool_price_check.py
    uv run python scripts/manapool_price_check.py --file cart.json
    ... --over-market-pct 50     # flag threshold (percent over Scryfall market)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import scryfall  # noqa: E402

MANAPOOL_SH = ROOT / ".claude" / "skills" / "manapool-search" / "manapool.sh"

# ManaPool finish_id -> (scryfall finish, is_foil)
FINISH_FOIL = {"FO": True, "NF": False, "FN": False, "ET": True}


def _load_cart(src: str | None) -> list[dict]:
    if src and src != "-":
        text = Path(src).read_text()
    else:
        text = sys.stdin.read()
    data = json.loads(text)
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise SystemExit("input is not a cart JSON array (or {items:[...]})")
    return items


def _mp_product(uuid: str) -> dict | None:
    """One Mana Pool product row for an mtgjson uuid (scryfall_id + variants).
    Per-uuid because the response doesn't echo which uuid produced each row;
    the wrapper's 24h cache makes repeat single lookups cheap."""
    qs = "mtgjson_uuids=" + urllib.parse.quote(uuid)
    res = subprocess.run(
        [str(MANAPOOL_SH), "raw", "GET", "/products/singles", qs],
        capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        return None
    data = json.loads(res.stdout).get("data", [])
    return data[0] if data else None


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


def main() -> int:
    ap = argparse.ArgumentParser(description="Flag Mana Pool cart lines over true market.")
    ap.add_argument("--file", default=None, help="Cart JSON path, or '-'/omit for stdin.")
    ap.add_argument("--over-market-pct", type=float, default=50.0,
                    help="Flag lines priced this %% or more over Scryfall/TCG market. Default 50.")
    args = ap.parse_args()

    cart = _load_cart(args.file)
    uuids = [c["card_id"] for c in cart if c.get("card_id")]
    if not uuids:
        raise SystemExit("no card_id (mtgjson uuid) on any cart line; can't map.")

    print(f"mapping {len(set(uuids))} cart cards via Mana Pool products…", file=sys.stderr)
    prod_by_uuid: dict[str, dict] = {}
    for u in dict.fromkeys(uuids):  # dedup, preserve order
        p = _mp_product(u)
        if p:
            prod_by_uuid[u] = p

    scryfall_ids = sorted({p["scryfall_id"] for p in prod_by_uuid.values() if p.get("scryfall_id")})
    scry: dict[str, dict] = {}
    if scryfall_ids:
        found, _ = scryfall.collection([{"id": s} for s in scryfall_ids])
        for c in found:
            scry[c["id"]] = c.get("prices") or {}

    rows = []
    no_market = []
    unmapped = 0
    for line in cart:
        prod = prod_by_uuid.get(line.get("card_id"))
        if not prod:
            unmapped += 1
            continue
        foil = FINISH_FOIL.get(line.get("finish_id"), False)
        cond = line.get("condition_id") or "NM"
        your = _usd(line.get("price_cents"))
        mp_cheap = _usd(_variant_low(prod, foil, cond))
        sp = scry.get(prod.get("scryfall_id"), {})
        m = sp.get("usd_foil") if foil else sp.get("usd")
        market = float(m) if m not in (None, "") else None
        # treatment label (from scryfall frame/promo would need extra fetch;
        # use MP's own finish + set/num which already encode the printing)
        rec = {
            "name": prod.get("name") or "?",
            "set": (prod.get("set_code") or "").upper(),
            "num": str(prod.get("number") or ""),
            "fin": "foil" if foil else "nonfoil",
            "your": your, "mp_cheap": mp_cheap, "market": market,
        }
        if market is None or your is None:
            no_market.append(rec)
            continue
        over = your - market
        pct = (over / market * 100) if market else 0.0
        rec["over"] = over
        rec["pct"] = pct
        rows.append(rec)

    rows.sort(key=lambda r: (-r["pct"], r["name"], r["set"], r["num"]))

    print("| Card | Fin | Your $ | MP cheapest | Scry/TCG market | Over market |")
    print("|---|:--:|--:|--:|--:|--:|")
    n_flag = 0
    flagged_total_over = 0.0
    for r in rows:
        link = f"https://scryfall.com/card/{r['set'].lower()}/{r['num']}" if r["set"] and r["num"] else ""
        card = f"[{r['name']} ({r['set']}) {r['num']}]({link})" if link else r["name"]
        flag = " ⚠️" if r["pct"] >= args.over_market_pct else ""
        if flag:
            n_flag += 1
            flagged_total_over += r["over"]
        print(f"| {card} | {r['fin']} | {_fmt(r['your'])} | {_fmt(r['mp_cheap'])} | "
              f"{_fmt(r['market'])} | +{_fmt(r['over'])} ({r['pct']:+.0f}%){flag} |")

    print()
    print(f"**{len(rows)} cards priced · {n_flag} flagged ≥{args.over_market_pct:.0f}% over market "
          f"(total ${flagged_total_over:.2f} over market on flagged lines).**")
    if no_market:
        print(f"\n_{len(no_market)} cards had no Scryfall market price and were not judged: "
              f"{', '.join(x['name'] for x in no_market[:8])}{'…' if len(no_market) > 8 else ''}_")
    if unmapped:
        print(f"\n_{unmapped} cart lines couldn't be mapped to a product (skipped)._", file=sys.stderr)
    print(f"\n_Flag = cart price ≥ {args.over_market_pct:.0f}% over Scryfall/TCG market. "
          f"MP cheapest shown for corroboration (if it ~= your price, even ManaPool's floor is high — "
          f"a scarcity/availability premium, not the optimizer picking a pricier seller)._", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
