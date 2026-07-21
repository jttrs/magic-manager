# `fin` — Final Fantasy

> Per-family memory doc. Read this before answering set-specific questions about
> `fin` or working on `fin`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `fin`
**Family root type:** `expansion`
**Family released:** 2025-06-13
**Last audit:** 2026-07-08 (backfilled from session context)

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `fin` | expansion | 599 | 2025-06-13 | parent — includes Cid, Timeless Artificer chase (§3) |
| `fic` | commander | 486 | 2025-06-13 | Four commander decks; contains FIC Secret Rendezvous chase |
| `fca` | masterpiece | 66 | 2025-06-13 | Final Fantasy: Through the Ages — UB reskin sheet with `sourcematerial` promo_type |
| `pfin` | promo | 94 | 2025-06-13 | Prerelease datestamped promos (`Ns` CNs) |
| `pss5` | promo | 2 | 2025-06-13 | FIN Standard Showdown premiums |
| `rfin` | promo | 2 | 2025-06-13 | Regional promos — **Japan-only distribution** (English collectors typically skip) |
| `afin` | memorabilia | 53 | 2025-06-13 | Art Series |
| `afic` | memorabilia | 24 | 2025-12-05 | Final Fantasy Scene Box — physical display product |
| `tfin` | token | 37 | 2025-06-13 |  |
| `tfic` | token | 11 | 2025-06-13 |  |
| `wfin` | token | 3 | 2025-06-13 | FIN Asia WPN Promo Tokens |

**Separately-rooted bonus sheets:** none — FIN's family is fully linked via `parent_set_code`.

**`mm` invocations:** default `set:fin+related` resolution works correctly.

---

## 2. Treatments

`selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["fin"] = frozenset({"surgefoil"})` (see `src/magic_manager/selectors.py:81`).

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `surgefoil` | `ff` | **yes** → in DUPE_FOIL | Same-art fancy-foil sheet. Canonical example: FIN 532 Prompto (surgefoil) is same art as FIN 387 (no surgefoil), just on a fancy-foil finish. Filtered as a dupe when the sibling exists. |
| `chocobotrackfoil` | `ff` | **no — unique art** | Intentionally NOT in DUPE_FOIL. FIN 564 Cloud, Midgar Mercenary has `chocobotrackfoil` but is a **unique art** (different painting than FIN 375 or other Cloud variants), just on a chocobo-track fancy-foil sheet. Kept in missing-set output. |
| `sourcematerial` | `sm` | n/a (part of masterpiece sheet) | Discriminator for FCA "Through the Ages" reskin sheet — 66 cards, borderless full-art, often with `flavor_name` populated for the theme rename. See `docs/scryfall-printing-treatments.md` §4a. |
| `ffi` through `ffxvi` | (metadata only) | n/a | Per-game tags on FCA (and some pfin/pss5 prints). Not a visual treatment; informational only. |

**Full-art convention:** FIN prints follow the older UB convention — borderless-inverted cards have `full_art: false` (unlike SPM/TLA/TMT which flipped this). See `docs/scryfall-printing-treatments.md` §6.5.

---

## 3. Chase variants

Detected by `selectors._modifier_chase` (default threshold 3, added `751e627`). The `mm query missing-set fin` pipeline includes an `uncommon-chase` sub-selector that surfaces these.

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Cid, Timeless Artificer | 15 | `fin` 216, 407–420 | uncommon | regular |
| Cid, Timeless Artificer (ext) | 1 | `fin` 480 | uncommon | ext |
| Cid, Freeflier Pilot | 2 | `fic` 13, 131 | rare | regular + ext |
| Secret Rendezvous | 4 | `fic` 217, 218, 219, 253 | uncommon | 217–219 regular, 253 surgefoil-only |

**Cid, Timeless Artificer** is the canonical FIN chase: 15 distinct arts across FIN 216 (Cid of FF XIV, standard base slot) and 407–420 (one per FF game II through XVI, `boosterfun` treatment). Every FF-game Cid corresponds to a specific numbered game — this is the completionist's target set. Ext-treatment FIN 480 is the FF XIV Cid in extended-art frame.

**Secret Rendezvous** is the FF7 Gold Saucer date-scene cycle — **four distinct arts** (all Yuu Fujiki), each pairing Cloud with a different date partner at the fireworks (verified by image + distinct `illustration_id` per print):
- `fic` 217 — Yuffie ("Hey! Say something, why don't you!")
- `fic` 218 — Aerith ("It's beautiful, isn't it?")
- `fic` 219 — Barret ("Hey spike-head...")
- `fic` 253 — Tifa ("Ok, I'm going to just go ahead and say it...")

None are extended-art — all four use the standard bordered frame. 217–219 have plain nonfoil/foil finishes; **253 (Tifa) exists ONLY as surgefoil** (its unique art has no non-surgefoil printing).

⚠️ **Known filter gap:** because 253 carries the `surgefoil` promo_type, `FAMILY_DUPE_FOIL_PROMO_TYPES["fin"]` (§2) drops it from `mm query missing-set fin` as if it were a same-art fancy-foil dupe. But 253 is a UNIQUE art (Tifa), not a foil reprint of 217–219 — so a completionist chasing all four date scenes will never be told to buy the Tifa one. The `surgefoil`-is-always-a-dupe assumption holds for FIN's basic lands but breaks for this card. Not yet fixed in code; see §8.

---

## 4. Scenes / posters / panoramas

**No verified scene groupings** in FIN so far. `docs/scryfall-printing-treatments.md` lines 275-283 note that FIC 460–475 might be a "scene box" range analogous to LTR 399–451, but this has NOT been audited and confirmed via artist-run detection. Rerun the detection recipe from `docs/sets/ltr.md` §4a against FIN if the question comes up.

**FCA masterpiece sheet** (66 cards, `fca` 1–66) is a bonus-sheet-per-FF-game grouping (`ffi` through `ffvii` tags on prints), not a spatial "scene" — the sheet is themed but the cards aren't a physical panorama.

**Scene Box product `afic`** (24 memorabilia cards, released 2025-12-05) is a physical display box distinct from the borderless main-set prints. Excluded from default checklists (memorabilia).

---

## 5. Unobtainable rules

`selectors.FAMILY_UNOBTAINABLE_RULES["fin"]` — **not configured** (no LTR-style scroll-frame equivalent surfaced yet).

FIN's `rfin` regional promos (2 cards, Japan-only distribution) are functionally unobtainable for English collectors but are handled generically by `sets.py:180-188` (non-English-only imports get zero rows).

Also filtered globally (not via FIN-specific rules):
- `serialized` promo_type → any 1-of-N chase prints.
- `rebalanced` / `alchemy` promo_types → digital-only Arena/Alchemy prints (many exist for FIN: A-Vivi Ornitier at FIN A-248, etc.).

---

## 6. PRM destinations

FIN's PRM-stamped physical promo cards can land in these Scryfall set codes:

| Physical stamp | Scryfall set | Channel | Example |
|---|---|---|---|
| Prerelease datestamped, CN `Ns` | `pfin` | Set prerelease | `pfin` 38s Aerith (name resolves via artist) |
| Play Promo, small CN | `pw25` | WPN Play Promo | `pw25` 2 Despark (artist Maji) |
| Regional Japan-only | `rfin` | Regional | `rfin` 1-2 |
| Standard Showdown premiums | `pss5` | In-store event | `pss5` 1 Ultima, `pss5` 2 Squall SeeD Mercenary |

Physical CN often doesn't match Scryfall CN (leading zeros stripped, or `Ns` suffix pattern). Resolve by name+artist per `.claude/skills/bulk-add/SKILL.md` PRM guidance.

---

## 7. Edge cases & gotchas

- **Digital-only Arena prints** — FIN has extensive A-prefixed Alchemy rebalanced variants (e.g. FIN A-248 A-Vivi Ornitier). All filtered globally by `UNOBTAINABLE_PROMO_TYPES`.
- **FCA `flavor_name` mixed** — some FCA cards have `flavor_name` populated (renamed to a FF-themed name), others don't (kept oracle name because it fit the theme). Both kinds are still part of the reskin sheet — discriminator is `sourcematerial` in `promo_types`, not `flavor_name`. See `docs/scryfall-printing-treatments.md` §4a.
- **`wfin` FIN Asia WPN Promo Tokens** — 3 tokens with `w`-prefix set code (unusual). Token set, excluded by default from checklists.
- **`rfin` Japan-only** — the 2 regional promo prints only exist in Japanese; English collectors treat as unobtainable. `sets.py:180-188` filters these correctly via language check.

---

## 8. Code refs

- `selectors.py:78-90` — `FAMILY_DUPE_FOIL_PROMO_TYPES["fin"] = frozenset({"surgefoil"})`. **Known false-positive:** this drops FIC 253 Secret Rendezvous (Tifa) as a "surgefoil dupe" even though its art is unique (§3). A precise fix would exempt prints whose `illustration_id` has no non-surgefoil sibling in the family, rather than treating `surgefoil` as unconditionally dupe. Low priority (one card), but revisit if more surgefoil-only unique arts surface.
- `selectors.py:_modifier_chase` — surfaces Cid + Secret Rendezvous chases via `mm query missing-set fin` (but NOT 253, per the filter gap above)
- FCA reskin sheet handling — no per-family code; discovered via `sourcematerial` promo_type in `treatments.py:114`
- Related docs: [`../scryfall-printing-treatments.md`](../scryfall-printing-treatments.md) §4a (FCA reskin sheet properties), §6.5 (full_art convention).
