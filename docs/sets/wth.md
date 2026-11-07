# `wth` — Weatherlight

> Per-family memory doc. Read this before answering set-specific questions about
> `wth` or working on `wth`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `wth`
**Family root type:** `expansion`
**Family released:** 1997-06-09
**Last audit:** 2026-11-06 via `/characterize-set wth` (one-at-a-time run — tier decisions pending owner review).

---

> **Last Mirage-block set, old border, nonfoil only, no basics, no promos.** 167 cards, with four lands at 164–167 (Gemstone Mine, Lotus Vale, Scorched Ruins, Winding Canyons).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `wth` | expansion | 167 | 1997-06-09 | parent — booster set 1–167 (no basics) |

No children (no promo or token set).

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 167 | `wth` 1–167 (62 C / 55 U / 50 R) | `regular` | rarity/base sub-selectors — R ≈ $508 (Null Rod 154 ~$108, Scorched Ruins 166 ~$65, Lotus Vale 165 ~$46, Firestorm 101 ~$44, Winding Canyons 167 ~$36, Abeyance 1 ~$28) |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] wth = []` to enable `mm query missing-set wth`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] wth = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Odd rarity counts** (62 C / 55 U / 50 R) — a 167-card set, not the usual 143.
- **Pre-foil era:** every print is nonfoil.
- MTGJSON: 4 decks typed `MTGO Theme Deck` (Air Forces, Dead and Alive, Fiery Fury, Gatecrasher); no paper sealed products listed besides boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.wth.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.wth]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py wth --list-boosters` (2026-11-06): `draft` EV ~$16.07.
