---
name: trueup-pools
description: >-
  Product-coverage — impute which deterministic-content PRODUCTS (precon /
  jumpstart / scene box / card pool / complete Secret Lair drop) your loose cards
  came from, so you know what you've bought and what to buy at the PRODUCT level
  rather than card-by-card. Coverage is measured against the V19 ledger's
  unattributed-backfill balance (owned minus what's already attributed to
  products you own), so one physical copy backs at most one product and overlap
  cases self-correct. Read-only report by default; --apply imputes the covered
  products as acquisition events (deck row + precon ingest event). Triggers:
  "product coverage", "what products have I bought", "which of my loose cards are
  scene boxes / jumpstart packs / drops", "what should I buy at the product
  level", "reconcile / attribute my unknown cards", "true up my precons".
---

# trueup-pools (product-coverage)

Thin relay over the deterministic `scripts/trueup_pools.py` (invoked as
`mm deck product-coverage`; `mm deck trueup` is a back-compat alias). The script
does ALL logic; this skill picks the mode and relays the tiered output.

## What it answers

"Which sealed products can my collection account for (→ likely purchased), and
what should I consider buying — at the product level, not card-by-card." It's the
product grain of the V19 star schema: an imputed product-acquisition event
(`ingest_events`) linked by `ingest_id` to the exact card copies
(`inventory_events`) it explains.

## The model (relay faithfully)

- **Coverage is measured against the UNATTRIBUTED-BACKFILL balance**, not raw
  free inventory: owned − what's already attributed to products you own. So a
  card already accounted for (e.g. a Mountain in your owned LTR starter kit) has
  0 balance and can't back a new product. **One copy → at most one product.**
- **Self-correcting, no "not-owned" flags.** An LTR jumpstart whose Mountains are
  all attributed to your starter kit shows 0 balance → not claimable. Buy it
  later + add its cards → they enter the unattributed pool → it becomes coverable.
- **Full coverage only.** A product is "owned (covered)" only if its ENTIRE
  recipe fits the unattributed balance.
- **Contests resolve by PRIORITY, automatically.** When full-coverage products
  share a card the balance can't cover for all, the highest-priority claimant
  wins it (config `config/product_priority.toml`): Bundle Land Packs sit LOW
  (basic-land filler shouldn't beat a real product for a shared basic); same-tier
  version variants prefer the LOWER number (the "(1)" beats "(2)" quirk). Losers
  drop to NOT COVERED. Override a specific case with `--pick <fileName>` (you
  know you opened it) — pick beats priority.

## The recipe

```bash
uv run mm deck product-coverage                 # read-only report, --from-unattributed (default)
uv run mm deck product-coverage tla             # scope to one set/family or product-name substring
uv run mm deck product-coverage --all           # every set you own cards from
uv run mm deck product-coverage --apply         # IMPUTE covered products (writes; default is read-only)
uv run mm deck product-coverage --pick P1_LTR,P2_LTR --apply   # resolve contested, then impute
uv run mm deck product-coverage --json          # machine-readable
```

## Output sections

- **OWNED — covered from unattributed cards** — products whose full recipe fits
  the unattributed balance → likely purchased; imputed on `--apply`.
- **NOT COVERED** — products that lost a shared card to a higher-priority
  competitor (priority auto-resolved). Shows which product the cards went to;
  override with `--pick <fileName>` if you actually opened this one.
- **SECRET LAIR** — complete drops (every CN owned → treated as a covered
  product) and near-complete (≥ `--sld-partial-threshold`, advisory).

## `--apply` (writes)

For each OWNED-covered product, in one transaction:
1. Registers a `deconstructed` deck row (`register_precon_from_loose`) — makes
   `precon_unit_counts` correct; NO inventory add, NO pledge.
2. Records the product-grain acquisition as a `precon` ingest event and moves the
   card copies from the `unattributed-backfill` bucket onto it (`ingest.reattribute`,
   net-zero, capped to the balance) — so `inventory == SUM(delta)` still holds and
   no copy is double-attributed. Self-improving: next run sees those copies gone
   from the unattributed pool.

## Workflow

1. Run the read-only report for the chosen scope; relay OWNED / NOT COVERED /
   SECRET LAIR sections + the summary as a short markdown list.
2. If any NOT-COVERED product is one the user actually opened, override with
   `--pick <fileName>`.
3. On the user's go-ahead, `mm db snapshot` then `--apply`; relay the write summary.
4. Confirm `mm audit ingest-ledger` exits 0 and `mm audit provenance` shows the
   unattributed bucket shrank by the imputed products' copies.

## Cross-references

- `scripts/trueup_pools.py` — the deterministic engine.
- `decks.precon_recipe_needs` / `register_precon_from_loose` / `precon_unit_counts_for`.
- `ingest.reattribute` / `reconcile_inventory_ledger`; `sld.all_drops` / `collect_drop_ids`.
- `mm audit provenance` / `mm audit ingest-ledger` — the standing guards.
- [[import-precon]] / [[add-precon]] / [[construct-from-loose]] — the explicit
  write-side siblings (when you KNOW you bought/built something).
