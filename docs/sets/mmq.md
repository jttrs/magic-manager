# `mmq` — Mercadian Masques

> Per-family memory doc. Read this before answering set-specific questions about
> `mmq` or working on `mmq`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mmq`
**Family root type:** `expansion`
**Family released:** 1999-10-04
**Last audit:** 2026-11-06 via `/characterize-set mmq` (one-at-a-time run — tier decisions pending owner review).

---

> **First Masques-block set, old border, no mythics.** 20 basics. Its English prerelease foil (`pmmq` Overtaker 89) reuses the booster card's CN and art.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mmq` | expansion | 350 | 1999-10-04 | parent — booster set 1–350 (basics 331–350) |
| `pmmq` | promo | 1 | 1999-10-04 | prerelease Overtaker `89` — foil, `datestamped`, same art as `mmq` 89, ~$5 |

`set:mmq+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 350 | `mmq` 1–350 (130 C / 110 U / 110 R; basics 331–350) | `regular` | rarity/base sub-selectors — R ≈ $612 nonfoil / $8285 foil (Rishadan Port 324 ~$106 / ~$1501 foil, Food Chain 246 ~$52, Misdirection 87 ~$49 / ~$1267 foil, Dust Bowl 316 ~$41, Squee, Goblin Nabob 214 ~$35) |
| prerelease | 1 | `pmmq` 89 | `regular` | **same art** — auto-dropped |

**`promo_types`:** `pmmq` 89 carries `prerelease` + `datestamped` and shares art with `mmq` 89, so missing-set drops it correctly. No fancy-foil sheet →
proposed `[dupe_foil] mmq = []` to enable `mm query missing-set mmq`.

---

## 3–4.

Foil commons are pricey (common foil total ~$3696, vs ~$80 nonfoil). No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] mmq = []` | 0 | **apply** — empty, enables missing-set |
| `pmmq` prerelease | 1 | none needed — auto-dropped (same art) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `89` | `pmmq` | prerelease (datestamped, same art) | Overtaker |

---

## 7. Edge cases & gotchas

- **Rishadan Port 324 alone is ~17% of nonfoil rare value.**
- MTGJSON: 4 Theme Decks (Deepwood Menace, Disrupter, Rebel's Call, Tidal Mastery) plus an `Enhanced Deck` version of each, Tournament Pack, Fat Pack.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.mmq.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.mmq]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Tournament Pack | starter-size sealed pack | — |
| Theme Decks ×4 (+ Enhanced) | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mmq --list-boosters` (2026-11-06): `draft` EV ~$18.28, `fat-pack` ~$15.35, `tournament` ~$70.18.
