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
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from manapool_common import load_cart, map_cart, _fmt  # noqa: E402
from magic_manager import sets as sets_mod, util  # noqa: E402
from magic_manager.cart import (  # noqa: E402 — the checks live in the engine
    OVER_MARKET_USD_MIN as _OVER_MARKET_USD_MIN, check_dupes, check_missing, check_overpay,
    check_owned, infer_set_anchors, is_flagged,
)


# ---------- helpers ----------

def _scryfall_url(setc: str, num: str) -> str:
    return f"https://scryfall.com/card/{setc.lower()}/{num}" if setc and num else ""


def _card_link(name: str, setc: str, num: str) -> str:
    """`[name (SET) cn](url)` with pipes escaped; plain name if no url."""
    safe = (name or "?").replace("|", "\\|")
    url = _scryfall_url(setc, num)
    label = f"{safe} ({setc}) {num}" if setc and num else safe
    return f"[{label}]({url})" if url else safe


# ---------- rendering ----------
#
# Each section builder returns a list of markdown lines (no printing) so the SAME
# builder feeds both the chat report and the full file artifact (DRY). Output is
# data only — a summary table then one data table per check, each closed by a
# bold Total row; no prose, no empty-state sentences (an empty section still
# renders header + Total(0)). Deterministic: fixed columns, fixed row order (the
# check functions sort), fixed money formatting.
#
# Chat vs file split (mirrors the missing-from-set skill): the chat report is the
# ACTIONABLE subset — full owned/missing lists (capped for safety) plus only the
# FLAGGED overpay rows — while the full report (every overpay row) is written to
# output/cart-check/reports/ and linked. Prevents a 100+-row overpay table from flooding chat.

_CHAT_ROW_CAP = 40  # per-table row cap for the chat report; the file is uncapped

# A line must clear BOTH gates to be flagged: the % gate (--over-market-pct)
# AND an absolute-dollar floor. The dollar floor kills the low-threshold noise
# where a big percentage is pennies (e.g. $0.21 → $0.25 is +19% but +$0.04).


def _is_flagged(row: dict, over_market_pct: float) -> bool:
    return is_flagged(row, over_market_pct)

def _summary_lines(set_code: str | None, n_lines: int, results: dict, over_market_pct: float) -> list[str]:
    out = ["## Summary", "", "| Metric | Value |", "|---|--:|",
           f"| Set family | {(set_code.lower() + '+related') if set_code else '(unscoped)'} |",
           f"| Cart lines | {n_lines} |"]
    if "dupes" in results:
        out.append(f"| Dupe printings | {len(results['dupes'])} |")
    if "owned" in results:
        rows = results["owned"]
        out.append(f"| Owned (redundant) | {len(rows)} · {_fmt(sum(r['your'] for r in rows))} |")
    if "missing" in results:
        rows = results["missing"]
        out.append(f"| Missing from cart | {len(rows)} · {_fmt(sum((r['market'] or 0.0) for r in rows))} |")
    if "overpay" in results:
        b = results["overpay"]
        n_flag = sum(1 for r in b["rows"] if _is_flagged(r, over_market_pct))
        flagged_over = sum(r["over"] for r in b["rows"] if _is_flagged(r, over_market_pct))
        out.append(f"| Overpay flagged (≥{over_market_pct:.0f}% & >{_fmt(_OVER_MARKET_USD_MIN)}) "
                   f"| {n_flag} · {_fmt(flagged_over)} |")
    return out


def _capped(rows: list[dict], cap: int | None) -> tuple[list[dict], int]:
    """(shown_rows, n_hidden). cap=None means show all."""
    if cap is None or len(rows) <= cap:
        return rows, 0
    return rows[:cap], len(rows) - cap


def _qty_price(qty: int, price: float | None) -> str:
    """`{qty} · {$price}` for a present finish, `—` when that finish is absent."""
    return f"{qty} · {_fmt(price)}" if qty else "—"


def _dupes_lines(rows: list[dict], cap: int | None = None) -> list[str]:
    shown, hidden = _capped(rows, cap)
    out = ["## Dupes", "", "| Card | Nonfoil | Foil | Cheaper | Note |",
           "|---|--:|--:|--:|:--|"]
    for r in shown:
        out.append(f"| {_card_link(r['name'], r['set'], r['num'])} | "
                   f"{_qty_price(r['nf_qty'], r['nf_price'])} | "
                   f"{_qty_price(r['fo_qty'], r['fo_price'])} | "
                   f"{_fmt(r['cheaper']) if r['cheaper'] is not None else '—'} | {r['note']} |")
    if hidden:
        out.append(f"| _+{hidden} more (see file)_ | | | | |")
    out.append(f"| **Total ({len(rows)})** | | | | |")
    return out


def _owned_lines(rows: list[dict], cap: int | None = None) -> list[str]:
    shown, hidden = _capped(rows, cap)
    out = ["## Owned", "", "| Card | Fin | Owned | Cart $ |", "|---|:--:|--:|--:|"]
    for r in shown:
        out.append(f"| {_card_link(r['name'], r['set'], r['num'])} | {r['fin']} | "
                   f"{r['owned_qty']} | {_fmt(r['your'])} |")
    if hidden:
        out.append(f"| _+{hidden} more (see file)_ | | | |")
    out.append(f"| **Total ({len(rows)})** | | | **{_fmt(sum(r['your'] for r in rows))}** |")
    return out


def _missing_lines(rows: list[dict], cap: int | None = None) -> list[str]:
    shown, hidden = _capped(rows, cap)
    out = ["## Missing", "", "| Card | Fin | Market $ |", "|---|:--:|--:|"]
    for r in shown:
        out.append(f"| {_card_link(r['name'], r['set'], r['num'])} | {r['fin']} | {_fmt(r['market'])} |")
    if hidden:
        out.append(f"| _+{hidden} more (see file)_ | | |")
    out.append(f"| **Total ({len(rows)})** | | **{_fmt(sum((r['market'] or 0.0) for r in rows))}** |")
    return out


def _overpay_lines(buckets: dict, over_market_pct: float, flagged_only: bool = False) -> list[str]:
    rows = buckets["rows"]
    n_flag = sum(1 for r in rows if _is_flagged(r, over_market_pct))
    flagged_total_over = sum(r["over"] for r in rows if _is_flagged(r, over_market_pct))
    display = [r for r in rows if _is_flagged(r, over_market_pct)] if flagged_only else rows
    title = "## Overpay (flagged)" if flagged_only else "## Overpay"
    out = [title, "", "| Card | Fin | Your $ | MP $ | Market $ | Δ $ | Δ % | Flag |",
           "|---|:--:|--:|--:|--:|--:|--:|:--:|"]
    for r in display:
        flagged = _is_flagged(r, over_market_pct)
        out.append(f"| {_card_link(r['name'], r['set'], r['num'])} | {r['fin']} | "
                   f"{_fmt(r['your'])} | {_fmt(r['mp_cheap'])} | {_fmt(r['market'])} | "
                   f"{r['over']:+.2f} | {r['pct']:+.0f}% | {'⚠️' if flagged else ''} |")
    if flagged_only and not display:
        out.append("| _none ≥ threshold — full pricing in file_ | | | | | | | |")
    denom = len(display) if flagged_only else len(rows)
    out.append(f"| **Total ({denom}{'/' + str(len(rows)) if flagged_only else ''})** | | | | | "
               f"**{flagged_total_over:+.2f}** | | **{n_flag} ⚠️** |")
    return out


def _report_blocks(set_code, n_lines, results, over_market_pct, *, chat: bool) -> list[str]:
    """Assemble the full report (chat=False) or the concise chat report
    (chat=True: full-but-capped owned/missing, flagged-only overpay)."""
    cap = _CHAT_ROW_CAP if chat else None
    blocks: list[list[str]] = [_summary_lines(set_code, n_lines, results, over_market_pct)]
    if "dupes" in results:
        blocks.append(_dupes_lines(results["dupes"], cap))
    if "owned" in results:
        blocks.append(_owned_lines(results["owned"], cap))
    if "missing" in results:
        blocks.append(_missing_lines(results["missing"], cap))
    if "overpay" in results:
        blocks.append(_overpay_lines(results["overpay"], over_market_pct, flagged_only=chat))
    # join blocks with a blank line between
    lines: list[str] = []
    for i, b in enumerate(blocks):
        if i:
            lines.append("")
        lines.extend(b)
    return lines


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser(description="Audit a Mana Pool cart: owned / missing / overpay.")
    ap.add_argument("--set", dest="set_code", default=None,
                    help="Set-family anchor (e.g. tla). Required for the missing check; "
                         "scopes owned/overpay to set:CODE+related when given.")
    ap.add_argument("--check", choices=["owned", "missing", "overpay", "dupes", "all"],
                    default="all", help="Which check(s) to run. Default all.")
    ap.add_argument("--file", default=None, help="Cart JSON path, or '-' for stdin.")
    ap.add_argument("--method", choices=["headless", "bookmarklet"], default=None,
                    help="Force cart fetch path. Default: try headless, else stdin.")
    ap.add_argument("--over-market-pct", type=float, default=10.0,
                    help="Flag overpay lines this %% or more over market. Default 10.")
    ap.add_argument("--treatment-class", default="preferred",
                    help="Treatment class for the missing check. Default preferred.")
    args = ap.parse_args()

    # `all` is context-sensitive: with a set anchor it runs everything; without
    # one it runs only the anchor-free checks (dupes + overpay) — so a bare,
    # zero-context invocation still produces a useful audit instead of erroring.
    if args.check == "all":
        checks = (["dupes", "owned", "missing", "overpay"] if args.set_code
                  else ["dupes", "overpay"])
    else:
        checks = [args.check]

    # Missing requires an anchor (only reachable now via an EXPLICIT --check missing).
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
        if chk == "dupes":
            results["dupes"] = check_dupes(mapped)
        elif chk == "owned":
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

    title = f"# Mana Pool cart check — {len(mapped)} line(s)"

    # Write the FULL report (every row, uncapped) to output/cart-check/reports/ so the chat report
    # can stay concise. Worth writing whenever a big table ran (overpay or dupes).
    file_link = None
    if "overpay" in results or "dupes" in results:
        full = [title, ""] + _report_blocks(
            args.set_code, len(mapped), results, args.over_market_pct, chat=False)
        out_dir = util.output_dir("cart-check", "reports")
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        anchor = (args.set_code or "cart").lower()
        out_path = out_dir / f"cart-check-{anchor}-{ts}.md"
        out_path.write_text("\n".join(full) + "\n", encoding="utf-8")
        file_link = out_path

    # STDOUT: the concise, chat-ready report (capped owned/missing, flagged-only
    # overpay). Full detail lives in the file linked at the end.
    print(title)
    print()
    for line in _report_blocks(
            args.set_code, len(mapped), results, args.over_market_pct, chat=True):
        print(line)
    if file_link is not None:
        detail = (f"{len(results['overpay']['rows'])} priced lines" if "overpay" in results
                  else f"{len(results['dupes'])} dupe printings")
        print()
        print(f"🧾 Full cart check ({detail}): "
              f"[{file_link.relative_to(ROOT)}](file://{file_link.resolve()})")

    # STDERR: all commentary.
    if family_codes:
        print(f"scoped to set:{args.set_code.lower()}+related; "
              f"out-of-family cart lines skipped where noted.", file=sys.stderr)
    for s in skips:
        print(s, file=sys.stderr)
    # No anchor was given: impute the family from the cart's own set codes so the
    # user can opt into the set-scoped checks (owned + missing) on a re-run.
    if not args.set_code:
        anchors = infer_set_anchors(mapped)
        if anchors:
            plural = "y" if len(anchors) == 1 else "ies"
            print(f"imputed set famil{plural}: {', '.join(anchors)} — re-run with "
                  f"--set <code> to add the owned + missing checks.", file=sys.stderr)
        else:
            print("could not impute a set family (no mapped set codes); pass "
                  "--set <code> for the owned + missing checks.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
