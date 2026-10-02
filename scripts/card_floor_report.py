"""Deterministic "cheapest card floor" report — the cheapest printing of each
card in a set of cards, at a chosen scope and finish mode.

Given any selector (the repo's universal "set of cards" input — ``set:fin+related``,
``cards:e:sld cn≥1858``, ``deck:<slug>``, ``inventory``, ``wishlist:…``) OR a
pasted Moxfield-style block, this reports, per PRINTING in the selection:

  * the price of THAT printing (local, finish-aware) — "this-print $", and
  * the cheapest printing of the same card (by oracle_id) at the chosen SCOPE —
    the floor, i.e. the cheapest way to get the card's mechanics into a deck.

Scopes (``--scope``):
  anywhere   (default) LIVE batched ``oracleid:`` Scryfall floor across every set.
  in-family  LOCAL floor restricted to the selection's resolved set family/families
             (no network) — "cheapest I can get it from within this family".
  local      LOCAL floor across every synced printing (no network).

Finish modes (``--finish``):
  either    (default) the cheaper finish, nonfoil preferred on a tie — one $ col.
  preserve  keep nonfoil and foil floors distinct (a print may exist in only one
            finish) — two $ cols.

All floor math lives in ``magic_manager.card_floor`` (the single engine); this
script is the thin report/formatting layer. Reference output shape:
``Card | CN | this-print $ | cheapest-anywhere (set/finish)``.

Cross-universe exception: the default ``--scope anywhere`` is inherently a
LIVE, cross-every-set lookup (local can't answer "cheapest anywhere"), so it
is NOT subject to the repo's local-first convention — see CLAUDE.md § Price
freshness: cross-universe exception. ``--refresh`` is accepted only for CLI
surface consistency with the local-first commands; it has no additional
effect here.

Emits (matching set-status's chat relay + edhrec/sealed-value's artifacts):
  * a markdown table to stdout (Scryfall-hyperlinked) for chat relay, and
  * JSON + XLSX under output/card-floor/reports/.

Usage:
    uv run python scripts/card_floor_report.py 'set:sld cn>=1858 cn<=1872'
    uv run python scripts/card_floor_report.py 'cards:oracleid:...' --scope in-family
    uv run python scripts/card_floor_report.py 'deck:my-deck' --finish preserve
    printf '1 Sol Ring (CMM) 425\\n' | uv run python scripts/card_floor_report.py --stdin

Exit codes:
    0 — report written (even if the selection is empty)
    2 — bad selector / bad invocation / Scryfall lookup failure
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_OUTPUT_TYPE = "card-floor"  # → output/card-floor/reports/
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import (  # noqa: E402
    card_floor, exports, parsers, scryfall, scryfall_urls, selectors,
    sets as sets_mod, util,
)


# ---------- input resolution ----------

def _rows_from_selector(selector: str):
    """Materialize a selector to printing rows (raises SelectorParseError/LookupError)."""
    return selectors.materialize(selector)


def _rows_from_stdin():
    """Resolve a pasted Moxfield-style block to printing rows via /cards/collection.

    Returns a list of lightweight row-likes with ``.scryfall_id``, ``.finish``,
    ``.card`` — the same shape ``selectors.materialize`` yields — so the rest of
    the pipeline is input-source-agnostic."""
    result = parsers.parse_text(sys.stdin.read())
    idents = [{"set": e.set.lower(), "collector_number": e.collector_number}
              for e in result.entries if e.set and e.collector_number]
    if not idents:
        return []
    found, _ = scryfall.collection(idents)

    class _Row:
        __slots__ = ("scryfall_id", "finish", "card")

        def __init__(self, card):
            self.scryfall_id = card.get("id")
            # Default to the printing's cheaper-available finish for "this-print";
            # a pasted block rarely pins finish and the floor is finish-aware anyway.
            self.finish = "foil" if card.get("finishes") == ["foil"] else "nonfoil"
            self.card = card

    return [_Row(c) for c in found]


# ---------- price helpers ----------

def _this_print_usd(card: dict, finish: str) -> float | None:
    """The price of THIS printing in ``finish`` (local cards-row or live card dict).

    Materialized rows carry ``prices_usd`` / ``prices_usd_foil`` (local) OR a live
    ``prices`` dict (stdin path); support both."""
    if "prices" in card:  # live Scryfall card dict (stdin path)
        return card_floor.price(card, "usd_foil" if finish == "foil" else "usd")
    key = "prices_usd_foil" if finish == "foil" else "prices_usd"
    v = card.get(key)
    return float(v) if v is not None else None


def _resolve_family_codes(rows) -> set[str]:
    """Union of the resolved set families for every set the selection touches —
    the scope for ``--scope in-family``. Each distinct set code is resolved to its
    family (so ``set:fin`` folds in its 8 siblings); unresolvable codes fall back
    to themselves."""
    codes = {(r.card.get("set") or r.card.get("set_code") or "").lower()
             for r in rows}
    codes.discard("")
    fam: set[str] = set()
    for c in codes:
        try:
            fam |= {x.lower() for x in sets_mod.resolve(c).all_codes}
        except LookupError:
            fam.add(c)
    return fam


# ---------- rendering ----------

def _card_set(card: dict) -> str:
    return (card.get("set") or card.get("set_code") or "").lower()


def _print_url(card: dict) -> str:
    return scryfall_urls.scryfall_search_url(
        f"!\"{card.get('name') or ''}\"")


def _sort_key(entry: dict):
    return (entry["name"].lower(), entry["set"], util.cn_sort_key(entry["cn"]))


def _floor_cell(fl) -> str:
    """Render a collapsed Floor as ``$X.XX (SET #cn, finish)`` or ``—``."""
    if fl is None or fl.usd is None:
        return "—"
    loc = f"{(fl.set_code or '').upper()} #{fl.collector_number}" if fl.set_code else "?"
    return f"{util.fmt_usd(fl.usd)} ({loc}, {fl.finish})"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Cheapest-printing floor report for a set of cards.")
    ap.add_argument("selector", nargs="?", default=None,
                    help="A selector DSL string (set:/cards:/deck:/inventory/…). "
                         "Omit with --stdin to read a Moxfield-style block.")
    ap.add_argument("--stdin", action="store_true",
                    help="Read a pasted Moxfield-style block from stdin instead "
                         "of a selector.")
    ap.add_argument("--scope", choices=["anywhere", "in-family", "local"],
                    default="anywhere",
                    help="anywhere = live batched Scryfall floor (default); "
                         "in-family = local floor within the selection's set "
                         "family; local = local floor across all synced printings.")
    ap.add_argument("--finish", choices=["either", "preserve"], default="either",
                    help="either = cheaper finish, nonfoil-preferred (default); "
                         "preserve = separate nonfoil/foil floor columns.")
    # Cross-universe exception (CLAUDE.md § Price freshness): --scope anywhere
    # is inherently a live, cross-every-set lookup, so --refresh is a no-op
    # here — accepted only to keep the CLI surface uniform with local-first commands.
    ap.add_argument("--refresh", action="store_true",
                    help="(Prices are always fetched live for this command's "
                         "default --scope anywhere — it needs current "
                         "cross-set market data; --refresh is accepted for "
                         "CLI consistency and has no additional effect.)")
    args = ap.parse_args()

    if args.stdin == (args.selector is not None):
        print("error: pass exactly one of a selector argument OR --stdin",
              file=sys.stderr)
        return 2

    # 1. Resolve the selection to printing rows.
    try:
        rows = _rows_from_stdin() if args.stdin else _rows_from_selector(args.selector)
    except (selectors.SelectorParseError, LookupError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except scryfall.ScryfallError as e:
        print(f"error: scryfall lookup failed: {e}", file=sys.stderr)
        return 2

    if not rows:
        print("No cards in the selection.", file=sys.stderr)
        print("## Card floor — 0 cards\n\n(empty selection)")
        return 0

    oids = [oid for r in rows if (oid := r.card.get("oracle_id"))]

    # 2. Floor lookup at the chosen scope (the ONE engine call).
    try:
        if args.scope == "anywhere":
            floors = card_floor.anywhere_floors(oids, finish_mode=args.finish)
            scope_note = "cheapest anywhere (live)"
        else:
            fam = _resolve_family_codes(rows) if args.scope == "in-family" else None
            floors = card_floor.local_floors(oids, family_codes=fam,
                                             finish_mode=args.finish)
            scope_note = ("cheapest in-family (local)" if args.scope == "in-family"
                          else "cheapest local")
    except scryfall.ScryfallError as e:
        print(f"error: scryfall lookup failed: {e}", file=sys.stderr)
        return 2

    # 3. Build one entry per printing (dedupe identical printing+finish rows).
    entries: list[dict] = []
    seen: set[tuple] = set()
    for r in rows:
        card = r.card
        oid = card.get("oracle_id")
        key = (r.scryfall_id, r.finish)
        if key in seen:
            continue
        seen.add(key)
        fl = floors.get(oid)
        entry = {
            "name": card.get("name") or "?",
            "oracle_id": oid,
            "set": _card_set(card),
            "cn": card.get("collector_number") or "",
            "finish": r.finish,
            "this_print_usd": _this_print_usd(card, r.finish),
            "url": _print_url(card),
        }
        if args.finish == "preserve":
            entry["floor_nonfoil"] = fl.nonfoil if fl else None
            entry["floor_foil"] = fl.foil if fl else None
        else:
            entry["floor"] = fl if fl else None
        entries.append(entry)
    entries.sort(key=_sort_key)

    # 4. Markdown (chat relay) + stderr summary.
    priced = sum(1 for e in entries if e.get("this_print_usd") is not None)
    print(f"Reported {len(entries)} printing(s); {priced} with a local this-print "
          f"price. Scope: {scope_note}; finish: {args.finish}.", file=sys.stderr)

    lines = [f"## Card floor — {len(entries)} printings · {scope_note}", ""]
    if args.finish == "preserve":
        lines += ["| Card | CN | This print ($) | Floor nonfoil | Floor foil |",
                  "|---|---|---:|---|---|"]
        for e in entries:
            safe = f"{e['name']} ({e['set'].upper()}) {e['cn']}".replace("|", "\\|")
            lines.append(
                f"| [{safe}]({e['url']}) | {e['set'].upper()} #{e['cn']} | "
                f"{util.fmt_usd(e['this_print_usd'])} | "
                f"{_floor_cell(e['floor_nonfoil'])} | {_floor_cell(e['floor_foil'])} |")
    else:
        lines += ["| Card | CN | This print ($) | Cheapest floor (set/finish) |",
                  "|---|---|---:|---|"]
        for e in entries:
            safe = f"{e['name']} ({e['set'].upper()}) {e['cn']}".replace("|", "\\|")
            lines.append(
                f"| [{safe}]({e['url']}) | {e['set'].upper()} #{e['cn']} | "
                f"{util.fmt_usd(e['this_print_usd'])} | {_floor_cell(e['floor'])} |")
    print("\n".join(lines))

    # 5. Artifacts (JSON + XLSX).
    out_dir = util.output_dir(_OUTPUT_TYPE, "reports")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base = f"card-floor-{args.scope}-{args.finish}-{stamp}"
    _write_json(entries, args, scope_note, out_dir / f"{base}.json")
    _write_xlsx(entries, args, out_dir / f"{base}.xlsx")
    print(f"Wrote {out_dir / (base + '.json')} and {base}.xlsx", file=sys.stderr)
    return 0


# ---------- artifacts ----------

def _floor_payload(fl) -> dict | None:
    if fl is None or fl.usd is None:
        return None
    return {"usd": fl.usd, "finish": fl.finish,
            "set_code": fl.set_code, "collector_number": fl.collector_number}


def _write_json(entries, args, scope_note: str, out_path: Path) -> None:
    payload_rows = []
    for e in entries:
        row = {k: e[k] for k in ("name", "oracle_id", "set", "cn", "finish",
                                 "this_print_usd")}
        if args.finish == "preserve":
            row["floor_nonfoil"] = _floor_payload(e["floor_nonfoil"])
            row["floor_foil"] = _floor_payload(e["floor_foil"])
        else:
            row["floor"] = _floor_payload(e["floor"])
        payload_rows.append(row)
    payload = {
        "scope": args.scope,
        "finish_mode": args.finish,
        "scope_note": scope_note,
        "generated_at": datetime.now(UTC).isoformat(),
        "rows": payload_rows,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_xlsx(entries, args, out_path: Path) -> None:
    if args.finish == "preserve":
        headers = ["card", "set", "cn", "finish", "this_print_usd",
                   "floor_nonfoil_usd", "floor_nonfoil_loc",
                   "floor_foil_usd", "floor_foil_loc", "oracle_id"]
        cell_rows = []
        for e in entries:
            nf, ff = e["floor_nonfoil"], e["floor_foil"]
            cell_rows.append([
                e["name"], e["set"].upper(), e["cn"], e["finish"], e["this_print_usd"],
                nf.usd if nf else None, _loc(nf),
                ff.usd if ff else None, _loc(ff), e["oracle_id"]])
        money_cols = (5, 6, 8)
        widths = {1: 34, 2: 6, 3: 7, 4: 8, 5: 13, 6: 13, 7: 16, 8: 11, 9: 16, 10: 38}
    else:
        headers = ["card", "set", "cn", "finish", "this_print_usd",
                   "floor_usd", "floor_set", "floor_cn", "floor_finish", "oracle_id"]
        cell_rows = []
        for e in entries:
            fl = e["floor"]
            cell_rows.append([
                e["name"], e["set"].upper(), e["cn"], e["finish"], e["this_print_usd"],
                fl.usd if fl else None,
                (fl.set_code or "").upper() if fl else None,
                fl.collector_number if fl else None,
                fl.finish if fl else None, e["oracle_id"]])
        money_cols = (5, 6)
        widths = {1: 34, 2: 6, 3: 7, 4: 8, 5: 13, 6: 11, 7: 9, 8: 9, 9: 11, 10: 38}
    spec = exports.xlsx.SheetSpec(
        title="card-floor", headers=headers, rows=cell_rows,
        money_cols=money_cols, text_cols=(3,), widths=widths)
    exports.xlsx.write_workbook(out_path, [spec])


def _loc(fl) -> str | None:
    if fl is None or fl.set_code is None:
        return None
    return f"{fl.set_code.upper()} #{fl.collector_number}"


if __name__ == "__main__":
    sys.exit(main())
