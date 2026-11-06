# `bok` — Betrayers of Kamigawa

> Per-family memory doc. Read this before answering set-specific questions about
> `bok` or working on `bok`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `bok`
**Family root type:** `expansion`
**Family released:** 2005-02-04
**Last audit:** 2026-11-06 via `/characterize-set bok` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Kamigawa set, pre-mythic.** Old border-era rarity: **no mythics** (C/U/R), no basics. Home of Umezawa's Jitte and the flip-card Budoka Pupil.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `bok` | expansion | 165 | 2005-02-04 | parent — booster set 1–165 (no basics) |
| `pbok` | promo | 2 | 2005-02-04 | prerelease Ink-Eyes, Servant of Oni `71★` (alt art, `datestamped`, ~$21) + release Budoka Pupil `122★` (same art) |

`set:bok+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 165 | `bok` 1–165, no basic lands (55 C / 55 U / 55 R) | `regular` | rarity/base sub-selectors — R+M ≈ $229 nonfoil / $2066 foil (Lifegift 132 ~$24, Umezawa's Jitte 163 ~$21 / ~$383 foil, Goryo's Vengeance 67 ~$20 / ~$130, Higure, the Still Wind 37 ~$18, Disrupting Shoal 33 ~$16 / ~$285) |

**`promo_types`:** the prerelease Ink-Eyes `71★` has its own art; the release Budoka Pupil `122★` (~$0.67) reuses the booster art. Only the prerelease carries `datestamped` (dropped by missing-set, which hides a ~$21 alt-art card); the same-art release foil is listed next to `bok` 122. No fancy-foil sheet →
proposed `[dupe_foil] bok = []` to enable `mm query missing-set bok`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] bok = []` | 0 | **apply** — empty, enables missing-set |
| `pbok` promos | 2 | **owner's call** — 1 of 2 has its own art (Ink-Eyes ~$21) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `71★` | `pbok` | prerelease (alt art) | Ink-Eyes, Servant of Oni |
| `122★` | `pbok` | release (same art) | Budoka Pupil // Ichiga, Who Topples Oaks |

---

## 7. Edge cases & gotchas

- **No basic lands**, **no mythics**, no token set.
- Foil premium is steep (Jitte ~$383 foil, Disrupting Shoal ~$285).
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include a `fat-pack` type.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.bok.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.bok]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py bok --list-boosters` (2026-11-06): `draft` EV ~$9.48, `fat-pack` ~$3.13.
