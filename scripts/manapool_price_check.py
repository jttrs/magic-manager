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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Shared cart plumbing — cart load, mtgjson-uuid → product mapping, and the
# overpay comparison all live in manapool_common (DRY with manapool_cart_check).
from manapool_common import load_cart, map_cart, overpay_rows, _fmt  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Flag Mana Pool cart lines over true market.")
    ap.add_argument("--file", default=None, help="Cart JSON path, or '-'/omit for stdin.")
    ap.add_argument("--over-market-pct", type=float, default=50.0,
                    help="Flag lines priced this %% or more over Scryfall/TCG market. Default 50.")
    args = ap.parse_args()

    cart = load_cart(args.file, method="bookmarklet")
    uuids = [c["card_id"] for c in cart if c.get("card_id")]
    if not uuids:
        raise SystemExit("no card_id (mtgjson uuid) on any cart line; can't map.")

    print(f"mapping {len(set(uuids))} cart cards via Mana Pool products…", file=sys.stderr)
    mapped = map_cart(cart)
    buckets = overpay_rows(mapped)
    rows = buckets["rows"]
    no_market = buckets["no_market"]
    unmapped = buckets["unmapped"]

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
