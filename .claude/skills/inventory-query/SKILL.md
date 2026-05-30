---
name: inventory-query
description: Inline workflow for asking the local DB questions about owned cards, missing cards from sets/ranges, collection value, and Scryfall search URLs informed by what you do/don't own. Triggers: "what's missing from <set>?", "what do I own from <set>?", "value of my <X>?", "top N most valuable?", "scryfall URL for <selector>?", "missing mythics from FCA under $20?", or any English question that maps to a local-DB query.
---

# Inventory Query

Translate English questions about the local collection into `mm query` invocations built on the V2 selector grammar. No new logic — the skill is the human-to-CLI mapping layer.

## When to use

- "What's missing from <set>?" — gap reports against a synced set universe.
- "What do I own from <set>?" — slice the inventory by set membership.
- "What's my collection worth?" / "value of <X>?" — value rollups, total or sliced.
- "Top N most valuable cards?" / "do I have multiples?" / "stats by rarity?" — aggregate questions.
- "Generate a Scryfall URL for <X>" — build search URLs (chunked at 20) from any selector.
- Any English question that boils down to "ask the local DB about cards I own / want / have decked / from a set."

**Don't** use for:
- Adding cards to inventory (use [[bulk-add]] for chat-driven CN ranges, [[import-list]] for pasted Moxfield blocks).
- Exporting to Moxfield/Archidekt/TCGplayer for trade or deck-building (use [[export-list]] — it knows the per-platform output formats).
- Cataloging a new set from scratch (use [[generate-set-list]] to produce the inventory checklist XLSX first).

## Decision tree

Deterministic English-to-CLI mapping. Pick the row whose left side matches the user's phrasing.

| User asks | Command |
|---|---|
| "What's missing from X?" | `uv run mm query xlsx 'set:X missing'` |
| "What do I own from X?" | `uv run mm query show 'set:X owned'` |
| "Value of my X?" (whole collection) | `uv run mm query value 'inventory'` (or `mm query total`) |
| "Value of my X?" (slice) | `uv run mm query value 'set:X owned'` |
| "Top N most valuable cards I own?" | `uv run mm query top N` (default N=10) |
| "Do I have any multiples?" | `uv run mm query multiples` |
| "Total collection value?" | `uv run mm query total` |
| "Scryfall URL for X?" | `uv run mm query url '<selector for X>'` |
| "X missing under $Y?" | `uv run mm query xlsx 'set:X missing value<=Y'` |
| "X missing mythics?" | `uv run mm query xlsx 'set:X missing rarity=mythic'` |
| "Mythics from X under $Y I still need?" | `uv run mm query xlsx 'set:X missing rarity=mythic value<=Y'` |
| "Stats / breakdown by rarity?" | `uv run mm query stats` |
| "What dragons do I own?" | `uv run mm query show 'inventory scryfall:t:dragon'` (or `cards:t:dragon owned`) |
| "Cards in deck X I still need?" | `uv run mm query xlsx 'deck:X missing'` |
| "Wishlist entries I haven't bought?" | `uv run mm query show 'wishlist'` (wishlist IS the unbought-list; nothing to subtract) |

When a question doesn't fit a row, fall through to the **Selector cookbook** below and compose the selector by hand. All `mm query` subcommands accept any selector the parser accepts.

## Selector cookbook

A selector is `TERM (' ' MODIFIER)*`. The TERM picks the universe of `(printing, finish, qty)` tuples; modifiers filter that universe. Modifiers commute — `set:fca missing rarity=mythic value<=20` and `set:fca value<=20 rarity=mythic missing` produce identical results. Filter combination is AND across all modifiers; there is no OR operator in V2.

### Terms

| Term | Meaning | Example |
|---|---|---|
| `inventory` | Every printing owned at qty>0 (the inventory table). | `inventory` |
| `wishlist` | Every wishlist entry, all categories. | `wishlist` |
| `wishlist:CAT` | Wishlist entries in one category. | `wishlist:edh-staples` |
| `deck:SLUG` | Every card in a named deck (all boards). | `deck:atraxa-superfriends` |
| `set:CODE` | Every printing in a set from the local cards table. Requires the set to be synced. | `set:fca` |
| `set:CODE+related` | Same, expanded to the full family graph (anchor + bonus sheets, etc.). | `set:fin+related` |
| `cards:Q` | Run a Scryfall API query, intersect by id with locally-synced cards. "Cards I might own from this query." | `cards:t:dragon` |
| `scryfall:Q` | Live Scryfall API query, no local intersection. Every printing in MTG matching Q. | `scryfall:t:dragon r:mythic` |

### Modifiers

| Modifier | Meaning | Example |
|---|---|---|
| `missing` | Set difference: TERM minus inventory by `(scryfall_id, finish)`. Rejected on `inventory`/`wishlist` (tautology). | `set:fca missing` |
| `missing:nonfoil` / `missing:foil` / `missing:either` | Finish-aware missing. `nonfoil` keeps only nonfoil rows; `foil` only foil; `either` (default) keeps both. | `set:sld missing:foil` |
| `owned` | Set intersection with inventory. Inverse of `missing`. Same restriction. | `set:fca owned` |
| `qty>=N` / `qty<=N` / `qty=N` | Filter by quantity. Useful on `inventory` for "show me multiples." | `inventory qty>=2` |
| `finish=foil` / `finish=nonfoil` | Filter by finish. Terminal — no `either` here. | `inventory finish=foil` |
| `rarity=common\|uncommon\|rare\|mythic\|special\|bonus` | Filter by rarity. | `set:sld missing rarity=mythic` |
| `cn>=N` / `cn<=N` | Filter by collector number (numeric prefix; letter suffixes coerce by stripping non-digits). | `inventory cn>=1858 cn<=1872` |
| `value>=N` / `value<=N` | Filter by current Scryfall USD price for the row's finish. Rows without a price are dropped. | `inventory value>=10` |
| `scryfall:Q` (post-filter) | Run Scryfall query, intersect by id with the in-flight rows. Lets you compose two queries. | `set:fca missing scryfall:t:dragon` |

## Subcommand reference

All subcommands accept `--json` for machine-readable output and exit 0 on success, 2 on selector parse error.

- **`mm query show '<selector>' [--first N]`** — tabular dump. Columns: qty, finish, set, cn, rarity, name (with `flavor_name / oracle_name` form when applicable), unit_usd, line_value. `--first N` caps display; total count is always printed.
- **`mm query value '<selector>'`** — emits total USD, row count, count of rows with no price, and top-5 by line value.
- **`mm query xlsx '<selector>' [--name SLUG] [--out PATH]`** — writes `queries/<slug>-<timestamp>.xlsx`. Columns: set, collector_number, name, rarity, finish, qty, unit_usd, line_value, scryfall_id. Hidden `_meta` sheet records the selector verbatim, slug, timestamp, and row count. Empty results still write a file with headers and emit a stderr warning.
- **`mm query url '<selector>' [--chunk-size 20]`** — synthesizes Scryfall search URLs using `!"oracle_name"` form, deduped by oracle name (multiple finishes/printings of the same card collapse to one URL term). Default chunk size is 20.
- **`mm query top [N]`** — top-N inventory rows by line value. Default N=10.
- **`mm query total`** — shorthand for `mm query value 'inventory'`.
- **`mm query multiples`** — inventory rows with `qty>=2`, ordered by qty desc.
- **`mm query stats`** — inventory rollup: totals, by-rarity, by-set, by-finish.

`xlsx` writes to `queries/`, which is gitignored. Use `--out` to write somewhere else (e.g. into a deck-building project alongside an export).

## Artifact lifecycle

XLSX files at `queries/<slug>-<timestamp>.xlsx` live forever until the user deletes them. The skill never auto-cleans. The slug is deterministic — `_selector_slug()` lowercases, keeps alphanumerics, collapses everything else to single hyphens, trims edges. So `set:fca missing rarity=mythic value<=20` always slugifies to `set-fca-missing-rarity-mythic-value-20`. Same selector → same slug → predictable filename, with the timestamp differentiating runs.

To overwrite a fixed name, pass `--name <slug>` or `--out <path>`.

## Caveats

- **`set:X missing` requires the cards table to have been synced for X.** Run `mm set sync X` (or `mm set master-list X`) first. Without sync, the universe is empty and `missing` returns nothing useful — the selector won't error, it'll just produce zero rows.
- **`cards:Q` and `scryfall:Q` are NOT the same.** `cards:Q` runs the Scryfall API query and intersects results with locally-synced cards by id — it's "every card matching Q that I've already cataloged." `scryfall:Q` is the live API query unfiltered — every printing in MTG matching Q (qty=1 nonfoil placeholders). Use `cards:` when you want to layer ownership questions on top (`cards:t:dragon owned`); use `scryfall:` when you want the universe (`scryfall:t:dragon r:mythic` to see every mythic dragon).
- **URL chunking is hardcoded at 20 cards per chunk.** Larger result sets emit multiple URLs, one per chunk, deduped by oracle name. This is per user direction — some browsers truncate `or`-heavy URLs past ~20 terms.
- **Rejected forms.** The parser explicitly rejects:
  - `inventory missing` / `wishlist missing` — "missing requires a TERM that defines a card universe." Inventory IS the inventory; the difference is empty by definition.
  - `inventory owned` / `wishlist owned` — same reason.
  - `set:X missing owned` — "missing and owned are inverses; pick one."
  - Unknown TERMs (`foo:bar`) and unknown modifiers (`xyz=1`) — error lists the valid forms.
- **Modifiers are intersection (AND), not union.** There's no OR operator in V2. If you need disjunction, push it into the TERM via `cards:` or `scryfall:` and use the API's native `or` syntax (e.g. `cards:'r:mythic or r:rare'`). Modifier order doesn't matter — same result either way.
- **`value>=N` / `value<=N` drop rows with no USD price.** Otherwise `missing value<=20` would silently include every unpriced card. If you need unpriced rows, omit the value filter.
- **Wishlist `either` finish materializes as nonfoil** for value math (cheaper-finish convention). Override with a `finish=foil` modifier if you want foil prices.

## Examples

### "What FCA mythics do I still need under $20?"

```
uv run mm query xlsx 'set:fca missing rarity=mythic value<=20'
```

Output:

```
wrote queries/set-fca-missing-rarity-mythic-value-20-2026-05-30-141322.xlsx (12 rows)
```

Open the XLSX to scan; the `_meta` sheet records the selector verbatim so future-you remembers what generated the file.

### "What's my collection worth?"

```
uv run mm query total
```

Output:

```
Selector 'inventory': $26.38 across 18 rows
Top 5 by line value:
  $7.84  Cloud's Buster Sword / Umezawa's Jitte (SLD) 1865 [foil]
  $4.21  Tidus's Brotherhood Sword / Sword of Truth and Justice (SLD) 1867 [foil]
  $3.08  Aerith's Curaga Magic / Heroic Intervention (SLD) 1872 [foil]
  $2.45  Hope's Aero Magic / Cyclonic Rift (SLD) 1869 [foil]
  $1.92  Yuna's Holy Magic / Prismatic Ending (SLD) 1868 [foil]
```

### "Top 5 most valuable cards I own?"

```
uv run mm query top 5
```

Output:

```
Top 5 inventory rows by line value:
  $7.84  Cloud's Buster Sword / Umezawa's Jitte (SLD) 1865 [foil] qty=1
  $4.21  Tidus's Brotherhood Sword / Sword of Truth and Justice (SLD) 1867 [foil] qty=1
  $3.08  Aerith's Curaga Magic / Heroic Intervention (SLD) 1872 [foil] qty=1
  $2.45  Hope's Aero Magic / Cyclonic Rift (SLD) 1869 [foil] qty=1
  $1.92  Yuna's Holy Magic / Prismatic Ending (SLD) 1868 [foil] qty=1
```

### "Generate a Scryfall URL for the SLD foils I have"

```
uv run mm query url 'inventory finish=foil'
```

Output (18 cards under the 20-card cap → one URL):

```
18 distinct cards → 1 URL(s)
Chunk 1/1 (18 cards): https://scryfall.com/search?q=%21%22Day+of+Judgment%22+or+%21%22Temporal+Extortion%22+or+%21%22Toxic+Deluge%22+or+%21%22Praetor%27s+Grasp%22+or+%21%22Star+of+Extinction%22+or+%21%22Staff+of+the+Storyteller%22+or+...
```

For 50 cards, output would be three chunks (20 + 20 + 10), each with its own URL.

### "Stats breakdown by rarity?"

```
uv run mm query stats
```

Output:

```
Total: $26.38 / 18 cards / 18 rows

By rarity:
  mythic     rows=   1 qty=   1 value=$4.21
  rare       rows=  14 qty=  14 value=$19.83
  uncommon   rows=   3 qty=   3 value=$2.34

By set:
  SLD        rows=  18 qty=  18 value=$26.38

By finish:
  foil       rows=  18 qty=  18 value=$26.38
```

## Cross-references

- [[bulk-add]] — when the user wants to ADD cards from a CN range/list, not query existing inventory. The bulk-add flow ends with the cards in `inventory`; this skill queries that table.
- [[import-list]] — when the user has a pasted Moxfield/Archidekt block. Routes to `mm inventory import` / `mm wishlist import` / `mm deck import` depending on intent. Use that skill, then come back here to query the result.
- [[export-list]] — when the user wants to send cards OUT to Moxfield, Archidekt, TCGplayer, or a plain decklist. Selector grammar is shared, but `mm export` produces platform-formatted text rather than `mm query show`'s tabular view.
- [[generate-set-list]] — when the user wants the inventory-checklist XLSX for a whole set (with every printing as a row). That's the opposite direction — `master-list` writes the universe; `mm query xlsx 'set:X missing'` writes the gap report.
- [[scryfall-search]] — for ad-hoc Scryfall queries unrelated to local ownership. `mm scryfall '<query>'` is the underlying tool; the `cards:` and `scryfall:` selector terms layer on top of it.
