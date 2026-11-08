# `fra` — `Reality Fracture`

> Per-family memory doc. Read this before answering set-specific questions about
> `fra` or working on `fra`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `fra`
**Family root type:** `expansion`
**Family released:** 2026-10-02 (Secret Lair Bundle promos + a few foil-only borderless prints dated 2026-10-23; Alchemy 2026-10-13)
**Last audit:** 2026-11-02 via `/characterize-set fra` (batch run; tier decisions pending owner review).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `fra` | expansion | 461 (Scryfall `/sets` says 462; search returns 461) | 2026-10-02 | parent. Main set CN 1–290 (281–290 basics), boosterfun 291–461 |
| `frc` | commander | 103 | 2026-10-02 | ONE Commander deck, *Multiverse Reforged* (Jace, Multiverse Architect, FRC 1). CN 1–2 borderless face cards; CN ~89–103 extended-art (collector-booster only, nonfoil) |
| `pfra` | promo | 90 | 2026-10-02 | Promo Pack `Np` (promopack + stamped) only — **no prerelease `Ns` datestamped prints** |
| `afra` | memorabilia | 54 | 2026-10-02 | Art Series (double-faced art cards) |
| `tfra` | token | 18 | 2026-10-02 | tokens |
| `tfrc` | token | 17 | 2026-10-02 | commander tokens (parent `frc`) |
| `yfra` | alchemy | 31 | 2026-10-13 | digital-only, `security_stamp: arena` |

**Separately-rooted bonus sheets:** none. Checked Scryfall `/sets` 2026-09-20 → 2026-11-05: only `mbc` (Mystery Booster Commander, unrelated) and `tfdc` (FDN) are outside the family. `set:fra+related` covers everything; no `--only` needed.

**Special Guests live in `spg`, not here:** FRA Play Boosters carry a `specialGuest` sheet of 10 cards = **SPG 159–168** (Austere Command, Consider, Consign to Memory, Eye of Ugin, Flesh Duplicate, Mind Twist, Necrodominance, Root Maze, Splinter Twin, Sublime Epiphany). See [`spg.md`](spg.md).

---

## 2. Treatments

Computed via `treatments.compute_treatment` (survey 2026-11-02). Every class below is named for `audit_treatment_coverage.py`.

**Frame/finish treatment classes present:**

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | ~290 | `fra` 1–290, `frc`, `pfra` | `regular` | handled by rarity/base sub-selectors |
| borderless legends / planeswalkers | 30 | `fra` 291–320 | `b` (inverted, mostly +legendary) | KEPT (default) — pending owner review. Paired "reality" versions (e.g. Ajani Resolute 291 / Ajani Unrelenting 308) |
| borderless full-art mythic/rare (nonfoil-only) | 13 | `fra` 321–333 | `b` (inverted, `full_art: true`, nonfoil only) | KEPT (default) — pending owner review. Foil of the same art is the facetfoil 449–461 |
| borderless showcase | 25 | `fra` 334–358 | `shw` (borderless, `showcase`) | KEPT (default) — pending owner review. The family's borderless-showcase frame |
| borderless "braintwister" | 23 | `fra` 359–381 | `b` (363 Jace has no `inverted` → computes `''`/regular-ish but borderless) | KEPT (default) — pending owner review. MTGJSON sheet `braintwisterFrc` (collector slot shared with frc cards) |
| borderless basics ("tower lands") | 15 | `fra` 382–396 | `b` (`full_art`) | KEPT (default) — 3 arts × 5 basics, same artist per type |
| borderless dual lands | 5 | `fra` 397–401 | `b` | KEPT (default) — Piotr Dura cycle |
| **Japan showcase (black border)** | 10 | `fra` 403–412 | `b\|shw` (black border, `showcase`+`inverted`, foil-only, `japanshowcase`) | **KEPT (default) — pending owner review.** High-risk class: black-bordered showcase. $15–$85 each, ~$306 total |
| Japan showcase fracturefoil | 10 | `fra` 413–422 | `b\|shw\|ff` | same art as 403–412 → **dupe foil** (configured `[dupe_foil] fra = ["fracturefoil"]` (2026-11-08)); $128–$497 ea, ~$2,167 total |
| extended-art | 9 + ~15 | `fra` 423–431, `frc` ~89–103 | `ext` | auto-dropped by `preferred` |
| dark-frame promo-pack charms | 5 | `fra` 432–436 | `b` (black border, `inverted`, `promopack`) | KEPT (default) — pending owner review. Same illustration as base charms 132/138/150/155/160; Promo Pack `darkFrame` sheet; unpriced |
| Bundle promo | 1 | `fra` 437 | `regular` (foil-only, `bundle`) | kept via rare sub-selector — distinct art Carnivorous Cultivator |
| Secret Lair Bundle guest-artist borderless | 11 | `fra` 438–448 (dated 2026-10-23) | `b` (foil-only) | KEPT (default) — pending owner review. 439–448 = MTGJSON `secret-lair-bundle-promo` sheet (2 per Secret Lair Bundle); 438 Emrakul is on no booster sheet (source unverified). ~$326 total |
| facetfoil | 13 | `fra` 449–461 | `b` (**not `ff`** — `facetfoil` is NOT in `FANCY_FOIL_PROMO_TYPES`) | same art as 321–333 → dupe foil, but `[dupe_foil]` CAN'T catch it (no `ff`); needs an unobtainable rule (§5). $74–$438 ea, ~$3,327 total |
| headliner serialized | 1 | `fra` 402 Bloodline Recollector | `fa\|ff` (serialized+headliner+doublerainbow) | globally dropped (`serialized` in `UNOBTAINABLE_PROMO_TYPES`) |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `fracturefoil` (+`japanshowcase`) | `ff` | **yes** — 413–422 share `illustration_id` with 403–412 | → configured `[dupe_foil] fra = ["fracturefoil"]` (2026-11-08) |
| `facetfoil` | none (computes `b`) | **yes** — 449–461 share `illustration_id` with 321–333 | dupe_foil gate misses it (SNC `stepandcompleat` pattern) → `promo_types_any_of = ["facetfoil"]` rule proposed |
| `japanshowcase` | (frame: `shw`) | no — unique art | kept (default) — pending owner review |
| `promopack` + `stamped` | none (`regular`) | yes — `pfra` `Np` = base card + stamp | leaks via rare/mythic-regular; `stamped` rule proposed (mirrors TDM/ONE) |
| `promopack` (alone) | (frame `b`) | same art as base charm | 432–436 dark-frame charms |
| `bundle` | none | 437 unique art; 445 is an SLB guest print | kept |
| `serialized`/`headliner`/`doublerainbow` | `ff` | — | 402, globally filtered |

**Full-art convention:** `full_art = TRUE` on 321–333, 382–396 basics, 402–422 and 442/449–461; FALSE on the 291–320 / 334–401 (non-basic) borderless bands.

**Booster pairing quirk:** Play and Collector boosters contain a `pair<Name>` slot (two "alternate reality" versions of the same character, e.g. Thalia 205/214, Teyo borderless 295/306) plus a `thirdNot<Name>` slot. Paired cards are distinct cards (different names/oracle), not dupes.

---

## 3. Chase variants

No uncommon-regular chase: `set:fra+related missing rarity=uncommon treatment=regular chase` → 0 rows.

The bare `chase` modifier matches 62 rows, all artifacts of the treatment structure, not real multi-art chases:

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| 11 SLB/facetfoil mythics (Enlightened Confidant, Craterclaw Colossus, Darklight Phoenix, …) | 3 | 321–333 + 439–448 + 449–461 | mythic/rare | `b` — facetfoil counted as a 3rd "art" because it doesn't compute `ff` |
| The Theorist, Jace Beleren | 3+ | `fra` 43 / 363 / `pfra` 43p (+405/415, 443) | mythic | regular / borderless / showcase |
| Carnivorous Cultivator // Enroot | 3 | `fra` 100 / 437 / `pfra` 100p | rare | regular (437 bundle, 100p stamped) |
| Basics | 3 per type | 382–396 | common | `b` |

---

## 4. Scenes / posters / panoramas

None detected. Borderless runs by artist: Aleksi Briclot draws most planeswalkers in 291–317 (scattered, not contiguous); Piotr Dura 397–401 (5-card dual-land cycle — possible landscape panorama, not visually verified); basics 382–396 are 3-of per artist per land type. No `poster` promo_type. Nothing configured.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Candidate | Status | Rationale |
|---|---|---|
| `[dupe_foil] fra = ["fracturefoil"]` | **applied 2026-11-08** | 413–422 same art as Japan showcase 403–412; compute `b\|shw\|ff` so dupe_foil catches them (~$2,167) |
| `promo_types_any_of: ["facetfoil"]` | proposed (exclude) | 449–461 same art as 321–333 but compute `b` (no `ff`), ~$3,327 scarcity tier (collector foilBoosterfun only) |
| `promo_types_any_of: ["stamped"]` (or `["promopack"]` to also take 432–436) | proposed (exclude) | `pfra` 90 `Np` stamped prints compute `regular` and would leak via rare/mythic-regular (~$488 nonfoil / ~$755 foil). Mirrors TDM/ONE |
| dark-frame charms 432–436 (`promopack` alone) | kept (default) — pending owner review | Same art as base charms, Promo Pack only, unpriced |
| Japan showcase black-border 403–412 | kept (default) — pending owner review | Distinct art, foil-only collector, ~$306 |
| Secret Lair Bundle guest-artist borderless 438–448 | kept (default) — pending owner review | Distinct art, SLB-exclusive (2 per bundle), ~$326 |
| borderless 291–401 + showcase 334–358 | kept (default) — pending owner review | The family's ordinary boosterfun tiers |
| headliner serialized 402 | n/a | globally filtered |

Before/after missing totals: n/a — family unconfigured, so `set_status.py fra` reports "missing: not configured" and no concentration note fires. Scarcity shape by inspection: facetfoil ~$3,327 + fracturefoil ~$2,167 dominate the alt-treatment $; both are same-art foils.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` (e.g. `43p`) | `pfra` | Promo Pack (promopack + stamped) | The Theorist, Jace Beleren 43p |
| `432`–`436` | `fra` | Promo Pack dark-frame charm (`darkFrame` sheet) | Fatehold Charm 432 |
| `437` | `fra` | Bundle promo (foil) | Carnivorous Cultivator // Enroot 437 |
| `439`–`448` | `fra` | Secret Lair Bundle promo (2 per bundle, foil) | Overwrite the Multiverse 445 |
| SPG 159–168 | `spg` | Special Guests in Play Boosters | Splinter Twin SPG 167 |

No `pfra` prerelease `Ns` prints exist (all 90 `pfra` CNs end in `p`). No bulk-add skill references to `pfra`/`frc` yet.

---

## 7. Edge cases & gotchas

- `yfra` (31 Alchemy cards) is arena-stamped → dropped by `_is_digital_only` in the missing-set sub-selectors (bare `set:fra+related missing` still lists them; `treatment=collectible-alt` shows 0). The only "arena" grep hit in missing is the paper card *Hexhaven Dueling Arena* (FRA 181) — not a leak.
- `facetfoil` is a new fancy-foil token not in `treatments.FANCY_FOIL_PROMO_TYPES`; adding it there (code change) would let `[dupe_foil]` handle 449–461 instead of an unobtainable rule.
- 363 The Theorist, Jace Beleren is borderless with NO frame effects (not `inverted`) — computes to `''`, so it's handled by the mythic-regular sub-selector despite being a borderless booster-fun print.
- `frc` extended-art rares (~89–103) are nonfoil-only and appear in FRA Collector Boosters via the `braintwisterFrc`/`foilBoosterfun` sheets (external uuids).
- Scryfall `/sets` lists `fra` at 462 cards; `search set:fra unique=prints` returns 461 (CN 1–461 contiguous). Recheck on next sync.
- 438 Emrakul (borderless foil, 2026-10-23) is on no MTGJSON booster sheet — source product unverified.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] fra = ["fracturefoil"]` — configured 2026-11-08 (enables `mm query missing-set fra`).
- `config/families.toml` `[[unobtainable.fra.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).

---

## 9. Product types

| Product | Archetype (→ [product-types.md](../product-types.md)) | Family-specific detail |
|---|---|---|
| Multiverse Reforged | Commander deck | `MultiverseReforged_FRC`; the only FRC deck; commander Jace, Multiverse Architect (FRC 1) |
| Reality Fracture Bundle | Bundle | 9 Play Boosters + Land Pack + foil promo **FRA 437** Carnivorous Cultivator |
| Reality Fracture Secret Lair Bundle | Bundle (gift) | 6 Play + 2 Collector Boosters + Land Pack + `secret-lair-bundle-promo` pack (2 of FRA 439–448) |
| Promo Pack / Foil Promo Pack | promo pack | `curated` + `darkFrame` (432–436) + `seasonal` (90 `pfra` stamped) sheets |
| Prerelease Pack | prerelease kit | 6 Play Boosters + `prerelease` pack; no datestamped promos on Scryfall |
| Draft Night | limited aid | — |
| Reality Fracture Redemption | MTGO Redemption | digital redemption, not tracked |

**Booster types (for `sealed-value` EV):** `uv run python scripts/sealed_value.py fra --list-boosters` (2026-11-02):

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `play` | EV ~$5.38, 91% coverage; `specialGuest` sheet points at SPG 159–168 (sync `spg` for full coverage); `pair<Name>` slots |
| `collector` | EV ~$24.87, 93% coverage; `braintwisterFrc` + `foilBoosterfun` include `frc` cards |
| `promo` / `promo-foil` | ~58% coverage — `curated` sheet uuids not all resolvable locally |
| `secret-lair-bundle-promo` | EV ~$53.96 (2 cards from 439–448) |
