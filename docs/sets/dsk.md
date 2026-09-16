# `dsk` — Duskmourn: House of Horror

> Per-family memory doc. Read this before answering set-specific questions about
> `dsk` or working on `dsk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `dsk`
**Family root type:** `expansion`
**Family released:** `2024-09-27`
**Last audit:** `2026-09-15` via `/characterize-set dsk`.

---

## 1. Family map

7 Scryfall codes, all linked via `parent_set_code` (clean graph — no separately-
rooted bonus sheets). A standard modern expansion + Commander product.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dsk` | expansion | 419 | 2024-09-27 | parent |
| `dsc` | commander | 373 | 2024-09-27 | Duskmourn: House of Horror Commander decks |
| `pdsk` | promo | 160 | 2024-09-27 | promos — 80 cards × (`Np` promopack+stamped / `Ns` prerelease+datestamped) |
| `adsk` | memorabilia | 54 | 2024-09-27 | Art Series |
| `tdsk` | token | 19 | 2024-09-27 | tokens |
| `tdsc` | token | 23 | 2024-09-27 | Commander tokens |
| `ydsk` | alchemy | 30 | 2024-09-27 | Alchemy: Duskmourn (digital-only) |

`mm set master-list dsk` / `set:dsk+related` resolve the whole family from the
parent (no `--only` needed). 792 prints in the family total; the default-scoped
value-bearing sets are `dsk` (expansion) + `dsc` (commander).

---

## 2. Treatments

Which `promo_types` appear in this family, and how they map through
`treatments.compute_treatment()` (`src/magic_manager/treatments.py`).

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b` / `shw` (frame-dependent) | n/a (structural) | showcase / borderless frames; KEPT — the preferred collectible print |
| `japanshowcase` (+`boosterfun`) | `shw` | **no — unique art** | DSK 386-395 — the 5 Enduring + 5 Overlord mythics in the "Japan showcase" manga treatment, own illustration_id (Enduring Courage jp 392 `2ee73a3a` ≠ base 133/boosterfun 378 `7e6acd36`). KEPT as the preferred representative. |
| `fracturefoil` (+`japanshowcase`+`boosterfun`) | `shw\|ff` | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | DSK 396-405 — the fracture-foil premium of the japanshowcase art. Each shares its illustration_id EXACTLY with its japanshowcase-only sibling (all 10 verified: Enduring Courage 402↔392 `2ee73a3a`, Overlord of the Mistmoors 397↔387 `1e516888`, …). Same art on a fracture-foil sheet → dupe. Computes to `ff`, so the DUPE_FOIL gate catches it; drops the fracturefoil, keeps the japanshowcase. ~$1,768 total. Mirrors EOE/ECL/FDN exactly. |
| `doubleexposure` (+`boosterfun`) | `b` (nonfoil 351-355) / `b\|shw\|ff` (textured 406-410) | **no — unique art** | DSK 351-355 — the 5 headliner planeswalkers/creatures (Wandering Rescuer, Valgavoth, Tyvar, Kaito, Niko) in the borderless "double exposure" showcase, own illustration_id (Valgavoth 352 `136ad302` ≠ base 120 `7111e6eb`). KEPT — distinct art the collector may want. |
| `textured` (+`doubleexposure`+`boosterfun`) | `b\|shw\|ff` | **no — unique art (chase tier)** | DSK 406-410 — the textured-foil premium of the 5 double-exposure headliners. Each is its OWN illustration_id, distinct from both the base AND the plain doubleexposure sibling (Valgavoth textured 407 `23251999` ≠ doubleexposure 352 `136ad302`). NOT a dupe → the DUPE_FOIL/preferred filters KEEP them. Fancy-foil chase tier ($38-$307, ~$584 total). Left in scope (§5 sanity check — modest total, distinct art, wanted-chase like FIN's anime borderless). |
| `poster` (+`bundle`) | `b` | promo (distinct art) | DSC 371-373 (Archon of Cruelty / Goryo's Vengeance / Living Death) — borderless Commander-bundle poster promos, singletons ($13-$26). KEPT — distinct promo the user may want (like buyabox/bundle). |
| `promopack`+`stamped` | `''` (empty) | dupe (stamp) — but auto-dropped | pdsk `Np` prints. Compute to EMPTY treatment (not `regular`), so the GLOBAL preferred filter already drops them — verified NO leak into missing-set. No family rule needed (contrast TDM, where these compute to `regular` and needed a `stamped` rule). |
| `prerelease`+`datestamped` | `''` (empty) | dupe (stamp) — auto-dropped | pdsk `Ns` prints. Same as above — empty treatment, auto-dropped, no leak. |
| `bundle` / `buyabox` | `''` | promo | scattered singletons; auto-handled, kept if distinct. |

**Full-art convention:** standard (borderless/showcase carry `border_color:
borderless` or `frame_effects: showcase`/`inverted`; `full_art` not relied upon).

---

## 3. Chase variants

**None** by the `chase` modifier (0 rows) — no card name has ≥3 distinct-art
printings at the same `(name, treatment)`. The set's variety is base / showcase /
japanshowcase / fracturefoil / doubleexposure / textured tiers of a *given* art,
not multi-art of one card.

---

## 4. Scenes / posters / panoramas

**None (narrative scenes).** The only `poster` prints in the family are the 3
DSC Commander-bundle promos (371-373, poster+bundle) — three unrelated reprints
(Archon of Cruelty / Goryo's Vengeance / Living Death), not a contiguous
artist-run scene. Not encoded in `FAMILY_SCENES`.

---

## 5. Unobtainable rules

**None proposed.** No print in the family is being personally ruled out.

Scarcity-tier sanity check (2026-09-15): the top of
`missing treatment=collectible-alt --sort value-desc` is the fracturefoil dupes
(396-405, dropped by the DUPE_FOIL config below) and, beneath them, the textured
double-exposure headliners (406-410, ~$584 total: Valgavoth 407 $307, Kaito 409
$102, Tyvar 408 $75, Niko 410 $61, Wandering Rescuer 406 $39). The textured tier
is distinct art and modest in aggregate — treated as a **wanted chase** (FIN/TLA
default), NOT scarcity-junk, so it is KEPT. No `FAMILY_UNOBTAINABLE_RULES["dsk"]`
entry. (For reference: the tmt/tla/fin headliner rules were $2k-$3k EACH; DSK has
no comparable tier.)

**Missing-set impact (recorded 2026-09-15):** with the `{fracturefoil}` DUPE_FOIL
config and no unobtainable rule, the 10 fracturefoil dupes (CN 396-405,
~$1,768.08 in the inventory-relative missing list) drop out; their japanshowcase
siblings (386-395, treatment `shw`) remain as the preferred representative. No
pdsk stamped/prerelease leak (empty treatment, global-dropped). The textured
(406-410) + doubleexposure (351-355) unique-art prints stay in scope.

---

## 6. PRM destinations

Standard modern promo channels; `pdsk` holds them all (160 prints = 80 cards ×
two stamp variants):

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` (e.g. `133p`) | `pdsk` | Promo Pack (promopack + stamped) | Enduring Courage 133p |
| `Ns` (e.g. `133s`) | `pdsk` | Prerelease (prerelease + datestamped) | Enduring Courage 133s |

The `N` mirrors the main-set card. Resolve a presented PRM by name+stamp-type and
read the `pdsk` CN off the match. Both stamp variants compute to empty treatment,
so the preferred filter drops them automatically (no family rule).

---

## 7. Edge cases & gotchas

- **`ydsk` (alchemy)** is digital-only (Alchemy: Duskmourn, 30 cards) — globally
  filtered by the Arena/Alchemy `_is_digital_only` path. Verified no arena leak:
  `set:dsk+related missing | grep arena` returns nothing.
- **pdsk stamped prints compute to EMPTY treatment**, not `regular` — so they are
  dropped by the global preferred filter and DON'T leak into missing-set. This is
  the opposite of TDM (whose `Np` promopack prints computed to `regular` and
  needed an explicit `stamped` rule). No `stamped`/`datestamped` rule needed here.
- **`dsc` (commander)** is a normal `commander` set_type (373 cards) — no
  set_type mismatch like TMT's `tmc`.
- Two token sets (`tdsk` main, `tdsc` commander) — both excluded from the default
  value scope.
- **textured (406-410) is unique art, NOT a dupe** — each has its own
  illustration_id distinct from the plain doubleexposure sibling. Do not add
  `textured` to DUPE_FOIL (it would falsely drop distinct-art chases and, worse,
  wouldn't even pair — no same-art sibling exists).

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["dsk"]` — **proposed** (not yet
  applied): `frozenset({"fracturefoil"})` (10 fracturefoil mythics dupe their
  japanshowcase siblings; mirrors EOE/ECL/FDN).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["dsk"]` — **not configured** (no
  scarcity/taste exclusions; the textured headliner tier is a kept wanted-chase).
- `FAMILY_SCENES["dsk"]` — not configured (no narrative scenes; §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Duskmourn: House of Horror Commander decks | Commander deck | `dsc` (373 cards); 4 commander decks |
| Duskmourn: House of Horror Art Series | Art Series | `adsk` (54 cards) |
| Commander bundle poster promos | Bundle | DSC 371-373 (Archon of Cruelty / Goryo's Vengeance / Living Death), poster+bundle |

**Booster types (for `sealed-value` EV).** MTGJSON carries per-card WotC booster
weights for `dsk`. Enumerate with `uv run python scripts/sealed_value.py dsk --list-boosters`.

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `play` / `play-arena` | EV ~$6.9 / ~$6.6; coverage ~92.5% — the standard Play Booster (Duskmourn had no separate Draft/Set Booster; Play Boosters replaced them) |
| `collector` | EV ~$28.7; coverage 92.7% (some collector-sheet cards unpriced until synced) |
| `collector-sample` | EV ~$3.99; coverage 90% — sample-pack sheet |
| `nightmare` | EV ~$26.6; coverage 100% — the Duskmourn-specific "Nightmare" booster (themed premium pack); 1 layout |
| `prerelease` | EV ~$4.52; coverage 89.3% — the prerelease pack (points at pdsk datestamped prints) |
