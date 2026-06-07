---
name: missing-from-set
description: Canonical "what am I missing from set X?" workflow for any set/family. Always invokes `mm query missing-set <CODE>` which emits Scryfall printing-specific URL chunks to chat plus file:// links (XLSX checklist + plain-text ManaPool bulk-add + plain-text TCGplayer Mass Entry split by finish). Triggers: "what am I missing from FIN/avatar/tmnt/<set>?", "what's left to buy from <set>?", "missing rare/mythics from <set>?", "give me a checklist of what I need from <set>", "build me a ManaPool cart for the <set> gaps", "TCGplayer mass entry for missing <set>".
---

# Missing-from-set

Set-agnostic, deterministic, file-driven. The user has a strong opinion about output format that this skill exists to enforce:

- **Scryfall URL chunks** → in chat, every time, as the canonical printing-specific table.
- **Missing checklist (XLSX)** → file artifact in `queries/`, referenced by `file://` link in chat. **Never rendered inline.** Distinct from the "inventory checklist" produced by `mm set master-list` ([[generate-set-list]]); see [Not to be confused with](#not-to-be-confused-with-inventory-checklists) below.
- **ManaPool bulk-add (.txt)** → file artifact in `queries/`, referenced by `file://` link in chat. Plain text, paste-ready (no comments / headers / fences — portals reject extra characters). `*F*` per-line foil marker.
- **TCGplayer Mass Entry (.txt × 2)** → file artifacts in `queries/`, split by finish (cart UI applies foil per-batch, not per-line). Plain text, paste-ready. The foil/nonfoil file is omitted entirely if 0 rows for that finish.

That's the whole output. Don't render the checklist as a markdown table in chat. Don't paste the bulk-add file contents as fenced code in chat. Don't ask which format the user wants — they want all four (XLSX + 1 ManaPool .txt + up to 2 TCG .txt), with chat-rendering only for the URLs.

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

That's it. One command. Set-agnostic AS LONG AS the family is configured (see [New family protocol](#new-family-protocol) below). The orchestrator handles all of:

1. **Resolve the family** via the existing `+related` graph in `selectors.py:_materialize_set` — works for FIN today, Avatar/TMNT/etc. tomorrow with the same invocation.
2. **Compose the three sub-selectors** (printing-level, post-treatment-filter):
   - `set:<CODE>+related missing rarity=rare treatment=regular`
   - `set:<CODE>+related missing rarity=mythic treatment=regular`
   - `set:<CODE>+related missing treatment=preferred`

   The default treatment class for the alt sub-selector is **`preferred`**, which is `collectible-alt` minus three categories of prints that the user can't or doesn't want to physically acquire: (a) **digital-only Arena/Alchemy rebalanced prints** (any `promo_types` containing `rebalanced` or `alchemy` — e.g. FIN A-248 A-Vivi Ornitier, FCA A-19 A-Winota) — these have no physical counterpart and are excluded universally, no per-family config needed; (b) **datestamped reprints** (e.g. PFIN's prerelease-stamped versions of FIN cards) that have a non-stamped sibling in the family; (c) **fancy-foil-only prints** (e.g. FIN 532 Prompto on a surgefoil sheet) whose art is identical to a cheaper sibling per the family's per-family `FAMILY_DUPE_FOIL_PROMO_TYPES` configuration. The `preferred` filter ALSO applies the digital-only AND datestamped exclusions to the rare/mythic regular sub-selectors so those prints don't slip through there.

   Net rule: "unique art the user can't get any cheaper way." Surgefoil reprints of borderless cards are dupes; chocobo-track foils with their own art are kept; PFIN prerelease stamps of regular cards are dupes; etc.
3. **Materialize the union** by `scryfall_id`, dropping cards owned in any finish (printing-level missing semantics).
4. **Emit Scryfall printing-specific URLs** to stdout as a chunked markdown table — sorted cheapest-first, 20 printings per chunk (matches Scryfall web UI's nested-condition cap), `unique=prints&order=usd&dir=asc` so each chunk shows the exact missing printings sorted by cheapest-first within the chunk.
5. **Write missing checklist** (XLSX) to `queries/missing-<code>-checklist-<timestamp>.xlsx` (set-grouped, sorted by CN within each set). The hidden `_meta` sheet records `kind: "missing"` so consumers can distinguish this from inventory checklists (which carry `kind: "inventory"`).
6. **Write ManaPool bulk-add .txt** to `queries/missing-<code>-manapool-<timestamp>.txt` (single flat list of all rows, sorted by set/CN/finish, `*F*` foil marker per line — Moxfield's documented import token, which ManaPool consumes natively). Plain text, no headers/comments/fences — portals reject anything that's not a card row.
7. **Write TCGplayer Mass Entry .txt files split by finish** — `queries/missing-<code>-tcgplayer-nonfoil-<timestamp>.txt` and `queries/missing-<code>-tcgplayer-foil-<timestamp>.txt`. Plain text, format `<qty> <Card Name> [SETCODE] CN`. TCGplayer applies foil per-batch via the cart UI toggle (not per-line), so foil rows live in a separate file. Either file is **omitted entirely** if 0 rows for that finish (e.g. a fully-nonfoil missing set produces only the nonfoil .txt).
8. **Print `file://` link lines** at the end of stdout — XLSX, ManaPool, then TCGplayer files (if non-empty) — so the user can click to open each artifact.

The chat rendering is automatically capped at the URL table + file links — the orchestrator never includes the inventory of cards or the bulk-add file contents inline.

## Flags

| Flag | Effect |
|---|---|
| `--chunk-size N` | Override the 20-printing cap on Scryfall URL chunks. Default 20 matches Scryfall's web-UI nested-conditions limit; raising it will produce URLs that fail to load. Lower it if specific browsers truncate URLs. |
| `--treatment-class <class>` | Override the alt sub-selector's treatment class. Default `preferred` (excludes pure-`ff`, `ext`, datestamped-with-sibling, and family-configured fancy-foil dupes). Pass `collectible-alt` to skip the dupe-foil and datestamped filtering (re-includes surgefoil dupes and PFIN stamped reprints). Pass `alt` to also include pure-`ff`. Pass `any-alt` to also include `ext`. Use the lower classes only when the user explicitly says "include fancy foils" / "include stamped reprints" / "include extended art." |

## New family protocol

`treatment=preferred` requires per-family configuration in `selectors.FAMILY_DUPE_FOIL_PROMO_TYPES`. Each entry maps an anchor set code (e.g. `fin`) to a frozenset of `promo_types` strings that signal "same art, just on a fancy-foil sheet" — the dupe-foil markers for that family.

For Final Fantasy: `{"surgefoil"}`. Chocobo-track foils are intentionally NOT in the set because they have unique art.

**When the user asks about a family that ISN'T configured**, the selector layer raises a clear error pointing at the missing config. The skill MUST NOT silently fall back to `collectible-alt` and pretend the answer is filtered correctly — the user explicitly does NOT want that.

The required protocol when this happens:

1. **Stop and tell the user** the family isn't configured. Quote the anchor code and the configured anchor list from the error message.
2. **Run `mm query show 'set:<CODE>+related treatment=any-alt' --first 50`** (or similar) to surface a sample of fancy-foil prints in the new family.
3. **Ask the user**, with concrete examples from step 2: which `promo_types` on these prints signal "same art, just on a fancy-foil sheet" vs "unique art that happens to come on a fancy-foil sheet"? Show specific cards (set + CN + promo_types + Scryfall image link if relevant) so the user can adjudicate visually.
4. **Add the entry to `FAMILY_DUPE_FOIL_PROMO_TYPES`** in `src/magic_manager/selectors.py` based on the user's answer. Re-run `mm query missing-set <CODE>` to verify.
5. **Memory**: update `memory/precon_workflow.md` or a new family-specific note if the user articulates a durable rule worth carrying forward (e.g. "any future Star Wars set will probably use `lightsaberfoil` similarly to FIN's surgefoil").

Don't skip steps. The user's stated principle is "unique art I can't get any cheaper way" — the dupe-foil set is the only place where assistant judgment about visual identity intersects with set-specific data, and getting it wrong silently bakes errors into every subsequent missing-set query.

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

📋 Checklist (xlsx): [queries/missing-fin-checklist-2026-06-06-192352.xlsx](file:///Users/torre/.../queries/missing-fin-checklist-2026-06-06-192352.xlsx)
🛒 ManaPool bulk-add (149 rows): [queries/missing-fin-manapool-2026-06-06-192352.txt](file:///Users/torre/.../queries/missing-fin-manapool-2026-06-06-192352.txt)
🛒 TCGplayer nonfoil (126 rows): [queries/missing-fin-tcgplayer-nonfoil-2026-06-06-192352.txt](file:///Users/torre/.../queries/missing-fin-tcgplayer-nonfoil-2026-06-06-192352.txt)
🛒 TCGplayer foil (23 rows): [queries/missing-fin-tcgplayer-foil-2026-06-06-192352.txt](file:///Users/torre/.../queries/missing-fin-tcgplayer-foil-2026-06-06-192352.txt)
```

## When the user wants something different

These are the explicit overrides that REQUIRE the user to ask for them. Default is always the canonical recipe above.

| User says | Action |
|---|---|
| "Show the checklist in chat" / "render it inline" / "I don't want a file" | Run `mm query missing-set <CODE>`, then ALSO run `mm query show '<one of the sub-selectors>' --first N` and render those rows in chat. Confirm with the user which sub-selector they care about — there are 3, and rendering all 286 inline is rarely useful. |
| "Show the ManaPool block in chat" | Same idea: run the canonical recipe (artifacts written), then `cat queries/missing-<code>-manapool-<ts>.txt` and inline the contents in fenced code. Or `mm export manapool '<sub-selector>'` for one specific subset. |
| "Include extended art" | Run `mm query missing-set <CODE> --treatment-class any-alt`. Document the change in chat ("Used `any-alt` per request — extended-art rows are included"). |
| "Include fancy-foil-only reprints" | `mm query missing-set <CODE> --treatment-class alt`. Same documentation note. |
| "Just the rare/mythics, skip alt" | NOT supported by `mm query missing-set`. Run `mm query xlsx 'set:<CODE>+related missing rarity=rare treatment=regular' --sort value-asc` and `mm query xlsx 'set:<CODE>+related missing rarity=mythic treatment=regular' --sort value-asc` separately — pass the resulting file links to the user. Mention this is a non-default ask. |
| "Sort by name" / "sort by rarity" | The canonical XLSX is set-grouped + CN-sorted (matches physical box-flipping). For other orders, run `mm query xlsx '<full union as a single selector>' --sort <key>` separately. |
| "I only want the ManaPool file" / "I only want TCGplayer files" | The orchestrator emits all the artifacts in one shot — they're cheap to write. Just point the user at the link they care about; don't add CLI flags to suppress the others. If they really want ad-hoc one-format export, `mm export manapool '<selector>'` or `mm export tcgplayer '<selector> finish=nonfoil'` is the manual escape hatch. |

## Caveats

- **Sets that haven't been synced yet.** `mm query missing-set <CODE>` will return 0 rows (clean exit). Tell the user to run `mm set sync <CODE> --include-related` first.
- **The default treatment class is opinionated for the current user.** It excludes `ext` (extended art) and pure-`ff` (fancy-foil-only reprints) because those don't represent unique art. If the user's preferences change, the default in the orchestrator can be revisited.
- **Printing-level missing.** Owning any finish of a printing hides BOTH finishes from the result. For finish-specific gap reports ("what foils am I missing?"), use `mm query xlsx 'set:<CODE>+related missing:foil ...'` — that's a finish-aware query, not the canonical missing-set workflow.
- **Cards committed to decks still count as "owned" for the missing-set query.** This skill does NOT subtract `deck_cards` commitments. If the user wants "what would I have to buy if I didn't deconstruct any decks?", run `mm query show 'inventory available'` (different question shape) — see [[inventory-query]].
- **Don't paste the artifact contents into chat.** The user explicitly asked for files-only. If they need to see what's in the file, give them a `file://` link or run `open <path>` for them.

## Not to be confused with: inventory checklists

The XLSX written by this skill is a **missing checklist** — purpose: shopping list of printings the user doesn't yet own. The XLSX written by `mm set master-list` (the [[generate-set-list]] skill) is an **inventory checklist** — purpose: cataloging physical cards. Different artifacts, different purposes, different filter rules:

| | Missing checklist (this skill) | Inventory checklist ([[generate-set-list]]) |
|---|---|---|
| **Produced by** | `mm query missing-set` | `mm set master-list` |
| **File location** | `queries/missing-<code>-checklist-<ts>.xlsx` | `checklists/<slug>-checklist.xlsx` |
| **`_meta.kind`** | `missing` | `inventory` |
| **Spine** | printing-level union of what's missing from inventory | full family universe (with safe variant exclusions) |
| **Columns** | set, cn, name, rarity, **finish**, qty, **unit_usd**, **line_value**, scryfall_id | set, cn, name, rarity, treatment, mana_value, usd, usd_foil, **qty_normal, qty_foil** |
| **Filter philosophy** | **Strict** — `preferred` treatment class drops ext, pure-`ff`, datestamped-with-sibling, family-configured fancy-foil dupes (e.g. FIN surgefoil), and Arena/Alchemy. "Unique art the user can't get more cheaply elsewhere." | **Permissive** — keeps ext / pure-`ff` / fancy-foil dupes (the user might own incidental copies cracked from boosters etc., and the inventory checklist needs to track them). Drops only safe-to-exclude variants (prerelease/datestamped/stamped/promopack/serialized/yellow-bordered) plus Arena/Alchemy. |
| **Round-trips** | NO, read-only | YES, via `mm set ingest` |

Mental model: **missing checklist = "what I want to buy"; inventory checklist = "what I could own."** If the user asks "what am I missing from set X?" / "what's left to buy?" / "shopping list" → this skill. If they ask for "a checklist of FIN" / "let me catalog my Final Fantasy cards" → [[generate-set-list]].

## Cross-references

- [[inventory-query]] — broader inventory questions (value rollups, top N, owned-from-set, `mm deck find`). The new `available` modifier subtracts deck commitments.
- [[generate-set-list]] — for the user's first pass on a new set (creates the inventory checklist XLSX). Feeds [[ingest-new-inventory-list]] which populates inventory so this skill's `missing` math has data to subtract.
- [[bulk-add]] — for adding cards from a CN range/list into inventory (the inverse direction).
- [[import-precon]] — for adding the contents of a Magic precon (FIC, future Avatar/TMNT precons, etc.). Closes gaps that this skill would otherwise report as missing.
- [[scryfall-search]] — for the underlying Scryfall query syntax. The "Query gotchas" section there documents `cn:"N"` quoting, the 20-condition web cap, and `unique=prints` — all of which `mm query missing-set` already handles correctly.
- [[export-list]] — for ManaPool/TCGplayer/etc. format details when the user asks for non-default export targets.
