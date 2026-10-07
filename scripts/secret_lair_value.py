"""Deterministic markdown table of the most recent N Secret Lair drops.

Thin driver over :mod:`magic_manager.sld_market` (the same engine the web
Market → Secret Lair view uses). A "drop" is the MTGJSON DeckList notion of one
Secret Lair Drop, merged across its base printing and any ``... Foil Edition``
sibling; drops sort newest-first by release date (name ascending tie-break).

Each row is valued through ``market.product_cost(kind='sld')`` (DRY with the
web app and Deals):
  - Sealed mkt = the drop's sealed product (that edition) on the market
    (TCGplayer via the provider chain).
  - Exact cards = the drop's cards PLUS its bonus card (or bonus-pack EV) at
    their exact printings.
  - Cheapest cards = each of those cards at its cheapest printing (local prices).
  - Gap = sealed − exact cards (negative ⇒ the sealed drop costs less than its
    cards).

Prices are local-first (CLAUDE.md § Price freshness): a missing ``sld`` sync is
filled; stale prices are used as-is. ``--refresh`` is accepted for CLI surface
consistency and has no additional effect.

Usage:
    uv run python scripts/secret_lair_value.py            # 10 newest, regular editions
    uv run python scripts/secret_lair_value.py 20 --foil  # 20 newest, foil editions

Exit codes: 0 ran to completion; 2 bad invocation or MTGJSON lookup failure.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import mtgjson, sld, sld_market, util  # noqa: E402


def _gap_cell(g: dict | None) -> str:
    if g is None:
        return "—"
    sign = "−" if g["usd"] < 0 else "+"
    return f"{sign}{util.fmt_usd(abs(g['usd']))} ({sign}{abs(g['pct']):.0f}%)"


def main() -> int:
    ap = argparse.ArgumentParser(description="Value table for the most recent N Secret Lair drops.")
    ap.add_argument("limit", nargs="?", type=int, default=10, help="Number of most recent drops (default 10).")
    ap.add_argument("--limit", type=int, default=None, dest="limit_opt", help="Same as the positional; wins if both are given.")
    ap.add_argument("--foil", action="store_true", help="Value the Foil Edition of each drop (drops without one are skipped).")
    ap.add_argument("--refresh", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    n = args.limit_opt if args.limit_opt is not None else args.limit
    if n <= 0:
        print("error: limit must be a positive integer", file=sys.stderr)
        return 2
    finish = "foil" if args.foil else "nonfoil"
    try:
        rows = sld_market.survey(n, finish)
    except mtgjson.MtgJsonError as e:
        print(f"error: mtgjson lookup failed: {e}", file=sys.stderr)
        return 2

    failed = sum(1 for r in rows if r["error"])
    print(f"Valued {len(rows) - failed} of {len(rows)} drops ({finish}){f'; {failed} failed' if failed else ''}.", file=sys.stderr)
    edition = "Foil Edition" if args.foil else "regular edition"
    print(f"## Secret Lair Drop value — {n} newest, {edition}")
    print()
    print("*Sealed mkt = the drop's sealed product on the market. Exact cards = the drop's "
          "cards plus its bonus card at their exact printings. Cheapest cards = each card at its "
          "cheapest printing anywhere. Gap = sealed − exact cards (negative ⇒ sealed is cheaper).*")
    print()
    print("| Drop | Release | Cards | Sealed mkt | Exact cards | Cheapest cards | Gap |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        safe = r["name"].replace("|", "\\|")
        c = r["cost"]
        if c is None:
            print(f"| {safe} | {r['release_date']} | — | — | — | — | error: {r['error']} |")
            continue
        url = sld.search_url([ln["collector_number"] for ln in c["lines"] if ln["set_code"].lower() == "sld" and ln["collector_number"] != "?"])
        print(f"| [{safe}]({url}) | {r['release_date']} | {c['total_cards']} | {util.fmt_usd(c['market'])} | "
              f"{util.fmt_usd(c['exact'])} | {util.fmt_usd(c['floor'])} | "
              f"{_gap_cell(sld_market.gap(c))} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
