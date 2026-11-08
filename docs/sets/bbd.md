# `bbd` — Battlebond

> Per-family memory doc. Read this before answering set-specific questions about
> `bbd` or working on `bbd`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `bbd`
**Family root type:** `draft_innovation`
**Family released:** 2018-06-08
**Last audit:** 2026-11-05 via `/characterize-set bbd` (one-at-a-time run — tier decisions pending owner review).

---

> **Two-Headed Giant draft set built around Partner pairs.** Base frame only,
> new cards mixed with multiplayer reprints (Doubling Season, Mycosynth Lattice,
> Seedborn Muse, Land Tax). The one treatment quirk: the two Kenrith
> planeswalkers have a nonfoil print (1–2) and a foil-only alternate-art print
> (255–256), each on its own booster sheet.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `bbd` | draft_innovation | 256 | 2018-06-08 | parent — Kenriths 1–2, partner pairs 3–22, main set 23–249, basics 250–254, alt-art Kenriths 255–256 |
| `pbbd` | promo | 22 | 2018-06-08 | prerelease `Ns` datestamped foils — the 20 partner cards 3s–22s + Kenriths 255s–256s |
| `tbbd` | token | 8 | 2018-06-08 | tokens |

`set:bbd+related` covers all three. `draft_innovation` isn't a default
inventory set type, but the anchor is always included by
`mm set master-list bbd`.

---

## 2. Treatments

Survey (`survey_treatment_signature.py BBD`, 286 prints): all `regular`. The
only `promo_types` are `prerelease` + `datestamped` + `setpromo` on the 22
`pbbd` prints.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| Kenriths, nonfoil | 2 | `bbd` 1 Will, 2 Rowan (nonfoil-only, mythic; draft sheet `mythicPartner1`) | `regular` | mythic-regular |
| Kenriths, alt-art foil | 2 | `bbd` 255 Will ~$18, 256 Rowan ~$13 (foil-only, **different art** from 1–2; draft sheet `foilMythicPartner1`) | `regular` | **not a dupe** — distinct illustration, keep |
| partner pairs | 20 | `bbd` 3–22 (rare legendary pairs 3–12: Regna/Krav, Zndrsplt/Okaun, Virtus/Gorm, Khorvath/Sylvia, Pir/Toothy; uncommon pairs 13–22) | `regular` | rarity sub-selectors |
| main set + basics | 232 | `bbd` 23–254 (foil + nonfoil) | `regular` | rarity sub-selectors |
| prerelease datestamped | 22 | `pbbd` `Ns` | `regular` | auto-dropped (~$118 foil; Virtus the Veiled `7s` ~$18) |
| tokens | 8 | `tbbd` | `regular` | tokens |

Rarity totals (`bbd`): 106 C / 80 U / 53 R / 17 M. R+M ≈ $411 nonfoil /
$1,098 foil (Doubling Season 195 ~$36 / $50, Mycosynth Lattice 241 ~$35 / $72,
Morphic Pool 83 ~$30, Archfiend of Despair 44 ~$23, Sea of Clouds 84 ~$20,
Seedborn Muse 212 ~$19).

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 22 prints, auto-dropped |
| `setpromo` | — | marker on every `pbbd` print | not a dupe signal |

No fancy-foil sheet → proposed `[dupe_foil] bbd = []` to enable
`mm query missing-set bbd`.

**Full-art convention:** none.

---

## 3. Chase variants

The alt-art foil Kenriths 255–256 are the only alternate prints in the
booster. Prices are driven by the multiplayer reprints, not by treatments.

---

## 4. Scenes / posters / panoramas

None. (Partner pairs are rules pairs, not art scenes.)

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] bbd = []` | 0 | **apply** — empty, enables missing-set |
| alt-art foil Kenriths 255–256 | 2 | keep — booster cards with their own art |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pbbd` | prerelease, datestamped (foil) | Virtus the Veiled `7s` |

No Promo Pack, FNM or buy-a-box prints.

---

## 7. Edge cases & gotchas

- **Same card, two arts, split by finish:** Will Kenrith exists as nonfoil 1 and
  foil 255, with different illustrations. A "missing foil Will Kenrith" means
  255, not a foil of 1 (which doesn't exist). The prerelease promos `255s` /
  `256s` use the alt art; `clb` and `plst` reprints use the 1–2 art.
- **Partner sheets:** MTGJSON's draft booster puts each partner pair on a shared
  sheet so both halves open together — `sealed-value` EV accounts for this.
- **Every other card has both finishes**, including the basics.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.bbd.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.bbd]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | Partner-pair sheets; Kenriths split nonfoil 1–2 / foil 255–256 |
| Booster Box / Case | booster product | — |
| Blister Pack | limited aid tool (MTGJSON `limited_aid_tool` / `sealed_set`) | — |

No precon decks in MTGJSON for `bbd`.

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py bbd --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$9.91, 99.7% coverage |
| `prerelease` | EV ~$8.98, 100% coverage |
