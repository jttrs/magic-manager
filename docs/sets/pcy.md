# `pcy` — Prophecy

> Per-family memory doc. Read this before answering set-specific questions about
> `pcy` or working on `pcy`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `pcy`
**Family root type:** `expansion`
**Family released:** 2000-06-05
**Last audit:** 2026-11-06 via `/characterize-set pcy` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Masques-block set, old border, no mythics, no basics.** Its English prerelease foil (`ppcy` Avatar of Hope 3) reuses the booster card's CN and art. Rhystic Study is a **common** here (~$66).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `pcy` | expansion | 143 | 2000-06-05 | parent — booster set 1–143 (no basics) |
| `ppcy` | promo | 1 | 2000-06-05 | prerelease Avatar of Hope `3` — foil, `datestamped`, same art as `pcy` 3, ~$7 |

`set:pcy+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `pcy` 1–143 (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R ≈ $83 nonfoil / $1291 foil (Avatar of Woe 56 ~$16 / ~$228 foil, Overburden 39 ~$14, Entangler 7 ~$13, Foil 34 ~$11 / ~$240 foil) |
| prerelease | 1 | `ppcy` 3 | `regular` | **same art** — dropped by `drop_datestamped_with_sibling` |

**`promo_types`:** `ppcy` 3 carries `prerelease` + `datestamped` and shares art with `pcy` 3, so missing-set drops it correctly. No fancy-foil sheet →
configured `[dupe_foil] pcy = []` (2026-11-08) to enable `mm query missing-set pcy`.

---

## 3–4.

Rhystic Study 45 (common, ~$66 / ~$457 foil) is the most valuable card; it's invisible to the rare/mythic sub-selectors. No scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] pcy = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `ppcy` prerelease | 1 | none needed — auto-dropped (same art) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `3` | `ppcy` | prerelease (datestamped, same art) | Avatar of Hope |

---

## 7. Edge cases & gotchas

- **Before 2000-10 the prerelease promo is English** and same-art (contrast [`inv`](inv.md) onward, where it's a novelty language).
- **Valuable commons:** Rhystic Study 45, Spore Frog 126, Alexi's Cloak 29 — commons are over a third of nonfoil value.
- MTGJSON: 4 Theme Decks (Distress, Pummel, Slither, Turnaround), Fat Pack.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] pcy = []` — configured 2026-11-08 (enables `mm query missing-set pcy`).
- `config/families.toml` `[[unobtainable.pcy.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.pcy]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py pcy --list-boosters` (2026-11-06): `draft` EV ~$21.21, `fat-pack` ~$11.99.
