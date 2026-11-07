# `ema` — Eternal Masters

> Per-family memory doc. Read this before answering set-specific questions about
> `ema` or working on `ema`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ema`
**Family root type:** `masters`
**Family released:** 2016-06-10
**Last audit:** 2026-11-05 via `/characterize-set ema` (one-at-a-time run — tier decisions pending owner review).

---

> **Legacy/Vintage-focused Masters reprint set** (Force of Will, Chrome Mox,
> Mana Crypt, Wasteland). All 249 cards are reprints in the base frame, every
> one in both finishes. No promo child, no basics. Same shape as
> [`mm3`](mm3.md) / [`ima`](ima.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ema` | masters | 249 | 2016-06-10 | parent — the only card set, CN 1–249 (lands at the end: gain lands, Karakas 240, Wasteland 248) |
| `tema` | token | 16 | 2016-06-10 | tokens |

`set:ema+related` covers both. `masters` isn't a default inventory set type,
but the anchor is always included by `mm set master-list ema`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`, no `full_art`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (foil + nonfoil) | 249 | `ema` 1–249 (101 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $867 nonfoil / $1,615 foil |
| tokens | 16 | `tema` | `regular` | tokens |

Top cards: Chrome Mox 219 (~$153 / $301 foil), Force of Will 49 (~$64 /
$151), Argothian Enchantress 158 (~$63), Vampiric Tutor 112 (~$53), Mana Crypt
225 (~$39), Sensei's Divining Top 232, Enlightened Tutor 9, Natural Order 177.

**New art (local check):** 38 prints (Argothian Enchantress 158, Wasteland
248, Natural Order 177, Vindicate 210, Control Magic 42, the three Hondens,
…). The local catalog undercounts older sets, so treat the count as an upper
bound.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] ema = []` to enable `mm query missing-set ema`.

---

## 3. Chase variants

None as treatments; value is in the mythic/rare reprints.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ema = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **Rarities are re-assigned for the Masters set** (Karakas 240 is mythic,
  Wasteland 248 rare).
- No basics; draft booster EV is high (~$19.80) for a 2016 set.
- Whole family is booster-obtainable.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ema.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ema]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / Booster Box | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ema --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$19.80, 99.9% coverage |
