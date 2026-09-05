---
name: sealed-value
description: Deterministic card-value estimate for a sealed MTG product — Booster Box, Bundle, Intro/Planeswalker/Clash Pack, Beginner Box, Gift/Deck-Builder's Toolkit, etc. Identifies the product from MTGJSON, walks its contents RECURSIVELY (a Booster Box → 36 Booster Packs → per-card booster EV), and reports two independent valuations per node: INTRINSIC (booster EV from MTGJSON's per-card WotC weights + precon deck singles + explicit card singles) and MARKET (external sealed price, provider-pluggable). Writes a txt + XLSX breakdown to queries/. Script-driven via `scripts/sealed_value.py <set_code> [product-substr]`. Triggers: "/sealed-value", "value this sealed product", "what are the cards in <product> worth", "EV of a draft/set/play/collector booster", "how much are the singles in a <booster box / bundle / intro pack>", "is this sealed product worth it", "value the M15 booster box".
---

# sealed-value

Deterministic, script-driven sealed-product card valuator. Claude invokes
`scripts/sealed_value.py <set_code> [product-substr]`, relays the stdout tree +
totals, and hands the user the `queries/` artifact paths. No inline arithmetic —
the script is the single source of truth. The EV weights come from MTGJSON's
published per-card booster sheets (exact WotC weighting, not a rarity average),
so the historically-hard "how likely is each card" problem is solved by data.

## When to use

- "What are the cards in this **Booster Box / Bundle / Intro Pack / Clash Pack /
  Beginner Box** worth?" / "value this sealed product" / "is it worth it?"
- "What's the **EV of an M15 draft booster** / a **FDN collector booster**?"
  (use `--list-boosters` to enumerate a set's booster types + per-type EV).
- Recursive products: a Box that contains N packs, a Toolkit that nests packs
  from OTHER sets — the tree resolves and values each component and the whole.

**Don't** use for:
- Ingesting a precon you BOUGHT into inventory/decks — that's [[import-precon]] /
  [[add-precon]] (this only *values*, it writes nothing to the DB).
- Just listing what ships in a product (no prices) — that's [[mtgjson-search]].
- Valuing loose singles you already own — that's `mm query value <selector>`.

## The canonical recipe

```bash
uv run python scripts/sealed_value.py <set_code> "<product substring>"   # txt + xlsx (default)
uv run python scripts/sealed_value.py m15 "will of the masses"
uv run python scripts/sealed_value.py m15 "2015 core set booster box"
uv run python scripts/sealed_value.py fdn --list-boosters                # booster types + per-type EV
uv run python scripts/sealed_value.py m15 "clash pack" --format xlsx
uv run python scripts/sealed_value.py m15 "booster box" --market tcgcsv  # add external market $
uv run python scripts/sealed_value.py m15 "booster box" --market compare --ebay
```

`set_code` is required; the product substring is optional when a set has one
product (else the script lists candidates and exits 2 — pick a more specific
substring). Relay the whole stdout block (the indented tree + the `TOTALS` line)
and the written file paths.

## What it computes

Per node, two independent valuations:
- **intrinsic** (deterministic, offline): `pack` → `ev.booster_ev` (Σ over pack
  layouts of their probability × Σ sheet-count × Σ per-card weight/totalWeight ×
  price, foil-aware); `deck` → `sets._rollup_deck_prices` (summed precon
  singles); `cards` → explicit singles; `variable` → weighted-average over the
  configs (flagged as an approximation); a `sealed` container → Σ of its
  children × their counts.
- **market** (external, opt-in): a per-unit sealed price from a provider
  (`--market tcgcsv|tcgapi|chain|compare`). Default `null` → market shows
  `(manual)` and the report surfaces the product's TCGplayer link.

For a container it reports **market(whole)** (the box's own price) AND
**market(parts)** (Σ component prices) — value the whole and the components.

`--ebay` adds an ADVISORY sold-comp figure; it is non-deterministic (varies per
fetch) so it is shown separately and never enters the deterministic artifact.

**Always-on "Top singles" section.** After the tree/TOTALS, the report ALWAYS
appends a **Top-15 high-value singles table** — the per-card breakdown of *which
cards carry the value* (name hyperlinked to Scryfall, set, CN, finish, unit $),
sorted by value descending, plus the full deterministic-singles total. This
reuses the `construct` engine (`expand_sealed` → `net_against_loose`), so the
singles total ties out to the tree's deck/singles intrinsic. Only DETERMINISTIC
cards are listed (fixed decks + explicit card inserts); random booster cards
can't be itemized and are noted as excluded (their value is the EV above). A
pure-booster product (a plain booster box) shows an "all random boosters" note
instead of a table. **You do not need to also run `construct-value` for the
high-value singles — sealed-value now includes them.** The full (untruncated)
table is written to the artifacts.

## Output shape

Two artifacts in `queries/` (ephemeral; pruned by [[cleanup-queries]]):
- `sealed-value-<code>-<slug>-<ts>.txt` — the indented tree + the FULL top-value
  singles table (all priced cards, not just the top 15), paste-ready.
- `sealed-value-<code>-<slug>-<ts>.xlsx` — sheet `tree` (one row per node:
  depth/name/kind/count/category/market/ev/deck/singles/ebay/tcgId/url/diagnostics)
  + sheet `sheets` (the auditable per-booster-sheet EV breakdown:
  booster_type/sheet/foil/total_weight/n_cards/n_unpriced/ev_per_pull)
  + sheet `singles` (every deterministic single, value-sorted:
  rank/name/set_code/collector_number/finish/unit_usd/scryfall_url).

Stdout: `## Sealed value — <product>` + the tree + a `TOTALS` line
(market whole / market parts / intrinsic / coverage) + diagnostics + the
**Top singles (by value)** table + file paths.

## Determinism guarantees

- EV weights are read from MTGJSON's `booster` data at runtime — the single
  source of truth, never hand-cataloged. Different booster types (draft/set/
  play/collector/beginner) are selected automatically by each pack's
  `contents.pack[].code`.
- Prices come from the local `cards` table (the script syncs referenced sets
  first). Unpriced cards stay in the EV denominator, so EV *under*-reports and
  the shortfall is surfaced as `coverage` + a per-node diagnostic — never
  silently absorbed.
- `other` contents (dice, guides, playmats, storage) are ignored — cards only.
- No `Date.now()`/random in any row; timestamps appear only in filenames.

## Guardrails

- Read-only against the DB (values, never writes). Writes only ephemeral
  `queries/` artifacts.
- Market defaults to manual (offline). External providers are opt-in and degrade
  to `(manual)` if unconfigured/unreachable. eBay is advisory-only. Provider
  setup (tcgcsv/tcgapi/eBay signup + `.env` keys) is in
  [`docs/market-providers.md`](../../../docs/market-providers.md).
- Exit 0 on success; exit 2 on product-not-found / ambiguous substring / no
  sealed data / (for `--list-boosters`) no booster data.

## Not to be confused with

- [[import-precon]] / [[add-precon]] — INGEST a bought precon's cards into the
  DB. This skill only estimates value; it writes nothing to inventory/decks.
- [[mtgjson-search]] — lists product CONTENTS (no valuation).
- [[secret-lair-value]] — values recent Secret Lair drops (a different product
  line with its own release cadence). This is any sealed product, recursively.

## Cross-references

- `scripts/sealed_value.py` — the script this skill drives.
- `src/magic_manager/ev.py` (`booster_ev`, `sheet_ev`, `build_uuid_price_map`),
  `src/magic_manager/sealed.py` (`identify_product`, `build_product_tree`,
  `aggregate`, market providers), `sets._rollup_deck_prices`,
  `mtgjson.sealed_products` / `set_file` / `deck`.
- [`docs/market-providers.md`](../../../docs/market-providers.md) — market-price
  provider setup (tcgcsv/tcgapi/eBay auth + `.env` keys) and the pluggable seam.
- [[characterize-set]] — records a family's booster types in `docs/sets/<anchor>.md` §9.
- [[jumpstart-buildable]] / [[secret-lair-value]] / [[set-status]] — sibling
  deterministic script-driven skills.
```
