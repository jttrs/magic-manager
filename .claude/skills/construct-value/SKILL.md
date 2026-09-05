---
name: construct-value
description: Deterministic three-way cost to CONSTRUCT a decklist or sealed product from singles — (1) buy it SEALED, (2) buy every card NET-NEW, (3) use your LOOSE (unpledged) collection first and buy net-new only for the shortfall — plus a per-card table (Scryfall-linked name, set code, collector number, need/loose/buy qty, unit + line $, sorted by value desc). Identifies sealed products via MTGJSON (recursing Case → Kit → decks) or takes a decklist by MTGJSON fileName, local slug, pasted Moxfield block, or deck URL. Writes txt + XLSX to queries/. Script-driven via `scripts/construct_value.py`. Triggers: "/construct-value", "how much to build <deck/precon/product> from singles", "cost to construct X from scratch", "…using my collection", "what would this decklist cost me", "value the singles in this Starter Kit and how much do I already have".
---

# construct-value

Deterministic, script-driven "cost to build" valuator. Claude invokes
`scripts/construct_value.py …`, relays the stdout table + `TOTALS` line, and
hands over the `queries/` artifact paths. No inline arithmetic — the script is
the single source of truth. All valuation logic lives in
`magic_manager.construct`, which **reuses** the sealed engine
(`sealed.build_product_tree`/`aggregate` for the sealed price), the deck-price
rollup path, the shared `sets.card_price_map`, and `inventory.free_quantity`
(loose = owned − pledged) — nothing is re-implemented.

## When to use

- "How much would it cost to **build** this precon / decklist / Starter Kit **from
  singles**?" — both from scratch AND netting what I already own loose.
- "Is it cheaper to buy the **sealed** product or the **singles**?"
- "For product/deck X, how many cards do I **already have loose**, and what's the
  **net** cost to finish it?"
- Any sealed product with **deterministic** contents (precon decks, explicit
  singles): Starter Kit, Commander deck, Planeswalker deck, Beginner Box, etc.

**Don't** use for:
- Valuing the CARDS/EV of a random booster box/bundle — that's [[sealed-value]]
  (random packs can't be "constructed from singles"; this skill excludes them
  from the buildable table and notes it).
- Ingesting a bought precon into the DB — that's [[import-precon]] / [[add-precon]]
  (this only values; it writes nothing to inventory/decks).
- Just listing product contents (no prices) — that's [[mtgjson-search]].
- A whole-family "what am I missing" buy list — that's [[missing-from-set]].

## The canonical recipe

```bash
# Sealed product (set code + name substring) — all three valuations:
uv run python scripts/construct_value.py acr "Assassins Creed Starter Kit" --market compare

# MTGJSON precon by fileName (decklist — no sealed price):
uv run python scripts/construct_value.py --deck-file AncientArsenal_ACR

# A local deck by slug (uses its stored deck_cards recipe):
uv run python scripts/construct_value.py --slug atraxa-superfriends

# A pasted Moxfield-style block (or a file):
uv run python scripts/construct_value.py --decklist - < list.txt
uv run python scripts/construct_value.py --decklist /path/to/list.txt
```

Provide **exactly one** input form. `--market` (`null|tcgcsv|tcgapi|chain|compare`,
default `tcgcsv`) only affects the SEALED price; scratch/with-collection always
come from local Scryfall singles prices. `--format txt|xlsx|all` (default `all`).

### Deck URLs (Moxfield / Archidekt / MTGGoldfish) — Claude-side recipe

The script is deterministic/offline and does **not** fetch URLs. When the user
gives a deck URL, Claude does the fetch, then feeds the script a normalized block:

1. `WebFetch` the deck URL (perms for those three domains are already granted in
   `.claude/settings.local.json`). Prefer an export/text endpoint if the site
   offers one.
2. Normalize each line to `<qty> <Card Name> (SET) <CN>` (append ` *F*` for foils).
   Include set + collector number when the source has them — the script prices by
   exact print when present, else by name via Scryfall `/cards/collection`.
3. Write the block to a temp file and call `--decklist <tmpfile>`.
4. Relay the table + TOTALS as usual; delete the temp file.

## What it computes

For every input, `construct.expand_*` produces priced `(printing, finish, qty)`
needs, then:

- **scratch** = Σ `need·unit_usd` — buy every card new.
- **with-collection** = Σ `max(0, need − loose)·unit_usd`, where `loose` =
  `inventory.free_quantity` (owned minus copies pledged to built decks). Needs are
  **aggregated by `(scryfall_id, finish)` BEFORE netting**, so a card appearing in
  two decks nets your loose copies **once** — no double-spend.
- **sealed** = the whole product's external market price via the reused
  `sealed.build_product_tree`/`aggregate` (sealed input only; `n/a` for a decklist).

The **card table** is sorted by unit value desc: Scryfall-linked name, set code,
collector number, finish, need/loose/buy qty, unit $ and buy (line) $.

## Output shape

Two artifacts in `queries/` (ephemeral; pruned by [[cleanup-queries]]):
- `construct-value-<label>-<ts>.txt` — the markdown table + `TOTALS` line, paste-ready.
- `construct-value-<label>-<ts>.xlsx` — sheet `cards` (one row per printing:
  name/set/cn/finish/need/loose/buy/unit/scratch/buy/scryfall_url) + sheet
  `summary` (the three totals, coverage, excluded random packs, diagnostics).

Stdout: `## Construct value — <label>` + the table + a `TOTALS` line
(sealed / scratch / with-collection / coverage) + diagnostics + file paths.

## Determinism guarantees

- Singles prices come from the local `cards` table via the shared
  `sets.card_price_map` (the script syncs referenced sets first). Unpriced
  printings are counted in the need but contribute $0, surfaced as `coverage` +
  an `! N card(s) unpriced` note — never silently absorbed.
- `loose` is `inventory.free_quantity` at run time; the with-collection figure is
  the LOOSE (unpledged) answer, which can exceed a raw-owned estimate if copies
  are pledged to built decks.
- Random booster contents are EXCLUDED from the buildable table (can't construct a
  random pack from singles) and listed as a diagnostic.
- No `Date.now()`/random in any row; timestamps appear only in filenames.

## Guardrails

- Read-only against the DB (values + loose counts, never writes). Writes only
  ephemeral `queries/` artifacts. URL fetching happens on the Claude side, not in
  the script.
- Exactly one input form required; sealed market defaults to `tcgcsv` and degrades
  to `(manual)` if a provider is unconfigured. Provider setup (tcgcsv/tcgapi keys)
  is in [`docs/market-providers.md`](../../../docs/market-providers.md).
- Exit 0 on success; exit 2 on bad invocation / product-or-deck not found /
  nothing constructable (e.g. a product that is only random boosters).

## Not to be confused with

- [[sealed-value]] — values the CARDS/EV inside a sealed product (incl. random
  booster EV). This skill answers the orthogonal "what would it cost me to BUILD
  the deterministic cards" and nets your loose collection. They share the sealed
  engine and the price map.
- [[import-precon]] / [[add-precon]] — INGEST a bought precon. This only values.
- [[missing-from-set]] / [[jumpstart-buildable]] — family/theme buy lists, not a
  single product/deck's construct cost.

## Cross-references

- `scripts/construct_value.py` — the CLI this skill drives.
- `src/magic_manager/construct.py` — `expand_sealed`/`expand_deck_file`/
  `expand_slug`/`expand_decklist_text`, `net_against_loose`, `summarize`.
- Reused: `src/magic_manager/sealed.py` (`build_product_tree`, `aggregate`,
  `make_market_provider`, `_resolve_subproduct`), `sets.card_price_map` /
  `unsynced_set_codes` / `sync`, `inventory.free_quantity`, `parsers.parse_text` /
  `resolve`, `mtgjson.deck` / `deck_list` / `sealed_products`, `decks.deck_show`.
- [[sealed-value]] / [[jumpstart-buildable]] / [[secret-lair-value]] /
  [[set-status]] — sibling deterministic script-driven skills.
