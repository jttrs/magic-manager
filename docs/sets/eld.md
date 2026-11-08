# `eld` — Throne of Eldraine

> Per-family memory doc. Read this before answering set-specific questions about
> `eld` or working on `eld`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `eld`
**Family root type:** `expansion`
**Family released:** 2019-10-04
**Last audit:** 2026-11-05 via `/characterize-set eld` (one-at-a-time run — tier decisions pending owner review).

---

> The first set with **Collector Boosters** and with **showcase frames**
> (the storybook Adventure frame). Also the first set with in-set Brawl Deck
> exclusives (`eld` 314–333).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `eld` | expansion | 397 | 2019-10-04 | parent — booster set 1–269, extras 270–397, 1 `A-` Alchemy rebalance (CN 0 locally) |
| `peld` | promo | 138 | 2019-10-04 | prerelease `Ns` datestamped (68) + Promo Pack `Np` stamped (68) + 2 resale |
| `teld` | token | 20 | 2019-10-04 | tokens (7 full-art, incl. Goat 1) |

`set:eld+related` covers the family. No commander or masterpiece child.

---

## 2. Treatments

Survey (`survey_treatment_signature.py ELD`, 1,075 print-rows by finish).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 269 | `eld` 1–269 (121 C / 80 U / 53 R / 15 M; basics 250–269) | `regular` | rarity/base sub-selectors (R+M ≈ $152 nonfoil) |
| **borderless planeswalkers** | 3 | `eld` 270 Garruk, 271 Oko, 272 The Royal Scions (no `inverted`) | `regular` (same gap as [`thb`](thb.md) 255–257, [`iko`](iko.md) 276–278) | **kept (default) — pending owner review.** Distinct art (0 share it with base); ~$15 nonfoil / ~$37 foil |
| **showcase storybook (Adventure) frame** | 30 | `eld` 273–302 | `shw` | **kept (default) — pending owner review.** Distinct art from base (0 in-family shares); ~$17 / ~$40 |
| buy-a-box | 1 | `eld` 303 Kenrith, the Returned King | `regular` | **unique card** (not in 1–269) — keep |
| Planeswalker-deck exclusives | 10 | `eld` 304–313 (Rowan, Fearless Sparkmage 304 + 3; Oko, the Trickster 309 + 3; dual lands 308, 313 are reprints) | `regular` | **unique cards** (8 of 10) — keep; ~$3 total |
| Brawl-deck exclusives | 20 | `eld` 314–333 (commanders Alela 324, Chulane 326 ~$5, Korvold 329 ~$4, Syr Gwyn 330; Arcane Signet 331 + Command Tower 333 reprints) | `regular` | **unique cards** (18 of 20, never in Draft boosters) — keep; ~$22 nonfoil. Nonfoil only except the 4 commanders |
| extended-art | 58 | `eld` 334–391 | `ext` | auto-dropped — the family's money: The Great Henge 370 ~$76 / ~$151 foil, Wishclaw Talisman 357 foil ~$173, Embercleave 359. ~$330 nonfoil / ~$967 foil |
| bundle | 1 | `eld` 392 (foil) | `regular` | rare-regular |
| promo-pack inverted uncommons | 5 | `eld` 393–397 (`promopack`, `inverted`) | `b` | sub-rare (Glass Casket 393) |
| Alchemy rebalance | 1 | `eld` `A-*` | — | dropped by `_is_digital_only` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | auto-dropped |
| `promopack` + `stamped` | `regular` | **yes** — `peld` `Np` = base + stamp | 68 prints, ~$205 nonfoil / ~$321 foil; ONE/NEO/TDM `stamped` rule |
| `promopack` (alone) | `b` | sub-rare inverted uncommons | `eld` 393–397 |
| `planeswalkerdeck` / `brawldeck` | — | unique cards | 304–333 |
| `bundle` / `buyabox` / `resale` | — | distinct | kept |
| `boosterfun` | — | marker on 270–302 + ext | not a dupe signal |

No fancy-foil sheet → configured `[dupe_foil] eld = []` (2026-11-08) to enable `mm query missing-set eld`.

**Full-art convention:** tokens only (7 in `teld`). ELD basics 250–269 are regular frame.

---

## 3. Chase variants

None among uncommons. The chase is extended art (above).

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] eld = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `peld` promo-pack stamped `Np` | 68 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$205 |
| showcase 273–302, borderless PWs 270–272 | 33 | keep — distinct art |
| buy-a-box 303, PW-deck 304–313, Brawl 314–333 | 31 | keep — real cards found nowhere in 1–269 |

**Scarcity check:** not run yet (written before `[dupe_foil]` was added).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `peld` | prerelease, datestamped (foil) | — |
| `Np` | `peld` | Promo Pack, stamped | — |
| `133★`, `235★` | `peld` | resale (foil) | Opportunistic Dragon, Stonecoil Serpent |
| `303` | `eld` | Buy-a-Box | Kenrith, the Returned King |
| `304`–`313` | `eld` | Planeswalker Decks | Oko, the Trickster 309 |
| `314`–`333` | `eld` | Brawl Decks | Korvold, Fae-Cursed King 329 |
| `392` | `eld` | Bundle (foil) | — |
| `393`–`397` | `eld` | Promo Pack inverted uncommons | Glass Casket 393 |

---

## 7. Edge cases & gotchas

- **Two "only in a product" bands** — Planeswalker Decks (304–313) and Brawl
  Decks (314–333) — hold real cards that never appear in Draft boosters. Don't
  exclude them as alt prints.
- **Brawl-deck cards are nonfoil only** except the four face commanders
  (foil + nonfoil).
- **Borderless planeswalkers compute `regular`** — the recurring gap (cmr /
  2xm / m21 / iko / thb / eld).
- **Collector-booster EV coverage is low (66%)** across 36 layouts; treat the
  `collector` EV as a lower bound.
- Theme boosters exist (`theme-{w,u,b,r,g}`) but, unlike [`thb`](thb.md), ELD
  has no theme-booster-exclusive cards.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] eld = []` — configured 2026-11-08 (enables `mm query missing-set eld`).
- `config/families.toml` `[[unobtainable.eld.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.eld]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft / Collector boosters | booster product | Collector carries ext + showcase + borderless |
| Theme boosters ×5 | theme booster | W/U/B/R/G, no exclusives |
| Planeswalker Decks ×2 | Planeswalker deck | Rowan / Oko; cards at 304–313 |
| Brawl Decks ×4 | Brawl deck | Faerie Schemes (Alela), Knights' Charge (Syr Gwyn), Savage Hunger (Korvold), Wild Bounty (Chulane); cards at 314–333 |
| Bundle | Bundle | `eld` 392; MTGJSON *Throne of Eldraine Bundle Land Pack* (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py eld --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$4.40, 88% coverage |
| `collector` | EV ~$15.87, 66% coverage |
| `theme-{w,u,b,r,g}` | EV ~$6.67–$11.86 (green highest) |
| `prerelease` / `promo` / `promo-foil` | ~$4.60 / ~$6.35 / ~$11.12 |
| `arena` | digital code card, ignore |
