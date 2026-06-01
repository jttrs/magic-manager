---
name: missing-from-set
description: Canonical "what am I missing from set X?" workflow for any set/family. Always invokes `mm query missing-set <CODE>` which emits Scryfall printing-specific URL chunks to chat plus two file:// links (XLSX checklist + ManaPool bulk-add MD). Triggers: "what am I missing from FIN/avatar/tmnt/<set>?", "what's left to buy from <set>?", "missing rare/mythics from <set>?", "give me a checklist of what I need from <set>", "build me a ManaPool cart for the <set> gaps".
---

# Missing-from-set

Set-agnostic, deterministic, file-driven. The user has a strong opinion about output format that this skill exists to enforce:

- **Scryfall URL chunks** → in chat, every time, as the canonical printing-specific table.
- **Checklist (XLSX)** → file artifact in `queries/`, referenced by `file://` link in chat. **Never rendered inline.**
- **ManaPool bulk-add (MD)** → file artifact in `queries/`, referenced by `file://` link in chat. **Never rendered inline.**

That's the whole output. Don't render the checklist as a markdown table in chat. Don't paste the ManaPool blocks as fenced code in chat. Don't ask which format the user wants — they want all three, with chat-rendering only for the URLs.

## When to use

- "What am I missing from `<set>`?" / "What's left to buy from `<set>`?"
- "Build me a ManaPool cart for the `<set>` gaps"
- "Give me a checklist of what I need from `<set>`"
- "Missing rare/mythics from `<set>`?" / any phrasing that maps to the printing-level missing union

**Don't** use for:
- Aggregate questions ("how much is my collection worth?", "top 10 most valuable") — use `mm query value` / `mm query top` directly.
- "What do I OWN from `<set>`?" — that's `mm query show 'set:<CODE>+related owned'`.
- Adding cards to inventory ([[bulk-add]] / [[import-list]] / [[import-precon]]).

## The canonical recipe

```bash
uv run mm query missing-set <CODE>
```

That's it. One command. Set-agnostic. The orchestrator handles all of:

1. **Resolve the family** via the existing `+related` graph in `selectors.py:_materialize_set` — works for FIN today, Avatar/TMNT/etc. tomorrow with the same invocation.
2. **Compose the three sub-selectors** (printing-level, post-treatment-filter):
   - `set:<CODE>+related missing rarity=rare treatment=regular`
   - `set:<CODE>+related missing rarity=mythic treatment=regular`
   - `set:<CODE>+related missing treatment=collectible-alt`
3. **Materialize the union** by `scryfall_id`, dropping cards owned in any finish (printing-level missing semantics).
4. **Emit Scryfall printing-specific URLs** to stdout as a chunked markdown table — sorted cheapest-first, 20 printings per chunk (matches Scryfall web UI's nested-condition cap), `unique=prints&order=usd&dir=asc` so each chunk shows the exact missing printings sorted by cheapest-first within the chunk.
5. **Write XLSX checklist** to `queries/missing-<code>-checklist-<timestamp>.xlsx` (set-grouped, sorted by CN within each set).
6. **Write ManaPool bulk-add MD** to `queries/missing-<code>-manapool-<timestamp>.md` (3 fenced blocks, one per sub-selector, with `★` foil markers per line).
7. **Print two `file://` link lines** at the end of stdout so the user can click to open either artifact.

The chat rendering is automatically capped at the URL table + two file links — the orchestrator never includes the inventory of cards or the ManaPool block contents inline.

## Flags

| Flag | Effect |
|---|---|
| `--chunk-size N` | Override the 20-printing cap on Scryfall URL chunks. Default 20 matches Scryfall's web-UI nested-conditions limit; raising it will produce URLs that fail to load. Lower it if specific browsers truncate URLs. |
| `--treatment-class <class>` | Override the alt sub-selector's treatment class. Default `collectible-alt` (excludes pure-`ff` and `ext`). Pass `alt` to include pure-`ff`. Pass `any-alt` to also include `ext`. Use these only when the user explicitly says "include fancy foils" or "include extended art." |

## Output format (what the user sees in chat)

Just relay the orchestrator's stdout verbatim — don't add summary tables, don't reformat. The orchestrator's output is already in the user's preferred shape. Example:

```
# Missing from set:fin+related — 286 distinct printings · $15,362.25

## Scryfall URLs (15 chunks, cheapest first)

| # | Printings | Price band | URL |
|---:|---:|---|---|
| 1 | 20 | $0.25 → $1.20 | [chunk 1](https://scryfall.com/...) |
| 2 | 20 | $1.40 → $2.49 | [chunk 2](https://scryfall.com/...) |
...
| 15 | 6 | $1979.40 → — | [chunk 15](https://scryfall.com/...) |

📋 Checklist (xlsx): [queries/missing-fin-checklist-2026-05-31-192604.xlsx](file:///Users/torre/.../queries/missing-fin-checklist-2026-05-31-192604.xlsx)
🛒 ManaPool bulk-add: [queries/missing-fin-manapool-2026-05-31-192604.md](file:///Users/torre/.../queries/missing-fin-manapool-2026-05-31-192604.md)
```

## When the user wants something different

These are the explicit overrides that REQUIRE the user to ask for them. Default is always the canonical recipe above.

| User says | Action |
|---|---|
| "Show the checklist in chat" / "render it inline" / "I don't want a file" | Run `mm query missing-set <CODE>`, then ALSO run `mm query show '<one of the sub-selectors>' --first N` and render those rows in chat. Confirm with the user which sub-selector they care about — there are 3, and rendering all 286 inline is rarely useful. |
| "Show the ManaPool block in chat" | Same idea: run the canonical recipe (artifacts written), then `cat queries/missing-<code>-manapool-<ts>.md` and inline the requested block(s) in fenced code. Or `mm export manapool '<sub-selector>'` for one specific subset. |
| "Include extended art" | Run `mm query missing-set <CODE> --treatment-class any-alt`. Document the change in chat ("Used `any-alt` per request — extended-art rows are included"). |
| "Include fancy-foil-only reprints" | `mm query missing-set <CODE> --treatment-class alt`. Same documentation note. |
| "Just the rare/mythics, skip alt" | NOT supported by `mm query missing-set`. Run `mm query xlsx 'set:<CODE>+related missing rarity=rare treatment=regular' --sort value-asc` and `mm query xlsx 'set:<CODE>+related missing rarity=mythic treatment=regular' --sort value-asc` separately — pass the resulting file links to the user. Mention this is a non-default ask. |
| "Sort by name" / "sort by rarity" | The canonical XLSX is set-grouped + CN-sorted (matches physical box-flipping). For other orders, run `mm query xlsx '<full union as a single selector>' --sort <key>` separately. |
| "TCGplayer cart, not ManaPool" | Run `mm export tcgplayer '<sub-selector> finish=nonfoil'` and `... finish=foil'` per Phase 3 of the original orchestration plan (see [[export-list]]). Two paste blocks per sub-selector because TCGplayer has no per-line foil marker. ManaPool is the canonical bulk-add target because it round-trips foil correctly; TCGplayer is the explicit override. |

## Caveats

- **Sets that haven't been synced yet.** `mm query missing-set <CODE>` will return 0 rows (clean exit). Tell the user to run `mm set sync <CODE> --include-related` first.
- **The default treatment class is opinionated for the current user.** It excludes `ext` (extended art) and pure-`ff` (fancy-foil-only reprints) because those don't represent unique art. If the user's preferences change, the default in the orchestrator can be revisited.
- **Printing-level missing.** Owning any finish of a printing hides BOTH finishes from the result. For finish-specific gap reports ("what foils am I missing?"), use `mm query xlsx 'set:<CODE>+related missing:foil ...'` — that's a finish-aware query, not the canonical missing-set workflow.
- **Cards committed to decks still count as "owned" for the missing-set query.** This skill does NOT subtract `deck_cards` commitments. If the user wants "what would I have to buy if I didn't deconstruct any decks?", run `mm query show 'inventory available'` (different question shape) — see [[inventory-query]].
- **Don't paste the artifact contents into chat.** The user explicitly asked for files-only. If they need to see what's in the file, give them a `file://` link or run `open <path>` for them.

## Cross-references

- [[inventory-query]] — broader inventory questions (value rollups, top N, owned-from-set, `mm deck find`). The new `available` modifier subtracts deck commitments.
- [[generate-set-list]] — for the user's first pass on a new set (creates the inventory checklist XLSX). Feeds [[ingest-new-inventory-list]] which populates inventory so this skill's `missing` math has data to subtract.
- [[bulk-add]] — for adding cards from a CN range/list into inventory (the inverse direction).
- [[import-precon]] — for adding the contents of a Magic precon (FIC, future Avatar/TMNT precons, etc.). Closes gaps that this skill would otherwise report as missing.
- [[scryfall-search]] — for the underlying Scryfall query syntax. The "Query gotchas" section there documents `cn:"N"` quoting, the 20-condition web cap, and `unique=prints` — all of which `mm query missing-set` already handles correctly.
- [[export-list]] — for ManaPool/TCGplayer/etc. format details when the user asks for non-default export targets.
