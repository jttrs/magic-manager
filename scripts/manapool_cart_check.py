"""Deterministic Mana Pool cart audit — three atomic checks, one mapping pass.

Given the live Mana Pool cart (and, for the missing check, a set-family anchor),
report any combination of three independent checks:

  owned    cart lines whose printing you ALREADY own in local inventory
           (redundant purchases — candidates to remove from the cart).
  missing  family gaps (per `mm query missing-set`) that are NOT in the cart
           (printings you still ought to add). Requires --set.
  overpay  cart lines priced over true Scryfall/TCG market (the existing
           swindle check — identical logic to manapool_price_check.py).

Each check is atomic (`--check owned|missing|overpay|all`) and they SHARE:
  - the cart fetch            (manapool_common.load_cart → manapool_cart)
  - the cart→card mapping pass (manapool_common.map_cart; ONE pass feeds all)
  - the overpay comparison    (manapool_common.overpay_rows)
  - the missing-set union     (magic_manager.missing.missing_printings)

so nothing here re-derives logic that already exists elsewhere (DRY).

Set scoping: when --set is given, `owned` and `overpay` only judge cart lines
inside `set:CODE+related`; out-of-family lines are counted and reported as a
skip (stderr), not misclassified. `missing` always requires --set.

Usage:
    uv run python scripts/manapool_cart_check.py --set tla                      # all checks, live cart
    uv run python scripts/manapool_cart_check.py --set tla --check owned --file cart.json
    uv run python scripts/manapool_cart_check.py --set tla --check missing
    pbpaste | uv run python scripts/manapool_cart_check.py --set tla --method bookmarklet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from manapool_common import (  # noqa: E402
    CartLine, load_cart, map_cart, overpay_rows, _fmt,
)
from magic_manager import db, missing as missing_mod, sets as sets_mod  # noqa: E402
from magic_manager.selectors import _cn_sort_key  # noqa: E402


# ---------- helpers ----------

def _scryfall_url(setc: str, num: str) -> str:
    return f"https://scryfall.com/card/{setc.lower()}/{num}" if setc and num else ""


def _card_link(name: str, setc: str, num: str) -> str:
    """`[name (SET) cn](url)` with pipes escaped; plain name if no url."""
    safe = (name or "?").replace("|", "\\|")
    url = _scryfall_url(setc, num)
    label = f"{safe} ({setc}) {num}" if setc and num else safe
    return f"[{label}]({url})" if url else safe


def _row_market(foil: bool, card: dict) -> float | None:
    val = card.get("prices_usd_foil") if foil else card.get("prices_usd")
    return float(val) if val not in (None, "") else None


# ---------- the three atomic checks ----------

def check_owned(mapped: list[CartLine], family_codes: set[str] | None) -> tuple[list[dict], int]:
    """Cart lines whose (scryfall_id, finish) is already owned in inventory.

    Returns (rows, skipped) where skipped counts out-of-family lines when
    family_codes is given. A line is "owned" iff inventory qty>0 for the same
    printing AND the same finish. Deterministic sort (set, cn, finish).
    """
    # Collect the scryfall_ids we need to test, honoring family scoping.
    candidates: list[CartLine] = []
    skipped = 0
    for m in mapped:
        if not m.scryfall_id:
            continue  # unmapped — can't test ownership; overpay reports these
        if family_codes is not None and (m.set_code or "").lower() not in family_codes:
            skipped += 1
            continue
        candidates.append(m)

    if not candidates:
        return [], skipped

    sids = list({m.scryfall_id for m in candidates})
    placeholders = ",".join("?" for _ in sids)
    owned: dict[tuple[str, str], int] = {}
    with db.connect() as conn:
        for r in conn.execute(
            f"SELECT scryfall_id, finish, quantity FROM inventory "
            f"WHERE scryfall_id IN ({placeholders})",
            sids,
        ).fetchall():
            owned[(r["scryfall_id"], r["finish"])] = r["quantity"]

    rows: list[dict] = []
    for m in candidates:
        fin = "foil" if m.foil else "nonfoil"
        qty = owned.get((m.scryfall_id, fin), 0)
        if qty > 0:
            rows.append({
                "name": m.name or "?", "set": m.set_code or "", "num": m.number or "",
                "fin": fin, "owned_qty": qty, "your": (m.price_cents or 0) / 100.0,
            })
    rows.sort(key=lambda r: (r["set"], _cn_sort_key(r["num"]), r["fin"]))
    return rows, skipped


def check_missing(anchor: str, mapped: list[CartLine], treatment_class: str) -> list[dict]:
    """Family gaps (missing.missing_printings) that are NOT already in the cart.

    Cart membership is keyed on (scryfall_id, finish) — both sides normalized to
    the 'nonfoil'|'foil' string — so a nonfoil cart line does not suppress a
    foil gap (or vice-versa). Deterministic sort (set, cn, finish).
    """
    in_cart = {(m.scryfall_id, "foil" if m.foil else "nonfoil")
               for m in mapped if m.scryfall_id}
    gaps = missing_mod.missing_printings(anchor, treatment_class)
    rows: list[dict] = []
    for r in gaps:
        if (r.scryfall_id, r.finish) in in_cart:
            continue
        rows.append({
            "name": r.card.get("name") or "?",
            "set": r.card.get("set") or "",
            "num": r.card.get("collector_number") or "",
            "fin": r.finish,
            "market": _row_market(r.finish == "foil", r.card),
        })
    rows.sort(key=lambda r: (r["set"], _cn_sort_key(r["num"]), r["fin"]))
    return rows


def check_overpay(mapped: list[CartLine], family_codes: set[str] | None) -> tuple[dict, int]:
    """Overpay buckets over (optionally family-scoped) mapped lines.

    Returns (buckets, skipped) where buckets is manapool_common.overpay_rows'
    output and skipped counts out-of-family lines when family_codes is given.
    """
    skipped = 0
    if family_codes is not None:
        scoped: list[CartLine] = []
        for m in mapped:
            # keep unmapped lines (overpay_rows counts them as 'unmapped'); scope
            # only lines we could place in/out of the family.
            if m.set_code and m.set_code.lower() not in family_codes:
                skipped += 1
                continue
            scoped.append(m)
        mapped = scoped
    return overpay_rows(mapped), skipped


# ---------- rendering ----------
#
# Output contract: STDOUT is data only — a summary table then one data table per
# requested check, each closed by a bold Total row. No prose, no empty-state
# sentences (an empty section still renders header + Total(0)). All commentary
# (scope, skips, unmapped/no-market notes) goes to STDERR. Deterministic: fixed
# columns, fixed row order (the check functions sort), fixed money formatting.

def _render_summary(set_code: str | None, n_lines: int, results: dict, over_market_pct: float) -> None:
    print("## Summary")
    print()
    print("| Metric | Value |")
    print("|---|--:|")
    print(f"| Set family | {(set_code.lower() + '+related') if set_code else '(unscoped)'} |")
    print(f"| Cart lines | {n_lines} |")
    if "owned" in results:
        rows = results["owned"]
        print(f"| Owned (redundant) | {len(rows)} · {_fmt(sum(r['your'] for r in rows))} |")
    if "missing" in results:
        rows = results["missing"]
        print(f"| Missing from cart | {len(rows)} · {_fmt(sum((r['market'] or 0.0) for r in rows))} |")
    if "overpay" in results:
        b = results["overpay"]
        n_flag = sum(1 for r in b["rows"] if r["pct"] >= over_market_pct)
        flagged_over = sum(r["over"] for r in b["rows"] if r["pct"] >= over_market_pct)
        print(f"| Overpay flagged (≥{over_market_pct:.0f}%) | {n_flag} · {_fmt(flagged_over)} |")


def _render_owned(rows: list[dict]) -> None:
    print("## Owned")
    print()
    print("| Card | Fin | Owned | Cart $ |")
    print("|---|:--:|--:|--:|")
    for r in rows:
        print(f"| {_card_link(r['name'], r['set'], r['num'])} | {r['fin']} | "
              f"{r['owned_qty']} | {_fmt(r['your'])} |")
    print(f"| **Total ({len(rows)})** | | | **{_fmt(sum(r['your'] for r in rows))}** |")


def _render_missing(rows: list[dict]) -> None:
    print("## Missing")
    print()
    print("| Card | Fin | Market $ |")
    print("|---|:--:|--:|")
    for r in rows:
        print(f"| {_card_link(r['name'], r['set'], r['num'])} | {r['fin']} | "
              f"{_fmt(r['market'])} |")
    print(f"| **Total ({len(rows)})** | | **{_fmt(sum((r['market'] or 0.0) for r in rows))}** |")


def _render_overpay(buckets: dict, over_market_pct: float) -> None:
    print("## Overpay")
    print()
    rows = buckets["rows"]
    print("| Card | Fin | Your $ | MP $ | Market $ | Δ $ | Δ % | Flag |")
    print("|---|:--:|--:|--:|--:|--:|--:|:--:|")
    n_flag = 0
    flagged_total_over = 0.0
    for r in rows:
        flagged = r["pct"] >= over_market_pct
        if flagged:
            n_flag += 1
            flagged_total_over += r["over"]
        print(f"| {_card_link(r['name'], r['set'], r['num'])} | {r['fin']} | "
              f"{_fmt(r['your'])} | {_fmt(r['mp_cheap'])} | {_fmt(r['market'])} | "
              f"{r['over']:+.2f} | {r['pct']:+.0f}% | {'⚠️' if flagged else ''} |")
    print(f"| **Total ({len(rows)})** | | | | | **{flagged_total_over:+.2f}** | | "
          f"**{n_flag} ⚠️** |")


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser(description="Audit a Mana Pool cart: owned / missing / overpay.")
    ap.add_argument("--set", dest="set_code", default=None,
                    help="Set-family anchor (e.g. tla). Required for the missing check; "
                         "scopes owned/overpay to set:CODE+related when given.")
    ap.add_argument("--check", choices=["owned", "missing", "overpay", "all"], default="all",
                    help="Which check(s) to run. Default all.")
    ap.add_argument("--file", default=None, help="Cart JSON path, or '-' for stdin.")
    ap.add_argument("--method", choices=["headless", "bookmarklet"], default=None,
                    help="Force cart fetch path. Default: try headless, else stdin.")
    ap.add_argument("--over-market-pct", type=float, default=50.0,
                    help="Flag overpay lines this %% or more over market. Default 50.")
    ap.add_argument("--treatment-class", default="preferred",
                    help="Treatment class for the missing check. Default preferred.")
    args = ap.parse_args()

    checks = ["owned", "missing", "overpay"] if args.check == "all" else [args.check]

    # Missing requires an anchor.
    if "missing" in checks and not args.set_code:
        print("error: --set CODE is required for the missing check.", file=sys.stderr)
        return 2

    # Resolve family scope (owned/overpay honor it; missing is inherently scoped).
    family_codes: set[str] | None = None
    if args.set_code:
        try:
            family_codes = {c.lower() for c in sets_mod.resolve(args.set_code).all_codes}
        except LookupError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    # Fetch + the ONE mapping pass, shared across every requested check.
    cart = load_cart(args.file, args.method)
    if not cart:
        print("error: empty cart (nothing to check).", file=sys.stderr)
        return 2
    print(f"mapping {len({c['card_id'] for c in cart if c.get('card_id')})} "
          f"cart cards via Mana Pool products…", file=sys.stderr)
    mapped = map_cart(cart)

    # Run every requested check first (collect results), so the summary table can
    # lead the report. Notes accumulate for stderr.
    results: dict = {}
    skips: list[str] = []
    for chk in checks:
        if chk == "owned":
            rows, skipped = check_owned(mapped, family_codes)
            results["owned"] = rows
            if skipped:
                skips.append(f"owned: {skipped} out-of-family line(s) skipped")
        elif chk == "missing":
            results["missing"] = check_missing(args.set_code, mapped, args.treatment_class)
        elif chk == "overpay":
            buckets, skipped = check_overpay(mapped, family_codes)
            results["overpay"] = buckets
            if buckets["unmapped"]:
                skips.append(f"overpay: {buckets['unmapped']} unmapped line(s) skipped")
            if skipped:
                skips.append(f"overpay: {skipped} out-of-family line(s) skipped")
            no_market = buckets["no_market"]
            if no_market:
                skips.append(f"overpay: {len(no_market)} line(s) had no market price, not judged "
                             f"({', '.join(x['name'] for x in no_market[:8])}"
                             f"{'…' if len(no_market) > 8 else ''})")

    # STDOUT: title, summary, then one data table per check (in fixed order).
    print(f"# Mana Pool cart check — {len(mapped)} line(s)")
    print()
    _render_summary(args.set_code, len(mapped), results, args.over_market_pct)
    for chk in ("owned", "missing", "overpay"):
        if chk not in results:
            continue
        print()
        if chk == "owned":
            _render_owned(results["owned"])
        elif chk == "missing":
            _render_missing(results["missing"])
        elif chk == "overpay":
            _render_overpay(results["overpay"], args.over_market_pct)

    # STDERR: all commentary.
    if family_codes:
        print(f"scoped to set:{args.set_code.lower()}+related; "
              f"out-of-family cart lines skipped where noted.", file=sys.stderr)
    for s in skips:
        print(s, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
