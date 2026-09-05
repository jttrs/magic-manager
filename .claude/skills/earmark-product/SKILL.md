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

1. **WebFetch the store URL.** Extract: the **product title**, the **asking
   price** + currency, and enough to name the set (set name / year / product
   line). Note the exact variant if the page has a selector (e.g. which 2019
   Commander deck). Common storefront hosts (tcgplayer, cardkingdom, manapool)
   are already permitted in `.claude/settings.local.json`; a **new host** (e.g.
   `cashcardsunlimited.com`) may prompt for a one-time WebFetch permission —
   that's expected.
2. **Resolve to an MTGJSON identity.** Map the title to a `set_code` + product
   name. Use `uv run mm mtgjson set <CODE>` or the [[mtgjson-search]] skill to
   list a set's `sealedProduct` names, and pick the matching one (or a unique
   substring). This is REQUIRED — `mm earmark add` refuses to save a product it
   can't resolve (it validates via `sealed.identify_product` and exits 2).
   - If the set is ambiguous from the page, search Scryfall/MTGJSON for the
     product line + year to pin the code (e.g. "Commander 2019" → `c19`).
3. **Call the CLI:**
   ```bash
   uv run mm earmark add <set_code> \
     --name "<MTGJSON product name or unique substring>" \
     --url "<the store URL>" \
     --price <asking price> [--currency USD] [--store "<label>"] [--notes "…"]
   ```
   `--store` defaults to the URL host if omitted. To add another storefront for
   a product already earmarked, just run `add` again with the new `--url` — it
   collates under the same product.
4. **Relay** the CLI's one-line result (inserted/updated product + link). If
   `add` exits 2 on an ambiguous/absent name, re-run with a more specific
   `--name` substring drawn from the candidate list it printed.

## Not to be confused with

- [[review-earmarked-products]] — prints the deal table (live market vs asking)
  for everything earmarked.
- [[sealed-value]] / [[construct-value]] — one-off valuation of a product now.

## Cross-references

- `mm earmark add|list|rm-link|rm-product` — the CLI group (`cli.py`).
- `src/magic_manager/earmarks.py` — the CRUD module (V12 `earmarked_products` +
  `earmark_links` tables). Stores only the non-derivable asking-price snapshot.
- `sealed.identify_product` — the MTGJSON-identity validator the `add` command
  enforces. `mtgjson.sealed_products(code)` — the product-name source.
