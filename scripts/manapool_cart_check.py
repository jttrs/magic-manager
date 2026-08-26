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
QUERIES_DIR = ROOT / "queries"
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


def check_dupes(mapped: list[CartLine]) -> list[dict]:
    """Cart lines that duplicate a printing you're already buying.

    Unscoped by design (a dupe is a dupe regardless of --set family): group by
    scryfall_id — which on Scryfall uniquely identifies one ART, finish being
    orthogonal — and flag any printing bought more than once. Two flavors:
      hard  a single finish has qty >= 2 (two literally identical cards).
      soft  both a nonfoil and a foil of the same printing are in the cart
            (same art, two finishes — the collection tracks these as distinct
            copies, but when BUYING you usually want only the cheaper).
    A printing can be both. One collated row per dupe printing, carrying each
    finish's qty + cheapest cart price so the user can pick or confirm intent.
    """
    # group[scryfall_id] = {"nf_qty","fo_qty","nf_price","fo_price","name","set","num"}
    groups: dict[str, dict] = {}
    for m in mapped:
        if not m.scryfall_id:
            continue
        g = groups.setdefault(m.scryfall_id, {
            "name": m.name or "?", "set": m.set_code or "", "num": m.number or "",
            "nf_qty": 0, "fo_qty": 0, "nf_price": None, "fo_price": None,
        })
        qty = m.quantity or 1
        price = m.price_cents / 100 if m.price_cents is not None else None
        if m.foil:
            g["fo_qty"] += qty
            if price is not None and (g["fo_price"] is None or price < g["fo_price"]):
                g["fo_price"] = price
        else:
            g["nf_qty"] += qty
            if price is not None and (g["nf_price"] is None or price < g["nf_price"]):
                g["nf_price"] = price

    rows: list[dict] = []
    for g in groups.values():
        hard = g["nf_qty"] >= 2 or g["fo_qty"] >= 2
        soft = g["nf_qty"] >= 1 and g["fo_qty"] >= 1
        if not (hard or soft):
            continue
        notes: list[str] = []
        if g["nf_qty"] >= 2:
            notes.append(f"×{g['nf_qty']} nonfoil")
        if g["fo_qty"] >= 2:
            notes.append(f"×{g['fo_qty']} foil")
        if soft:
            notes.append("foil+nonfoil")
        prices = [p for p in (g["nf_price"], g["fo_price"]) if p is not None]
        rows.append({
            "name": g["name"], "set": g["set"], "num": g["num"],
            "nf_qty": g["nf_qty"], "nf_price": g["nf_price"],
            "fo_qty": g["fo_qty"], "fo_price": g["fo_price"],
            "cheaper": min(prices) if (soft and prices) else None,
            "note": ", ".join(notes),
        })
    rows.sort(key=lambda r: (r["set"], _cn_sort_key(r["num"])))
    return rows


def infer_set_anchors(mapped: list[CartLine]) -> list[str]:
    """Distinct family anchors of the cart's mapped set codes.

    Each mapped line carries the Scryfall set code of its printing; collapsing
    those to family anchors via sets_mod.resolve (24h-cached /sets) tells us
    which family (or families) the cart belongs to — one anchor => deterministic
    imputation, several => ambiguous (report all, let the user disambiguate).
    """
    codes = {m.set_code.lower() for m in mapped if m.set_code and m.scryfall_id}
    anchors: set[str] = set()
    for c in codes:
        try:
            anchors.add(sets_mod.resolve(c).code)
        except LookupError:
            pass
    return sorted(anchors)


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
# queries/ and linked. Prevents a 100+-row overpay table from flooding chat.

_CHAT_ROW_CAP = 40  # per-table row cap for the chat report; the file is uncapped


def _summary_lines(set_code: str | None, n_lines: int, results: dict, over_market_pct: float) -> list[str]:
    out = ["## Summary", "", "| Metric | Value |", "|---|--:|",
           f"| Set family | {(set_code.lower() + '+related') if set_code else '(unscoped)'} |",
           f"| Cart lines | {n_lines} |"]
    if "owned" in results:
        rows = results["owned"]
        out.append(f"| Owned (redundant) | {len(rows)} · {_fmt(sum(r['your'] for r in rows))} |")
    if "missing" in results:
        rows = results["missing"]
        out.append(f"| Missing from cart | {len(rows)} · {_fmt(sum((r['market'] or 0.0) for r in rows))} |")
    if "overpay" in results:
        b = results["overpay"]
        n_flag = sum(1 for r in b["rows"] if r["pct"] >= over_market_pct)
        flagged_over = sum(r["over"] for r in b["rows"] if r["pct"] >= over_market_pct)
        out.append(f"| Overpay flagged (≥{over_market_pct:.0f}%) | {n_flag} · {_fmt(flagged_over)} |")
    return out


def _capped(rows: list[dict], cap: int | None) -> tuple[list[dict], int]:
    """(shown_rows, n_hidden). cap=None means show all."""
    if cap is None or len(rows) <= cap:
        return rows, 0
    return rows[:cap], len(rows) - cap


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
    n_flag = sum(1 for r in rows if r["pct"] >= over_market_pct)
    flagged_total_over = sum(r["over"] for r in rows if r["pct"] >= over_market_pct)
    display = [r for r in rows if r["pct"] >= over_market_pct] if flagged_only else rows
    title = "## Overpay (flagged)" if flagged_only else "## Overpay"
    out = [title, "", "| Card | Fin | Your $ | MP $ | Market $ | Δ $ | Δ % | Flag |",
           "|---|:--:|--:|--:|--:|--:|--:|:--:|"]
    for r in display:
        flagged = r["pct"] >= over_market_pct
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

    title = f"# Mana Pool cart check — {len(mapped)} line(s)"

    # Write the FULL report (every row, uncapped) to queries/ so the chat report
    # can stay concise. Only worth writing when overpay ran (it's the big table).
    file_link = None
    if "overpay" in results:
        full = [title, ""] + _report_blocks(
            args.set_code, len(mapped), results, args.over_market_pct, chat=False)
        QUERIES_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        anchor = (args.set_code or "cart").lower()
        out_path = QUERIES_DIR / f"cart-check-{anchor}-{ts}.md"
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
        print()
        print(f"🧾 Full cart check ({len(results['overpay']['rows'])} priced lines): "
              f"[{file_link.relative_to(ROOT)}](file://{file_link.resolve()})")

    # STDERR: all commentary.
    if family_codes:
        print(f"scoped to set:{args.set_code.lower()}+related; "
              f"out-of-family cart lines skipped where noted.", file=sys.stderr)
    for s in skips:
        print(s, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
