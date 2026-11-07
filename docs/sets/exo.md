# `exo` — Exodus

> Per-family memory doc. Read this before answering set-specific questions about
> `exo` or working on `exo`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `exo`
**Family root type:** `expansion`
**Family released:** 1998-06-15
**Last audit:** 2026-11-06 via `/characterize-set exo` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Tempest-block set, old border, nonfoil only, no basics, no mythics.** Its prerelease promo (`pexo` Monstrous Hound 89) is **nonfoil**, same CN and art as the booster card.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `exo` | expansion | 143 | 1998-06-15 | parent — booster set 1–143 (no basics) |
| `pexo` | promo | 1 | 1998-06-15 | prerelease Monstrous Hound `89` — nonfoil, `datestamped`, same art as `exo` 89, ~$5 |

`set:exo+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `exo` 1–143 (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R ≈ $1409 (City of Traitors 143 ~$553, Survival of the Fittest 129 ~$437, Recurring Nightmare 72 ~$79, Hatred 64 ~$65, Mind Over Matter 40 ~$49) |
| prerelease | 1 | `pexo` 89 | `regular` | **same art** — auto-dropped |

**`promo_types`:** `pexo` 89 carries `prerelease` + `datestamped` and shares art with `exo` 89, so missing-set drops it correctly. No fancy-foil sheet →
proposed `[dupe_foil] exo = []` to enable `mm query missing-set exo`.

---

## 3–4.

City of Traitors 143 and Survival of the Fittest 129 (both Reserved List) are ~70% of rare value. No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] exo = []` | 0 | **apply** — empty, enables missing-set |
| `pexo` prerelease | 1 | none needed — auto-dropped (same art) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `89` | `pexo` | prerelease (nonfoil, datestamped, same art) | Monstrous Hound |

---

## 7. Edge cases & gotchas

- **Pre-foil era:** every print, including the prerelease, is nonfoil.
- MTGJSON: 4 Theme Decks (Dominator, Groundbreaker, White Heat, Widowmaker) as `Basic Deck`s plus an `Advanced Deck` version of each.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.exo.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.exo]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 (+ Advanced) | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py exo --list-boosters` (2026-11-06): `draft` EV ~$40.81.
