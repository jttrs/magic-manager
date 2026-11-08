# `znr` — Zendikar Rising

> Per-family memory doc. Read this before answering set-specific questions about
> `znr` or working on `znr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `znr`
**Family root type:** `expansion`
**Family released:** 2020-09-25
**Last audit:** 2026-11-04 via `/characterize-set znr` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

9 Scryfall codes, all parented to `znr`.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `znr` | expansion | 392 | 2020-09-25 | parent — booster set 1–280, extras 281–391, 15 `A-` Alchemy rebalances |
| `zne` | masterpiece | 30 | 2020-09-25 | **Zendikar Rising Expeditions** — 30 lands, all mythic, foil + nonfoil |
| `znc` | commander | 142 | 2020-09-25 | 2 Commander decks (Land's Wrath — Obuun; Sneak Attack — Anowon) |
| `pznr` | promo | 153 | 2020-09-25 | prerelease `Ns` datestamped (84) + Promo Pack `Np` stamped (68) + `203★` Scute Swarm (resale) |
| `tznr` / `tznc` | token | 12 / 11 | 2020-09-25 | tokens |
| `sznr` | token | 9 | 2020-09-25 | substitute cards |
| `mznr` | minigame | 5 | 2020-09-25 | minigame inserts |
| `aznr` | memorabilia | 81 | 2020-09-25 | Art Series |

**Separately-rooted bonus sheets:** none. `set:znr+related` covers the family.

---

## 2. Treatments

Survey (`survey_treatment_signature.py ZNR`, 849 prints).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 265 | `znr` 1–265 + basics 266–280 (full-art) + 380–384 | `regular` | rarity/base sub-selectors (84 R+M ≈ $250 nonfoil) |
| full-art basics | 15 | `znr` 266–280 (`fullart`) | `regular` | basics, never rare/mythic |
| **borderless planeswalkers + Pathways** | 9 | `znr` 281–283 (Jace, Nahiri, Nissa), 284–289 (6 Pathway MDFCs) | `b` | **kept (default) — pending owner review.** Distinct from base; art shared only with `aznr` Art Series. ~$28 nonfoil / ~$43 foil |
| **showcase "landfall" frame** | 24 | `znr` 290–313 (`showcase`+`inverted`; Omnath, Lotus Cobra, Scute Swarm, Moraug…) | `shw` | **kept (default) — pending owner review.** Distinct art (4 share it only with their `plst` List reprint); ~$33 nonfoil / ~$56 foil |
| extended-art | 66 | `znr` 314–379 | `ext` | auto-dropped |
| buy-a-box | 1 | `znr` 385 Orah, Skyclave Hierophant (ext, foil) | `ext` | auto-dropped with ext |
| bundle | 1 | `znr` 386 Charix, the Raging Isle (foil) | `regular` | rare-regular |
| promo-pack inverted commons/uncommons | 5 | `znr` 387–391 (`promopack`, `inverted`) | `b` | same art as base (5/5); sub-rare, only `preferred` sees them |
| **Zendikar Expeditions** | 30 | `zne` 1–30 (all mythic, foil + nonfoil) | `regular` | mythic-regular — **kept (default) — pending owner review.** The family's alt-$ giant: ~$895 nonfoil / ~$1,479 foil (Ancient Tomb 21 ~$137, Cavern of Souls 22, Misty Rainforest 10, Polluted Delta 2). 8 art links, all outside `zne` (earlier Expeditions/List prints) |
| Commander ext face cards | 2 | `znc` 7 Anowon, 8 Obuun (`extendedart`, foil + nonfoil) | `ext` | auto-dropped; base `znc` 1–2 are the face commanders |
| Alchemy rebalance | 15 | `znr` `A-*` | — | dropped by `_is_digital_only` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | auto-dropped |
| `promopack` + `stamped` | `regular` | **yes** — `pznr` `Np` = base + stamp | 68 prints, ~$141 nonfoil / ~$170 foil; ONE/NEO/TDM `stamped` rule |
| `promopack` (alone) | `b` | same art as base | `znr` 387–391 — spared by a `stamped`-only rule |
| `resale` | — | `pznr` 203★ Scute Swarm | kept |
| `bundle` / `buyabox` | — | distinct | 386 / 385 |

No fancy-foil sheet → configured `[dupe_foil] znr = []` (2026-11-08) to enable `mm query missing-set znr`.

**Full-art convention:** `full_art = 1` on basics 266–280 only (+ substitute cards).

---

## 3. Chase variants

None among uncommons beyond normal price spread.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] znr = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pznr` promo-pack stamped `Np` | 68 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$141 |
| `zne` Expeditions | 30 | keep — the desirable bonus sheet (~$895 / ~$1,479); owner may prefer excluding it as a separate chase target given the price |
| showcase 290–313 | 24 | keep |
| borderless 281–289 | 9 | keep |
| promo-pack inverted 387–391 | 5 | keep — sub-rare |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists. By inspection the
Expeditions are ~3.5× the whole base R+M value.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pznr` | prerelease, datestamped (foil) | — |
| `Np` | `pznr` | Promo Pack, stamped | — |
| `203★` | `pznr` | resale | Scute Swarm |
| `385` | `znr` | Buy-a-Box (ext foil) | Orah, Skyclave Hierophant |
| `386` | `znr` | Bundle (foil) | Charix, the Raging Isle |
| `387`–`391` | `znr` | Promo Pack inverted commons/uncommons | Into the Roil 387 |

---

## 7. Edge cases & gotchas

- **Expeditions are `zne`, not `exp`.** BFZ/OGW Expeditions are `exp`
  (separate family); ZNR's 30 are `zne` and ride `set:znr+related`. Several
  lands exist in both — confirm the set code.
- **Basics are split**: full-art 266–280 and regular-frame 380–384 (the
  latter after the ext band).
- 6 Pathway MDFCs: base frame at 258–261, 263–264; borderless alt-art at
  284–289.
- Party mechanic: theme booster `theme-party` exists alongside the colour ones.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] znr = []` — configured 2026-11-08 (enables `mm query missing-set znr`).
- `config/families.toml` `[[unobtainable.znr.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.znr]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander decks ×2 | Commander deck | Land's Wrath (Obuun) / Sneak Attack (Anowon) — `znc` |
| Draft / Set / Collector boosters | booster product | Expeditions appear in Set and Collector boosters; Collector carries the ext band |
| Theme boosters | theme booster | W/U/B/R/G + Party |
| Bundle | Bundle | `znr` 386 Charix |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py znr --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` / `set` | EV ~$3.37 / ~$4.53, ~89–93% coverage |
| `collector` | EV ~$18.11, 90.5% |
| `theme-{w,u,b,r,g,party}` | EV ~$5.37–$8.48 (green highest) |
| `prerelease` / `promo` / `promo-foil` | ~$3.15 / ~$6.86 / ~$9.71 |
| `arena` | digital code card, ignore |
