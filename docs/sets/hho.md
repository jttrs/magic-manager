# `hho` — Happy Holidays

> Per-family memory doc. Read this before answering set-specific questions about
> `hho` or working on `hho`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `hho`
**Family root type:** `funny`
**Family released:** 2006-12-01 (one card added each December since)
**Last audit:** 2026-11-06 via `/characterize-set hho` (one-at-a-time run — tier decisions pending owner review).

---

> **Wizards' yearly holiday gift cards**: one silver-bordered foil per year,
> sent to staff and partners, never sold. Standalone root, no children. A
> growing set — each December adds a CN.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `hho` | funny | 23 (Scryfall) / 21 local | 2006-12-01 → 2025-11-15 | parent — CN 6–25 one card per year + `21★` Treasure token |

Scryfall lists 23; the local sync holds 20 cards (CN 6–25) plus the `21★`
token. CNs 1–5 don't exist locally. `funny` isn't a default inventory set type,
but the anchor is always included by `mm set master-list hho`.

---

## 2. Treatments

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| holiday cards 2006–2013 | 8 | `hho` 6–13 (rare, foil-only, `datestamped` + `event`) | `regular` | rare-regular — Gifts Given 7 ~$401, Fruitcake Elemental 6 ~$252, Snow Mercy 10 ~$180, Evil Presents 8 ~$176 |
| holiday cards 2014–2020 | 7 | `hho` 14–20 (mythic, foil-only, `datestamped` + `event`) | `regular` | mythic-regular — Mishra's Toy Workshop 14 ~$66 |
| holiday cards 2021– | 5 | `hho` 21–25 (2021–2024 mythic, 2025 Cheer 25 rare; `event` only) | `regular` | rarity sub-selectors |
| metal Treasure token | 1 | `hho` `21★` (`metal` + `serialized` + `thick`, `is_token = 1`, unpriced) | `regular` | token — dropped by missing-set |

Total ≈ $1,695 foil for the 20 cards.

**`promo_types` dupe-foil / stamped signals:** 2006–2020 carry
`datestamped`, but there is no same-name sibling, so
`missing.drop_datestamped_with_sibling` keeps them. Proposed
`[dupe_foil] hho = []` to enable `mm query missing-set hho`.

---

## 3. Chase variants

Gifts Given 7 (~$401) and Fruitcake Elemental 6 (~$252) — the scarce early
years.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] hho = []` | 0 | **apply** — empty, enables missing-set |
| whole family | 20 | **owner's call** — never sold (gift-only); kept (default) — pending owner review |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **The set grows every year.** Re-sync `hho` each December (`mm set sync hho`)
  or the newest card is missing locally.
- **Rarity changes over time:** rare 2006–2013, mythic 2014–2024, rare again
  for Cheer (2025). A mythic filter skips the most valuable cards.
- **The token is in the parent set** (`21★`, `is_token = 1`) and is a metal,
  serialized card.
- **Release date per card** — each print's `released_at` is its own December.
- MTGJSON has no booster or deck data for `hho`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.hho.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.hho]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| holiday gift card | promo (not sold) | one foil per year |

**Booster types (for `sealed-value` EV):** none.
