---
name: bulk-add
description: Inline chat workflow for adding small batches of cards from a set by collector-number range. Use whenever the user says they have cards from Secret Lair (SLD), Special Guests (SPG), Magazine Inserts (PMEI), a single Commander precon, or any other set where they want to add specific CNs without seeding the whole set as an inventory checklist. Triggers: "add SLD 1858-1872", "I just opened a Secret Lair drop", "I have these SPG cards", "add (CODE) CN1, CN2, CN3 foil", or any phrasing combining a set code + CN ranges/lists.
---

# Bulk Add

Conversational add-to-inventory for a set + collector-number ranges. Scryfall query → preview → confirm → import. No new CLI commands; the skill wires existing pieces together.

## When to use

- Small batches from an evolving set (Secret Lair especially — new drops monthly, the user owns small slices).
- One-off additions from SPG, PMEI, or any set where seeding the full master-list would be overkill.
- Any "I have <set> <CN>, <CN>, <CN>" or "<set> <range>" request in chat.

**Don't** use for:
- Cataloging a whole set the user is trying to complete (use [[generate-set-list]] + the inventory-checklist flow).
- Pasted Moxfield/Archidekt blocks (use [[import-list]] directly — the user already has the text format).

## Workflow

### 1. Parse the request

Accept any of these shapes:

| Input | Meaning |
|---|---|
| `SLD 1858-1872` | range, all nonfoil |
| `SLD 1858, 1860, 1862` | discrete list |
| `SLD 1858-1872, 7001-7003` | multiple ranges, all nonfoil |
| `SLD 1858-1872 nonfoil, 7001-7003 foil` | per-range finish |
| `SLD 1858-1860 foil` | range, all foil |
| `SLD 1858 both` | one nonfoil AND one foil copy |
| `SLD 1858-1872 nonfoil +foil` | one nonfoil AND one foil of EACH card in the range |

Default finish if unspecified: **nonfoil**.

Multiple set codes per request OK — process each independently.

### 2. Resolve via `mm scryfall`

Build a single query per set code:

```bash
uv run mm scryfall 'set:sld (cn>=1858 cn<=1872 or cn>=7001 cn<=7003)' \
  --first 200 \
  --fields set,collector_number,name,treatment,rarity,prices_usd,prices_usd_foil
```

Notes on the syntax:
- `cn>=A cn<=B` is the Scryfall range operator. Wrap multi-range disjunctions in parens with `or`.
- `--first 200` is paranoia; the largest sane single batch is well under 100 cards.
- Add `--json` instead of `--fields` when you need release_date for the gap-check.

For discrete CN lists (`1858, 1860, 1862`), use `cn:1858 or cn:1860 or cn:1862`.

### 3. Show the preview

Tight table with these columns: `set`, `collector_number`, **name**, `treatment`, `rarity`, `finish`, `price`. Compute `finish` per the user's tokens. Show price from `prices_usd` for nonfoil rows, `prices_usd_foil` for foil rows. Add a total at the bottom.

Sort by collector_number ascending so the user can scan against their physical pile.

**Reskin printings — render flavor_name.** When a card has a populated `flavor_name` (most SLD UB drops, FCA, MAR, PZA, FIC bonus reskins, etc.), the user is physically holding a card whose printed name is the flavor name, not the oracle name. The preview MUST display `<flavor_name> / <oracle_name>` (e.g. `Spira's Punishment / Day of Judgment`). This matches the convention used by `mm list show`, `mm intake` feedback, and the inventory-checklist XLSX — same merged form everywhere a human reads names.

To pull flavor_name in the resolve step, request it explicitly via `--json` or by adding `flavor_name` to `--fields`:

```bash
uv run mm scryfall '<query>' --first 200 \
  --fields set,collector_number,name,treatment,rarity,prices_usd,prices_usd_foil \
  --json    # then format the table yourself, including flavor_name
```

The `--fields` table view doesn't currently include flavor_name as a known column — use `--json` and post-process when reskins are likely (any SLD/SPG/FCA/MAR/PZA range, or any UB-heavy set).

### 4. Gap-check (release-date + CN-contiguity)

This catches accidentally-missed cards from the same Secret Lair drop. The signal is **release_date AND CN contiguity TOGETHER** — not either alone.

Algorithm:
1. Fetch the user's resolved cards with `--json`. Extract their `released_at` values.
2. For each distinct date in the user's request, fetch the CN-window neighbors:
   ```bash
   uv run mm scryfall 'set:sld cn>=A-5 cn<=B+5' --first 50 --json
   ```
   where `[A, B]` brackets the user's request range, padded by ~5 CNs on either side.
3. Filter the neighbors to those with the same `released_at` as the user's range.
4. Subtract the cards the user already requested. The remainder is the **possible-gap list**.

Show the possible-gap list **separately, below the preview**, labeled like:

> **Release-date neighbors not in your request:**
> Same release date (2025-06-09) and adjacent CNs. Possibly part of the same Secret Lair drop you forgot to add.

Don't include them in the preview total. The user explicitly asked for this safety check.

If the gap-check turns up zero neighbors, just say "No release-date neighbors detected." in one line — don't omit the section, since presence of the line confirms the check ran.

**Edge case**: if release_date isn't available in the JSON (network blip, edge data), say so and skip the gap-check rather than guessing.

### 5. Confirm

Use `AskUserQuestion`:

```
Question: Import these N cards into `<label>`?
Options:
  - "Yes, import all <N> cards" (default label: owned:<set>)
  - "Cancel — let me revise"
```

If the user accepts the gap-check suggestion (e.g. "yes, add 1873 too"), restart from step 2 with the expanded range — don't try to compose two imports.

### 6. Execute

Compose a Moxfield-style text block:

```
1 Day of Judgment (SLD) 1858
1 Temporal Extortion (SLD) 1859
...
1 Feed the Swarm (SLD) 7001 *F*
```

Format rules (driven by `parsers.parse_text` at `src/magic_manager/parsers.py:97`):
- Quantity, then **oracle** name, then `(SET)` (uppercase fine, lowercase fine), then CN, optional ` *F*` for foil.
- One card per line. Blank lines OK.
- For `both` finish, emit two lines (one without `*F*`, one with).

**Use the oracle name in the import block, not the flavor name.** The resolver (`parsers.resolve()` at `parsers.py:348`) accepts both forms — typing `Spira's Punishment (SLD) 1858` resolves cleanly — but oracle name is the canonical form and matches the export round-trip path (Moxfield, Archidekt, TCGplayer all expect oracle names). The cards table stores flavor_name as a separate column and `mm list show` will render `<flavor> / <oracle>` automatically based on that column.

Pipe to `mm list import`:

```bash
printf '%s' "$BLOCK" | uv run mm list import owned:sld
```

`mm list import` will:
- Auto-upsert each card into the `cards` table (so SLD doesn't need to be pre-synced).
- Resolve each line via Scryfall (already cached from step 2 — no extra HTTP).
- Insert-or-sum into `owned:sld` (free-form-list semantics).

Surface any warnings or `not_found` entries verbatim. Most common warning: name/printing mismatch (means our text-block name didn't match what Scryfall returned for that CN — usually our copy/paste error, fix and re-run).

### 7. Confirm what landed

```bash
uv run mm list show owned:sld
uv run mm list value owned:sld
```

Report:
- Total rows in `owned:sld` after this import.
- Total value (USD).
- Whether any cards were already at qty>0 before this run (means the user re-imported the same range — flag it).

## Default label: `owned:<set>`

Lowercase set code, no other suffix. Examples:
- `owned:sld` — Secret Lair cards
- `owned:spg` — Special Guests cards
- `owned:fic` — FIC cards added piecemeal (not via the master-list flow)

The user can override per-invocation. The default is `owned:` because:
- Mirrors the existing prefix vocabulary (`set:`, `wishlist:`, `deck:`, `idea:`, `buy:`).
- Visually parallel to `set:<code>` — "stuff from this set, but only what I own."
- The free-form-list semantics ("re-import sums quantities") match how SLD usage actually works: the user adds one drop at a time, accumulating over months.

## Foil/nonfoil notes

- DB stores `nonfoil` or `foil` only (CHECK constraint at `db.py:81`).
- SLD ships exotic finishes (`gilded`, `etched`, `surgefoil`, etc.). Map them all to `foil` for storage. The `treatment` column on `cards` preserves the visual distinction at display time.
- `prices_usd_foil` is whatever Scryfall reports for that printing's foil — usually the most expensive variant.

## Caveats

- **Flavor names are display-only.** Stored on the `cards` table as `flavor_name`. Renders as `<flavor> / <oracle>` in `mm list show`, intake REPL feedback, and inventory-checklist XLSX. NOT used in exports (Moxfield/Archidekt/TCGplayer get the oracle name). Resolver accepts both forms on import.
- **`is_reskin = 1` is set when EITHER `flavor_name IS NOT NULL` OR `'sourcematerial' in promo_types`.** Catches both the FCA/MAR/PZA bonus sheets and the SLD per-IP-tagged drops. See `docs/scryfall-set-families-and-bonus-sheets.md` §4a.
- **Re-import sums quantities.** Importing `SLD 1858 nonfoil` twice gives qty=2. Always check `mm list show <label>` before re-importing if you're unsure whether a previous attempt landed.
- **`owned:<set>` is NOT reconciled with `set:<set>` master math.** `mm export 'set:sld missing'` doesn't subtract `owned:sld` automatically. That's a V2 feature (selector grammar extension). For now, the two lists are independent.
- **The CN range `cn>=A cn<=B` only matches base-numeric CNs.** Letter-suffix CNs (`1858a`, `212s`) need explicit listing or a `cn:1858a or cn:1858b` style query.
- **Gap-check is informational, not authoritative.** Same release date doesn't always mean same drop (SLD often releases multiple drops on the same day). The CN-contiguity filter mitigates but doesn't eliminate false positives. Show the user the data and let them decide.

## Examples

### One drop, simple

User: *"I have SLD 1858-1872 to add."*

Steps:
1. `uv run mm scryfall 'set:sld (cn>=1858 cn<=1872)' --first 30`  → 15 cards, all `b` treatment, mostly rare.
2. Show preview.
3. Gap-check: query `set:sld cn>=1853 cn<=1877 --json`, filter to release_date=2025-06-09, exclude user's range. → If no neighbors with same date, say "no release-date neighbors detected." If `1857` shares the date, flag it.
4. Confirm.
5. `printf '%s' "$BLOCK" | uv run mm list import owned:sld` where `$BLOCK` is 15 lines of `1 Day of Judgment (SLD) 1858` etc.
6. Show final tally.

### Two ranges, mixed finish

User: *"add SLD 1858-1872 nonfoil and 7001-7003 foil"*

Steps:
1. `uv run mm scryfall 'set:sld (cn>=1858 cn<=1872 or cn>=7001 cn<=7003)' --first 30`  → 18 cards.
2. Preview with finish column reflecting the per-range tokens. Use `prices_usd` for the first range, `prices_usd_foil` for the second.
3. Gap-check: two release dates (2025-06-09 and 2025-06-12). Run two CN-window queries, filter, dedupe. Display findings.
4. Confirm.
5. Compose a 18-line block with `*F*` only on the 7001-7003 lines.
6. Import + show.

### "Just opened the X drop"

User: *"just opened the Equinox Secret Lair, CNs 7001-7003"*

Same flow. The gap-check will probably show zero neighbors (small drop, all 3 CNs accounted for) — confirm that, proceed to import.

## Cross-references

- [[import-list]] — for paste-from-clipboard text blocks (Moxfield, Archidekt, etc.). This skill REUSES `mm list import` under the hood.
- [[scryfall-search]] — for the underlying query syntax. `mm scryfall` is the preferred search interface.
- [[generate-set-list]] — when the user wants to catalog a whole set, not just specific CNs.
- [`docs/spg-source-attribution.md`](../../../docs/spg-source-attribution.md) — companion "evolving set on its own schedule" pattern (SPG / PMEI). SLD is the same shape; this skill is the right tool for SPG/PMEI bulk-adds too.
