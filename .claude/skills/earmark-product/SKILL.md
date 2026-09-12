---
name: earmark-product
description: Save a sealed MTG product from a storefront URL onto a cross-store watchlist ("earmarks"). Claude fetches the store page, extracts the product name + asking price, resolves it to an MTGJSON identity, and records it via `mm earmark add`. The same product on multiple storefronts collates to one product with several links. Triggers: "/earmark-product <url>", "earmark this product", "add this to my watchlist", "save this sealed product link", "track this product's price", "watch this on <store>".
---

# earmark-product

Thin wrapper: Claude turns a **store URL** into a validated earmark row. The DB
write is done by the deterministic CLI `mm earmark add`; the only thing Claude
does is the one non-deterministic step the script can't — fetch the page and
read off the product name + asking price. **No price math here** (that's the
review's job); this skill just captures the link + the asking-price snapshot.

## When to use

- The user pastes a **storefront product URL** for a sealed product (TCGplayer,
  Card Kingdom, Cash Cards Unlimited, ManaPool, a Shopify store, …) and wants it
  tracked.
- "Earmark this", "add to my watchlist", "watch this product's price".

**Don't** use for:
- Valuing a product right now — that's [[sealed-value]] / [[construct-value]].
- A decklist or single card URL — earmarks are for *sealed products* only.
- Reviewing what's saved — that's [[review-earmarked-products]].

## Recipe (what Claude does)

1. **Resolve the store URL → MTGJSON identity** via the shared recipe in
   [`_shared/resolve-storefront-product.md`](../_shared/resolve-storefront-product.md):
   WebFetch (or the eBay/screenshot fallback) → read title + asking price →
   propose `set_code` + product-name substring → validate with
   `uv run mm resolve-product <set_code> --name "<substr>"`. Keep the asking
   price + currency the page showed.
2. **Call the CLI** with the resolved identity:
   ```bash
   uv run mm earmark add <set_code> \
     --name "<MTGJSON product name or unique substring>" \
     --url "<the store URL>" \
     --price <asking price> [--currency USD] [--store "<label>"] [--notes "…"]
   ```
   `add` re-validates via the same `sealed.identify_product` checkpoint (exit 2 on
   an unresolved name — refine `--name` from the candidate list). `--store`
   defaults to the URL host. Re-run `add` with a new `--url` to collate another
   storefront under the same product.
3. **Relay** the CLI's one-line result (inserted/updated product + link).

## Not to be confused with

- [[review-earmarked-products]] — prints the deal table (live market vs asking)
  for everything earmarked.
- [[sealed-value]] / [[construct-value]] — one-off valuation of a product now.

## Cross-references

- [`_shared/resolve-storefront-product.md`](../_shared/resolve-storefront-product.md)
  — the shared URL→identity recipe (also used by [[sealed-value]]).
- `mm resolve-product` / `mm earmark add|list|rm-link|rm-product` — the CLI (`cli.py`).
- `src/magic_manager/earmarks.py` — the CRUD module (V12 `earmarked_products` +
  `earmark_links` tables). Stores only the non-derivable asking-price snapshot.
- `sealed.identify_product` — the MTGJSON-identity validator the `add` command
  enforces. `mtgjson.sealed_products(code)` — the product-name source.
