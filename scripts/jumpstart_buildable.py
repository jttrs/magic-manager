"""Deterministic "buildable set" missing-cards report for a Jumpstart set.

Thin driver over :mod:`magic_manager.jumpstart` (``buildable_missing``), which
the web Collection → Jumpstart sheet shares.

Goal: hold the MINIMUM cards to have one built copy of every theme coexisting,
while still being able to assemble any *version* of a theme on demand — one
version of each theme constructed, plus the unique/extra cards from that theme's
other versions. This reports the cards still MISSING to reach that target, as
missing-set-style artifacts (ManaPool txt + TCGplayer txt + XLSX).

A "theme" is a Jumpstart variant name minus its trailing version suffix,
parenthesized or bare: ``Angels (1)`` / ``Angels (2)`` → theme ``Angels``;
``Corruption 1`` / ``Corruption 2`` (ONE-style naming) → theme ``Corruption``.

Target math (per scryfall_id):
  - within a theme: MAX count across that theme's versions (union at max
    multiplicity → any single version is buildable, reusing shared cards);
  - across themes:  SUM of each theme's target (all themes built at once, so a
    card used by K themes needs K copies).
  → target[card] = Σ_themes max_versions(count_in_version).

Owned = TOTAL inventory quantity per card (summed across finishes, INCLUDING
copies pledged to already-built packs — you can deconstruct to reuse them).
Finish is not tracked: a foil copy satisfies the need; the buy list is nonfoil.
missing[card] = max(0, target − owned). Basics are included.

Usage:
    uv run python scripts/jumpstart_buildable.py j25
    uv run python scripts/jumpstart_buildable.py j25 --format manapool
    uv run python scripts/jumpstart_buildable.py j25 --out-dir /tmp

Exit codes:
    0 — report written (even if nothing missing)
    2 — bad invocation / no Jumpstart variants for the set
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import exports, jumpstart, mtgjson, sets, util  # noqa: E402

# Engine re-exports (tests and muscle memory import them from here).
theme_of = jumpstart.theme_of
build_target = jumpstart.build_target


def _write_xlsx(rows: list, out_path: Path) -> None:
    headers = ["set", "collector_number", "name", "rarity", "finish",
               "qty", "unit_usd", "line_value"]
    cell_rows = []
    for r in rows:
        c = r.card
        unit = c.get("prices_usd")
        line = (unit * r.quantity) if unit is not None else None
        cell_rows.append([
            (c.get("set") or "").upper(), c.get("collector_number"),
            c.get("name"), c.get("rarity"), r.finish, r.quantity, unit, line,
        ])
    spec = exports.xlsx.SheetSpec(
        title="buildable-missing", headers=headers, rows=cell_rows,
        widths={1: 6, 2: 8, 3: 40, 4: 10, 5: 9, 6: 6, 7: 10, 8: 11},
        money_cols=(7, 8), text_cols=(2,),
    )
    exports.xlsx.write_workbook(out_path, [spec])


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Report cards missing to make every Jumpstart theme buildable.")
    ap.add_argument("set_code", help="Jumpstart set code (e.g. j25).")
    ap.add_argument("--format", choices=["manapool", "tcgplayer", "xlsx", "all"],
                    default="all", help="Which artifact(s) to write (default: all).")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="Override output dir for ALL artifacts (default: segments "
                         "buy-lists → output/jumpstart-buildable/buy-lists/, checklist "
                         "→ output/jumpstart-buildable/checklists/).")
    ap.add_argument("--no-filter", action="store_true",
                    help="Skip the physical-buyable gate (don't drop tokens / "
                         "digital-only / family-unobtainable / meld-back prints). "
                         "Default is to filter, matching every other buy-list.")
    args = ap.parse_args()
    code = args.set_code.lower()

    variants = mtgjson.jumpstart_variants(code)
    if not variants:
        print(f"error: no Jumpstart variants found for set {code!r}. "
              f"Check `mm mtgjson decks --set {code}`.", file=sys.stderr)
        return 2

    # Sync the family so cards/prices resolve locally.
    print(f"Syncing {code.upper()} family for prices…")
    try:
        sets.sync(sets.resolve(code).filtered_codes())
    except Exception as e:  # noqa: BLE001 — best-effort, mirrors sets.py contract
        print(f"  ! sync failed: {e} (prices/names may under-report)", file=sys.stderr)

    res = jumpstart.buildable_missing(code, filter_buyable=not args.no_filter)
    rows, target, owned = res.rows, res.target, res.owned
    n_themes, n_variants, n_filtered, skipped = res.themes, res.variants, res.filtered, res.skipped

    from datetime import UTC, datetime
    ts = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
    # Buy-lists (manapool/tcgplayer) and the checklist land in different
    # categories; --out-dir (if given) overrides both to one dir.
    buylist_dir = args.out_dir or util.output_dir("jumpstart-buildable", "buy-lists")
    checklist_dir = args.out_dir or util.output_dir("jumpstart-buildable", "checklists")
    buylist_dir.mkdir(parents=True, exist_ok=True)
    checklist_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if args.format in ("manapool", "all"):
        p = buylist_dir / f"buildable-{code}-manapool-{ts}.txt"
        p.write_text(exports.build("manapool", rows), encoding="utf-8")
        written.append(p)
    if args.format in ("tcgplayer", "all"):
        p = buylist_dir / f"buildable-{code}-tcgplayer-{ts}.txt"
        p.write_text(exports.build("tcgplayer", rows), encoding="utf-8")
        written.append(p)
    if args.format in ("xlsx", "all"):
        p = checklist_dir / f"buildable-{code}-checklist-{ts}.xlsx"
        _write_xlsx(rows, p)
        written.append(p)

    target_total = sum(target.values())
    missing_total = sum(r.quantity for r in rows)
    buy_usd = sum((r.card.get("prices_usd") or 0.0) * r.quantity for r in rows)
    print(f"\n{code.upper()} buildable set — {n_themes} theme(s) across {n_variants} variant(s)")
    print(f"  target:  {len(target)} distinct cards / {target_total} copies")
    print(f"  owned:   {sum(owned.values())} copies of target cards")
    print(f"  missing: {len(rows)} distinct / {missing_total} copies · ${buy_usd:,.2f} to buy")
    if n_filtered:
        print(f"  (filtered {n_filtered} non-buyable print(s): tokens / digital / "
              f"unobtainable / meld-backs — pass --no-filter to include)")
    if skipped:
        print(f"  ! {len(skipped)} missing card(s) not in local cards table (name-only): "
              f"{', '.join(sorted(set(skipped))[:10])}"
              + (" …" if len(set(skipped)) > 10 else ""), file=sys.stderr)
    for p in written:
        print(f"  → {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
