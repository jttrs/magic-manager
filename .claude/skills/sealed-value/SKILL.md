---
name: sealed-value
description: Deterministic card-value estimate for sealed MTG product(s) — Booster Box, Bundle, Intro/Planeswalker/Clash Pack, Beginner Box, Commander deck display, Secret Lair drop, etc. ONE product or MANY at once. Identifies each product from MTGJSON, walks its contents RECURSIVELY (a Booster Box → 36 Booster Packs → per-card booster EV), and reports INTRINSIC (booster EV from MTGJSON's per-card WotC weights + precon deck singles) and MARKET (external sealed price, provider-pluggable) valuations. Handles storefront URLs, a pasted list of links, a cart page, OR the user's open browser tabs — resolving each to its identity and emitting one combined deal table. Script-driven via `scripts/sealed_value.py` / `scripts/sealed_value_batch.py`. Triggers: "/sealed-value", "value this sealed product / booster box / this URL", "value my open tabs / these links / my cart / my watchlist", "what are the cards in <product> worth", "which of these products is the best deal", "EV of a draft/collector booster", "is this sealed product worth it".
---

# sealed-value

Deterministic, script-driven sealed-product card valuator — for ONE product or
MANY. Claude routes the request (below), runs the deterministic script(s), and
presents the result as a clean markdown chart + the `queries/` artifact paths.
The scripts do all the arithmetic (single source of truth); the agent's job is to
render their numbers as a **complete, well-formatted table in chat** — every
requested product a row, nothing silently dropped. EV weights come from MTGJSON's
published per-card booster sheets (exact WotC weighting, not a rarity average),
so the historically-hard "how likely is each card" problem is solved by data.

## Input routing — decide this FIRST

This skill is orchestration-first with a single-product bypass. Look at what the
user gave you and pick the branch:

1. **One product, already named** ("value the M15 booster box", "value afc
   Commander Deck Display") → **BYPASS** to the single-product recipe below
   (`sealed_value.py <set_code> "<substr>"`). No resolution needed.
2. **One storefront URL in chat** ("value this: <url>") → resolve that ONE URL to
   its identity (shared recipe → `mm resolve-product`), then run the
   single-product recipe. A quick one-off; no batch.
3. **MANY inputs — open browser tabs, a pasted list of links, or a cart page**
   ("value my open tabs", "value these links", "which of these is the best deal")
   → **ORCHESTRATE** (see "Multi-product orchestration"): gather URLs → resolve
   each → one combined batch table. This is the default for anything plural.

When in doubt between (2) and (3): one URL → bypass; two or more, or "my tabs/
cart/list" → orchestrate.

## When to use

- Single: "what are the cards in this **Booster Box / Bundle / Intro Pack /
  Commander display / Secret Lair drop** worth?" / "value this sealed product" /
  "value this <url>" / "is it worth it?"
- Many: "**value my open tabs**", "value **these links** / **my cart** / **my
  watchlist**", "which of these products is the best deal?"
- "What's the **EV of an M15 draft booster**?" (`--list-boosters` enumerates a
  set's booster types + per-type EV).

**Don't** use for:
- Ingesting a precon you BOUGHT into inventory/decks — that's [[import-precon]] /
  [[add-precon]] (this only *values*, it writes nothing to the DB).
- Just listing what ships in a product (no prices) — that's [[mtgjson-search]].
- Valuing loose singles you already own — that's `mm query value <selector>`.

## Multi-product orchestration (tabs / links / cart)

A thin chain over three existing deterministic pieces — no new logic:

1. **Gather the URLs.**
   - Open browser tabs → run the personal [[scrape-browser-tab-urls]] script,
     narrowing with `--filter` when the task names a store/domain:
     ```bash
     uv run --no-project python "$HOME/.claude/scripts/scrape_browser_tab_urls.py" --filter <store-or-mtg> --format json
     ```
   - Pasted list of links / a cart page → use those URLs directly (WebFetch the
     cart page for its line-item links if needed).
2. **Classify EVERY tab, then resolve the product ones.** First split the tabs
   into **product tabs** (a specific sealed product / SLD drop for sale) and
   **non-product tabs** (Gmail, docs, searches, *cart* pages, single-card pages).
   Keep an explicit list of both — you must account for every tab in the final
   output, not silently drop any. For each product tab, resolve to an MTGJSON
   identity via the shared recipe in
   [`_shared/resolve-storefront-product.md`](../_shared/resolve-storefront-product.md)
   (WebFetch/eBay-fallback → propose `set_code`+name or `sld`+drop →
   `uv run mm resolve-product <set_code> --name "<substr>" [--url <u>]`). For EACH
   item keep three things: the asking price the page shows, the exact `url` (the
   name column links to it), and — for every Secret Lair — an explicit `edition`
   of `foil` or `nonfoil` (never leave it implicit; the foil and nonfoil editions
   price very differently).
3. **Batch-value the resolved list** — build a JSON array and pipe it in. Include
   `url` and (for SLD) `edition` on every item:
   ```bash
   echo '[{"set_code":"afc","product":"Commander Deck Display","asking_price":434.99,"url":"https://…"},
          {"set_code":"sld","drop":"Far Out, Man","asking_price":29.99,"edition":"foil","url":"https://…"}]' \
     | uv run python scripts/sealed_value_batch.py --market chain
   ```
4. **Relay a COMPLETE, well-formatted chart in chat — always.** Do NOT paste the
   raw script stdout; render your own clean markdown table so it displays nicely,
   and make it EXHAUSTIVE — **every product tab is a row**, in a stable order
   (group by store or by value; your call, but include them all). The columns are
   fixed: **Product | Finish | Listing | Sealed mkt (±) | Exact singles (±) |
   Floor (±)**. The **Product cell is a markdown link to the item's URL**
   (`[name](url)`); the **Finish cell is explicit `foil`/`nonfoil` for every row**
   (Secret Lairs especially). Copy the script's `fmt_delta_cell` cells verbatim
   (value with the in-paren delta). Rows the batch couldn't value still appear —
   with `—` in the value cells and a short reason (delisted/404, no market comp,
   unresolved name). After the table, add:
   - a **one-line coverage note**: `N tabs → M valued, K product tabs unpriced
     (reason), P non-product tabs skipped (listed below)`, so nothing is silently
     missing;
   - the skipped **non-product tabs** named briefly (so the user sees they were
     considered, not lost);
   - a short **deal read** (best deals = positive Sealed-mkt delta; overpriced =
     negative), then the `queries/` artifact path.
   If a product tab won't resolve, try once more with a better `--name` substring
   before listing it as unpriced; never omit it.

## The canonical recipe (single product — the bypass branch)

```bash
uv run python scripts/sealed_value.py <set_code> "<product substring>"   # txt + xlsx (default)
uv run python scripts/sealed_value.py m15 "will of the masses"
uv run python scripts/sealed_value.py m15 "2015 core set booster box"
uv run python scripts/sealed_value.py fdn --list-boosters                # booster types + per-type EV
uv run python scripts/sealed_value.py m15 "clash pack" --format xlsx
uv run python scripts/sealed_value.py m15 "booster box" --market tcgcsv  # add external market $
uv run python scripts/sealed_value.py m15 "booster box" --market manapool # exact-uuid $ + sold comps
uv run python scripts/sealed_value.py m15 "booster box" --market compare --ebay
uv run python scripts/sealed_value.py afc "commander deck display" --market chain --listing 434.99  # 4-col + deltas vs asking
uv run python scripts/sealed_value.py sld "far out man" --listing 45 --edition foil  # a Secret Lair drop (foil edition)
```

Pass `--listing/--asking <price>` to show the delta vs the store's asking price in
cols 2-4; `--edition foil` values a Secret Lair's foil printings + foil sealed product.

`set_code` is required; the product substring is optional when a set has one
product (else the script lists candidates and exits 2 — pick a more specific
substring). Relay the whole stdout block (the indented tree + the `TOTALS` line)
and the written file paths.

**Secret Lair drops** (`set_code == sld`) route to the shared `sld` engine
(same source as [[secret-lair-value]]): pass a drop-name substring
(`sealed_value.py sld "<drop>"`). SLD prices LIVE from Scryfall (no local sync)
and reports the drop's own Secret Lair printings PLUS the "cheapest-anywhere
floor" (the cheapest printing of each card across all sets — the cheapest way to
get the cards into a deck). Use [[secret-lair-value]] for the recent-N-drops
table; use this for ONE named drop (or as part of a batch/tab valuation).

**Batch mode** is the "Multi-product orchestration" section above —
`scripts/sealed_value_batch.py` takes a JSON list of resolved items (sealed
products and/or SLD drops, optional `asking_price`) and emits one combined deal
table. That's what the tabs/links/cart branch funnels into.

## The unified 4-column schema

Every renderer (single / batch / recent-N) reports the SAME four columns, in
this order, so a product reads the same everywhere:

1. **Listing** — the store's asking price (from `--listing`/`--asking`, or a
   batch item's `asking_price`; blank if unknown).
2. **Sealed market** — the product's own price on the wider secondary market
   (the `--market` providers). SLD drops resolve to their MTGJSON `sealedProduct`
   (base + foil editions) and price through the same seam.
3. **Exact singles** — Σ market of the product's EXACT card printings.
4. **Floor singles** — Σ cheapest printing of each card ANYWHERE (by oracle_id).

Columns 2/3/4 render an **in-cell delta vs the listing** — `$399.95 (-$35.04)`,
where the delta is `value − listing` (positive ⇒ that measure exceeds the
listing ⇒ the listing is a good deal). A pure random-booster product has no fixed
singles, so cols 3/4 show the booster **EV** (labeled `EV`). SLD/foil editions:
pass `--edition foil` (single) or an `edition` hint (batch) to value the foil
printings + foil sealed product. The shared producer is `valuation.value_sealed_product`
/ `valuation.value_sld_drop`; the shared cell formatter is `util.fmt_delta_cell`.

## What it computes (the intrinsic engine behind cols 3/4)

Per node, two independent valuations:
- **intrinsic** (deterministic, offline): `pack` → `ev.booster_ev` (Σ over pack
  layouts of their probability × Σ sheet-count × Σ per-card weight/totalWeight ×
  price, foil-aware); `deck` → `sets._rollup_deck_prices` (summed precon
  singles); `cards` → explicit singles; `variable` → weighted-average over the
  configs (flagged as an approximation); a `sealed` container → Σ of its
  children × their counts.
- **market** (external, opt-in): a per-unit sealed price from a provider
  (`--market manapool|tcgcsv|tcgapi|chain|compare`). Default `null` → market
  shows `(manual)` and the report surfaces the product's TCGplayer link.
  `manapool` joins by exact MTGJSON uuid; `chain` tries manapool→tcgcsv→tcgapi;
  `compare` shows all three side-by-side.

For a container it reports **market(whole)** (the box's own price) AND
**market(parts)** (Σ component prices) — value the whole and the components.

`--market manapool` (or chain/compare) also prints a **Mana Pool** advisory line
with the real recent-**sold**-comp median (`recent_sales`) — settled prices, not
just listings — joined by exact uuid. `--ebay` adds an eBay advisory from active
buy-it-now listings. Both are non-deterministic (vary per fetch), shown as
separate lines and never entered into the deterministic artifact.

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
- Prices come from the local `cards` table. The script **auto-refreshes** any
  referenced set whose prices are missing OR stale (>7 days old) before valuing,
  so numbers stay current; the report ends with a `Prices fetched: <date>` footer
  as the freshness basis. Pass `--no-refresh` to skip the re-sync (offline/fast)
  and use local prices as-is — it warns which sets are stale. Unpriced cards stay
  in the EV denominator, so EV *under*-reports and the shortfall is surfaced as
  `coverage` + a per-node diagnostic — never silently absorbed.
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

- `scripts/sealed_value.py` (single product / SLD drop) + `scripts/sealed_value_batch.py`
  (many, one combined table) — the scripts this skill drives.
- [`_shared/resolve-storefront-product.md`](../_shared/resolve-storefront-product.md)
  + `mm resolve-product` — the URL→MTGJSON-identity checkpoint (shared with
  [[earmark-product]]); [[scrape-browser-tab-urls]] — the open-tabs front end.
- `src/magic_manager/ev.py` (`booster_ev`, `sheet_ev`, `build_uuid_price_map`),
  `src/magic_manager/sealed.py` (`identify_product`, `build_product_tree`,
  `aggregate`, market providers), `src/magic_manager/sld.py` (SLD drops),
  `sets._rollup_deck_prices`, `mtgjson.sealed_products` / `set_file` / `deck`.
- [`docs/market-providers.md`](../../../docs/market-providers.md) — market-price
  provider setup (tcgcsv/tcgapi/eBay auth + `.env` keys) and the pluggable seam.
- [[characterize-set]] — records a family's booster types in `docs/sets/<anchor>.md` §9.
- [[jumpstart-buildable]] / [[secret-lair-value]] / [[set-status]] — sibling
  deterministic script-driven skills.
```
