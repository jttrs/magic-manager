# `khm` — Kaldheim

> Per-family memory doc. Read this before answering set-specific questions about
> `khm` or working on `khm`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `khm`
**Family root type:** `expansion`
**Family released:** 2021-02-05
**Last audit:** 2026-11-04 via `/characterize-set khm` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

9 Scryfall codes, all parented to `khm`.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `khm` | expansion | 407 | 2021-02-05 | parent — booster set 1–285, extras 286–407, 18 `A-` Alchemy rebalances |
| `khc` | commander | 119 | 2021-02-05 | 2 Commander decks (Elven Empire — Lathril; Phantom Premonition — Ranar) |
| `pkhm` | promo | 158 | 2021-02-05 | prerelease `Ns` datestamped (84) + Promo Pack `Np` stamped (68) + 4 `resale` + `2★` etched Lathril |
| `tkhm` / `tkhc` | token | 23 / 8 | 2021-02-05 | tokens (8 full-art) |
| `skhm` | token | 9 | 2021-02-05 | double-faced substitute cards |
| `mkhm` | minigame | 5 | 2021-02-05 | minigame inserts |
| `akhm` | memorabilia | 81 | 2021-02-05 | Art Series |

**Separately-rooted bonus sheets:** none. `set:khm+related` covers the family.

---

## 2. Treatments

Survey (`survey_treatment_signature.py KHM`, 808 prints).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 285 | `khm` 1–285 (incl. snow basics) | `regular` | rarity/base sub-selectors (~$355 nonfoil) |
| **borderless planeswalkers / Pathways** | 8 | `khm` 286–293 (Valki // Tibalt, Tyvar, Kaya, Niko; 4 Pathway MDFCs) | `b` | **kept (default) — pending owner review.** Distinct art |
| **borderless "Norse" mythics** | 5 | `khm` 294–298 (`inverted`: Starnheim Unleashed, Alrund's Epiphany, Haunting Voyage, Quakebringer, Battle Mammoth) | `b` | **kept (default) — pending owner review.** Distinct art; 286–298 ≈ $43 nonfoil total |
| **showcase legends (black border)** | 34 | `khm` 299–332 (`showcase`+`legendary`; gods, sagas-era legends) | `shw` | **kept (default) — pending owner review.** Distinct art (0/34 share art); the black-border showcase is the high-risk class; ~$185 nonfoil / ~$315 foil |
| extended-art | 41 | `khm` 334–399 (minus the theme/bundle CNs) | `ext` | auto-dropped |
| **theme-booster exclusives** | 20 | `khm` 374–393 (`themepack`, nonfoil only, uncommon/rare) | `regular` | rare-regular — **unique cards** sold only in theme boosters (Valkyrie Harbinger 374), not alt prints (0/20 share art); keep |
| bundle | 6 | `khm` 394–400 (snow-covered basics + Reflections of Littjara 400 foil) | `regular` | kept |
| promo-pack inverted commons/uncommons | 5 | `khm` 401–405 (`inverted`, black border) | `b` | sub-rare; only the `preferred` sub-selector sees them |
| **Vorinclex concept art** | 2 | `khm` 406 (`concept`+`setextension`, borderless, ~$68), 407 (same art, `stepandcompleat`, foil-only) | `b` | 406 **kept (default) — pending owner review.** 407 is a same-art foil that does NOT compute `ff` → dupe_foil misses it (DMU 435/436 pattern) |
| etched Lathril | 1 | `pkhm` `2★` (`resale`, etched) | `b\|ff` | auto-dropped (etched) |
| Alchemy rebalance | 18 | `khm` `A-*` | — | dropped by `_is_digital_only` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | auto-dropped |
| `promopack` + `stamped` | `regular` | yes — `pkhm` `Np` | 68 prints, ~$228 nonfoil; ONE/NEO/TDM `stamped` rule |
| `stepandcompleat` (+`concept`, `setextension`) | none (computes `b`) | yes — 407 shares art with 406 | `promo_types_any_of = ["stepandcompleat"]` |
| `themepack` | — | no — unique cards | 374–393 |
| `bundle` / `buyabox` / `resale` | — | distinct | kept |

No fancy-foil sheet → proposed `[dupe_foil] khm = []` to enable `mm query missing-set khm`.

**Full-art convention:** `full_art = 1` only on tokens/substitute cards (`tkhm` 8, `skhm` 9).

---

## 3. Chase variants

None. `set:khm+related missing rarity=uncommon treatment=regular chase` → 0 rows.

---

## 4. Scenes / posters / panoramas

None detected.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] khm = []` | 0 | **apply** — empty, enables missing-set |
| `pkhm` promo-pack stamped `Np` | 68 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$228 |
| `khm` 407 Vorinclex stepandcompleat | 1 | **exclude** — `promo_types_any_of = ["stepandcompleat"]` (same art as 406, foil-only) |
| Vorinclex concept 406 | 1 | keep or exclude — owner's call (~$68 nonfoil, the family's top kept alt) |
| showcase legends 299–332 | 34 | keep — distinct-art Norse frame |
| borderless 286–298 | 13 | keep |
| theme-booster exclusives 374–393 | 20 | keep — real cards |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pkhm` | prerelease, datestamped (foil) | — |
| `Np` | `pkhm` | Promo Pack, stamped | — |
| resale / `2★` | `pkhm` | resale promos; etched Lathril | Lathril 2★ |
| `374`–`393` | `khm` | Theme Booster exclusives (nonfoil) | Valkyrie Harbinger 374 |
| `394`–`400` | `khm` | Bundle (snow basics + Reflections of Littjara) | — |
| `401`–`405` | `khm` | Promo Pack inverted commons/uncommons | Usher of the Fallen 401 |
| `406`–`407` | `khm` | Vorinclex concept art (Collector Booster / set extension) | — |

---

## 7. Edge cases & gotchas

- **CN ranges interleave:** the ext band (334–399) is broken by the theme-booster
  exclusives (374–393) and bundle prints (394–400). Classify by `promo_types`/frame.
- **Theme-booster cards are not alt prints** — they exist only in `khm` 374–393,
  nonfoil, and look like base frame.
- Snow-covered basics are both in the base set and the Bundle (394–399).
- Four Pathway MDFCs (290–293) are double-faced lands; the back shares the row.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.khm.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.khm]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander decks ×2 | Commander deck | Elven Empire (Lathril) / Phantom Premonition (Ranar) — `khc` |
| Theme boosters | theme booster | W/U/B/R/G + Vikings; carry the 374–393 exclusives |
| Bundle | Bundle | snow basics + Reflections of Littjara; Bundle Land Pack in MTGJSON |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py khm --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` / `set` | EV ~$5.33 / ~$6.73, ~98% coverage |
| `collector` | EV ~$16.36, 93.8% |
| `theme-{w,u,b,r,g,vikings}` | EV ~$8.51–$20.58 (green highest) |
| `prerelease` / `promo` / `promo-foil` | ~$4.07 / ~$9.55 / ~$12.77 |
| `arena` | digital code card, ignore |
