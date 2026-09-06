# `tdm` — Tarkir: Dragonstorm

> Per-family memory doc. Read this before answering set-specific questions about
> `tdm` or working on `tdm`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `tdm`
**Family root type:** `expansion`
**Family released:** `2025-04-11`
**Last audit:** `2026-09-05` via `/characterize-set tdm`.

---

## 1. Family map

7 Scryfall codes, all linked via `parent_set_code` (clean graph — no separately-
rooted bonus sheets). A standard modern expansion + Commander product.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `tdm` | expansion | 427 | 2025-04-11 | parent |
| `tdc` | commander | 413 | 2025-04-11 | Tarkir: Dragonstorm Commander decks |
| `ptdm` | promo | 160 | 2025-04-11 | promos — 80 cards × (`p` promopack+stamped / `s` prerelease+datestamped) |
| `atdm` | memorabilia | 54 | 2025-04-11 | Art Series |
| `ttdm` | token | 16 | 2025-04-11 | tokens |
| `ttdc` | token | 34 | 2025-04-11 | Commander tokens |
| `ytdm` | alchemy | 30 | 2025-04-11 | Alchemy: Tarkir (digital-only) |

`mm set master-list tdm` / `set:tdm+related` resolve the whole family from the
parent. 840 prints in the family total; the default-scoped value-bearing set is
`tdm` (expansion) + `tdc` (commander).

---

## 2. Treatments

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b` / `shw` / `ext` (frame-dependent) | n/a (structural) | showcase (`showcase`+`inverted`) frames; KEPT — the preferred collectible print |
| `halofoil` (+`boosterfun`) | `b\|shw\|ff` | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | TDM 409-418 — the 10 halofoil mythics (Ugin 409, Clarion Conqueror 410, Elspeth 411, Dracogenesis 412, Sarkhan 413, Craterhoof 414, All-Out Assault 415, Death Begets Life 416, Narset 417, Skirmish Rhino 418), foil-only, $17-$457. Each shares its `illustration_id` with a `boosterfun` showcase sibling (Ugin 409↔399 `b49ffc89`, Elspeth 411↔401 `b9668943`, Craterhoof 414↔404 `6469e9bf`, All-Out Assault 415↔405 `5405b6d5`, …) — same art, halofoil sheet. Computes to `ff`, so the DUPE_FOIL gate catches it; drops the halofoil, keeps the showcase. Total ~$1,451 |
| `serialized`+`headliner`+`doublerainbow` | `shw\|ff` | scarcity → dropped by GLOBAL filter | TDM 419 Mox Jasper — the family's headline serialized chase, foil-only, ~$2,750. `serialized` is in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so it never reaches missing-set. §5 lists a documented no-op rule for parity |
| `promopack` (+`stamped` on ptdm) | `regular` | dupe (stamp) → `FAMILY_UNOBTAINABLE_RULES` | ptdm `Np` prints — promo-pack stamped copies of base cards. Same card + a stamp; compute to `regular` so they bypass the preferred dedup and would leak into missing-set. Excluded via the `stamped` rule (§5) |
| `datestamped` (+`prerelease` on ptdm) | `regular` | dupe (stamp) → same `stamped`? NO | ptdm `Ns` prints — prerelease datestamped copies. NOTE: these carry `datestamped`, not `stamped` — the §5 rule keys on `stamped` and the `p` (promopack) sibling; verify the `s` prerelease prints are also caught (see §5 note) |
| `promopack` (on tdm 420-424) | `regular` | dupe of base | TDM 420-424 Static Snare/Roiling Dragonstorm/Strategic Betrayal/Channeled Dragonfire/Encroaching Dragonstorm — cheap ($0.15-$1.16), each has a plain base sibling (26/55/94/…). Low-value dupes |
| `buyabox` | `''` | promo | TDM 426 Qarsi Revenant — buy-a-box promo, singleton (~$0.85). KEPT — a distinct promo the user may want |
| `bundle` | `''` | promo | TDM 425 Temur Battlecrier — bundle promo, singleton (~$1.16). KEPT |

**Full-art convention:** standard (borderless/showcase carry `border_color:
borderless` or `frame_effects: showcase`/`inverted`; `full_art` not relied upon).

---

## 3. Chase variants

**None** by the `chase` modifier (0 rows) — no card name has ≥3 distinct-art
printings at the same `(name, treatment)`. The set's variety is base/showcase/
halofoil tiers of the *same* art, not multi-art of one card.

---

## 4. Scenes / posters / panoramas

**None.** The borderless-inverted block (71 prints) has two 3-card contiguous
runs by Tomas Duchek (TDM 339-341, 343-345), but inspection shows they are
UNRELATED cards (Rot-Curse Rakshasa / The Sibsig Ceremony / Sidisi; Cori-Steel
Cutter / Stadium Headliner / Tersa Lightshatter) that merely share an artist in
nearby CNs (split by Kevin Glint at 342) — a false-positive of the artist-run
heuristic, not a narrative scene. Not encoded in `FAMILY_SCENES`.

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["tdm"]` in `src/magic_manager/selectors.py`.

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {stamped}` | ptdm promo-pack STAMP variants — the `Np` promopack+stamped prints (same card as a kept base/showcase sibling + a stamp) compute to `regular` (bypass preferred dedup) and would leak ~$689 of duplicate stamped prints into missing-set. Mirrors the ONE family's `stamped` rule. |
| `promo_types_any_of: {serialized, headliner, doublerainbow}` | TDM 419 Mox Jasper (serialized+headliner+doublerainbow, foil-only, ~$2,750) — the family's headline chase. **Documented no-op:** `serialized` is already in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so 419 is filtered before this rule applies. Kept for parity/discoverability with the INR/ACR/ECL/SOS headliner families. |

**Note on the `s` (prerelease datestamped) prints:** ptdm `Ns` prints carry
`prerelease`+`datestamped`, NOT `stamped`. The `stamped` rule above catches the
`Np` promopack twins but NOT the `Ns` prerelease twins. If prerelease datestamped
prints leak into missing-set, widen the rule to
`promo_types_any_of: {stamped, datestamped}` (verify against the ONE family, which
used `stamped` only — its prerelease prints may compute differently). Recorded as
a watch-item; recheck the missing-set total after the config lands.

**Missing-set impact (recorded 2026-09-05):** with the `{halofoil}` DUPE_FOIL
config + the `{stamped}` rule, `missing treatment=preferred` resolves to **141
prints**. The halofoil tier (~$1,451) and the promo-pack stamp tier (~$689) drop
out; Mox Jasper (~$2,750) was already global-filtered. Verified no `stamped`/
`prerelease` leak, and the halofoil dedup pairs correctly — the top of the list is
the KEPT showcase prints (Ugin 399 showcase $114, Elspeth 401 $96, Craterhoof 404
$63), not the dropped halofoil 409-418. No scarcity-tier bloat.

---

## 6. PRM destinations

Standard modern promo channels; `ptdm` holds them all (160 prints = 80 cards ×
two stamp variants):

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` (e.g. `103p`) | `ptdm` | Promo Pack (promopack + stamped) | Cori-Steel Cutter 103p |
| `Ns` (e.g. `103s`) | `ptdm` | Prerelease (prerelease + datestamped) | Cori-Steel Cutter 103s |

The `N` mirrors the main-set card. Resolve a presented PRM by name+stamp-type and
read the `ptdm` CN off the match.

---

## 7. Edge cases & gotchas

- **`ytdm` (alchemy)** is digital-only (Alchemy: Tarkir, 30 cards) — globally
  filtered by the Arena/Alchemy `_is_digital_only` path. Verified no arena leak:
  `set:tdm+related missing | grep arena` returns nothing.
- **Mox Jasper 419** is the serialized headliner (~$2,750) — global-filtered.
- **`tdc` (commander)** is a normal `commander` set_type (413 cards) — no
  set_type mismatch like TMT's `tmc`.
- Two token sets (`ttdm` main, `ttdc` commander) — both excluded from the default
  value scope.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["tdm"]` — **configured**: `frozenset({"halofoil"})` (10 halofoil mythics dupe their showcase siblings).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["tdm"]` — **configured**: `[{"promo_types_any_of": frozenset({"stamped"})}, {"promo_types_any_of": frozenset({"serialized", "headliner", "doublerainbow"})}]` (promo-pack stamp tier + documented-no-op serialized headliner).
- `FAMILY_SCENES["tdm"]` — not configured (no narrative scenes; §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Tarkir: Dragonstorm Commander decks | Commander deck | `tdc` (413 cards); 5 wedge-clan decks |
| Tarkir: Dragonstorm Art Series | Art Series | `atdm` (54 cards) |
| Buy-a-Box / Bundle promos | Buy-a-Box / Bundle | Qarsi Revenant (`tdm` 426, buyabox), Temur Battlecrier (`tdm` 425, bundle) |

**Booster types (for `sealed-value` EV).** MTGJSON carries per-card WotC booster
weights for `tdm`. Enumerate with `uv run python scripts/sealed_value.py tdm --list-boosters`.

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `collector` | EV ~$32; coverage 87.8% (some collector-sheet cards from other sets unpriced until synced) |
| `collector-sample` | EV ~$2.86; low coverage (66%) — sample-pack sheet references unsynced prints |
| `play` / `play-arena` | EV ~$6 |
| `prerelease` (+ 5 clan variants: `prerelease-abzan/jeskai/mardu/sultai/temur`) | one per wedge clan; each ~$3.60-$5.55. The clan variants are the wedge-specific prerelease packs |

---
