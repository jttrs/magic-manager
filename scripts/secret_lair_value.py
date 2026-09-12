"""Deterministic markdown table of the most recent N Secret Lair drops.

A "drop" is the MTGJSON DeckList notion of one Secret Lair Drop product,
merged across its base printing and any ``... Foil Edition`` sibling (MTGJSON
lists foil-edition-only Secret Lairs as separate deck entries; we treat them
as the same logical drop). Drops are sorted newest-first by release date
(name ascending as the tie-break) and rendered with live Scryfall singles
prices, nonfoil and foil in separate columns plus a combined "buy everything"
figure.

Every price is fetched live via Scryfall's ``/cards/collection`` batch
endpoint through the project's rate-limited wrapper. Prices are cached
inside the wrapper (24h TTL) so re-runs the same day are instant. Deck
metadata comes from the MTGJSON wrapper (also cached).

Input:
  - positional ``limit`` (default 10) or ``--limit N`` — how many of the most
    recent drops to render. ``--limit`` wins if both are given.

Output:
  - stdout: a markdown title + legend, then the UNIFIED 4-column value table
    (shared with sealed_value / sealed_value_batch): Drop (hyperlinked to a
    Scryfall search for the drop's exact collector numbers), Release, Cards,
    Listing, Sealed mkt, Exact singles, Floor singles. Listing is N/A for this
    recent-drops survey (no per-drop asking price), so cols show bare values with
    no delta. Sealed mkt = the drop's sealed product on the wider secondary
    market (via the market providers). Exact singles = the drop's own Secret Lair
    printings (nonfoil). Floor singles = the CHEAPEST printing of each card
    anywhere (matched by oracle id) — the cheapest way to assemble the cards for
    a deck regardless of the Secret Lair treatment.
  - stderr: a one-line summary of how many drops were rendered out of the
    total known SLD drops, how many distinct printings were fetched, and how
    many distinct cards were priced for the floor lookup.

Exit codes:
  0 — ran to completion.
  2 — bad invocation, or MTGJSON/Scryfall lookup failure.

Determinism notes:
  - Drops sort by release date descending, name ascending tie-break.
  - Drop identity = base + Foil-Edition merged by stripping the
    " Foil Edition" suffix from the entry name; a base entry's name/date win
    as canonical regardless of encounter order.
  - Scryfall IDs are the de-duplicated union across a drop's sibling decks,
    preserving first-seen order.
  - Floor prices are the min over every printing (``oracleid:<id>
    unique=prints``) of that card's ``usd`` / ``usd_foil``; the per-oracle
    lookup is de-duplicated across all drops and 24h-cached at the wrapper.
  - Search URLs are built from ``set:sld (cn:... or ...)`` with collector
    numbers sorted via ``util.cn_sort_key`` and any trailing "★" stripped.

Usage:
    uv run python scripts/secret_lair_value.py
    uv run python scripts/secret_lair_value.py 5
    uv run python scripts/secret_lair_value.py --limit 20
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import mtgjson, scryfall, sld, util, valuation  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic value table for the most recent N Secret Lair drops.",
    )
    ap.add_argument(
        "limit", nargs="?", type=int, default=10,
        help="Number of most recent drops to render (default 10).",
    )
    ap.add_argument(
        "--limit", type=int, default=None, dest="limit_opt",
        help="Same as the positional argument; wins if both are given.",
    )
    ap.add_argument(
        "--market", choices=["null", "tcgcsv", "tcgapi", "manapool", "chain", "compare"],
        default="chain", help="Sealed-market source for the Sealed mkt column (default: chain).",
    )
    args = ap.parse_args()

    n = args.limit_opt if args.limit_opt is not None else args.limit
    if n <= 0:
        print("error: limit must be a positive integer", file=sys.stderr)
        return 2

    try:
        chosen, total = sld.recent_drops(n)
        # Resolve every drop's card ids, then fetch all printings in ONE batch so
        # the whole table shares one Scryfall call + one per-oracle floor cache.
        all_ids: list[str] = []
        seen_ids: set[str] = set()
        for g in chosen:
            g["ids"] = sld.collect_drop_ids(g["file_names"])
            for sid in g["ids"]:
                if sid not in seen_ids:
                    seen_ids.add(sid)
                    all_ids.append(sid)
        found, not_found = scryfall.collection([{"id": i} for i in all_ids])
    except mtgjson.MtgJsonError as e:
        print(f"error: mtgjson lookup failed: {e}", file=sys.stderr)
        return 2
    except scryfall.ScryfallError as e:
        print(f"error: scryfall lookup failed: {e}", file=sys.stderr)
        return 2

    card_by_id = {c["id"]: c for c in found}
    floors_cache: dict[str, tuple[float | None, float | None]] = {}

    # Value each drop through the unified 4-column producer, sharing the batch
    # fetch + floor cache. Keep the DropValue too (for the Cards + search-URL cols).
    try:
        rows = []
        for g in chosen:
            dv = sld.value_drop(g, floors=True, _card_by_id=card_by_id,
                                _floors_cache=floors_cache)
            pv = valuation.value_sld_drop(g, listing=None, market=args.market,
                                          _card_by_id=card_by_id, _floors_cache=floors_cache)
            rows.append((g, dv, pv))
    except scryfall.ScryfallError as e:
        print(f"error: scryfall lookup failed: {e}", file=sys.stderr)
        return 2

    print(
        f"Rendered {len(chosen)} drops (of {total} SLD drops). "
        f"Fetched {len(all_ids)} distinct printings; {len(not_found)} unresolved. "
        f"Floor-priced {len(floors_cache)} distinct cards.",
        file=sys.stderr,
    )

    print(f"## Secret Lair Drop value — top {n} by release (newest first)")
    print()
    print(
        "*Listing = N/A here (this is a recent-drops survey, no per-drop asking). "
        "Sealed mkt = the drop's sealed product on the wider secondary market. "
        "Exact singles = the drop's own Secret Lair printings (nonfoil). Floor "
        "singles = cheapest printing of each card anywhere (nonfoil) — the "
        "cheapest way to get the cards into a deck regardless of treatment.*"
    )
    print()
    print("| Drop | Release | Cards | Listing | Sealed mkt | Exact singles | Floor singles |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for g, dv, pv in rows:
        safe = pv.label.replace("|", "\\|")
        # Listing is None for the survey → fmt_delta_cell renders bare values.
        print(
            f"| [{safe}]({dv.search_url}) | {dv.release_date} | {dv.card_count} | "
            f"{util.fmt_usd(pv.listing)} | "
            f"{util.fmt_delta_cell(pv.sealed_market, pv.listing)} | "
            f"{util.fmt_delta_cell(pv.exact_singles, pv.listing)} | "
            f"{util.fmt_delta_cell(pv.floor_singles, pv.listing)} |"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
