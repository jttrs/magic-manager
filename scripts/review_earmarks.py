"""Deterministic review of earmarked sealed products and single cards (a watchlist deal table).

Reads the earmark watchlist (`earmarks.earmark_list`) and, for each product,
**recomputes** its live market + intrinsic value by REUSING the sealed engine
(`sealed.build_product_tree` / `aggregate`, the same path `sealed_value.py`
drives) — the DB stores only the non-derivable asking-price snapshot, never
derived values. Single cards are priced from the local `cards` table
(`sets.priced_map`, local-first) at the EXACT printing's finish — never the oracle
floor. Emits a markdown deal table (product names hyperlinked to their
storefronts, collated across stores) + a txt/xlsx to `output/earmarks-review/reports/`.

Columns: product (+ per-store links & asking prices), set, category, release,
best asking $, live market $, live intrinsic $, deal delta (market − best
asking), and the age of the asking-price snapshot. Sorted by deal delta desc
(best deals first).

Usage:
    uv run python scripts/review_earmarks.py
    uv run python scripts/review_earmarks.py --market compare
    uv run python scripts/review_earmarks.py --format txt

Exit codes:
    0 — report written (or nothing earmarked)
    2 — unexpected error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import earmarks, exports, sealed, sets, sld, util, valuation  # noqa: E402


def _fmt(v) -> str:
    return util.fmt_usd(v)


def _age_days(captured_at: str, today: str) -> int | None:
    """Whole days between an ISO ``captured_at`` and an ISO ``today`` (both
    ``YYYY-MM-DD…``). ``None`` if either is unparseable. Date math only — no
    ``datetime.now()`` in the script (today is passed in, keeping it
    deterministic/testable)."""
    from datetime import date
    try:
        c = date.fromisoformat(captured_at[:10])
        t = date.fromisoformat(today[:10])
    except (ValueError, TypeError):
        return None
    return (t - c).days


# ---------- per-product live valuation (reuses the sealed engine) ----------

def _value_product(set_code: str, product_name: str, market_provider,
                   *, edition: str | None = None,
                   market_name: str = "tcgcsv", refresh_stale: bool = False) -> dict:
    """Recompute market + intrinsic for one earmarked product.

    Dispatches on ``set_code`` exactly like the other sealed-value tools:

    - **Secret Lair drops** (``sld``) are MTGJSON *DeckList* entries, NOT walkable
      ``sealedProduct`` trees — the tree engine would price them by the shared
      ``dnd-50th-anniversary`` booster EV and report an identical (wrong) figure
      for every drop. Route them through ``valuation.value_sld_drop`` instead:
      market ← the drop's own sealedProduct price (``sealed_market``); intrinsic ←
      Σ the drop's exact Secret Lair printings (``exact_singles``). The stored name
      is the sealedProduct name (with a ``Secret Lair x`` scaffold + finish marker),
      so strip it back to a drop substring for ``sld.identify_drop``.
    - **Everything else** takes the sealed tree engine: identify → scout-build to
      discover referenced sets → sync missing+stale → rebuild with the provider →
      aggregate (mirrors ``sealed_value.py``).

    Returns ``{"market", "intrinsic", "error"}``.
    """
    if set_code.lower() == "sld":
        drop_substr = sld.strip_finish_marker(sld.normalize_name(product_name))
        # Prefer the stored edition (subtype, set by the unified resolver);
        # fall back to sniffing the name for pre-unification earmark rows.
        ed = edition if edition in ("foil", "nonfoil") else sld.edition_from_name(product_name)
        try:
            v = valuation.value_sld_drop(drop_substr, market=market_name, edition=ed)
        except LookupError as e:
            return {"market": None, "intrinsic": None, "error": str(e)}
        return {"market": v.sealed_market, "intrinsic": v.exact_singles, "error": None}

    try:
        product = sealed.identify_product(set_code, product_name)
    except LookupError as e:
        return {"market": None, "intrinsic": None, "error": str(e)}

    # Ensure referenced sets have current prices (missing always; stale only
    # with --refresh — local-first by default). referenced_set_codes folds in
    # cross-set booster sourceSetCodes.
    scout = sealed.build_product_tree(set_code, product)
    sets.ensure_priced(sealed.referenced_set_codes(scout),
                       refresh_stale=refresh_stale,
                       log=lambda m: print(m, file=sys.stderr))

    node = sealed.build_product_tree(set_code, product, market_provider=market_provider)
    totals = sealed.aggregate(node)
    return {"market": totals.market_whole, "intrinsic": totals.intrinsic, "error": None}


def _value_singles(products, *, refresh_stale: bool = False) -> dict[int, dict]:
    """Price every earmarked single, keyed by ``product_id``, with ONE local-first
    ``sets.priced_map`` call. Market is the EXACT printing's finish price
    (``usd_foil`` for foil, else ``usd``) — never the oracle floor; no intrinsic."""
    singles = [p for p in products if p.kind == "single"]
    if not singles:
        return {}
    pm = sets.priced_map([p.scryfall_id for p in singles if p.scryfall_id],
                         refresh=refresh_stale,
                         warn=lambda codes: print(
                             f"warning: stale prices for {', '.join(codes)} (--refresh to re-sync)",
                             file=sys.stderr),
                         log=lambda m: print(m, file=sys.stderr))
    out: dict[int, dict] = {}
    for p in singles:
        prices = pm.get(p.scryfall_id) or {}
        market = prices.get("usd_foil" if p.finish == "foil" else "usd")
        err = None if market is not None else \
            f"no local price for {p.set_code.upper()} #{p.collector_number} ({p.finish})"
        out[p.product_id] = {"market": market, "intrinsic": None, "error": err}
    return out


# ---------- rendering ----------

def _product_cell(p) -> str:
    """The Product column: name linked to its cheapest store, plus a parenthetical
    list of the other stores with their asking prices."""
    if not p.links:
        return p.product_name
    # links are pre-sorted cheapest-first by earmark_list
    primary = p.links[0]
    cell = f"[{p.product_name}]({primary.store_url})"
    store_bits = []
    for l in p.links:
        px = _fmt(l.asking_price) if l.asking_price is not None else "—"
        store_bits.append(f"[{l.store_name or 'store'}]({l.store_url}) {px}")
    return cell + "<br>" + " · ".join(store_bits)


def _build_rows(products, market_provider, today: str,
                *, market_name: str = "tcgcsv", refresh_stale: bool = False) -> list[dict]:
    """Value every product and assemble sortable row dicts."""
    rows = []
    single_vals = _value_singles(products, refresh_stale=refresh_stale)
    for p in products:
        if p.kind == "single":
            val = single_vals[p.product_id]
        else:
            val = _value_product(p.set_code, p.product_name, market_provider,
                                 edition=p.subtype,
                                 market_name=market_name, refresh_stale=refresh_stale)
        best = p.best_asking
        market = val["market"]
        delta = (market - best) if (market is not None and best is not None) else None
        ages = [d for d in (_age_days(l.captured_at, today) for l in p.links) if d is not None]
        rows.append({
            "product": p,
            "market": market,
            "intrinsic": val["intrinsic"],
            "best_asking": best,
            "delta": delta,
            "age": min(ages) if ages else None,
            "error": val["error"],
        })
    # Best deals first: rows with a delta sort desc; None-delta rows sink to the
    # bottom (ordered by name for stability).
    rows.sort(key=lambda r: (r["delta"] is None,
                             -(r["delta"] if r["delta"] is not None else 0.0),
                             r["product"].product_name))
    return rows


def _render_lines(rows, today: str) -> list[str]:
    lines = [f"## Earmarked products — deal review   [as of {today}]", ""]
    lines.append("| Product / stores | Set | Category | Release | Best ask | Market | Intrinsic | Deal Δ | Ask age |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        p = r["product"]
        delta = r["delta"]
        delta_cell = _fmt(delta) if delta is not None else "—"
        if delta is not None and delta > 0:
            delta_cell = f"**+{delta_cell.lstrip('$')}**" if delta_cell.startswith("$") else delta_cell
        age = f"{r['age']}d" if r["age"] is not None else "—"
        lines.append(
            f"| {_product_cell(p)} | {p.set_code.upper()} | {p.category or ('single' if p.kind == 'single' else '—')} | "
            f"{p.release_date or '—'} | {_fmt(r['best_asking'])} | {_fmt(r['market'])} | "
            f"{_fmt(r['intrinsic'])} | {delta_cell} | {age} |"
        )
    lines.append("")
    n = len(rows)
    good = sum(1 for r in rows if r["delta"] is not None and r["delta"] > 0)
    lines.append(f"TOTALS  {n} product(s) earmarked   {good} priced below live market "
                 f"(positive Deal Δ = market exceeds asking = a deal)")
    for r in rows:
        if r["error"]:
            lines.append(f"  · {r['product'].product_name}: {r['error']}")
    return lines


# ---------- XLSX artifact ----------

def _write_xlsx(rows, today: str, out_path: Path) -> None:
    headers = ["product_name", "set_code", "category", "release_date", "best_asking",
               "market", "intrinsic", "deal_delta", "ask_age_days", "n_stores",
               "store_urls", "kind"]
    cell_rows = []
    for r in rows:
        p = r["product"]
        cell_rows.append([
            p.product_name, p.set_code.upper(), p.category, p.release_date,
            r["best_asking"], r["market"], r["intrinsic"], r["delta"], r["age"],
            len(p.links), " | ".join(l.store_url for l in p.links), p.kind,
        ])
    earmarks_sheet = exports.xlsx.SheetSpec(
        title="earmarks", headers=headers, rows=cell_rows,
        money_cols=(5, 6, 7, 8), widths={1: 42, 3: 14, 11: 60},
    )
    exports.xlsx.write_workbook(out_path, [earmarks_sheet])


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Review earmarked sealed products and single cards: live market/intrinsic vs asking price.")
    ap.add_argument("--market", choices=["null", "tcgcsv", "tcgapi", "chain", "compare"],
                    default="tcgcsv", help="Live market price source (default: tcgcsv).")
    ap.add_argument("--format", choices=["txt", "xlsx", "all"], default="all",
                    help="Artifact(s) to write (default: all).")
    util.add_price_refresh_arg(ap)
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="Override output dir (default: output/earmarks-review/reports/).")
    args = ap.parse_args()
    if args.out_dir is None:
        args.out_dir = util.output_dir("earmarks-review", "reports")

    products = earmarks.earmark_list()
    if not products:
        print("(no earmarked products — use /earmark-product <store-URL> to add one)")
        return 0

    from datetime import UTC, datetime
    now = datetime.now(UTC)
    today = now.strftime("%Y-%m-%d")

    market_provider = sealed.make_market_provider(args.market)
    rows = _build_rows(products, market_provider, today,
                       market_name=args.market, refresh_stale=args.refresh)
    lines = _render_lines(rows, today)
    print("\n" + "\n".join(lines))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    ts = now.strftime("%Y-%m-%d-%H%M%S")
    written: list[Path] = []
    if args.format in ("txt", "all"):
        p = args.out_dir / f"earmarks-review-{ts}.txt"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(p)
    if args.format in ("xlsx", "all"):
        p = args.out_dir / f"earmarks-review-{ts}.xlsx"
        _write_xlsx(rows, today, p)
        written.append(p)
    for p in written:
        print(f"  → {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
