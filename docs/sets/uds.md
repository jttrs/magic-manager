# `uds` — Urza's Destiny

> Per-family memory doc. Read this before answering set-specific questions about
> `uds` or working on `uds`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `uds`
**Family root type:** `expansion`
**Family released:** 1999-06-07
**Last audit:** 2026-11-06 via `/characterize-set uds` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Urza-block set, old border, no mythics, no basics.** The most valuable rare slot of its era (Replenish, Metalworker, Academy Rector). Its English prerelease foil (`puds` False Prophet 6) reuses the booster card's CN and art.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `uds` | expansion | 143 | 1999-06-07 | parent — booster set 1–143 (no basics) |
| `puds` | promo | 1 | 1999-06-07 | prerelease False Prophet `6` — foil, `datestamped`, same art as `uds` 6, ~$14 |

`set:uds+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `uds` 1–143 (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R ≈ $1027 nonfoil / $7215 foil (Replenish 15 ~$218, Metalworker 135 ~$197, Academy Rector 1 ~$84, Yavimaya Hollow 143 ~$79, Powder Keg 136 ~$70, Rofellos 118 ~$62) |
| prerelease | 1 | `puds` 6 | `regular` | **same art** — auto-dropped |

**`promo_types`:** `puds` 6 carries `prerelease` + `datestamped` and shares art with `uds` 6, so missing-set drops it correctly. No fancy-foil sheet →
proposed `[dupe_foil] uds = []` to enable `mm query missing-set uds`.

---

## 3–4.

Replenish 15 and Metalworker 135 (Reserved List) are ~40% of nonfoil rare value. No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] uds = []` | 0 | **apply** — empty, enables missing-set |
| `puds` prerelease | 1 | none needed — auto-dropped (same art) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `6` | `puds` | prerelease (datestamped, same art) | False Prophet |

---

## 7. Edge cases & gotchas

- **Nonfoil rares are unusually close to foil** (foil ~7× vs ~12–14× in neighbouring sets) because of Reserved List rares.
- MTGJSON: 4 Theme Decks (Assassin, Battle Surge, Enchanter, Fiendish Nature) plus an `Enhanced Deck` version of each. No Fat Pack.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.uds.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.uds]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 (+ Enhanced) | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py uds --list-boosters` (2026-11-06): `draft` EV ~$32.92.
