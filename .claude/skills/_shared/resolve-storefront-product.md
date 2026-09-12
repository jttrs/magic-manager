# Shared recipe: storefront URL → MTGJSON identity

The reusable procedure for turning a **store product URL** (TCGplayer, Card
Kingdom, Cash Cards Unlimited, ManaPool, eBay, any Shopify store) into a
validated MTGJSON identity that the deterministic tools can price or record.
Referenced by [[earmark-product]] and [[sealed-value]] (its URL/tab flow) so the
logic lives in one place.

## Why this step is agent-mediated (not a deterministic parser)

Every storefront names and URL-encodes products differently, and titles don't
map cleanly to MTGJSON `sealedProduct` names (or Secret Lair drop names). There
is **no reliable deterministic parser** across arbitrary stores. So the pipeline
splits:

- **Agent** reads the page and proposes an identity (the non-deterministic step).
- **`mm resolve-product`** validates + canonicalizes it (the deterministic
  checkpoint) — it refuses anything that doesn't resolve to a real MTGJSON
  product or Secret Lair drop.

Downstream tools then consume the canonical identity, never the raw URL.

## The recipe

1. **Get the page content.** If the user pasted a URL, WebFetch it; if WebFetch
   is blocked (e.g. eBay 403s automated fetches), use the authenticated path that
   fits (the `ebay.sh` item lookup by id for eBay item URLs; otherwise ask the
   user to paste the title/price, or read it from a screenshot). Extract: the
   **product title**, the **asking price** + currency, and enough to name the set
   (set name / year / product line). Note the exact variant if the page has a
   selector.
   - Known-host hints: `cashcardsunlimited.com` product slugs and titles carry
     the full name (but a `-copy` slug can mislead — trust the rendered title,
     not the slug); `tcgplayer.com/product/<id>/...` titles include the set +
     product; eBay titles are seller-written (fuzzy — confirm against the image).

2. **Propose an MTGJSON identity.** Map the title to a `set_code` + product-name
   substring — OR, for a Secret Lair, `sld` + the drop-name substring. Use
   `uv run mm mtgjson set <CODE>` or [[mtgjson-search]] to list a set's
   `sealedProduct` names; pin an ambiguous set via a Scryfall/MTGJSON search on
   the product line + year (e.g. "Commander 2019" → `c19`; AFR commander decks →
   `afc`).

3. **Validate at the deterministic checkpoint:**
   ```bash
   uv run mm resolve-product <set_code|sld> --name "<product/drop substring>" [--url "<store url>"]
   ```
   It echoes the canonical identity as JSON (`kind`, `set_code`, `name`, `uuid`,
   `category`, …, plus `url`/`store` if `--url` given), or exits 2 with the
   candidate list. If it exits 2, refine `--name` from the candidates and retry.

4. **Feed the canonical identity downstream** — e.g. `mm earmark add` (watchlist),
   `scripts/sealed_value.py <set_code> "<name>"` (value one), or a JSON list to
   `scripts/sealed_value_batch.py` (value many, e.g. a set of browser tabs).

## Guardrails

- Never record/price a product that didn't pass `mm resolve-product` — an
  unresolvable identity means the tools can't value it later.
- The asking price is a **snapshot** the agent reads off the page; it's captured
  as provenance, never computed. Price math is the valuation tools' job.
