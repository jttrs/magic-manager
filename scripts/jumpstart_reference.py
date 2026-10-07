"""Deterministic two-sheet XLSX reference of Jumpstart pack versions.

Thin driver over :mod:`magic_manager.jumpstart` (``set_packs``).

Answers "which version of a Jumpstart pack is this?" (Angels (1) vs Angels (2),
etc.) and "what's in each version?". Emits ``reference/jumpstart-versions.xlsx``
with two sheets:

  - **packs** — one row per Jumpstart pack variant:
    ``set, theme, color, top_card, top_card_usd, card_count, usd_total``.
    (A reference, not an ingestible checklist — no keep/deconstruct qty fields.)
  - **cards** — one row per distinct card in each pack:
    ``set, theme, color, card_name, card_value, count`` (count = copies in pack).

Both sheets sort by COLOR then NAME (theme / card) A→Z. Color order is
``C → W → U → B → R → G`` for single symbols, then every multicolor code as one
trailing block (ordered by its letter sequence) — i.e. mono-first, then multi.

Color is the deck/card convention (actual WUBRG letters, no 'M' collapse; a
colorless card/pack → 'C'), matching the checklist writers. Card value is the
card's SHIPPED finish (foil price if the pack ships it foil, else nonfoil) —
the same basis the pack ``usd_total`` uses. Pack ``usd_total`` also folds in
the decorative front/title card price (as the checklist does); the front card
itself is NOT listed on either sheet (it isn't a version signal).

Prices/colors come from the local ``cards`` table, so the script syncs each
referenced set's family first (Jumpstart contents span the parent expansion).

Usage:
    uv run python scripts/jumpstart_reference.py            # ALL jumpstart sets
    uv run python scripts/jumpstart_reference.py j25        # one set
    uv run python scripts/jumpstart_reference.py --out /tmp/jr.xlsx

Exit codes:
    0 — written
    2 — bad invocation / no Jumpstart variants found
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import exports, jumpstart, sets, util  # noqa: E402

DEFAULT_OUT = ROOT / "reference" / "jumpstart-versions.xlsx"

_color_sort_key = jumpstart.color_sort_key


def _gather(codes: list[str]) -> tuple[list[dict], list[dict]]:
    """Build (pack_rows, card_rows) across the given set codes from the engine."""
    pack_rows: list[dict] = []
    card_rows: list[dict] = []
    for code in codes:
        if not jumpstart.variants(code):
            print(f"  (no Jumpstart variants for {code.upper()}, skipping)", file=sys.stderr)
            continue
        print(f"  {code.upper()}: reading packs (fills sets with no local cards)…")
        jumpstart.ensure_ready(code)
        for p in jumpstart.set_packs(code):
            pack_rows.append({
                "set": code.upper(), "theme": p.name, "color": p.color, "top_card": p.top_card,
                "top_card_usd": p.top_card_usd, "card_count": p.card_count, "usd_total": p.usd_total,
            })
            # One row per (printing, shipped finish); count summed across boards.
            merged: dict[tuple[str, bool], dict] = {}
            for c in p.cards:
                if not c.known:
                    continue
                row = merged.setdefault((c.scryfall_id, c.foil), {
                    "set": code.upper(), "theme": p.name, "color": c.color, "card_name": c.name,
                    "card_value": c.unit_usd, "count": 0, "rarity": c.rarity or "",
                    "collector_number": c.collector_number or "",
                })
                row["count"] += c.count
            card_rows.extend(merged.values())
    return pack_rows, card_rows


def _write_xlsx(pack_rows: list[dict], card_rows: list[dict], out_path: Path) -> None:
    # packs: set code first, then color (C→W→U→B→R→G→multi), then theme A→Z.
    pack_rows.sort(key=lambda r: (r["set"], _color_sort_key(r["color"]), (r["theme"] or "").lower()))
    # cards: set, then theme A→Z, then rarity (mythic→…→special), then collector number.
    card_rows.sort(key=lambda r: (
        r["set"], (r["theme"] or "").lower(),
        sets.RARITY_ORDER.get((r["rarity"] or "").lower(), 99),
        util.cn_sort_key(r["collector_number"]),
    ))

    packs = exports.xlsx.SheetSpec(
        title="packs",
        headers=["set", "theme", "color", "top_card", "top_card_usd",
                 "card_count", "usd_total"],
        rows=[[r["set"], r["theme"], r["color"], r["top_card"],
               r["top_card_usd"], r["card_count"], r["usd_total"]]
              for r in pack_rows],
        money_cols=(5, 7),
        widths={1: 6, 2: 26, 3: 8, 4: 28, 5: 12, 6: 11, 7: 11},
    )
    cards = exports.xlsx.SheetSpec(
        title="cards",
        headers=["set", "theme", "color", "card_name", "card_value", "count",
                 "rarity", "collector_number"],
        rows=[[r["set"], r["theme"], r["color"], r["card_name"],
               r["card_value"], r["count"], r["rarity"], r["collector_number"]]
              for r in card_rows],
        money_cols=(5,), text_cols=(8,),
        widths={1: 6, 2: 26, 3: 8, 4: 34, 5: 12, 6: 7, 7: 10, 8: 16},
    )
    exports.xlsx.write_workbook(out_path, [packs, cards])


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the Jumpstart versions reference XLSX.")
    ap.add_argument("set_code", nargs="?", default=None,
                    help="Jumpstart set code (e.g. j25). Omit for ALL Jumpstart sets.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"Output path (default: {DEFAULT_OUT.relative_to(ROOT)}).")
    args = ap.parse_args()

    if args.set_code:
        codes = [args.set_code.lower()]
    else:
        print("Discovering all Jumpstart sets from MTGJSON DeckList…")
        codes = jumpstart.jumpstart_set_codes()
        if not codes:
            print("error: no Jumpstart sets found in DeckList.", file=sys.stderr)
            return 2
        print(f"  {len(codes)} set(s): {', '.join(c.upper() for c in codes)}")

    pack_rows, card_rows = _gather(codes)
    if not pack_rows:
        print(f"error: no Jumpstart variants found for {codes}.", file=sys.stderr)
        return 2

    _write_xlsx(pack_rows, card_rows, args.out)
    print(f"\nWrote {len(pack_rows)} pack row(s) + {len(card_rows)} card row(s) "
          f"across {len(codes)} set(s) to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
