"""Survey a set family's print universe to identify candidate treatment
signatures for dupe-foil filtering or per-family unobtainable rules.

Use case: when a new release lands (Avatar Eternal, TMNT, future Star Wars,
etc.), `mm query missing-set <CODE>` errors on `treatment=preferred` until
the family is configured in `selectors.FAMILY_DUPE_FOIL_PROMO_TYPES` and
optionally `selectors.FAMILY_UNOBTAINABLE_RULES`. This script surfaces the
data the user needs to adjudicate those configs without grepping the DB.

What it does:
1. Resolves the family graph for an anchor set code (parent + bonus sheets +
   commander deck + promos + memorabilia).
2. Counts every distinct ``promo_types`` token across the family's prints.
3. For each candidate token, finds 3 example prints + their same-name
   siblings in the family WITHOUT that token, so the user can compare art
   visually via Scryfall URLs.
4. Also surfaces co-occurrence patterns (e.g. silverfoil AND scroll on LTR's
   scroll-frame prints) so the user can spot AND-of-promo_types treatments.

Usage:
    uv run python scripts/survey_treatment_signature.py LTR
    uv run python scripts/survey_treatment_signature.py FIN

Then read the output, decide which signatures map to:
- "dupe of a sibling, just on a fancy-foil sheet" -> FAMILY_DUPE_FOIL_PROMO_TYPES
- "exists, distinct art, but I won't shop for it"  -> FAMILY_UNOBTAINABLE_RULES
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

# Make src/ importable so we can resolve family graphs via sets.resolve().
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import sets as sets_mod  # noqa: E402

DB_PATH = ROOT / "db" / "magic_manager.db"


def _decode_json_field(raw):
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return []
    return list(raw)


def _scryfall_url(uri: str | None) -> str:
    return (uri or "").split("?")[0]


def survey(anchor_code: str) -> None:
    anchor = anchor_code.lower()
    try:
        resolved = sets_mod.resolve(anchor)
    except LookupError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)

    family = tuple(resolved.all_codes)
    print(f"=== {anchor.upper()} family ({len(family)} sets) ===")
    print(f"  {', '.join(sorted(family))}")
    print()

    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in family)

    # Pull every print in the family.
    rows = con.execute(
        f"""SELECT scryfall_id, set_code, collector_number, name, rarity,
                   border_color, frame_effects, promo_types, prices_usd,
                   prices_usd_foil, scryfall_uri
              FROM cards WHERE set_code IN ({placeholders})""",
        family,
    ).fetchall()
    print(f"total prints in family: {len(rows)}")
    print()

    # 1. Count promo_types tokens.
    pt_counter: Counter[str] = Counter()
    for r in rows:
        for pt in _decode_json_field(r["promo_types"]):
            pt_counter[pt] += 1

    print("--- promo_types frequency ---")
    for pt, n in pt_counter.most_common():
        print(f"  {n:>5}  {pt}")
    print()

    # 2. Pairwise co-occurrence — surfaces AND-of-promo_types treatments.
    pair_counter: Counter[tuple[str, str]] = Counter()
    for r in rows:
        pts = sorted(_decode_json_field(r["promo_types"]))
        for i, a in enumerate(pts):
            for b in pts[i + 1:]:
                pair_counter[(a, b)] += 1
    if pair_counter:
        print("--- top promo_types co-occurrence pairs (≥10) ---")
        for (a, b), n in pair_counter.most_common(20):
            if n < 10:
                break
            print(f"  {n:>5}  {a} + {b}")
        print()

    # 3. For each promo_type with frequency > 5, show 3 example prints and
    #    each one's same-name siblings in the family without that token.
    candidates = [pt for pt, n in pt_counter.items() if n > 5]
    skip = {"universesbeyond", "boosterfun"}  # too generic to be a treatment signal
    candidates = [pt for pt in candidates if pt not in skip]

    print("--- per-token examples + sibling diff ---")
    for pt in sorted(candidates):
        examples = [
            r for r in rows
            if pt in _decode_json_field(r["promo_types"])
        ][:3]
        if not examples:
            continue
        print(f"\n* {pt!r} ({pt_counter[pt]} prints)")
        for ex in examples:
            ex_pts = _decode_json_field(ex["promo_types"])
            ex_fes = _decode_json_field(ex["frame_effects"])
            # Same-name siblings WITHOUT this pt.
            sibs = [
                s for s in rows
                if s["name"] == ex["name"]
                and s["scryfall_id"] != ex["scryfall_id"]
                and pt not in _decode_json_field(s["promo_types"])
            ]
            print(
                f"    {ex['set_code'].upper()} {ex['collector_number']:<6} "
                f"{ex['rarity']:<8} {ex['name'][:36]:<36}"
            )
            print(
                f"        bc={ex['border_color']:<10} fe={ex_fes} pts={ex_pts}"
            )
            print(f"        {_scryfall_url(ex['scryfall_uri'])}")
            print(f"        siblings WITHOUT {pt!r}: {len(sibs)}")
            for s in sibs[:2]:
                s_pts = _decode_json_field(s["promo_types"])
                print(
                    f"          - {s['set_code'].upper()} {s['collector_number']:<6} "
                    f"pts={s_pts}"
                )
                print(f"            {_scryfall_url(s['scryfall_uri'])}")

    print()
    print("=== next steps ===")
    print("After visually comparing the example URLs above, decide for each")
    print("treatment signature:")
    print("  (A) Same art as a sibling, just on a fancy-foil sheet → add the")
    print("      promo_type to FAMILY_DUPE_FOIL_PROMO_TYPES[anchor] in")
    print("      src/magic_manager/selectors.py.")
    print("  (B) Distinct art, but you'll never shop for it (rare distribution,")
    print("      personal taste) → add a rule to FAMILY_UNOBTAINABLE_RULES[anchor]")
    print("      in selectors.py. Use promo_types_all_of for AND-of-tokens")
    print("      treatments (e.g. silverfoil+scroll), promo_types_any_of for")
    print("      single-token signals.")
    print("  (C) Distinct art, you might shop for it → leave it out of both.")


def main():
    if len(sys.argv) != 2:
        print("usage: survey_treatment_signature.py <ANCHOR_CODE>", file=sys.stderr)
        sys.exit(2)
    survey(sys.argv[1])


if __name__ == "__main__":
    main()
