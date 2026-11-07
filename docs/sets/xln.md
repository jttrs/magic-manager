# `xln` — Ixalan

> Per-family memory doc. Read this before answering set-specific questions about
> `xln` or working on `xln`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `xln`
**Family root type:** `expansion`
**Family released:** 2017-09-29
**Last audit:** 2026-11-05 via `/characterize-set xln` (one-at-a-time run — tier decisions pending owner review).

---

> **Base-frame expansion with two Planeswalker Decks and a Buy-a-Box
> "Treasure Chest".** The ten transforming legendary lands (`compasslanddfc`)
> are the set's signature. The Treasure Chest (`pxtc`) holds foil copies of
> those ten lands with the booster art. The sibling set is [`rix`](rix.md),
> separately rooted.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `xln` | expansion | 289 | 2017-09-29 | parent — booster set 1–279 (basics 260–279), PW-deck cards 280–289 |
| `pxln` | promo | 120 | 2017-09-29 | prerelease `Ns` datestamped (78) + Promo Pack `Np` stamped (37) + buy-a-box / event promos (5) |
| `pxtc` | promo | 10 | 2017-09-29 | XLN Treasure Chest — foil transforming lands, same CNs as `xln` |
| `pss2` | promo | 5 | 2017-09-29 | XLN Standard Showdown basics, CN 1–5 (foil, rare) |
| `txln` | token | 11 | 2017-09-29 | tokens |

`set:xln+related` covers all five.

---

## 2. Treatments

Survey (`survey_treatment_signature.py XLN`): every print computes `regular`.
`compasslanddfc` (transforming lands) is cosmetic.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 279 | `xln` 1–279 (121 C / 80 U / 63 R / 15 M; 20 basics 260–279) | `regular` | rarity/base sub-selectors — R+M ≈ $136 nonfoil / $331 foil (Revel in Riches 117 ~$22, Primal Amulet 243 ~$12, Jace, Cunning Castaway 60 ~$11) |
| transforming legendary lands | 10 | `xln` 22, 74, 90, 173, 191, 234, 235, 243, 249, 250 (all rare) | `regular` | part of base |
| Planeswalker-deck exclusives | 10 | `xln` 280 Jace, Ingenious Mind-Mage + 281–284; 285 Huatli, Dinosaur Knight + 286–289 | `regular` | **unique cards** — keep; walkers foil-only (~$13 / ~$5), deck mates nonfoil-only |
| Treasure Chest lands | 10 | `pxtc` (same CNs as `xln`; foil-only, `buyabox`) | `regular` | **same art as base** — a foil copy; ≈ $95 |
| Standard Showdown basics | 5 | `pss2` 1–5 | `regular` | basics; art reused from `c16` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 78 prints, auto-dropped (~$497 foil) |
| `promopack` + `stamped` | `regular` | **yes** — `pxln` `Np` = base + stamp | 37 prints, ~$154 nonfoil / ~$263 foil (Revel in Riches `117p` ~$21); ONE/NEO/TDM `stamped` rule |
| `buyabox` (`pxtc`) | `regular` | **yes** — same art as the `xln` land | 10 prints; no stamp token, so a `stamped` rule won't catch them |
| `buyabox` (`pxln`) | — | **no** — Burning Sun's Avatar 135 has its own art | 1 print, ~$0.42 |
| `draftweekend` / `convention` / `openhouse` / `league` | — | 3 alt-art (Bishop of Rebirth 5, Deeproot Champion 185 ~$8, Walk the Plank 130), 1 same-art (Unclaimed Territory 258) | 4 prints |
| `standardshowdown` + `instore` | — | `pss2` basics | 5 prints |
| `setpromo` | — | marker on every `pxln` print | not a dupe signal |
| `planeswalkerdeck` | — | unique cards | 280–289 |

No fancy-foil sheet → proposed `[dupe_foil] xln = []` to enable `mm query missing-set xln`.

**Full-art convention:** none.

---

## 3. Chase variants

None among uncommons. Foil Treasure Chest lands (Growing Rites 191 ~$20,
Primal Amulet 243 ~$18) are the pricey alts.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] xln = []` | 0 | **apply** — empty, enables missing-set |
| `pxln` promo-pack stamped `Np` | 37 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$154 |
| `pxtc` Treasure Chest lands | 10 | **owner's call** — same-art foils of booster rares; a rule would need `set_code`/`promo_types_any_of = ["buyabox"]` scoped to `pxtc` (not `pxln` 135, which has its own art) |
| `pxln` buy-a-box 135 + event promos | 5 | **owner's call** — 4 have their own art |
| PW-deck 280–289 | 10 | keep — real cards |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pxln` | prerelease, datestamped (foil) | — |
| `Np` | `pxln` | Promo Pack, stamped | Revel in Riches `117p` |
| `5` | `pxln` | Draft Weekend (alt art) | Bishop of Rebirth |
| `130` | `pxln` | Open House (alt art) | Walk the Plank |
| `135` | `pxln` | Buy-a-Box (alt art) | Burning Sun's Avatar |
| `185` | `pxln` | convention (alt art) | Deeproot Champion |
| `258` | `pxln` | League | Unclaimed Territory |
| same CN as `xln` | `pxtc` | Treasure Chest (Buy-a-Box) | Search for Azcanta 74 |
| `1`–`5` | `pss2` | Standard Showdown | Island 2 |
| `280`–`289` | `xln` | Planeswalker Decks | Huatli, Dinosaur Knight 285 |

---

## 7. Edge cases & gotchas

- **Two Buy-a-Box sources:** the Treasure Chest set `pxtc` (same-art foil
  lands) and `pxln` 135 (alt-art Burning Sun's Avatar). Both carry `buyabox`,
  so a rule on that token alone would catch an alt-art print too.
- **`pxtc` CNs collide with `xln` CNs** (e.g. both have 74); always pair CN
  with set code.
- **The Treasure Chest is valued as a booster:** MTGJSON models it as a
  `treasure-chest` booster (4 rare/mythic, 2 foils, 2 foil basics, 1
  transforming land) — `sealed-value` EV ~$10.81.
- **`pss2` and [`g17`](g17.md) basics share art** with the `c16`/`c17`
  Commander basics.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.xln.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.xln]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Planeswalker Decks ×2 | Planeswalker deck | Jace / Huatli; cards at 280–289 |
| Booster Battle Pack | two-player pack (MTGJSON `multiple_decks` / `battle_pack`) | — |
| Deck Builder's Toolkit | kit | seven 2-colour decklists + fixed content (MTGJSON `Deck Builder's Toolkit`) |
| Bundle | Bundle | Bundle Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py xln --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$3.78, 99% coverage |
| `treasure-chest` | EV ~$10.81, 84% coverage |
| `prerelease` / `showdown` | ~$4.80 / ~$5.54 |
| `arena` | digital code card, ignore |
