"""Value MANY sealed products / Secret Lair drops in ONE combined table.

The batch companion to `sealed_value.py`: instead of one product per run (and one
artifact each), read a JSON list of ALREADY-RESOLVED items and emit a single
comparison table — one row per product: asking? / market / intrinsic / deal-delta
— plus one combined artifact. Built for "value my cart / this list of links / my
open browser tabs": the agent resolves each URL to an identity (via the shared
`resolve-storefront-product` recipe / `mm resolve-product`), then feeds the list
here.

Reuses the exact single-product engine — `sealed.identify_product` +
`build_product_tree` + `aggregate` for sealed products, and `sld.identify_drop` +
`value_drop` for Secret Lair drops — so every row matches its standalone
`sealed_value.py` run. Market provider assembly is shared via
`sealed.make_market_provider`.

Input (stdin or --in <file>): a JSON array of items, each either
  {"set_code": "afc", "product": "Commander Deck Display", "asking_price": 434.99, "url": "..."}
  {"set_code": "sld", "drop": "Far Out, Man", "asking_price": 29.99}
`asking_price`/`url` are optional (asking enables the deal-delta column).

Usage:
    uv run python scripts/sealed_value_batch.py --in items.json --market compare
    echo '[{"set_code":"afc","product":"Commander Deck Display"}]' | uv run python scripts/sealed_value_batch.py

Exit codes:
    0 — table rendered (individual items that fail to resolve are shown as errors, not fatal)
    2 — bad invocation / unparseable input / empty list
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import mtgjson, scryfall, sealed, sets, sld, util  # noqa: E402

QUERIES_DIR = ROOT / "queries"


def _fmt(v) -> str:
    return util.fmt_usd(v)


@dataclass
class BatchRow:
    label: str
    kind: str                     # "sealed" | "sld" | "error"
    asking: float | None
    market: float | None          # sealed: market_whole; sld: own-nonfoil total
    intrinsic: float | None       # sealed: intrinsic; sld: floor-nonfoil (cheapest to build)
    note: str = ""                # error message or a short qualifier


def _value_sealed(item: dict, market_provider) -> BatchRow:
    code = item["set_code"].lower()
    substr = item.get("product")
    label = item.get("label") or f"{code.upper()} {substr or ''}".strip()
    try:
        product = sealed.identify_product(code, substr)
    except LookupError as e:
        return BatchRow(label, "error", item.get("asking_price"), None, None, str(e))
    # Sync referenced sets (best-effort) so intrinsic prices resolve.
    scout = sealed.build_product_tree(code, product)
    try:
        sets.ensure_priced(sealed.referenced_set_codes(scout), refresh_stale=False, log=None)
    except Exception:  # noqa: BLE001 — pricing degrades, never fatal in a batch
        pass
    node = sealed.build_product_tree(code, product, market_provider=market_provider)
    totals = sealed.aggregate(node)
    return BatchRow(
        label=node.name, kind="sealed", asking=item.get("asking_price"),
        market=totals.market_whole, intrinsic=totals.intrinsic,
        note="" if totals.coverage >= 0.999 else f"coverage {totals.coverage:.0%}",
    )


def _value_sld(item: dict) -> BatchRow:
    substr = item.get("drop") or item.get("product")
    label = item.get("label") or f"SLD {substr or ''}".strip()
    try:
        drop = sld.identify_drop(substr or "")
        v = sld.value_drop(drop, floors=True)
    except LookupError as e:
        return BatchRow(label, "error", item.get("asking_price"), None, None, str(e))
    except (mtgjson.MtgJsonError, scryfall.ScryfallError) as e:
        return BatchRow(label, "error", item.get("asking_price"), None, None, str(e))
    # For an SLD drop: "market" = its own-printing nonfoil total; "intrinsic" =
    # the cheapest-anywhere nonfoil floor (cheapest way to get the cards).
    return BatchRow(
        label=v.name, kind="sld", asking=item.get("asking_price"),
        market=round(v.nonfoil_total, 2), intrinsic=round(v.nf_floor_total, 2),
        note="live Scryfall; market=own-nonfoil, intrinsic=nonfoil floor",
    )


def value_item(item: dict, market_provider) -> BatchRow:
    """Route one input item to the sealed or SLD engine."""
    if (item.get("set_code") or "").lower() == "sld":
        return _value_sld(item)
    return _value_sealed(item, market_provider)


def _render(rows: list[BatchRow], *, show_asking: bool) -> list[str]:
    """One combined markdown table. Deal-delta = market − asking (sealed) so a
    good deal (market above asking) is positive; only shown when asking present."""
    lines = ["| Product | Kind | Market | Intrinsic |"]
    sep = "|---|---|---:|---:|"
    if show_asking:
        lines = ["| Product | Kind | Asking | Market | Intrinsic | Deal Δ |"]
        sep = "|---|---|---:|---:|---:|---:|"
    lines.append(sep)
    for r in rows:
        name = r.label.replace("|", "\\|")[:52]
        if r.kind == "error":
            cells = (f"| {name} | error | " + ("— | " if show_asking else "")
                     + "— | — |" + (" — |" if show_asking else ""))
            lines.append(cells)
            continue
        if show_asking:
            delta = (r.market - r.asking) if (r.market is not None and r.asking is not None) else None
            dcell = _fmt(round(delta, 2)) if delta is not None else "—"
            lines.append(f"| {name} | {r.kind} | {_fmt(r.asking)} | {_fmt(r.market)} | "
                         f"{_fmt(r.intrinsic)} | {dcell} |")
        else:
            lines.append(f"| {name} | {r.kind} | {_fmt(r.market)} | {_fmt(r.intrinsic)} |")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Value many sealed products / SLD drops in one combined table.")
    ap.add_argument("--in", dest="infile", type=Path, default=None,
                    help="JSON array of items (default: read stdin).")
    ap.add_argument("--market", choices=["null", "tcgcsv", "tcgapi", "manapool", "chain", "compare"],
                    default="chain", help="Market source for sealed products (default: chain).")
    ap.add_argument("--format", choices=["txt", "none"], default="txt",
                    help="Also write a combined txt artifact (default: txt).")
    ap.add_argument("--out-dir", type=Path, default=QUERIES_DIR)
    args = ap.parse_args()

    raw = args.infile.read_text() if args.infile else sys.stdin.read()
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"error: input is not valid JSON: {e}", file=sys.stderr)
        return 2
    if not isinstance(items, list) or not items:
        print("error: input must be a non-empty JSON array of items.", file=sys.stderr)
        return 2

    market_provider = sealed.make_market_provider(args.market)
    rows = [value_item(it, market_provider) for it in items]
    show_asking = any(r.asking is not None for r in rows)

    meta = mtgjson.meta()
    header = f"## Sealed value — batch of {len(rows)}   [prices as of {meta.get('date', '?')}]"
    table = _render(rows, show_asking=show_asking)
    print(header)
    print()
    for line in table:
        print(line)
    # Surface per-row notes/errors below the table.
    notes = [(r.label, r.note) for r in rows if r.note]
    if notes:
        print()
        for label, note in notes:
            print(f"  · {label}: {note}")

    if args.format == "txt":
        args.out_dir.mkdir(parents=True, exist_ok=True)
        from datetime import UTC, datetime
        ts = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
        p = args.out_dir / f"sealed-value-batch-{ts}.txt"
        body = [header, ""] + table
        if notes:
            body += [""] + [f"  · {label}: {note}" for label, note in notes]
        p.write_text("\n".join(body) + "\n", encoding="utf-8")
        print(f"\n  → {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
