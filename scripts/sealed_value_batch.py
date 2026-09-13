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

from magic_manager import mtgjson, scryfall, sealed, sld, util, valuation  # noqa: E402

QUERIES_DIR = ROOT / "queries"


def _fmt(v) -> str:
    return util.fmt_usd(v)


@dataclass
class BatchRow:
    """One row = one product's unified 4-column valuation (or an error)."""
    label: str
    kind: str                     # "sealed" | "sld" | "error"
    valuation: "sealed.ProductValuation | None" = None
    note: str = ""                # error message
    url: str | None = None        # the item's storefront URL (name links to it)


def _value_sealed(item: dict, market: str, floors_cache: dict) -> BatchRow:
    code = item["set_code"].lower()
    substr = item.get("product")
    label = item.get("label") or f"{code.upper()} {substr or ''}".strip()
    url = item.get("url")
    try:
        pv = valuation.value_sealed_product(
            code, substr, listing=item.get("asking_price"), market=market,
            refresh_stale=False, floors_cache=floors_cache)
    except LookupError as e:
        return BatchRow(label, "error", note=str(e), url=url)
    return BatchRow(pv.label, "sealed", pv, url=url)


def _value_sld(item: dict, market: str, floors_cache: dict) -> BatchRow:
    substr = item.get("drop") or item.get("product")
    label = item.get("label") or f"SLD {substr or ''}".strip()
    url = item.get("url")
    edition = "foil" if str(item.get("edition", "")).lower() in ("foil", "traditional foil",
                                                                 "rainbow foil") else "auto"
    try:
        pv = valuation.value_sld_drop(
            substr or "", listing=item.get("asking_price"), market=market,
            edition=edition, _floors_cache=floors_cache)
    except LookupError as e:
        return BatchRow(label, "error", note=str(e), url=url)
    except (mtgjson.MtgJsonError, scryfall.ScryfallError) as e:
        return BatchRow(label, "error", note=str(e), url=url)
    return BatchRow(pv.label, "sld", pv, url=url)


def value_item(item: dict, market: str, floors_cache: dict) -> BatchRow:
    """Route one input item to the sealed or SLD 4-column producer."""
    if (item.get("set_code") or "").lower() == "sld":
        return _value_sld(item, market, floors_cache)
    return _value_sealed(item, market, floors_cache)


# The unified 4-column schema (listing / sealed market / exact singles / floor),
# with an in-cell delta vs listing in columns 2-4 (util.fmt_delta_cell).
def _md_link(label: str, url: str | None) -> str:
    """Markdown link `[label](url)` when a URL is present, else the bare label.
    Pipes/brackets in the label are escaped so the table cell stays intact."""
    safe = label.replace("|", "\\|").replace("[", "(").replace("]", ")")[:50]
    return f"[{safe}]({url})" if url else safe


def _render(rows: list[BatchRow]) -> list[str]:
    lines = ["| Product | Finish | Listing | Sealed mkt | Exact singles | Floor singles |",
             "|---|---|---:|---:|---:|---:|"]
    for r in rows:
        name = _md_link(r.label, r.url)
        if r.kind == "error" or r.valuation is None:
            lines.append(f"| {name} | — | — | — | — | — |")
            continue
        pv = r.valuation
        # Explicit finish per row (esp. Secret Lairs, which ship foil AND nonfoil
        # editions at very different prices). Sealed products are nonfoil by default.
        finish = pv.finish or "nonfoil"
        listing = _fmt(pv.listing)
        # Booster-only products: cols 3/4 are the booster EV (labeled), not singles.
        c3 = util.fmt_delta_cell(pv.exact_singles, pv.listing)
        c4 = util.fmt_delta_cell(pv.floor_singles, pv.listing)
        if pv.booster_only:
            c3 = f"{c3} EV"
            c4 = f"{c4} EV"
        lines.append(f"| {name} | {finish} | {listing} | "
                     f"{util.fmt_delta_cell(pv.sealed_market, pv.listing)} | {c3} | {c4} |")
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

    # Shared floor cache across all items (a card recurring across products is
    # priced once); market is a mode string passed through to the producers.
    floors_cache: dict = {}
    rows = [value_item(it, args.market, floors_cache) for it in items]

    meta = mtgjson.meta()
    header = f"## Sealed value — batch of {len(rows)}   [prices as of {meta.get('date', '?')}]"
    table = _render(rows)
    print(header)
    print()
    for line in table:
        print(line)
    print()
    print("*Cols: Listing = asking price · Sealed mkt = wider secondary market · "
          "Exact singles = the product's own printings · Floor singles = cheapest "
          "printing of each card anywhere. (±$) in cols 2-4 = value − listing.*")
    # Surface per-row notes/errors below the table.
    notes = [(r.label, r.note or (r.valuation.note if r.valuation else "")) for r in rows]
    notes = [(lbl, n) for lbl, n in notes if n]
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
