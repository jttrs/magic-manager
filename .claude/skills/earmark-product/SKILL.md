---
name: earmark-product
description: Save a sealed MTG product (or a single card printing) from a storefront URL onto a cross-store watchlist ("earmarks"). Claude fetches the store page, extracts the product name + asking price, resolves it to an MTGJSON identity, and records it via `mm earmark add`. The same product on multiple storefronts collates to one product with several links. Triggers: "/earmark-product <url>", "earmark this product", "add this to my watchlist", "save this sealed product link", "track this product's price", "watch this on <store>", "earmark this card", "watch this single".
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
- A decklist URL — earmarks are for sealed products and single cards only.
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
   `add` re-validates via the **same `_resolve_identity` checkpoint** as
   `mm resolve-product` (exit 2 on an unresolved name — refine `--name` from the
   candidate list). For a normal set that's `sealed.identify_product`; for **`sld`**
   it's `sld.identify_drop` (the engine that also PRICES the drop), with the finish
   (foil/nonfoil, inferred from the name) baked into the canonical name +
   `subtype`, so a drop's two editions collate as distinct rows. `--store` defaults
   to the URL host. Re-run `add` with a new `--url` to collate another storefront
   under the same product.
3. **Relay** the CLI's one-line result (inserted/updated product + link).

## Single cards

A single-card listing (a store page for one printing) is earmarked with `--cn` and
the listing's exact finish:

```bash
uv run mm earmark add <set_code> --cn <collector number> [--finish foil] \
  --name "<card name from the store title>" --url "<the store URL>" --price <asking price>
```

- **Tripwire: store titles mislabel set/CN.** Always pass `--name` so the CLI can
  cross-check the card (it also accepts the front face or flavor name). On a
  refusal (exit 2, "the store's set/CN may be wrong"), do NOT force it — find the
  real printing by name + price + image, then retry with the right set/CN.
- `--finish` must be the listing's exact finish (`nonfoil` default, or `foil`);
  the review prices that finish of that exact printing.
- `sld` + `--cn` is a Secret Lair *single*, not a drop.
- Validate first with `uv run mm resolve-product <set_code> --cn <CN> --name "<name>"`
  if unsure; `--name` is optional for singles but strongly recommended.

## Not to be confused with

- [[review-earmarked-products]] — prints the deal table (live market vs asking)
  for everything earmarked.
- [[sealed-value]] / [[construct-value]] — one-off valuation of a product now.

## Cross-references

- [`_shared/resolve-storefront-product.md`](../_shared/resolve-storefront-product.md)
  — the shared URL→identity recipe (also used by [[sealed-value]]).
- `mm resolve-product` / `mm earmark add|list|rm-link|rm-product` — the CLI (`cli.py`).
- `src/magic_manager/earmarks.py` — the CRUD module (V12 `earmarked_products` +
  `earmark_links` tables; V31 adds `kind` sealed|single and `earmarks.resolve_single`). Stores only the non-derivable asking-price snapshot.
- `cli._resolve_identity` — the shared MTGJSON-identity validator both `add` and
  `resolve-product` enforce (dispatches `sld` → `sld.identify_drop`, else
  `sealed.identify_product`). `mtgjson.sealed_products(code)` — the sealed-product
  name source; `sld.all_drops()` — the Secret Lair drop-name source.
