---
name: characterize-set
description: Thorough investigation of one Scryfall set family to produce or update `docs/sets/<anchor>.md` — the durable per-family memory doc. Covers family topology, treatment audit, chase-variant detection, scene/poster grouping, unobtainable candidates, PRM promo destinations, and edge-case card inspection. Also proposes `src/magic_manager/selectors.py` diffs for any FAMILY_DUPE_FOIL_PROMO_TYPES / FAMILY_UNOBTAINABLE_RULES entries the audit surfaces. Triggers: "characterize <set>", "audit <set> family", "onboard <set>", "what do I know about <set>?", "bootstrap docs for <set>", "run the new-family protocol for <set>", any first-time reference to a set that has no `docs/sets/<anchor>.md`.
---

# Characterize-set

Investigates one Scryfall set family top-to-bottom and produces `docs/sets/<anchor>.md` from `docs/sets/_TEMPLATE.md`. This is the canonical entry point for new-family onboarding — replaces the earlier "run `survey_treatment_signature.py` and hand-add to selectors" recipe in [[missing-from-set]] with a more thorough, doc-first workflow.

## When to use

- **First-time work on a new set-family** — user mentions a set for which `docs/sets/<anchor>.md` does not exist. Suggest running this skill before answering non-trivial set-specific questions.
- **Refresh after Scryfall data drift** — e.g. new masterpiece sheet added to an existing family, new promo channel discovered, chase variants added post-release.
- **Bootstrap for missing-set** — when `mm query missing-set <anchor>` raises `SelectorParseError` on the preferred sub-selector because `FAMILY_DUPE_FOIL_PROMO_TYPES` isn't configured yet.

**Don't** use for:
- Answering a specific question about a well-documented set — read `docs/sets/<anchor>.md` directly.
- Small updates to an existing doc — edit `docs/sets/<anchor>.md` in place and update the "Last audit" date.

## The 9-step workflow

Run these in order. Each step's output feeds the next. Cite specific findings in the final doc so future readers can re-run the audit.

### 1. Resolve family topology

```bash
uv run mm set list-related <anchor>
```

Capture parent + all related codes with their `set_type`, `card_count`, `released_at`. Note the parent's `set_type` — for older UB sets it might be `draft_innovation`, `commander`, etc., not `expansion`.

**Separately-rooted bonus sheets** — some Scryfall records have `parent_set_code: null` even though they logically belong to a family (e.g. `mar` "Marvel Universe" is a Spider-Man bonus sheet but not linked to `spm`). Check for these manually by:

```bash
.claude/skills/scryfall-search/scryfall.sh raw '/sets' '' | jq -r '.data[] | select(.released_at >= "<family-release>" and .released_at <= "<family-release+30d>") | [.code, .name, .set_type, .parent_set_code] | @tsv'
```

Cross-check the family's known-good structure against `docs/scryfall-set-families-and-bonus-sheets.md` §1 which catalogs verified topologies.

### 2. Run the treatment-signature audit

```bash
uv run python scripts/survey_treatment_signature.py <ANCHOR>
```

Output includes:
- Every `promo_types` token frequency across the family.
- Top co-occurrence pairs (catches AND-of-tokens treatments like LTR's `silverfoil+scroll`).
- Per-token examples: 3 prints with the token + their same-name siblings WITHOUT it, plus Scryfall URLs for visual comparison.

**Interpret each fancy-foil token:**
- If the token-bearing print is **visually identical** to a same-name sibling without the token → it's a **dupe foil** → add to `FAMILY_DUPE_FOIL_PROMO_TYPES[anchor]`.
- If the token-bearing print has **unique art** → keep it out of DUPE_FOIL. Note in the doc's Treatments section as "kept — unique art despite fancy foil" (e.g. FIN chocobotrackfoil).
- If a token co-occurs with another (like `silverfoil+scroll` for LTR scroll frames) AND the user won't shop for the print → propose an entry in `FAMILY_UNOBTAINABLE_RULES[anchor]` with `promo_types_all_of: frozenset(...)`.

### 3. Enumerate chase-variant candidates

```bash
uv run mm query show 'set:<anchor>+related missing rarity=uncommon treatment=regular chase'
uv run mm query show 'set:<anchor>+related missing rarity=uncommon treatment=regular chase:5'
```

The default `chase` threshold is 3 (added `751e627`, see `src/magic_manager/selectors.py:_modifier_chase`). Try `chase:5` to see the strong-signal chases only. Record what shows up:
- Card name + count of distinct-art printings + CN range.
- Which treatment class(es) each chase spans (usually `regular`, sometimes also `ext`).

To include cards the user already owns (since the missing filter excludes those):

```bash
uv run mm query show 'set:<anchor>+related chase' | head -30
```

### 4. Scene / poster / panorama detection

Scryfall's UI groups certain borderless cards as "Scene Cards" but doesn't tag them in card metadata. Detect via `(artist, contiguous-CN)` clustering:

```bash
.claude/skills/scryfall-search/scryfall.sh search 'set:<anchor> border:borderless' unique=prints \
  | jq -r '.data[] | select((.promo_types // []) as $pt | ($pt|index("silverfoil")|not) and ($pt|index("scroll")|not) and ($pt|index("poster")|not) and ($pt|index("serialized")|not)) | select((.frame_effects // []) | index("inverted")) | select(.collector_number | test("^[0-9]+$")) | [(.collector_number|tonumber), .name, .artist] | @tsv' \
  | sort -k1,1n
```

Group consecutive rows sharing an artist. Runs of ≥3 are scenes. Also check for **poster/panorama sets** — cards with `promo_types: "poster"` (LTR 731-750) that span serialized (`z`-suffix) and non-serialized twins.

Reference implementation: `docs/ltr-borderless-scenes.md`.

### 5. PRM destination audit

For any `Ns`-style CN or `PRM`-stamped card the user might present later, know which Scryfall set actually holds it. Enumerate every promo sibling in the family:

```bash
for promo_code in <family's promo codes>; do
  echo "=== $promo_code ==="
  .claude/skills/scryfall-search/scryfall.sh search "set:$promo_code" unique=prints \
    | jq -r '.data[] | [.collector_number, .name, .artist, ((.promo_types // []) | join(","))] | @tsv' | sort
done
```

Common channels:
- `p<anchor>` — prerelease datestamped (CNs typically `Ns` where N mirrors main-set CN).
- `pw25` / `pw26` — Wizards Play Network Play Promos.
- `<L>mar` / similar special inserts (Marvel Legends).
- `pss5` etc. — Standard Showdown premiums.
- `rfin` etc. — Regional promos (typically JP-only).

Record what CN pattern maps to which set, and which artist commonly signals which channel.

### 6. Cross-reference bulk-add PRM knowledge

Grep `.claude/skills/bulk-add/SKILL.md` for anchor-specific mentions and pull them into the new doc's PRM section:

```bash
grep -i -E "pspm|pfin|ptla|ptmt|mar|<other family promo codes>" .claude/skills/bulk-add/SKILL.md
```

### 7. Edge-case card inspection

Spot-check a few tricky prints via `mm scryfall` — meld-back faces, digital-only Arena/Alchemy prints (should already be globally filtered), name-collision printings across siblings, `set_type` mismatches (like TMT's `tmc` being `set_type: eternal` despite being a commander deck).

### 8. Draft `docs/sets/<anchor>.md`

Copy `docs/sets/_TEMPLATE.md` to `docs/sets/<anchor>.md` and fill each section from steps 1-7. Keep it dense — no filler prose; every row of every table should be a fact you verified.

**Do NOT overwrite an existing doc silently** — if `docs/sets/<anchor>.md` already exists, read it first, produce a **proposed diff** for user review, and only apply after confirmation. Update the "Last audit" date at the top.

### 9. Propose code diffs (if any)

If the audit revealed:
- A `FAMILY_DUPE_FOIL_PROMO_TYPES` entry to add (e.g. `"spm": frozenset({"surgefoil"})`).
- A `FAMILY_UNOBTAINABLE_RULES` entry to add.

Emit the proposed diff for `src/magic_manager/selectors.py` and let the user approve before applying. Use `Edit` to apply after approval. Update the new doc's §8 "Code refs" to reflect the new entries.

**Never** apply code diffs before showing the diff and getting explicit approval — silent selector changes affect `mm query missing-set` output for real acquisitions.

### 10. Report

Emit a short summary of what was found and produced:

```
Characterized <anchor>: <N> sibling sets, <N> chase variants, <N> scenes,
<N> unobtainable rules proposed, <N> code diffs proposed.
Doc: file:///…/docs/sets/<anchor>.md
```

Update the "Last audit" date at the top of the new doc.

## Guardrails

- Read-only during investigation. All 7 audit steps hit Scryfall via the rate-limited wrapper or read from the local DB.
- Doc creation is safe (new file). Doc update requires diff-review-approve.
- Selector code changes ALWAYS require diff-review-approve. `_modifier_chase` and the missing-set pipeline both use these constants and silent changes affect purchases.
- If the family's parent isn't already synced (`mm set list-related` errors), run `mm set sync <anchor>` first — the audit needs the local `cards` table populated.

## Cross-references

- `docs/sets/_TEMPLATE.md` — the template every filled doc follows.
- `docs/scryfall-set-families-and-bonus-sheets.md` — general Scryfall family patterns (§1 lists observed families).
- `docs/scryfall-printing-treatments.md` — the treatment keyword space; per-set full_art convention drift.
- `docs/spg-source-attribution.md` — release-window mapping for SPG/PMEI (design doc, not implemented).
- `scripts/survey_treatment_signature.py` — the audit tool this skill orchestrates.
- `src/magic_manager/selectors.py:78-128` — FAMILY_DUPE_FOIL_PROMO_TYPES and FAMILY_UNOBTAINABLE_RULES.
- `src/magic_manager/selectors.py:_modifier_chase` — chase-variant detection logic.
- [[missing-from-set]] — the workflow this characterization enables.
- [[bulk-add]] — where PRM destination knowledge is currently referenced procedurally.
