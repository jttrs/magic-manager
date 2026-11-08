# `thb` — Theros Beyond Death

> Per-family memory doc. Read this before answering set-specific questions about
> `thb` or working on `thb`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `thb`
**Family root type:** `expansion`
**Family released:** 2020-01-24
**Last audit:** 2026-11-04 via `/characterize-set thb` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `thb` | expansion | 358 | 2020-01-24 | parent — booster set 1–254, extras 255–357 |
| `pthb` | promo | 137 | 2020-01-24 | prerelease `Ns` datestamped (68) + Promo Pack `Np` stamped (68) + `235★` resale |
| `tthb` | token | 14 | 2020-01-24 | tokens |

`set:thb+related` covers the family. No commander or masterpiece child.

---

## 2. Treatments

Survey (`survey_treatment_signature.py THB`, 509 prints).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 249 | `thb` 1–249 (106 C / 80 U / 53 R / 15 M across 1–254) | `regular` | rarity/base sub-selectors (R+M ≈ $223 nonfoil) |
| full-art basics | 5 | `thb` 250–254 | `fa` | basics |
| **borderless planeswalkers** | 3 | `thb` 255 Elspeth, 256 Ashiok, 257 Calix (no `inverted`) | `regular` (as [`m21`](m21.md) 279, [`iko`](iko.md) 276) | **kept (default) — pending owner review.** Distinct art; mythic-regular lists them beside base. ~$5 nonfoil |
| **showcase "Nyx" gods & demigods** | 11 | `thb` 258–268 (6 gods + 5 demigods; `enchantment`+`showcase`+`inverted`) | `b\|shw` | **kept (default) — pending owner review.** Distinct art from base (0 in-family shares; 5 demigods share art with their `plst` reprints). ~$60 nonfoil / ~$85 foil; Thassa 261 ~$26, Heliod 259 ~$21 |
| buy-a-box | 1 | `thb` 269 Athreos, Shroud-Veiled | `regular` | **unique card** (not in 1–254); art reused on `dsc` 212 — keep |
| Planeswalker-deck exclusives | 18 | `thb` 270–287 (Elspeth, Undaunted Hero 270 + 3 deck cards / Ashiok, Sculptor of Fears 274 + 3; 10 basics 278–287) | `regular` | **unique cards** (the 8 non-basics are not in 1–254) — keep; ~$4 total |
| theme-booster exclusives | 10 | `thb` 288–297 (2 rares per colour: Grasping Giant, Victory's Envoy, Sphinx Mindbreaker, Serpent of Yawning Depths, Demon of Loathing, Underworld Sentinel, Deathbellow War Cry, Terror of Mount Velus, Ironscale Hydra, Treeshaker Chimera) | `regular` | **unique cards** — keep; ~$10 total |
| extended-art | 54 | `thb` 298–351 | `ext` | auto-dropped — holds the top alts (Shadowspear 345 ~$44, Nyxbloom Ancient 330 ~$34, Thassa's Oracle 308 ~$27). ~$252 nonfoil / ~$574 foil |
| bundle | 1 | `thb` 352 (foil) | `regular` | rare-regular |
| promo-pack inverted commons/uncommons | 5 | `thb` 353–357 (`promopack`, `inverted`) | `b` | sub-rare |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | auto-dropped |
| `promopack` + `stamped` | `regular` | **yes** — `pthb` `Np` = base + stamp | 68 prints, ~$281 nonfoil / ~$370 foil; ONE/NEO/TDM `stamped` rule |
| `promopack` (alone) | `b` | sub-rare inverted commons/uncommons | `thb` 353–357 |
| `planeswalkerdeck` / `themepack` | — | unique cards | 270–297 |
| `bundle` / `buyabox` / `resale` | — | distinct | kept |

No fancy-foil sheet → proposed `[dupe_foil] thb = []` to enable `mm query missing-set thb`.

**Full-art convention:** basics 250–254 only.

---

## 3. Chase variants

None among uncommons. The showcase demigods 258, 260, 263, 264, 267 are
uncommon-rarity showcase prints; they are cheap (< $2).

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] thb = []` | 0 | **apply** — empty, enables missing-set |
| `pthb` promo-pack stamped `Np` | 68 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$281 |
| showcase Nyx 258–268, borderless PWs 255–257 | 14 | keep — distinct art |
| PW-deck / theme-booster exclusives 270–297, buy-a-box 269 | 29 | keep — real cards found nowhere in 1–254 |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pthb` | prerelease, datestamped (foil) | — |
| `Np` | `pthb` | Promo Pack, stamped | — |
| `235★` | `pthb` | resale (foil) | — |
| `269` | `thb` | Buy-a-Box | Athreos, Shroud-Veiled |
| `270`–`287` | `thb` | Planeswalker Decks | Elspeth, Undaunted Hero 270 |
| `288`–`297` | `thb` | Theme Boosters | Terror of Mount Velus 295 |
| `352` | `thb` | Bundle (foil) | — |
| `353`–`357` | `thb` | Promo Pack inverted commons/uncommons | — |

---

## 7. Edge cases & gotchas

- **Two "only in a product" bands** — Planeswalker Decks (270–287) and Theme
  Boosters (288–297) — hold real cards that never appear in Draft boosters.
  They aren't alt prints, so excluding them would hide real cards.
- **Borderless planeswalkers compute `regular`** (no `inverted`), while the
  Nyx showcase computes `b|shw`. Same pattern as cmr / 2xm / m21 / iko — a
  computed-treatment gap, not a THB quirk.
- `enchantment` frame effect (the Nyx starfield) appears on base cards too
  (46 base prints), so it isn't a treatment by itself.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.thb.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.thb]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft / Collector boosters | booster product | Collector carries ext + showcase + borderless |
| Theme boosters ×5 | theme booster | W/U/B/R/G, each with its own exclusive rares 288–297 |
| Planeswalker Decks ×2 | Planeswalker deck | Elspeth / Ashiok; cards at 270–287 |
| Bundle | Bundle | `thb` 352 |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py thb --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$6.40, 100% coverage |
| `collector` | EV ~$21.25, 99.7% |
| `theme-{w,u,b,r,g}` | EV ~$6.83–$12.80 (green highest) |
| `prerelease` / `promo` / `promo-foil` | ~$6.25 / ~$9.16 / ~$13.71 |
| `arena` | digital code card, ignore |
