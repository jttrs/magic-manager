# `3ed` — Revised Edition

> Per-family memory doc. Read this before answering set-specific questions about
> `3ed` or working on `3ed`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `3ed`
**Family root type:** `core`
**Family released:** 1994-04-11
**Last audit:** 2026-11-06 via `/characterize-set 3ed` (one-at-a-time run — tier decisions pending owner review).

---

> **Core set, white border, nonfoil only.** 15 basics. Home of the white-bordered dual lands (282–291). Its child `fbb` (Foreign Black Border) is 919 French / German / Italian prints, absent locally.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `3ed` | core | 306 | 1994-04-11 | parent — 1–291 + basics 292–306 |
| `fbb` | core | 307 cards / 919 prints (0 local) | 1994-04-11 | Foreign Black Border — French, German, Italian; not synced |

`set:3ed+related` covers both.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 306 | `3ed` 1–306 (75 C / 95 U / 121 R + 15 basics) | `regular` | rarity/base sub-selectors — R ≈ $7267 |
| dual lands | 10 | `3ed` 282–291 (Underground Sea 290 ~$1099, Volcanic Island 291 ~$1008, Tundra 289 ~$715, Tropical Island 288 ~$604, Badlands 282 ~$585 …; rare) | `regular` | part of base — **~$6227, ~86% of rare value** |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] 3ed = []` to enable `mm query missing-set 3ed`.

---

## 3–4.

The ten dual lands. No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] 3ed = []` | 0 | **apply** — empty, enables missing-set |
| `fbb` Foreign Black Border | 919 (0 local) | **owner's call** — non-English only, not syncable |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **`fbb` is non-English** (French / German / Italian).
- **No foils.** Every print shares art with another local set.
- MTGJSON: Revised Edition Gift Box and Starter Deck (a `starter` booster type in `sealed-value`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.3ed.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.3ed]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |
| Starter Deck | starter deck | — |
| Gift Box | gift bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py 3ed --list-boosters` (2026-11-06): `default` EV ~$70.50, `starter` ~$193.26.
