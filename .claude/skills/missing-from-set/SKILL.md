---
name: missing-from-set
description: Canonical "what am I missing from set X?" workflow for any set/family. Always invokes `mm query missing-set <CODE>` which emits Scryfall printing-specific URL chunks to chat plus file:// links (XLSX checklist + plain-text ManaPool bulk-add + plain-text TCGplayer Mass Entry). Triggers: "what am I missing from FIN/avatar/tmnt/<set>?", "what's left to buy from <set>?", "missing rare/mythics from <set>?", "give me a checklist of what I need from <set>", "build me a ManaPool cart for the <set> gaps", "TCGplayer mass entry for missing <set>".
---

# Missing-from-set

Set-agnostic, deterministic, file-driven. The user has a strong opinion about output format that this skill exists to enforce:

- **Scryfall URL chunks** → in chat, every time, as the canonical printing-specific table.
- **Missing checklist (XLSX)** → file artifact in `queries/`, referenced by `file://` link in chat. **Never rendered inline.** Distinct from the "inventory checklist" produced by `mm set master-list` ([[generate-set-list]]); see [Not to be confused with](#not-to-be-confused-with-inventory-checklists) below.
- **ManaPool bulk-add (.txt)** → file artifact in `queries/`, referenced by `file://` link in chat. Plain text, paste-ready (no comments / headers / fences — portals reject extra characters). `*F*` per-line foil marker.
- **TCGplayer Mass Entry (.txt)** → file artifact in `queries/`, paste-ready. Plain text, single flat list of all rows regardless of finish. TCGplayer doesn't accept a per-line foil marker; the user runs the cart optimizer afterward to choose finish per row.

That's the whole output. Don't render the checklist as a markdown table in chat. Don't paste the bulk-add file contents as fenced code in chat. Don't ask which format the user wants — they want all three artifact files (XLSX + ManaPool .txt + TCGplayer .txt), with chat-rendering only for the URLs.

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
7. **Write TCGplayer Mass Entry .txt** to `queries/missing-<code>-tcgplayer-<timestamp>.txt` — single flat list of all rows, format `<qty> <Card Name> [SETCODE] CN`. No per-line foil marker; the user runs TCGplayer's cart optimizer afterward to pick finish per row. Plain text, no headers/comments.
8. **Print three `file://` link lines** at the end of stdout (XLSX + ManaPool + TCGplayer) so the user can click to open each artifact.

The chat rendering is automatically capped at the URL table + file links — the orchestrator never includes the inventory of cards or the bulk-add file contents inline.

## Flags

| Flag | Effect |
|---|---|
| `--chunk-size N` | Override the 20-printing cap on Scryfall URL chunks. Default 20 matches Scryfall's web-UI nested-conditions limit; raising it will produce URLs that fail to load. Lower it if specific browsers truncate URLs. |
| `--treatment-class <class>` | Override the alt sub-selector's treatment class. Default `preferred` (excludes pure-`ff`, `ext`, datestamped-with-sibling, and family-configured fancy-foil dupes). Pass `collectible-alt` to skip the dupe-foil and datestamped filtering (re-includes surgefoil dupes and PFIN stamped reprints). Pass `alt` to also include pure-`ff`. Pass `any-alt` to also include `ext`. Use the lower classes only when the user explicitly says "include fancy foils" / "include stamped reprints" / "include extended art." |

## New family protocol

**Canonical entry point: [[characterize-set]].** When `mm query missing-set <CODE>` errors out because the family is unconfigured (or when no `docs/sets/<anchor>.md` exists yet), invoke the `characterize-set` skill first. It runs the full audit (family topology, treatment signatures, chase variants, scenes, PRM destinations, edge-case cards), produces `docs/sets/<anchor>.md`, and proposes the necessary `selectors.py` diffs for the two per-family knobs described below. Missing-set then works out of the box.

The two configurable per-family knobs in `src/magic_manager/selectors.py`:

1. **`FAMILY_DUPE_FOIL_PROMO_TYPES[anchor]`** — a frozenset of `promo_types` strings that signal "same art as a sibling, just on a fancy-foil sheet." Examples: FIN's `{"surgefoil"}`, LTR's `{"surgefoil", "doublerainbow"}`. Required for `treatment=preferred` — unconfigured anchors raise `SelectorParseError`.

2. **`FAMILY_UNOBTAINABLE_RULES[anchor]`** — a list of rules describing prints the user has personally ruled out of their want list (rare distribution, narrow channels, personal taste). These are NOT dupes — the art is distinct — but the user won't shop for them. Each rule is a dict; supported conditions:
   - `promo_types_all_of`: frozenset, all must be present (AND-of-tokens, e.g. LTR's `{"silverfoil", "scroll"}` for showcase scroll-frame prints)
   - `promo_types_any_of`: frozenset, any one is enough
   - `frame_effects_all_of`: frozenset
   - `border_color`: string (e.g. `"yellow"`)

   Rules within a family are OR'd; conditions within a rule are AND'd. Example: LTR has one rule excluding `{silverfoil, scroll}` co-occurrence prints.

**When the user asks about a family that's UNCONFIGURED for `FAMILY_DUPE_FOIL_PROMO_TYPES`**, the selector layer raises a clear error. The skill MUST NOT silently fall back to `collectible-alt` and pretend the filter is correct. Route the user to `characterize-set <anchor>` first.

**Uncommon chase variants** (added `751e627`) — the missing-set pipeline includes a fourth sub-selector `set:<code>+related missing rarity=uncommon treatment=regular chase` that surfaces card names with ≥3 distinct-art printings at the same treatment (LTR Nazgûl ×9, FIN Cid ×16, FIC Secret Rendezvous ×3). This is on by default; see `src/magic_manager/selectors.py:_modifier_chase` and the per-family §3 "Chase variants" tables in `docs/sets/<anchor>.md`.

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
🛒 TCGplayer Mass Entry (149 rows): [queries/missing-fin-tcgplayer-2026-06-06-192352.txt](file:///Users/torre/.../queries/missing-fin-tcgplayer-2026-06-06-192352.txt)
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
