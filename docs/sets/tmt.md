# `tmt` — Teenage Mutant Ninja Turtles

> Per-family memory doc. Read this before answering set-specific questions about
> `tmt` or working on `tmt`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `tmt`
**Family root type:** `expansion`
**Family released:** 2026-03-06
**Last audit:** 2026-07-08 via `survey_treatment_signature.py` + Scryfall direct queries

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `tmt` | expansion | 320 | 2026-03-06 | parent |
| `pza` | masterpiece | 20 | 2026-03-06 | **TMNT Source Material** — UB reskin sheet (~fca/mar equivalent), with `sourcematerial` promo_type. Small: only 20 cards vs FIN's 66 and SPM's 100. |
| `tmc` | eternal | 132 | 2026-03-06 | **Actually a Commander deck** — Scryfall classified it as `set_type: eternal` but functionally it's a preconstructed commander product ("Heroes in a Half Shell"). See §7 gotcha. |
| `atmt` | memorabilia | 54 | 2026-03-06 | Art Series |
| `ftmc` | memorabilia | 5 | 2026-03-06 | Front cards (beginner/eternal box) |
| `ttmt` | token | 10 | 2026-03-06 |  |
| `ttmc` | token | 31 | 2026-03-06 | Eternal (commander) tokens |

**Missing from list-related:** none currently observed — `mm set list-related tmt` returns the full set above. No SPM-style separately-rooted bonus sheet gotcha for TMT.

**`mm` invocations:** default `set:tmt+related` resolution works correctly.

---

## 2. Treatments

`selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["tmt"]` — **not configured yet.** Add: `frozenset({"surgefoil", "fracturefoil"})`. See §8.

TMT ships two dupe-foil signals per audit:

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `surgefoil` | `ff` | **yes** → add to DUPE_FOIL | Example: TMT 309 Forest (BEMOCS artist, `surgefoil+universesbeyond`) has TMT 195 Forest (same BEMOCS artist, no surgefoil) — same art, fancy-foil sheet. |
| `fracturefoil` | `ff` | **yes** → add to DUPE_FOIL | Example: TMT 291 Leonardo (A4Mitsuori, `fracturefoil+japanshowcase+universesbeyond`) has TMT 281 Leonardo (A4Mitsuori, `japanshowcase+universesbeyond`) — same art, fancy-foil sheet. |
| `japanshowcase` | (base treatment, unique art) | **no — unique art** | TMT 281 Leonardo (A4Mitsuori) is a DIFFERENT art than TMT 15 (Chris Seaman, base) and TMT 211 (Jim Cheung, boosterfun). Japan-showcase-frame chases carry unique art. Filtered from master-list output by `sets.py:EXCLUDED_PROMO_TYPES` (japanshowcase excluded there), but selectors-side these ARE in scope for missing-set. |
| `sourcematerial` | `sm` | n/a (part of pza masterpiece sheet) | 20 prints on the `pza` "TMNT Source Material" reskin sheet. |
| `headliner` | (attached to premium) | n/a | 3 prints, standard chase premium. |

**Full-art convention:** unknown; TMT hasn't been synced to local DB so `treatments.compute_treatment` behavior isn't observed. Likely follows the newer UB convention (`full_art: true` on borderless-inverted, like SPM/TLA) but verify on first sync.

---

## 3. Chase variants

Detected by `selectors._modifier_chase`. TMT ships each main character in **4 prints per name** (base + boosterfun + japanshowcase + japanshowcase-fracturefoil). After DUPE_FOIL filtering (fracturefoil→dupe), each name resolves to **3 distinct-art prints** — exactly at the default threshold.

| Card name | Distinct-art count | Prints (pre-dupe-filter) | Rarity |
|---|---:|---:|---|
| Leonardo, Cutting Edge | 3 | 4 | ? (TMT 15/211/281/291) |
| Michelangelo, Weirdness to 11 | 3 | 4 | ? |
| Donatello, Gadget Master | 3 | 4 | ? |
| Krang, Utrom Warlord | 3 | 4 | ? |
| Dark Leo & Shredder | 3 | 4 | ? |
| Casey Jones, Vigilante | 3 | 4 | ? |
| April O'Neil, Hacktivist | 3 | 4 | ? |

These are rare/mythic, not uncommon — the `mm query missing-set tmt` `uncommon-chase` sub-selector doesn't apply. However the base `rare-regular` and `mythic-regular` sub-selectors DO surface all missing distinct-art prints per name, so completion tracking works via the standard pipeline.

Also chase-worthy (3+ same-name prints):
- Mikey & Leo, Chaos & Order (3)
- Michelangelo, Improviser (3)
- Leonardo, Sewer Samurai (3)
- Krang & Shredder (3)
- Donatello, Mutant Mechanic (3)
- Don & Raph, Hard Science (3)
- Bebop & Rocksteady (3)
- Basic lands (Plains, Island, Mountain, Forest — 5 each; not shopping targets)

---

## 4. Scenes / posters / panoramas

**Not yet audited.** TMT sync hasn't happened locally. Apply the LTR scene-detection recipe (`docs/sets/ltr.md` §4a) once the family is synced.

Candidate: the 4-turtle character multi-print pattern (§3) could resemble a themed set rather than a spatial scene, similar to TLA's neonink 4-card themed chase.

Update this section when a scene audit runs.

---

## 5. Unobtainable rules

`selectors.FAMILY_UNOBTAINABLE_RULES["tmt"]` — not configured. No LTR-style scroll-frame equivalent surfaced yet.

Globally filtered:
- `serialized` promo_type.
- `rebalanced` / `alchemy` promo_types.

---

## 6. PRM destinations

**TMT audit incomplete.** No promo set (`ptmt`?) observed via `mm set list-related tmt`. The family may not have a dedicated prerelease-promo set code, or the release-window audit hasn't surfaced one yet. Query `.claude/skills/scryfall-search/scryfall.sh raw '/sets' ''` filtered to 2026-03 release date if the user presents a TMT PRM card.

Fill this section on next audit.

---

## 7. Edge cases & gotchas

- **`tmc` set_type=eternal but content=Commander** — the canonical UB `set_type` gotcha (per `docs/scryfall-set-families-and-bonus-sheets.md` §3). "Heroes in a Half Shell" is a preconstructed Commander deck; Scryfall classified it as `set_type: eternal` for reasons unclear to us. Don't hard-code assumptions like "commander decks are `set_type: commander`" — walk the family graph.
- **`pza` has only 20 cards** — much smaller than FIN's `fca` (66) and SPM's `mar` (100). Suggests TMT's masterpiece sheet is a lightweight reskin — fewer distinct arts to catalog.
- **`japanshowcase` prints in scope for missing-set** — even though `sets.py:EXCLUDED_PROMO_TYPES` filters japanshowcase from master-list output, selectors-side these ARE materialized. If the user wants japanshowcase excluded from missing-set too, an entry in `FAMILY_UNOBTAINABLE_RULES["tmt"]` with `promo_types_any_of: {"japanshowcase"}` would do it. Not currently added — awaiting user preference.
- **Local DB not synced** — as of this audit, `tmt` cards are not yet in the local DB (0 prints). Run `uv run mm set sync tmt` before using any inventory/selector queries. `mm query missing-set tmt` will error otherwise.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["tmt"]` — **not configured.** Recommended: `"tmt": frozenset({"surgefoil", "fracturefoil"})` (both are same-art dupes of siblings per audit).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["tmt"]` — not configured. If the user wants japanshowcase excluded, add `[{"promo_types_any_of": frozenset({"japanshowcase"})}]`.
- Related docs: [`../scryfall-set-families-and-bonus-sheets.md`](../scryfall-set-families-and-bonus-sheets.md) §3 (the tmc set_type-eternal gotcha).
