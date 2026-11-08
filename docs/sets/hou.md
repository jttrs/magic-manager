# `hou` — Hour of Devastation

> Per-family memory doc. Read this before answering set-specific questions about
> `hou` or working on `hou`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `hou`
**Family root type:** `expansion`
**Family released:** 2017-07-14
**Last audit:** 2026-11-05 via `/characterize-set hou` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Amonkhet set, base frame only**, with full-art basics, two
> Planeswalker Decks and a few alt-art event promos. Its Invocations live in
> `mp2`, which is a child of [`akh`](akh.md), not of `hou`.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `hou` | expansion | 209 | 2017-07-14 | parent — booster set 1–199 (full-art basics 185–189, regular basics 190–199), PW-deck cards 200–209 |
| `phou` | promo | 62 | 2017-07-14 | prerelease `Ns` datestamped (54) + Promo Pack `Np` stamped (4) + game day / draft weekend / buy-a-box (4) |
| `thou` | token | 13 | 2017-07-14 | tokens |

`set:hou+related` covers all three. The 24 HOU Invocations are `mp2` 31–54,
reached via `set:akh+related`.

---

## 2. Treatments

Survey (`survey_treatment_signature.py HOU`): `regular` except the 5 full-art
basics (`fa`) and the inverted game-day Adorned Pouncer (`b`).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 199 | `hou` 1–199 (85 C / 60 U / 42 R / 12 M) | `regular` | rarity/base sub-selectors — R+M ≈ $134 nonfoil / $282 foil (Torment of Hailfire 77 ~$35, Razaketh 73 ~$14, Unesh 52 ~$9) |
| full-art basics | 5 | `hou` 185–189 (one per type) | `fa` | **kept by default** — ~$1.50 / $6.60 |
| Planeswalker-deck exclusives | 10 | `hou` 200 Nissa, Genesis Mage + 201–204; 205 Nicol Bolas, the Deceiver + 206–209 | `regular` | **unique cards** — keep; walkers foil-only (Bolas ~$10), deck mates nonfoil-only |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 54 prints, auto-dropped (~$398 foil) |
| `promopack` + `stamped` | `regular` | **yes** — `phou` `Np` = base + stamp | 4 prints, ~$59 nonfoil / ~$180 foil (Torment of Hailfire `77p` ~$51 / $119) |
| `gameday` | — | **no** — own art | Adorned Pouncer 2 (inverted, ~$12), Abrade 83 |
| `draftweekend` + `datestamped` | — | **no** — own art | Ramunap Excavator 129 (~$5) |
| `buyabox` | — | **no** — own art | Wildfire Eternal 109 |
| `planeswalkerdeck` | — | unique cards | 200–209 |

No fancy-foil sheet → configured `[dupe_foil] hou = []` (2026-11-08) to enable `mm query missing-set hou`.

**Full-art convention:** the 5 basics at 185–189.

---

## 3. Chase variants

None among uncommons.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] hou = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `phou` promo-pack stamped `Np` | 4 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$59 |
| `phou` game day / draft weekend / buy-a-box | 4 | **owner's call** — all have their own art |
| PW-deck 200–209 | 10 | keep — real cards |

**Scarcity check:** not run yet (written before `[dupe_foil]` was added).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `phou` | prerelease, datestamped (foil) | — |
| `Np` | `phou` | Promo Pack, stamped | Torment of Hailfire `77p` |
| `2`, `83` | `phou` | Game Day (alt art) | Adorned Pouncer 2 |
| `109` | `phou` | Buy-a-Box (alt art) | Wildfire Eternal |
| `129` | `phou` | Draft Weekend (alt art, datestamped) | Ramunap Excavator |
| `200`–`209` | `hou` | Planeswalker Decks | Nicol Bolas, the Deceiver 205 |
| `31`–`54` | `mp2` | Invocations (HOU half) | The Scarab God 53 |

---

## 7. Edge cases & gotchas

- **Ramunap Excavator 129 carries `datestamped` but has its own art.** `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).
- **Invocations are filed under `akh`**: `mp2` lists both sets' Invocations,
  so a "missing from HOU" run won't show The Scarab God's Invocation.
- Only 4 Promo Pack prints — far fewer than later sets.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] hou = []` — configured 2026-11-08 (enables `mm query missing-set hou`).
- `config/families.toml` `[[unobtainable.hou.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.hou]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | foil slot can be an Invocation (`mp2` 31–54; MTGJSON sheet `foilOrMasterpiece1In129`) |
| Planeswalker Decks ×2 | Planeswalker deck | Nissa / Nicol Bolas; cards at 200–209 |
| Bundle | Bundle | Bundle Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py hou --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$5.00, 97.6% coverage |
| `prerelease` / `showdown` | ~$5.82 / ~$7.01 |
