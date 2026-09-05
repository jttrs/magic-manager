---
name: review-earmarked-products
description: Print a deterministic, well-formatted deal table of all earmarked sealed products — each product's storefront links + snapshot asking price alongside a LIVE-recomputed market and intrinsic (card) value, with a "deal delta" (market − best asking) so good deals sort to the top. Product names are hyperlinked to their store pages; products earmarked on multiple storefronts collate to one row. Triggers: "/review-earmarked-products", "show my earmarked products", "review my watchlist", "which earmarked products are good deals", "what's on my sealed watchlist", "are any of my earmarks worth buying".
---

# review-earmarked-products

Purely mechanical wrapper: invoke the deterministic script and relay its output.
The script is the single source of truth — it reads the earmark watchlist and
**recomputes** each product's market + intrinsic value live by reusing the
`sealed` engine (the same one behind [[sealed-value]]), so nothing derived is
ever stale in the DB. No arithmetic or valuation happens in this skill.

## When to use

- "Review my watchlist" / "show my earmarked products" / "which earmarks are
  good deals right now?"

**Don't** use for:
- Adding a product to the watchlist — that's [[earmark-product]].
- Valuing a single product not on the watchlist — [[sealed-value]] /
  [[construct-value]].

## The canonical recipe

```bash
uv run python scripts/review_earmarks.py                 # txt + xlsx (default), tcgcsv market
uv run python scripts/review_earmarks.py --market compare  # show tcgcsv vs tcgapi sourcing
uv run python scripts/review_earmarks.py --format txt
```

Relay the whole markdown table + the `TOTALS` line, and hand over the `queries/`
artifact paths. If the watchlist is empty the script says so (exit 0) — suggest
[[earmark-product]].

## What it computes

Per earmarked product (one row, links collated):
- **best asking** — cheapest asking-price snapshot across its storefront links
  (the non-derivable fact stored at earmark time).
- **market** / **intrinsic** — recomputed LIVE via `sealed.build_product_tree` +
  `aggregate` (whole-product market price + summed card value), after syncing any
  referenced sets. Reuses `sealed.make_market_provider` for the `--market` source.
- **deal delta** = market − best asking (positive = the sealed market exceeds
  what the store is asking = a deal). Rows sort by delta desc.
- **ask age** — days since the asking price was captured (a staleness signal;
  re-run [[earmark-product]] on the URL to refresh it).

## Output shape

Two artifacts in `queries/` (ephemeral; pruned by [[cleanup-queries]]):
- `earmarks-review-<ts>.txt` — the markdown deal table, paste-ready.
- `earmarks-review-<ts>.xlsx` — one row per product (name/set/category/release/
  best_asking/market/intrinsic/deal_delta/ask_age/n_stores/store_urls).

Stdout: `## Earmarked products — deal review` + the table + a `TOTALS` line.

## Determinism guarantees

- The DB stores only non-derivable facts (store URL + asking-price snapshot).
  Market/intrinsic are recomputed at review time — one source of price truth.
- Prices come from the local `cards` table (script syncs referenced sets first)
  and the chosen market provider; `--market null` is fully offline.
- No `Date.now()` in row data — "today" is captured once for the age column and
  the filename timestamp only.

## Cross-references

- `scripts/review_earmarks.py` — the script this skill drives.
- `src/magic_manager/earmarks.py` (`earmark_list`), `sealed.build_product_tree` /
  `aggregate` / `make_market_provider`, `sets.sync` / `unsynced_set_codes`.
- [[earmark-product]] — the writer half of this pair.
- [[sealed-value]] / [[construct-value]] — deeper one-off valuation of a product.
