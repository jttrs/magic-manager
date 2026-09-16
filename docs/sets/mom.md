# `mom` — March of the Machine

> Per-family memory doc. Read this before answering set-specific questions about
> `mom` or working on `mom`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mom`
**Family root type:** `expansion`
**Family released:** `2023-04-21`
**Last audit:** `2026-09-15` via `/characterize-set mom` (steps 1-9).

---

## 1. Family map

11 Scryfall codes, ALL linked via `parent_set_code: mom` (clean graph — no
separately-rooted bonus sheets). Notably `mul` (Multiverse Legends masterpiece)
and `moc` (Commander) are BOTH properly parented to `mom` — despite the nuance,
`set:mom+related` resolves the whole family from the parent (verified via
`mm set list-related mom`).

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mom` | expansion | 387 | 2023-04-21 | parent |
| `moc` | commander | 450 | 2023-04-21 | 5 Commander decks (Call for Backup, Cavalry Charge, Divine Convocation, Growing Threat, Tinker Time) |
| `mul` | masterpiece | 261 | 2023-04-21 | **Multiverse Legends** bonus sheet (65 legends × base-showcase / etched / halofoil / serialized). Parented to `mom`, NOT separately-rooted |
| `pmom` | promo | 134 | 2023-04-21 | promos — 54 `Np` promopack+stamped + 80 `Ns` prerelease+datestamped |
| `amom` | memorabilia | 81 | 2023-04-21 | Art Series |
| `fmom` | memorabilia | 5 | 2023-04-21 | Jumpstart Front Cards (Brood/Buff/Expendable/Overachiever/Reinforcement pack-title cards) |
| `tmom` | token | 23 | 2023-04-21 | tokens |
| `tmoc` | token | 46 | 2023-04-21 | Commander tokens |
| `tmul` | token | 2 | 2023-04-21 | Multiverse Legends tokens |
| `wmom` | token | 12 | 2023-04-21 | Japanese promo tokens |
| `smom` | token | 1 | 2023-04-21 | Substitute (helper) card |

1232 prints in the family total. Default value-bearing scope: `mom` (expansion)
+ `moc` (commander) + `mul` (masterpiece). **No separately-rooted bonus sheets**
— `set:mom+related` and `mm set master-list mom` need no `--only`.

**Sibling-but-not-family:** `mat` (March of the Machine: The Aftermath, expansion,
2023-05-12) is the release's epilogue micro-set. It has `parent_set_code: null`
and is its OWN characterized family (`docs/sets/mat.md`) — NOT part of
`set:mom+related`.

---

## 2. Treatments

The dominant structural fact is the **`mul` (Multiverse Legends) 4-version grid**:
each of the 65 legends prints as base-showcase (CN 1-65, nonfoil+foil), **etched**
(CN 66-130, foil, DISTINCT etched art), **halofoil** (CN 131-195, foil, SAME art
as base-showcase), and **serialized** (`z` suffix, e.g. 133z, doublerainbow, same
art, globally filtered).

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `halofoil` | `b\|shw\|ff` / `shw\|ff` | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | 65 prints (mul 131-195). Foil-only "halo foil" sheet over the base-showcase art. Each shares its illustration_id with the base showcase (Aegar 161↔31 `d114f3c0`, Anafenza 131↔1 `9247ed0e`, Aurelia 165↔35 `66459a4b`). Computes to `ff`, so the DUPE_FOIL gate catches it. **All 65 pair cleanly** to a same-name same-codes-minus-ff sibling (verified programmatically — 0 stragglers), UNLIKE `mat`'s Tyvar frame-mismatch case, so DUPE_FOIL (not a §5 rule) is the correct home. Keeps the base showcase, drops the halofoil. |
| `boosterfun` | `b` / `shw` / `ext` (frame-dependent) | n/a (structural) | 131 prints — standard showcase / borderless-inverted / extended-art alt-arts across mom+moc+mul. KEPT — the preferred collectible print. |
| etched (`frame_effects: etched`, no promo_type) | (etched) | **no — DISTINCT art** | mul 66-130. The Multiverse Legends etched-foil version has its OWN illustration_id (Aegar 96 `f661d604` ≠ base `d114f3c0`). Distinct art, KEPT. |
| `ravnicacity` | `shw` | **no — distinct showcase art** | 16 prints (mom 303-305 + mul Ravnica-City showcases). The Ravnica-guild-themed showcase frame. KEPT. Its halofoil twins (e.g. Aurelia mul 165 `halofoil,ravnicacity`) are dropped by the halofoil DUPE_FOIL entry. |
| `serialized` + `doublerainbow` | `b\|ff` / `b\|shw\|ff` | scarcity → dropped by GLOBAL filter | 70 prints: the 5 Praetor transform duals (mom 338-342 Elesh Norn/Jin-Gitaxias/Sheoldred/Urabrask/Vorinclex, foil-only, $1,000-$4,000 each) + the 65 mul `z` serialized twins ($290-$1,000 each). `serialized` is in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so all 70 drop before missing-set — the ~$40k+ scarcity tier never surfaces. §5 documents a no-op rule for parity. |
| `promopack` + `stamped` | `''` (regular) | dupe (stamp) → `FAMILY_UNOBTAINABLE_RULES` | 54 `pmom` `Np` prints. Same card as a kept base/showcase sibling + a promo-pack stamp; compute to EMPTY treatment (`regular`), so they never enter the `preferred`/collectible-alt slice — but they LEAK into the rare/mythic-regular sub-selectors of `missing-set`. Excluded via the `{stamped}` rule (§5). Mirrors SNC/EOE/ECL/SOS/MAT. |
| `prerelease` + `datestamped` | `''` (regular) | dupe (stamp) → built-in filter | 80 `pmom` `Ns` prints. Prerelease datestamped copies of base cards. Carry `datestamped`, so the built-in `_apply_preferred_post_filter` Step-2 datestamped-with-sibling check drops them from the rare/mythic-regular sub-selectors automatically — **no family rule needed**. |
| `bundle` | `''` | promo | mom 383? no — the bundle promo is a singleton. KEPT. |
| `buyabox` | `''` | promo | singleton buy-a-box promo. KEPT. |

**Full-art convention:** standard (borderless/showcase carry `border_color:
borderless` or `frame_effects: showcase`/`inverted`; `full_art` not relied upon).

---

## 3. Chase variants

**None** by the `chase` modifier — the canonical enumeration
(`set:mom+related missing rarity=uncommon treatment=regular chase`) returns 0
rows, and `chase:5` returns 0. No card name has ≥3 distinct-art printings at the
same `(name, treatment)`. The set's variety is the base/showcase/etched/halofoil/
serialized tiers of the SAME art (the mul grid), not multi-art of one card.

(NB: `set:mom+related chase` with no `missing` returns 277 rows — that's the
include-owned regular-print listing, a heuristic artifact, NOT chase variants.)

---

## 4. Scenes / posters / panoramas

**None.** The borderless-inverted block has no contiguous same-artist run of ≥3.
The 5 Praetor transform duals (mom 292-301 borderless-inverted showcases) are by
mixed artists (Kekai Kotaki, Dominik Mayer, Flavio Girón) at non-contiguous CNs
(292/294/297/299/301) — a false-positive of the artist-run heuristic, not a
narrative scene. Not encoded in `FAMILY_SCENES`.

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["mom"]` in `src/magic_manager/selectors.py`.

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {stamped}` | The 54 `pmom` `Np` promopack+stamped prints — same card as a kept base/showcase sibling + a stamp, priced on scarcity. Compute to empty (`regular`) treatment so they bypass the `preferred` dedup but LEAK into the rare/mythic-regular sub-selectors of `missing-set` (~$127 of duplicate stamped prints). `_apply_preferred_post_filter` applies `_is_family_unobtainable` to those sub-selectors, so this rule removes them. Signal is `stamped` ONLY (the 80 `Ns` prerelease twins carry `datestamped`, caught separately by the built-in Step-2). Validated: 0 `promopack`-without-`stamped` alt-arts in `pmom`, so `{stamped}` is exact (no SNC-style alt-art trap). Mirrors SNC/EOE/ECL/SOS/MAT. |
| `promo_types_any_of: {serialized, doublerainbow}` | The Praetor transform duals (mom 338-342, serialized+doublerainbow+boosterfun, foil-only, $1,000-$4,000) + the 65 mul `z` serialized twins ($290-$1,000). **Documented no-op:** `serialized` is already in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so all 70 drop before this rule applies. Kept for parity/discoverability with the INR/ECL/SOS/TDM serialized-headliner families. |

**Missing-set impact (recorded 2026-09-15, 355/525 owned):** with the `{halofoil}`
DUPE_FOIL config + the `{stamped}` rule, full `missing-set mom` resolves to **208
prints / $703.12** (from **262 / $829.87** with halofoil-dupe only and no stamped
rule). The 54 `pmom` promopack-stamp prints drop out (54 rows, ~$127); the 80
prerelease-datestamped prints were already dropped by the built-in filter; the 65
halofoils dedup to their base showcase (176→111 in the `preferred` slice); the 70
serialized prints ($40k+ tier) were already global-filtered. Top of the list is
legit collectible showcase mythics (Ragavan mul 21 nonfoil $44, Etali mom 298
$26, Sheoldred/Atraxa mul $24), no scarcity artifact, no arena leak. **No
concentration problem.**

---

## 6. PRM destinations

Standard modern promo channels; `pmom` holds them all (134 prints):

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` (e.g. `174p`) | `pmom` | Promo Pack (promopack + stamped) | Ancient Imperiosaur 174p |
| `Ns` (e.g. `174s`) | `pmom` | Prerelease (prerelease + datestamped) | Ancient Imperiosaur 174s |

The `N` mirrors the main-set card. Resolve a presented PRM by name+stamp-type and
read the `pmom` CN off the match. `wmom` holds 12 Japanese promo tokens (separate
JP-market channel). No anchor-specific mention in `bulk-add/SKILL.md` yet.

---

## 7. Edge cases & gotchas

- **`mul` (Multiverse Legends) is a 4-version grid** — base-showcase (1-65) /
  etched (66-130) / halofoil (131-195) / serialized `z`. Base + etched are
  distinct-art KEPT; halofoil is a same-art DUPE (dropped via §8 DUPE_FOIL);
  serialized global-filtered. The etched art differs from the showcase art
  (verified illustration_id), so it is NOT a dupe.
- **All 65 halofoils pair cleanly** — unlike `mat`'s Tyvar frame-mismatch
  straggler, so DUPE_FOIL is the robust home (not a wholesale §5 rule). Verified
  programmatically: 0 halofoils fail the `(name, codes-minus-ff)` sibling match.
- **Praetor transform duals (mom 338-342)** are the family's headline serialized
  chase (Elesh Norn // The Argent Etchings foil ~$4,000) — global-filtered via
  `serialized`.
- **`mat` is NOT in this family** — the Aftermath epilogue set is separately
  rooted (`parent_set_code: null`), its own `docs/sets/mat.md`.
- **Historic Brawl precons (Braaains, Collateral Damage, Flashy Fliers, Lightly
  Armored, …)** filed under `mom` in MTGJSON are Arena-only (releaseDate
  2024-07-08) — digital, not physical products.
- **Alchemy leak check:** verified no `arena`-stamped card appears in
  `set:mom+related missing` (`mul` has 1 rebalanced + 1 alchemy print, both
  digital, globally filtered).

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["mom"]` — **PROPOSED**: `frozenset({"halofoil"})` (65 mul halofoils dupe their base-showcase siblings; all pair cleanly, so DUPE_FOIL is exact). Mirrors the TDM halofoil case.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["mom"]` — **PROPOSED**: `[{"promo_types_any_of": frozenset({"stamped"})}, {"promo_types_any_of": frozenset({"serialized", "doublerainbow"})}]` (54 `Np` promo-pack stamps + documented-no-op serialized Praetor/`z` tier).
- `FAMILY_SCENES["mom"]` — not configured (no narrative scenes; §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| March of the Machine Commander decks | Commander deck | `moc` (450 cards); 5 decks — Call for Backup, Cavalry Charge, Divine Convocation, Growing Threat, Tinker Time |
| Multiverse Legends | masterpiece / bonus sheet | `mul` (261 cards); 65 legends × base-showcase/etched/halofoil/serialized. Play/Collector-booster insert |
| MOM Jumpstart packs | Jumpstart | 5 themes (Brood/Buff/Expendable/Overachiever/Reinforcement) × 2 versions = 10 packs (`*1_MOM`/`*2_MOM`); front cards in `fmom`. **Fixed decks → deck value, not booster EV.** Use `mm set jumpstart-list mom` |
| March of the Machine Art Series | Art Series | `amom` (81 cards) |
| Bundle / Welcome Booster | Bundle / Welcome Booster | `MarchOfTheMachineBundleLandPack_MOM`, `MarchOfTheMachineWelcomeBooster_MOM` |
| Historic Brawl precons | (Arena-only) | Braaains/Collateral Damage/Flashy Fliers/Lightly Armored/… — digital, 2024-07-08, not physical |

**Booster types (for `sealed-value` EV).** MTGJSON carries per-card WotC booster
weights for `mom`. Enumerate with `uv run python scripts/sealed_value.py mom --list-boosters`.

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `draft` | EV ~$6.31; coverage 86% |
| `set` | EV ~$6.82; coverage 76% (Multiverse Legends sheet references partly unpriced until `mul` synced) |
| `collector` | EV ~$22.33; 24 layouts (base/showcase/etched/halofoil + mul sheet) |
| `collector-sample` | EV ~$3.57 |
| `prerelease` | EV ~$6.68 |
| `jumpstart` | EV ~$13; coverage 100%. **Jumpstart packs are FIXED decks → value as decks, not booster EV** (the 10 `*_MOM` Jumpstart decks) |
| `arena` | EV ~$6.20 (digital) |
