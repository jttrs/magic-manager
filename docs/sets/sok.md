# `sok` — Saviors of Kamigawa

> Per-family memory doc. Read this before answering set-specific questions about
> `sok` or working on `sok`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `sok`
**Family root type:** `expansion`
**Family released:** 2005-06-03
**Last audit:** 2026-11-06 via `/characterize-set sok` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Kamigawa set, pre-mythic.** Old border-era rarity: **no mythics** (C/U/R), no basics. Includes flip cards (Erayo) and the legendary lands Miren and Oboro.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `sok` | expansion | 165 | 2005-06-03 | parent — booster set 1–165 (no basics) |
| `psok` | promo | 2 | 2005-06-03 | prerelease Kiyomaro, First to Stand `18★` (alt art, `datestamped`) + release Ghost-Lit Raider `99★` (same art) |

`set:sok+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 165 | `sok` 1–165, no basic lands (55 C / 55 U / 55 R) | `regular` | rarity/base sub-selectors — R+M ≈ $261 nonfoil / $1755 foil (Choice of Damnations 62 ~$23, Miren, the Moaning Well 163 ~$23 / ~$93 foil, Oboro, Palace in the Clouds 164 ~$22 / ~$115, Erayo, Soratami Ascendant 35 ~$20 / ~$187, Sakashima the Impostor 53 ~$18 / ~$155) |

**`promo_types`:** the prerelease Kiyomaro `18★` has its own art; the release Ghost-Lit Raider `99★` (~$0.99) reuses the booster art. Only the prerelease carries `datestamped` (dropped by missing-set); the same-art release foil is listed next to `sok` 99. No fancy-foil sheet →
proposed `[dupe_foil] sok = []` to enable `mm query missing-set sok`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] sok = []` | 0 | **apply** — empty, enables missing-set |
| `psok` promos | 2 | **owner's call** — 1 of 2 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `18★` | `psok` | prerelease (alt art) | Kiyomaro, First to Stand |
| `99★` | `psok` | release (same art) | Ghost-Lit Raider |

---

## 7. Edge cases & gotchas

- **No basic lands**, **no mythics**, no token set.
- Flip cards (e.g. Erayo, Soratami Ascendant // Erayo's Essence 35) are one print with two names.
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include a `fat-pack` type.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.sok.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.sok]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py sok --list-boosters` (2026-11-06): `draft` EV ~$11.20, `fat-pack` ~$7.73.
