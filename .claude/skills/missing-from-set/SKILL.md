---
name: missing-from-set
description: Recurring "what am I missing from set X?" workflow for any UB family — Final Fantasy today, Avatar/TMNT/etc. tomorrow. Composes a treatment-aware filter (rare/mythic regular-treatment + alt-treatment of any rarity, never extended-art) and emits the result as a chunked-by-set chat table, three deterministic XLSX checklists, or copy-pasteable TCGplayer/ManaPool bulk-add blocks. Triggers: "what am I missing from FIN/avatar/tmnt/<set>?", "build me a TCGplayer cart for the X gaps", "what's left to buy from <set>?", "missing rare/mythics from <set>?", "give me a checklist of what I need from <set>".
---

# Missing-from-set

Set-agnostic orchestration for "what am I missing from set X that I actually care about?" The shape of the question is identical for Final Fantasy, Avatar, TMNT, or any other UB expansion family — only the anchor set code changes.

## When to use

- "What am I missing from `<set>`?" — gap report against a synced family.
- "What's left to buy from `<set>`?" — same question, different phrasing.
- "Build me a TCGplayer/ManaPool cart for the `<set>` gaps."
- "Give me a checklist of what I need from `<set>`" — XLSX output.
- "Missing rare/mythics from `<set>`?" — same default filter applies.

**Don't** use for:
- Cataloging a brand new set (use [[generate-set-list]] then [[ingest-new-inventory-list]] first to populate inventory; then come back here).
- Open-ended inventory queries unrelated to a specific set ([[inventory-query]] handles those).
- Adding cards to inventory ([[bulk-add]]) or pasting clipboard blocks ([[import-list]]).

## What the user actually wants

Two non-obvious filter rules apply on every request:

1. **Skip regular-treatment commons and uncommons** — those rarities weren't fully cataloged for the regular printings, so showing them as "missing" is mostly false positives. **Alternate-treatment** commons/uncommons (borderless, showcase, etc.) WERE cataloged and matter, so they stay in.
2. **Always exclude extended-art entirely.** The user tracks them passively but never wants to buy back what's missing.

So the "missing-but-meaningful" set is:

> **Rare or mythic at regular treatment** *(no extended-art)* — OR — **any rarity at any non-extended alternate treatment** *(borderless, full-art, showcase, sourcematerial reskin, fancy foil)*

The selector grammar is AND-only — there's no OR — so this is expressed as a **union of three sub-selectors** orchestrated outside the grammar (see [Recipe](#recipe) below).

## Recipe

Parameterized on the anchor set code `<CODE>` (lower-case; e.g. `fin`, `avatar`, `tmnt`):

### 1. Resolve and sanity-check the family

```bash
uv run mm set list-related <CODE>
```

This prints the family graph (anchor + child sets — main, commander, masterpiece, promos, tokens, art series). Eyeball it — if the user typed a name like "Final Fantasy" rather than a code, this confirms you're targeting the right anchor.

Then verify the family is synced locally:

```bash
uv run python3 -c "
import sqlite3
c = sqlite3.connect('db/magic_manager.db')
for row in c.execute('SELECT set_code, COUNT(*) AS n FROM cards WHERE set_code IN (SELECT set_code FROM cards GROUP BY set_code) AND set_code IN (?,?,?,...) GROUP BY set_code'):
    print(row)
"
```

Easier: just run a probe selector and check the result count:

```bash
uv run mm query show 'set:<CODE>+related' --first 1 2>&1 | grep '^# rows:'
```

If the row count is 0, tell the user to sync first:

> The `<CODE>` family hasn't been synced locally yet. Run `uv run mm set sync <CODE> --include-related` (and/or `mm set master-list <CODE>` if you want the inventory checklist for the family), then ask again.

### 2. Compose the three sub-selectors

Default form, parameterized on `<CODE>`:

```
A. set:<CODE>+related missing rarity=rare    treatment=regular
B. set:<CODE>+related missing rarity=mythic  treatment=regular
C. set:<CODE>+related missing                treatment=alt
```

- `treatment=regular` → `compute_treatment()` returns empty (no `b`/`fa`/`shw`/`ext`/`sm`/`ff` codes).
- `treatment=alt` → non-empty AND does not contain `ext` — i.e. ANY alternate treatment except extended-art.
- These three subsets are **disjoint by construction** (rare-regular, mythic-regular, and alt have no row in common because `regular` and `alt` are mutually exclusive treatment classes, and rare/mythic are distinct rarities). So the union has no duplicates *for the default form*. Still dedupe by `(scryfall_id, finish)` if the user customizes the sub-selectors — future-proofing matters more than the negligible cost.

### 3. Materialize the union

Run all three in JSON mode and merge:

```bash
uv run python3 - <<'PY'
import subprocess, json
CODE = "fin"  # ← swap for the anchor
SUBS = [
    f'set:{CODE}+related missing rarity=rare treatment=regular',
    f'set:{CODE}+related missing rarity=mythic treatment=regular',
    f'set:{CODE}+related missing treatment=alt',
]
union = {}
for sel in SUBS:
    r = subprocess.run(['uv','run','mm','query','show',sel,'--json'],
                       capture_output=True, text=True, check=True)
    for row in json.loads(r.stdout):
        union[(row['scryfall_id'], row['finish'])] = row
rows = list(union.values())
print(f"union: {len(rows)} rows across {len(set(r['set'] for r in rows))} child sets")
PY
```

Tee the result to a temp JSON file if the user is going to ask follow-up questions ("now sort by value", "now the foils only", etc.) — re-running the three sub-queries is fast but not free.

### 4. Pick the output format

Ask via `AskUserQuestion` if it's not implied by the user's phrasing. Phrases that imply each:

- **Chat table** — "what am I missing", "show me", "what's the list" → render in chat.
- **XLSX** — "checklist", "spreadsheet", "Excel", "give me a file" → write XLSX artifacts.
- **Bulk-add** — "TCGplayer", "ManaPool", "build me a cart", "let me buy these" → emit paste blocks.

If the user says "all formats" or it's ambiguous, default to the chat table and offer the other two as follow-ups.

## Output formats

### A. Chat table — chunked by set code with subtotals

Always chunk by set code with a per-set subtotal row. Even a 50-row result is more scannable in 3-4 small per-set tables than as one wall.

Columns are the canonical wide-table format from [[inventory-query]]: `# / Qty / Set / CN / Finish / Unit / Line / Card`. The Card column is the verbatim `cards.name` (with reskin `flavor / oracle` form when `flavor_name` is set), wrapped in a Scryfall hyperlink to `cards.scryfall_uri` (strip `?utm_source=api`).

Layout:

```
## <Set name> (<CODE>) — N rows · $X.XX

| # | Qty | Set | CN | Finish | Unit | Line | Card |
|---|---:|---|---:|---|---:|---:|---|
| 1 | 1 | FCA | 11 | foil | $90.15 | $90.15 | [The Emperor, Hell Tyrant / Yawgmoth, Thran Physician](https://...) |
...

## <Next set name> (<CODE>) — M rows · $Y.YY

...

**Total: <N+M+...> rows · $<grand total> across <K> sets.**
```

Sort within each chunk follows the user's `--sort` choice (default `set,cn,finish`; `value-desc` when "by value" / "most expensive first"; `value-asc` when "cheapest first" / "low-hanging fruit"). Sets themselves are ordered alphabetically by code in the default sort; for `value-desc`/`value-asc`, sets are still ordered alphabetically (the within-set sort changes; the inter-set order stays predictable so the user can scroll deterministically).

For very large results (>200 rows), the assistant should produce the per-set tables but consider truncating each at 30 rows with a `… +K more in <CODE>` line per set, and offer XLSX as a follow-up.

### B. XLSX checklists — three files, deterministic slugs

Run `mm query xlsx` per sub-selector with explicit `--name` slugs so re-runs are predictable:

```bash
uv run mm query xlsx 'set:<CODE>+related missing rarity=rare treatment=regular' \
  --name missing-<CODE>-rare-regular [--sort <sort>]
uv run mm query xlsx 'set:<CODE>+related missing rarity=mythic treatment=regular' \
  --name missing-<CODE>-mythic-regular [--sort <sort>]
uv run mm query xlsx 'set:<CODE>+related missing treatment=alt' \
  --name missing-<CODE>-alt [--sort <sort>]
```

Each writes `queries/missing-<CODE>-<bucket>-<timestamp>.xlsx`. The hidden `_meta` sheet in each file records the originating selector verbatim, so file lineage stays traceable.

Three files (rather than one merged workbook) is the V1 shape — simpler, reusable across sets, and openable independently. If the user later asks for a single workbook with three sheets, that's a future enhancement; don't pre-build it.

### C. Bulk-add paste blocks — TCGplayer (two blocks) and ManaPool (one block)

**ManaPool** — single block, handles foil per-line via `★`:

```bash
uv run mm export manapool 'set:<CODE>+related missing <full union>'
```

You can't actually express the full union in one selector (no OR), so emit three separate ManaPool blocks (one per sub-selector) OR materialize the union via the Phase 3 recipe above and pipe through `mm export manapool` — but the simpler path is: tell the user "here are three blocks, paste each in turn", since ManaPool's bulk-add accepts repeated pastes that accumulate.

**TCGplayer** — TWO blocks per sub-selector (or per the full union if you've materialized it), since TCGplayer's Mass Entry has no per-line foil marker:

```bash
uv run mm export tcgplayer 'set:<CODE>+related missing rarity=rare treatment=regular finish=nonfoil'
uv run mm export tcgplayer 'set:<CODE>+related missing rarity=rare treatment=regular finish=foil'
# ...repeat for mythic-regular and alt
```

Surface the output in chat with explicit framing:

````
=== TCGplayer paste block 1 — NONFOIL ===
**Toggle TCGplayer's foil setting OFF before pasting.**

```
1 Vivi Ornitier [Final Fantasy]
1 Cloud, Midgar Mercenary [Final Fantasy]
...
```

=== TCGplayer paste block 2 — FOIL ===
**Toggle TCGplayer's foil setting ON before pasting.**

```
1 Lulu, Stern Guardian [Final Fantasy Commander]
...
```
````

If a sub-selector has zero foils, skip the foil block (and the toggle warning). If it has zero nonfoils (e.g. PMEI/PSS5/PFIN are foil-only), skip the nonfoil block.

For mass carts spanning all three sub-selectors, the cleanest path is to flatten by finish across all three — i.e. ONE TCGplayer "nonfoil" block (containing rare-regular nonfoils + mythic-regular nonfoils + alt nonfoils) and ONE TCGplayer "foil" block. Express via `(set:<CODE>+related missing finish=nonfoil) ∪ ...` materialized in Python, then pipe to `mm export tcgplayer`.

For both platforms, emit cards in default sort (`set,cn,finish`); both platforms re-sort on submit, so ordering doesn't matter for them. Don't pass `--sort value-desc` to the export step — it's wasted work.

## Sort handling

When the user adds a sort hint, thread `--sort <key>` through `mm query show` and `mm query xlsx` calls:

| User says | `--sort` value |
|---|---|
| (no hint, or "by set / by collector number / default") | omit (uses `default`) |
| "by value" / "most expensive first" / "what should I buy first?" / "priorities" | `value-desc` |
| "cheapest first" / "low-hanging fruit" / "easy wins" | `value-asc` |
| "by rarity" / "mythics first" | `rarity` |

Unpriced rows always sink to the bottom regardless of direction (None ≠ cheapest). For the chat table, the per-set chunking happens AFTER the sort, so within each set the user's chosen order is preserved.

For the bulk-add paste blocks, sort is irrelevant — both platforms re-sort on submit. Don't waste tokens on it there.

## Caveats

- **Sets that haven't been synced yet.** `set:<CODE>+related` returns empty if the cards table doesn't have any rows for that family. The skill must check this and surface the exact `mm set sync` command needed; don't proceed with empty selectors.
- **Tokens / art series / regional promos.** `set:<CODE>+related` includes `tfin`/`tfic`/`afin`/`afic`/`wfin` (and analogues for other families) when those are synced. Most users don't track tokens or art series in their physical inventory; if any of those sets has cards in the local DB but the user clearly didn't intend to track them, advise either re-syncing without `--include-kinds=token,memorabilia` (the default already excludes them) OR adding explicit per-set queries scoped to the sets they care about. For Final Fantasy specifically, the "main" sets are `fin`, `fic`, `fca`, `pfin`, `pmei`, `pss5`, `pw25`, `rfin` — tokens/art-series are not part of the default catalog.
- **PMEI/PSS5/PFIN/PW25/etc. are foil-only sets** (per their `finishes` JSON arrays). The `treatment=alt` filter still works correctly — treatment is a property of the printing's frame/promo metadata, not the finish. But the TCGplayer two-block emission MAY skip the nonfoil block for these sets (no nonfoils to emit).
- **Same name across sets.** The chat-table format from [[inventory-query]] handles same-name disambiguation via the Set+CN+Finish columns. Never inject treatment labels (like "(borderless)" or "(alt-art)") into the Card column — the data already disambiguates. See `inventory-query` skill's "Output rules" section.
- **Reskin display names** (FCA, FIC's reskin slots) follow the `flavor_name / oracle_name` convention. The `_row_display_name()` helper in `cli.py` and the canonical chat-table recipe both apply this; don't override.
- **The default filter is opinionated.** "Rare/mythic + alt-treatment" matches the current user's collecting style. If a different user asked the same question with different priorities, the sub-selectors would change. The skill prose documents the union recipe so the assistant can adapt it on request — e.g. "I also want commons/uncommons" → drop the `treatment=regular` constraint in subs A and B; "I do want extended art back" → swap `treatment=alt` for `treatment=any-alt`.

## Worked example — Final Fantasy

User: *"What am I missing from Final Fantasy?"*

```bash
# 1. Confirm anchor + family
uv run mm set list-related fin
# → fin (parent), fic (commander), fca (masterpiece), pfin (promos), rfin/pmei/pss5/pw25/...

# 2. Sanity-check synced rows
uv run mm query show 'set:fin+related' --first 1 2>&1 | grep '^# rows:'
# → # rows: 2700+   (good)

# 3. Materialize the three sub-selectors and union
uv run python3 - <<'PY'
import subprocess, json
SUBS = [
    'set:fin+related missing rarity=rare treatment=regular',
    'set:fin+related missing rarity=mythic treatment=regular',
    'set:fin+related missing treatment=alt',
]
union = {}
for sel in SUBS:
    r = subprocess.run(['uv','run','mm','query','show',sel,'--json'],
                       capture_output=True, text=True, check=True)
    for row in json.loads(r.stdout):
        union[(row['scryfall_id'], row['finish'])] = row
print(f"{len(union)} missing rows across {len(set(r['set'] for r in union.values()))} sets")
PY
# → 1256 missing rows across 4 sets
```

Render the chat table chunked by `fca` / `fic` / `fin` / `pfin` with subtotals; each set has its own table; grand total at the bottom.

If the user follows up with *"as XLSX"* → run the three `mm query xlsx` invocations.

If the user follows up with *"build me a TCGplayer cart for just the rare-regular missing"* → emit two TCGplayer blocks (nonfoil + foil) for sub-selector A only.

## Cross-references

- [[inventory-query]] — canonical wide-table format for chat output, decision-tree for general DB questions.
- [[generate-set-list]] — for the user's first pass on a new set (creates the inventory checklist XLSX). Feeds [[ingest-new-inventory-list]], which populates `inventory` so this skill's `missing` math has data to subtract.
- [[bulk-add]] — for adding cards to inventory after this skill identifies what to buy (the inverse direction).
- [[export-list]] — underlying export-format reference. This skill calls `mm export tcgplayer` and `mm export manapool` directly; export-list documents the per-platform formats.
