# `mh2` — Modern Horizons 2

> Per-family memory doc. Read this before answering set-specific questions about
> `mh2` or working on `mh2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mh2`
**Family root type:** `draft_innovation`
**Family released:** 2021-06-18
**Last audit:** 2026-11-04 via `/characterize-set mh2` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

6 Scryfall codes, all parented to `mh2`.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mh2` | draft_innovation | 492 | 2021-06-18 | parent — new cards 1–261, new-to-Modern reprints 262–303, extras 304–492, 1 `A-` Alchemy rebalance |
| `h1r` | draft_innovation | 40 | 2021-06-18 | **Modern Horizons 1 Timeshifts** — retro-frame MH1 reprints, foil / foil-etched only (Collector Booster) |
| `pmh2` | promo | 86 | 2021-06-18 | prerelease `Ns` datestamped (80) + Promo Pack `Np` stamped (6) |
| `tmh2` | token | 21 | 2021-06-18 | tokens |
| `mmh2` | minigame | 5 | 2021-06-18 | minigame inserts |
| `amh2` | memorabilia | 162 | 2021-06-18 | Art Series |

**Separately-rooted bonus sheets:** none. `h1r` is properly parented.
`set:mh2+related` covers the family. (The reverse sheet — MH2 retro reprints
seeded into MH3 — is `h2r`, part of the [`mh3`](mh3.md) family.)

---

## 2. Treatments

Survey (`survey_treatment_signature.py MH2`, 806 prints). Every mh2 card from
262 up also has a **foil-etched** finish; etched computes `regular` [etched] here
(no `inverted`), so it rides along with its print rather than forming a tier.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (new cards) | 261 | `mh2` 1–261 (foil + nonfoil) | `regular` | rarity/base sub-selectors (~$539 nonfoil) |
| new-to-Modern reprints | 42 | `mh2` 262–303 (foil + nonfoil + etched) | `regular` | booster-set cards — rarity/base sub-selectors |
| **borderless** | 23 | `mh2` 304–326 (`inverted`, 6 `legendary`; rare/mythic) | `b` | **kept (default) — pending owner review.** Distinct art (Solitude 307, Ragavan 315, Cabal Coffers 325); ~$275 nonfoil / ~$504 foil |
| **showcase (sketch frame)** | 54 | `mh2` 327–380 (`showcase`, 5 `legendary`; all rarities) | `shw` | **kept (default) — pending owner review.** Distinct art (76/77 incl. borderless share no art with another mh2 print); ~$157 nonfoil (Esper Sentinel 328 ~$57) |
| **retro-frame reprints** | 61 | `mh2` 381–441 (old-border frame, `boosterfun`, foil + nonfoil + etched; 38 rare/mythic) | `regular` (frame isn't visible to `compute_treatment`) | **kept (default) — pending owner review.** Same art as another print (61/61). Because they compute `regular`, the rare/mythic-regular sub-selectors list each retro rare beside its twin — ~$306 nonfoil (the fetchlands 434–441 lead) |
| extended-art | 39 | `mh2` 442–480 (rare) | `ext` | auto-dropped. Same art as base (39/39) |
| bundle basics | 10 | `mh2` 481–490 (`bundle`) | `regular` | commons — harmless |
| buy-a-box | 1 | `mh2` 491 Sanctum Prelate (foil) | `regular` | mythic-regular |
| bundle promo | 1 | `mh2` 492 Yusri, Fortune's Flame (foil) | `regular` | rare-regular |
| MH1 Timeshifts | 40 | `h1r` 1–40 (retro frame, foil + etched only) | `regular` [foil/etched] | **kept (default) — pending owner review.** Same art as the MH1 original (40/40), different set and frame; foil-only so only a foil basis lists them; ~$567 foil (Force of Negation 9 ~$120) |
| Alchemy rebalance | 1 | `mh2` `A-*` | — | dropped by `_is_digital_only` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | auto-dropped |
| `promopack` + `stamped` | `regular` | **yes** — `pmh2` 23p/52p/80p/106p/129p/166p | only 6 prints (~$31); ONE/NEO/TDM `stamped` rule |
| `boosterfun` | — | n/a | borderless, showcase, retro bands |
| `bundle` / `buyabox` | — | distinct | kept |

No textured / fancy-foil sheet → configured `[dupe_foil] mh2 = []` (2026-11-08) to enable
`mm query missing-set mh2`.

**Full-art convention:** no `full_art` prints outside tokens.

---

## 3. Chase variants

None. `set:mh2+related missing rarity=uncommon treatment=regular chase` → 0 rows.
The multi-print cards are base/borderless-or-showcase/retro/ext trios (e.g. the
fetchlands, e.g. Scalding Tarn base 254 + retro 439 + ext 478), not booster chases.

---

## 4. Scenes / posters / panoramas

None detected.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] mh2 = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pmh2` promo-pack stamped | 6 | **exclude** — `promo_types_any_of = ["stamped"]` |
| retro-frame 381–441 | 61 | **unsure** — same art, different frame; listed alongside its twin because it computes `regular` (~$306 extra). Exclude rule would be `collector_numbers` 381–441 (a `boosterfun`+black-border rule would also catch the showcase band). Same open question as [`dmr`](dmr.md)'s retro band |
| `h1r` MH1 Timeshifts | 40 | keep — the Collector Booster bonus sheet; foil-only |
| borderless 304–326 | 23 | keep |
| showcase sketch 327–380 | 54 | keep — distinct art (not the D&D rulebook frame that CLB/AFR exclude) |

**Scarcity check:** not run yet (written before `[dupe_foil]` was added). By inspection the
alt tiers are spread out — no single chase print dominates outside Ragavan /
Esper Sentinel.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pmh2` | prerelease, datestamped (foil) | — |
| `Np` | `pmh2` | Promo Pack, stamped | Murktide Regent 52p |
| `491` | `mh2` | Buy-a-Box (foil) | Sanctum Prelate |
| `481`–`490`, `492` | `mh2` | Bundle (basics + Yusri) | Yusri, Fortune's Flame 492 |

---

## 7. Edge cases & gotchas

- **Retro frame is invisible to treatment code.** The `cards` table has no
  `frame` column, so 381–441 look like plain `regular` prints; identify them by CN.
- **Etched is a finish on every 262+ card**, not a separate print (one row,
  three finishes) — unlike CLB/2x2 where etched has its own CN band.
- `h1r` cards are foil-only; on a nonfoil basis the sheet contributes nothing.
- Tombstone frame effect on a few retro prints.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] mh2 = []` — configured 2026-11-08 (enables `mm query missing-set mh2`).
- `config/families.toml` `[[unobtainable.mh2.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.mh2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft / Set / Collector boosters | booster product | Collector Booster carries `h1r` timeshifts + etched retro prints |
| Bundle | Bundle | `mh2` 481–490 basics + 492 promo |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mh2 --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` / `set` | EV ~$10.66 / ~$13.79, ~99% coverage |
| `collector` | EV ~$44.59, 99.2% |
| `prerelease` | EV ~$11.78 |
