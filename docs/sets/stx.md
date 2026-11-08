# `stx` — Strixhaven: School of Mages

> Per-family memory doc. Read this before answering set-specific questions about
> `stx` or working on `stx`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `stx`
**Family root type:** `expansion`
**Family released:** 2021-04-23
**Last audit:** 2026-11-04 via `/characterize-set stx` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

7 Scryfall codes, all parented to `stx`.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `stx` | expansion | 383 | 2021-04-23 | parent — booster set 1–275 (basics 366–375 sit at the end), extras 276–382, 10 `A-` Alchemy rebalances |
| `sta` | masterpiece | 126 (63 local) | 2021-04-23 | **Strixhaven Mystical Archive** — 63 iconic instants/sorceries, borderless showcase, foil + nonfoil + etched; CN 64–126 are the **Japanese-only** alt-art versions |
| `pstx` | promo | 164 | 2021-04-23 | prerelease `Ns` datestamped (90) + Promo Pack `Np` stamped (74) |
| `tstx` / `sstx` | token | 9 / 9 | 2021-04-23 | tokens / double-faced substitute cards |
| `mstx` | minigame | 5 | 2021-04-23 | minigame inserts |
| `astx` | memorabilia | 162 | 2021-04-23 | Art Series |

**Separately-rooted bonus sheets:** none. The Strixhaven Commander decks are
`c21` (Commander 2021), its own family — see [`c21`](c21.md).

---

## 2. Treatments

Survey (`survey_treatment_signature.py STX`, 795 local prints).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 286 | `stx` 1–275 + basics 366–375 | `regular` | rarity/base sub-selectors (~$140 nonfoil) |
| **borderless legends / planeswalkers** | 9 | `stx` 276–284 (Professor Onyx, Mila // Lukka, Rowan // Will, Kasmina, 5 Elder Dragons; `inverted`) | `b` | **kept (default) — pending owner review.** Distinct art; ~$60 nonfoil / ~$184 foil |
| extended-art | 81 | `stx` 285–365 | `ext` | auto-dropped |
| buy-a-box | 1 | `stx` 376 Dragonsguard Elite (ext, foil) | `ext` | auto-dropped with ext |
| bundle | 1 | `stx` 377 Archmage Emeritus (foil) | `regular` | rare-regular |
| promo-pack inverted uncommons | 5 | `stx` 378–382 (Fracture, Expressive Iteration, Mortality Spear, Rip Apart, Decisive Denial; `promopack`, `inverted`) | `b` | same art as base (5/5); uncommon, only `preferred` sees them |
| **Mystical Archive (English)** | 63 | `sta` 1–63 (borderless `showcase`, foil + nonfoil + etched; 15 mythic / 20 rare / 28 uncommon) | `shw` | **kept (default) — pending owner review.** The set's signature bonus sheet, one per Set/Draft booster; reprints (every card exists elsewhere) with new art. ~$313 nonfoil / ~$556 foil (Demonic Tutor 27 ~$78) |
| Mystical Archive (Japanese alt-art) | 63 | `sta` 64–126 (`lang: ja` only) | — | **not in the local catalog** — the sync keeps English printings, so they never appear in Collection or missing-set |
| Alchemy rebalance | 10 | `stx` `A-*` | — | dropped by `_is_digital_only` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | auto-dropped |
| `promopack` + `stamped` | `regular` | **yes** — `pstx` `Np` = base + stamp | 74 prints, ~$102 nonfoil / ~$148 foil; ONE/NEO/TDM `stamped` rule |
| `promopack` (alone) | `b` | same art as base | `stx` 378–382 — spared by a `stamped`-only rule |
| `bundle` / `buyabox` | — | distinct | kept |

`sta` etched is a finish on the same row (no separate etched CN band). No
fancy-foil sheet → configured `[dupe_foil] stx = []` (2026-11-08) to enable `mm query missing-set stx`.

**Full-art convention:** `full_art = 1` on `sstx` only.

---

## 3. Chase variants

None. `set:stx+related missing rarity=uncommon treatment=regular chase` → 0 rows.

---

## 4. Scenes / posters / panoramas

None detected. (The 5 borderless Elder Dragons 280–284 are separate pieces,
not a panorama.)

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] stx = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pstx` promo-pack stamped `Np` | 74 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$102 |
| `sta` Mystical Archive 1–63 | 63 | keep — the desirable bonus sheet; the biggest alt-$ tier |
| borderless 276–284 | 9 | keep |
| promo-pack inverted 378–382 | 5 | keep — sub-rare |
| `sta` 64–126 Japanese | 63 | n/a — not synced (English-only catalog) |

**Scarcity check:** not run yet (written before `[dupe_foil]` was added). By inspection the
Mystical Archive carries most of the alt-$ (Demonic Tutor, Teferi's Protection,
Tainted Pact lead).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pstx` | prerelease, datestamped (foil) | — |
| `Np` | `pstx` | Promo Pack, stamped | — |
| `376` | `stx` | Buy-a-Box (ext foil) | Dragonsguard Elite |
| `377` | `stx` | Bundle (foil) | Archmage Emeritus |
| `378`–`382` | `stx` | Promo Pack inverted uncommons | Fracture 378 |

---

## 7. Edge cases & gotchas

- **Japanese Mystical Archive is invisible locally.** `sta` 64–126 are
  Japanese-language-only printings; a Japanese STA in hand has no local row to
  add to (it would need a non-English catalog).
- Basics 366–375 sit after the ext band numerically (ext 285–365, then basics,
  then 376 buy-a-box) — CN ranges overlap classes; identify by frame/promo type.
- Every `sta` card is a reprint; `set:stx+related` counts it, but its oracle
  card also exists in many other sets.
- 2 MDFC dual planeswalkers (Mila // Lukka 277, Rowan // Will 278) sit in the borderless band.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] stx = []` — configured 2026-11-08 (enables `mm query missing-set stx`).
- `config/families.toml` `[[unobtainable.stx.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.stx]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft / Set / Collector boosters (+ Japanese set/draft) | booster product | one Mystical Archive card per Draft/Set booster |
| Theme boosters | theme booster | one per college (Lorehold, Prismari, Quandrix, Silverquill, Witherbloom) |
| Prerelease packs | prerelease | one per college |
| Bundle | Bundle | `stx` 377 promo |
| Commander 2021 decks | Commander deck | separate family `c21` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py stx --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` / `set` | EV ~$5.46 / ~$6.47, ~98% coverage |
| `collector` | EV ~$17.99, 85.5% |
| `jp` / `set-jp` | EV ~$4.45 / ~$5.19 (Japanese STA slots unpriced) |
| `theme-*` | EV ~$6.36–$10.21 (Prismari highest) |
| `prerelease-*` / `promo` / `promo-foil` | ~$4.57–$5.89 / ~$7.90 / ~$11.07 |
| `arena` | digital code card, ignore |
