# `iko` — Ikoria: Lair of Behemoths

> Per-family memory doc. Read this before answering set-specific questions about
> `iko` or working on `iko`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `iko`
**Family root type:** `expansion`
**Family released:** 2020-04-24
**Last audit:** 2026-11-04 via `/characterize-set iko` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `iko` | expansion | 389 | 2020-04-24 | parent — booster set 1–274, extras 275–384, 1 `A-` Alchemy rebalance |
| `piko` | promo | 137 | 2020-04-24 | prerelease `Ns` datestamped (68) + Promo Pack `Np` stamped (68) + `162★` resale Kogla |
| `tiko` | token | 14 | 2020-04-24 | tokens |

**Separately-rooted:** the Ikoria Commander decks are `c20` (Commander 2020),
its own family (`c20`). `set:iko+related` covers the three codes above.

---

## 2. Treatments

Survey (`survey_treatment_signature.py IKO`, 540 prints).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 274 | `iko` 1–274 (126 C / 80 U / 53 R / 16 M; 10 companions with the `companion` frame) | `regular` | rarity/base sub-selectors (R+M ≈ $240 nonfoil; The Ozolith 237 ~$63) |
| **Godzilla buy-a-box** | 1 | `iko` 275 Zilortha, Strength Incarnate (`godzillaseries`+`buyabox`, borderless `inverted`) | `b` | **kept (default) — pending owner review.** A unique card (only exists as a Godzilla print); ~$20 |
| **borderless planeswalkers** | 3 | `iko` 276 Lukka, 277 Vivien, 278 Narset (no `inverted`) | `regular` (as [`cmr`](cmr.md) 512 / [`m21`](m21.md) 279) | **kept (default) — pending owner review.** Distinct art; mythic-regular lists them beside base |
| **showcase "monster" frame** | 30 | `iko` 279–308 (5 borderless rares, 5 borderless mythic Apexes 299–308, 20 black-border commons/uncommons) | `shw` | **kept (default) — pending owner review.** Distinct art (0 share it with base); ~$22 nonfoil / ~$57 foil |
| **showcase Triomes** | 5 | `iko` 309–313 (Indatha, Ketria, Raugrin, Savai, Zagoth; borderless) | `shw` | **kept (default) — pending owner review.** Distinct art, ~$16–$23 each (~$92 nonfoil / ~$198 foil) |
| extended-art | 50 | `iko` 314–363 (incl. 10 companions 351–360) | `ext` | auto-dropped — holds The Ozolith ext 362 ~$75 |
| bundle | 1 | `iko` 364 (foil) | `regular` | rare-regular |
| promo-pack inverted commons/uncommons | 5 | `iko` 365–369 (`promopack`) | `b` | same art as base (5/5: 13, 91, 119, 164, 211); sub-rare |
| **Godzilla Series box toppers** | 15 | `iko` 370–384 (`boxtopper`+`godzillaseries`, borderless) | `b` | **kept (default) — pending owner review.** Same CARD as a base monster, renamed for Godzilla with new art (Illuna 379 = "Ghidorah, King of the Cosmos"). One per Draft/Set box / Collector booster. ~$289 nonfoil / ~$390 foil — the family's top alt (Illuna 379 ~$85, Luminous Broodmoth 371 ~$50) |
| Alchemy rebalance | 1 | `iko` `A-*` | — | dropped by `_is_digital_only` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | auto-dropped |
| `promopack` + `stamped` | `regular` | **yes** — `piko` `Np` = base + stamp | 68 prints, ~$303 nonfoil / ~$360 foil; ONE/NEO/TDM `stamped` rule |
| `promopack` (alone) | `b` | same art as base | `iko` 365–369 |
| `godzillaseries` | `b` | same card, new art + Godzilla name | 16 prints (275, 370–384) |
| `boxtopper` | `b` | — | 370–384 |
| `bundle` / `buyabox` / `resale` | — | distinct | kept |

No fancy-foil sheet → proposed `[dupe_foil] iko = []` to enable `mm query missing-set iko`.

**Full-art convention:** none in `iko`.

---

## 3. Chase variants

None among uncommons.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] iko = []` | 0 | **apply** — empty, enables missing-set |
| `piko` promo-pack stamped `Np` | 68 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$303 |
| Godzilla box toppers 370–384 | 15 | **owner's call** — chase alts of base monsters (~$289). Same question as [`2xm`](2xm.md)'s box toppers; `cn_range = [370, 384]` if excluded |
| Zilortha 275 | 1 | keep — the only print of that card |
| showcase 279–313, borderless PWs 276–278 | 38 | keep — distinct art |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `piko` | prerelease, datestamped (foil) | — |
| `Np` | `piko` | Promo Pack, stamped | — |
| `162★` | `piko` | resale | Kogla, the Titan Ape |
| `275` | `iko` | Buy-a-Box (Godzilla) | Zilortha, Strength Incarnate |
| `364` | `iko` | Bundle (foil) | — |
| `365`–`369` | `iko` | Promo Pack inverted commons/uncommons | — |
| `370`–`384` | `iko` | Godzilla Series box toppers | Illuna 379 |

---

## 7. Edge cases & gotchas

- **Godzilla cards carry two names** (Godzilla name printed large, Ikoria name
  small); Scryfall indexes them by the Ikoria name. A "Ghidorah" in hand is
  `iko` 379 Illuna.
- **Japanese Godzilla alt-art** (Japanese-language boosters, `box-topper-jp`)
  is not in the English local catalog.
- **Showcase borders vary inside one band**: rares/mythics borderless,
  commons/uncommons black-border — both compute via `showcase`.
- Companions (10) get their own `companion` frame effect in base and ext.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.iko.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.iko]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft / Collector boosters (+ Japanese) | booster product | Godzilla toppers 1 per Draft box (`box-topper`) and in Collector boosters |
| Theme boosters | theme booster | W/U/B/R/G + Monsters |
| Bundle | Bundle | `iko` 364 |
| Commander 2020 decks | Commander deck | separate family `c20` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py iko --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` / `jp` | EV ~$6.89 / ~$7.90 |
| `collector` / `collector-jp` | EV ~$42.33 / ~$38.97 |
| `box-topper` / `box-topper-jp` | EV ~$26.02 / ~$21.68 |
| `theme-{w,u,b,r,g,monsters}` | EV ~$9.88–$14.36 (white highest) |
| `prerelease` / `promo` / `promo-foil` | ~$6.75 / ~$9.36 / ~$13.19 |
| `arena` | digital code card, ignore |
