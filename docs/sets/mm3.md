# `mm3` — Modern Masters 2017

> Per-family memory doc. Read this before answering set-specific questions about
> `mm3` or working on `mm3`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `mm3`
**Family root type:** `masters`
**Family released:** 2017-03-17
**Last audit:** 2026-11-05 via `/characterize-set mm3` (one-at-a-time run — tier decisions pending owner review).

---

> **Modern-format Masters reprint set** (fetchlands, Cavern of Souls,
> Tarmogoyf). All 249 cards are reprints in the base frame, every one in both
> finishes. No promo child, no basics. Same shape as [`ima`](ima.md) /
> [`a25`](a25.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mm3` | masters | 249 | 2017-03-17 | parent — the only card set, CN 1–249 (lands at the end: guildgates, enemy fetchlands 229/239/240/244/249) |
| `tmm3` | token | 21 | 2017-03-17 | tokens |

`set:mm3+related` covers both. `masters` isn't a default inventory set type,
but the anchor is always included by `mm set master-list mm3`.

---

## 2. Treatments

All `regular`, no `promo_types`. `frame_effects` `miracle` (6 prints) is
cosmetic.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (foil + nonfoil) | 249 | `mm3` 1–249 (101 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $454 nonfoil / $661 foil |
| tokens | 21 | `tmm3` | `regular` | tokens |

Top cards: Cavern of Souls 232 (~$51), Scalding Tarn 244 (~$37), Misty
Rainforest 240 (~$36), Verdant Catacombs 249 (~$36), Marsh Flats 239,
Arid Mesa 229, Cyclonic Rift 35 (~$31), Craterhoof Behemoth 122 (~$28).

**New art (local check, 8):** Tarmogoyf 141, Graceful Reprieve 8, Abyssal
Specter 59, Hungry Spriggan 129, Agent of Masks 149, Golgari Germination 167,
Aethertow 205, Tattermunge Witch 212.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] mm3 = []` to enable `mm query missing-set mm3`.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] mm3 = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **Rarities are re-assigned for the Masters set** (the fetchlands are rare
  here).
- No basics; the guildgates fill the land slot.
- Whole family is booster-obtainable.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.mm3.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.mm3]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / Booster Box | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mm3 --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$11.16, 99.8% coverage |
