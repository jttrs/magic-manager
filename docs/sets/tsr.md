# `tsr` — Time Spiral Remastered

> Per-family memory doc. Read this before answering set-specific questions about
> `tsr` or working on `tsr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `tsr`
**Family root type:** `masters`
**Family released:** 2021-03-19
**Last audit:** 2026-11-04 via `/characterize-set tsr` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `tsr` | masters | 411 | 2021-03-19 | parent — main set 1–289, **timeshifted "bonus sheet" 290–410** (rarity `special`), Lotus Bloom 411 |
| `ptsr` | promo | 3 | 2021-03-19 | Promo Pack `Np` stamped (Angel's Grace 4p, Wheel of Fate 198p, Swarmyard 284p) |
| `ttsr` | token | 15 | 2021-03-19 | tokens |

No prerelease set (masters). `set:tsr+related` covers the family; no `--only`.

---

## 2. Treatments

Survey (`survey_treatment_signature.py TSR`, 429 prints). **Every print
computes `regular`** — there are no borderless/showcase/ext frames. The
"alternate" sheet is distinguished by FRAME (old-border retro, invisible to
`compute_treatment`) and by Scryfall rarity `special`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| main set | 289 | `tsr` 1–289 (121 C / 100 U / 54 R / 15 M incl. 411) | `regular` | rarity/base sub-selectors (~$345 R+M nonfoil) |
| **timeshifted bonus sheet** | 121 | `tsr` 290–410 (old-border frame, rarity **`special`**, foil + nonfoil) | `regular` | **⚠ never listed by missing-set** — its sub-selectors are rare-/mythic-regular, uncommon-chase and the preferred class; none matches rarity `special`. These are distinct cards (0 of 121 share an `oracle_id` with a main-set print), ~$353 nonfoil / **~$4,527 foil** (Thoughtseize 334 ~$442 foil, Ponder 315 ~$422 foil) |
| release / buy-a-box | 1 | `tsr` 411 Lotus Bloom (`release`+`buyabox`, foil) | `regular` | rare-regular |
| promo-pack stamped | 3 | `ptsr` 4p / 198p / 284p | `regular` | same card as base + stamp; ~$21 nonfoil |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `promopack` + `stamped` | `regular` | yes — base + stamp | 3 prints; `stamped` rule would drop them |
| `release` + `buyabox` | — | distinct | 411 Lotus Bloom |

No fancy-foil sheet → proposed `[dupe_foil] tsr = []` to enable `mm query missing-set tsr`.

**Full-art convention:** none.

---

## 3. Chase variants

None. `set:tsr+related missing rarity=uncommon treatment=regular chase` → 0 rows.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] tsr = []` | 0 | **apply** — empty, enables missing-set |
| `ptsr` promo-pack stamped | 3 | **exclude** — `promo_types_any_of = ["stamped"]` |
| timeshifted 290–410 | 121 | **keep — but it's a CODE gap, not a config one:** missing-set ignores rarity `special`, so these never appear in buy lists regardless. Fixing it means a `special` sub-selector (or folding `special` into rare) in `missing.missing_selectors` — owner decision |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists. By inspection the
timeshifted foils dominate the family's foil $ (~$4.5k of ~$5.6k).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` | `ptsr` | Promo Pack, stamped | Angel's Grace 4p |
| `411` | `tsr` | release / Buy-a-Box (foil) | Lotus Bloom |

---

## 7. Edge cases & gotchas

- **Rarity `special` is a blind spot.** Collection shows the timeshifts (it
  lists every printing), but `mm query missing-set tsr` and any
  `rarity=rare|mythic` selector skip them. Query them with
  `set:tsr+related rarity=special` (or `cn>=290 cn<=410`).
- **Retro frame isn't a column** — the timeshifted band is identified by CN /
  rarity, not frame.
- Huge foil premiums on the timeshift sheet (often 20–30× nonfoil).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.tsr.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.tsr]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | one timeshifted card per pack; no Set/Collector boosters |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py tsr --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$12.82, 99.1% coverage |
