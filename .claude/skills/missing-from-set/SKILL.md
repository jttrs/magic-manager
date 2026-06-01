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

The filter is **asymmetric** between "what I have" and "what I'm missing" — and this matters a lot. Pay attention.

### "Missing" queries (the default this skill produces)

Four rules:
1. **Skip regular-treatment commons and uncommons.** Those rarities weren't fully cataloged at regular treatment, so they'd be mostly false positives.
2. **Always exclude extended-art** (`treatment=ext`). The user tracks ext passively but never wants to buy back what's missing — at any rarity.
3. **Exclude pure fancy-foil at ANY rarity** (`treatment` is exactly `{ff}`). Fancy-foil-only rows are visually identical to their regular-frame counterparts — same art, same frame, same border; only the physical foil sheet differs. The user does NOT collect these as gaps. (The user did say to count them in inventory rollups for "what I have" queries — see asymmetry note above.) Multi-code rows like `b|ff` (borderless + fancy foil) and `fa|ff` (full-art + fancy foil) STILL pass because they carry an additional visual distinction.
4. **Printing-level ownership: owning ANY finish hides BOTH finishes.** The bare `missing` modifier is printing-level — if the user owns the nonfoil but not the foil (or vice versa), the printing does not appear in the default missing list. The user collects "unique art I'm missing", so foil-vs-nonfoil isn't a meaningful distinction at the default. This collapses the result to one row per scryfall_id (preferring nonfoil for display when both finishes exist in the materialized universe). **Override**: explicit `missing:foil` and `missing:nonfoil` modifiers stay finish-aware and surface partial-ownership gaps. Use these when the user asks "what foils am I missing from X?" or "what nonfoils am I missing from X?" specifically.

This is captured by the **`treatment=collectible-alt`** modifier (added in the same change set as this skill). It means: non-empty treatment AND not `ext` AND not pure-`{ff}`.

So the "missing-but-meaningful" set is:

> **Rare or mythic** at any non-`ext` treatment (regular, `b`, `fa`, `shw`, `sm`, `ff`, or any combination minus `ext`) — OR — **any rarity at `collectible-alt`** (borderless, full-art, showcase, sourcematerial reskin, or any multi-code combination — but **not** pure-`ff` and **not** `ext`)

### "What I have" queries (different filter)

When the user asks **"what do I own from set X?"** (or aggregate questions like total value, top N, etc.), there is **no treatment filter**. Every printing the user owns counts toward inventory rollups, including pure `ff` and `ext`. Don't conflate the two question shapes.

**Note on `inventory` vs `inventory available`**: `missing` queries materialize against the bare `inventory` term, which counts every owned copy regardless of whether it's currently sleeved into a deck. If the user wants a "what would I have to buy if I refused to deconstruct any current decks?" view (i.e. subtract committed copies from owned), they should ask explicitly — that's `inventory available`, not the default. See the [[inventory-query]] cookbook entry for `available`. The default `missing` calculation is "what art/printing is missing from my owned printings, period," not "what's currently on the shelf and free."

The selector grammar is AND-only — there's no OR — so the missing-query filter is expressed as a **union of three sub-selectors** orchestrated outside the grammar (see [Recipe](#recipe) below).

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
A. set:<CODE>+related missing rarity=rare
B. set:<CODE>+related missing rarity=mythic
C. set:<CODE>+related missing                treatment=collectible-alt
```

Note: A and B include any non-`ext` treatment at rare/mythic — the `treatment=ext` exclusion is built into the grammar's `collectible-alt` and `alt` classes, but A and B don't carry a treatment modifier on purpose. Wait — that means A and B WOULD include ext at rare/mythic, which violates rule 2 ("always exclude extended-art"). The correct sub-selector form is:

```
A. set:<CODE>+related missing rarity=rare    treatment=collectible-alt
B. set:<CODE>+related missing rarity=mythic  treatment=collectible-alt
C. set:<CODE>+related missing rarity=rare    treatment=regular
D. set:<CODE>+related missing rarity=mythic  treatment=regular
E. set:<CODE>+related missing                treatment=collectible-alt
```

…wait, that's redundant: E covers all of A and B. The minimal correct form is:

```
A. set:<CODE>+related missing rarity=rare    treatment=regular
B. set:<CODE>+related missing rarity=mythic  treatment=regular
C. set:<CODE>+related missing                treatment=collectible-alt
```

- A and B pick up high-rarity regular-treatment cards (no alt code at all).
- C picks up everything alt-but-collectible at any rarity (rare/mythic alt, plus C/U alt that aren't pure-`ff` and aren't `ext`).
- These three subsets are **disjoint by construction**: A∩B is empty (different rarities); A∩C and B∩C are empty because `regular` and `collectible-alt` are mutually exclusive treatment classes. So the union has no duplicates for the default form. Dedupe by `(scryfall_id, finish)` anyway in case the user customizes the sub-selectors.

### 2.1 What this rule actually keeps and drops

For Final Fantasy specifically (FIN/FIC/FCA/PFIN as of 2026-05-31, with the user's current 242-row inventory), the default rule produces 626 union rows from a ~2,100-row family universe of cards-not-yet-owned. Breakdown of what gets dropped:

| Dropped because | Count for FIN family | Reason |
|---|---:|---|
| Regular common | ~190 | Rule 1 — low-rarity baseline noise |
| Regular uncommon | ~255 | Rule 1 |
| Pure-`ff` common | ~70 | Rule 3 — visually identical to regular |
| Pure-`ff` uncommon | ~120 | Rule 3 |
| Pure-`ff` rare/mythic | ~440 | Rule 3 (universal: pure-`ff` is dropped at every rarity) |
| `ext` at any rarity | ~370 | Rule 2 — user doesn't collect ext |

Total: ~1,445 family rows are eligible-but-dropped. The remaining 626 rows are the union of A/B/C from the recipe above. If the user wants any of these back, override the default — see [Customization](#customization).

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
- **Scryfall browse URLs** — "view in Scryfall", "let me browse", "show me the cards on Scryfall", "see the art" → `mm query url --mode prints --sort value-asc`.
- **Bulk-add paste blocks** — "TCGplayer", "ManaPool", "build me a cart", "let me buy these" → emit paste blocks.

If the user says "all formats" or it's ambiguous, default to the chat table and offer the others as follow-ups.

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

### C. Scryfall browse URLs — printing-specific, cheapest-first

For "let me visually browse the missing printings on Scryfall," use **`mm query url --mode prints`** with `--sort value-asc`. This emits `(set:CODE cn:"CN")` ORed disjunctions with `&unique=prints&order=usd&dir=asc`, so each URL renders the exact missing printings (not generic alternatives) sorted cheapest-first. Default chunk size 20 matches Scryfall's web-UI nested-condition cap.

```bash
uv run mm query url 'set:<CODE>+related missing rarity=rare treatment=regular' --mode prints --sort value-asc
uv run mm query url 'set:<CODE>+related missing rarity=mythic treatment=regular' --mode prints --sort value-asc
uv run mm query url 'set:<CODE>+related missing treatment=collectible-alt' --mode prints --sort value-asc
```

Or (cleanest path): materialize the union outside the grammar, pipe selector-string substitutes through `mm query url --mode prints`, OR run the three calls and concatenate the chunked output. For a typical FIN-sized result, expect 12–20 chunks across the three sub-selectors combined. Surface them as a markdown table in chat with one row per chunk, columns `# / printings / price band / URL`.

**`--mode oracle`** (the default) is ALSO useful — but for a different question. If the user wants to "shop by name" (let Scryfall show every printing of each name so they can pick the cheapest variant available on the market), use `--mode oracle` instead. The trade-off is "exact printings I'm missing" (prints) vs "all printings of cards I'm missing, let me browse" (oracle). Default to `--mode prints` for set-completion intent; switch to `--mode oracle` if the user explicitly says "any printing is fine" / "I just want the card."

### D. Bulk-add paste blocks — TCGplayer (two blocks) and ManaPool (one block)

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

If the user follows up with *"let me browse on Scryfall, cheapest first"* → run `mm query url --mode prints --sort value-asc` per sub-selector (or against the merged set, if you've materialized it). Scryfall renders each printing distinctly because of `unique=prints`; `order=usd&dir=asc` puts the cheapest at the top of each chunk.

If the user follows up with *"build me a TCGplayer cart for just the rare-regular missing"* → emit two TCGplayer blocks (nonfoil + foil) for sub-selector A only.

## Customization

The default filter is opinionated for the current user. If they ask for variants, swap the sub-selectors in the recipe:

| User says | Change |
|---|---|
| "Include extended-art too" | Replace `treatment=collectible-alt` with `treatment=alt` (which keeps `ext`) AND drop the `treatment=regular` constraint on A/B (so `ext` rares/mythics also flow through). Single-selector form: `set:<CODE>+related missing` (no treatment modifier). |
| "Include fancy-foil reprints too" | Replace `treatment=collectible-alt` with `treatment=alt`. Pure-`ff` rows come back. |
| "Skip alt entirely, just regular rare/mythic" | Drop sub-selector C. The two remaining sub-selectors A and B are mutually exclusive by rarity, so dedup is trivial. |
| "Include common/uncommon regular too" | Add `set:<CODE>+related missing rarity=common treatment=regular` and `…rarity=uncommon treatment=regular` as additional sub-selectors. WARNING: this typically adds hundreds of rows and is what the default explicitly tries to suppress. |
| "Just the alt-treatment list, no regular" | Drop sub-selectors A and B; keep C only. |
| "What's in this set vs what I own" (no filter at all) | Single selector `set:<CODE>+related missing` — no treatment, no rarity. Maximum recall, includes ext and pure-`ff`. |

When deviating from the default, **mention the change explicitly in chat** so the user knows what filter the output came from. The default form is what they expect; any other form is a one-off.

## Cross-references

- [[inventory-query]] — canonical wide-table format for chat output, decision-tree for general DB questions.
- [[generate-set-list]] — for the user's first pass on a new set (creates the inventory checklist XLSX). Feeds [[ingest-new-inventory-list]], which populates `inventory` so this skill's `missing` math has data to subtract.
- [[bulk-add]] — for adding cards to inventory after this skill identifies what to buy (the inverse direction).
- [[export-list]] — underlying export-format reference. This skill calls `mm export tcgplayer` and `mm export manapool` directly; export-list documents the per-platform formats.
