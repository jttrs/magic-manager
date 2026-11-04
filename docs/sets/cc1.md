# `cc1` — Commander Collection: Green

> Per-family memory doc. Read this before answering set-specific questions about
> `cc1` or working on `cc1`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `cc1`
**Family root type:** `arsenal`
**Family released:** 2020-12-04
**Last audit:** 2026-11-04 via `/characterize-set cc1` (one-at-a-time run — tier decisions pending owner review).

---

> **A fixed-content box set.** 8 green Commander staples with new art, sold as a
> regular (nonfoil) box and a Premium (foil) box — hence both finishes on every
> card. No token (unlike [`cc2`](cc2.md), which adds one). Sibling families: `cc2`.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cc1` | arsenal | 8 | 2020-12-04 | parent — the only set, CN 1–8 |

No children. No `--only` needed.

---

## 2. Treatments

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (foil + nonfoil) | 8 | `cc1` 1–8 (2 mythic, 6 rare) | `regular` | rarity/base sub-selectors |

No alt treatments, no `promo_types`.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured, none needed. Proposed `[dupe_foil] cc1 = []` only to enable
`mm query missing-set cc1`.

**Totals (local prices, 2026-11-04):** ≈ $99 nonfoil / $145 foil (Worldly Tutor 6,
Sylvan Library 5, Seedborn Muse 4 lead).

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- Foil and nonfoil come from different sealed products (Premium vs regular box).
- Sol Ring 7 / Command Tower 8 have dozens of printings — confirm the set code.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.cc1.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.cc1]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander Collection Green / Green Premium | box set (MTGJSON `sealedProduct`) | nonfoil vs foil versions of the same 8 cards |

**Booster types (for `sealed-value` EV):** none.
