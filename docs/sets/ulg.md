# `ulg` — Urza's Legacy

> Per-family memory doc. Read this before answering set-specific questions about
> `ulg` or working on `ulg`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ulg`
**Family root type:** `expansion`
**Family released:** 1999-02-15
**Last audit:** 2026-11-06 via `/characterize-set ulg` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Urza-block set, old border, no basics, no mythics — the first expansion printed in foil.** Its English prerelease foil (`pulg` Beast of Burden 122) reuses the booster card's CN and art.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ulg` | expansion | 143 | 1999-02-15 | parent — booster set 1–143 (no basics) |
| `pulg` | promo | 1 | 1999-02-15 | prerelease Beast of Burden `122` — foil, `datestamped`, same art as `ulg` 122, ~$8 |

`set:ulg+related` covers all. (`mm set list-related` reports `pulg` as 2 cards; Scryfall search returns 1.)

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `ulg` 1–143 (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R ≈ $851 nonfoil / $7343 foil (Grim Monolith 126 ~$477 / ~$3484 foil, Deranged Hermit 101 ~$87, Palinchron 38 ~$43, Goblin Welder 80 ~$39, Memory Jar 129 ~$37) |
| prerelease | 1 | `pulg` 122 | `regular` | **same art** — auto-dropped |

**`promo_types`:** `pulg` 122 carries `prerelease` + `datestamped` and shares art with `ulg` 122, so missing-set drops it correctly. No fancy-foil sheet →
proposed `[dupe_foil] ulg = []` to enable `mm query missing-set ulg`.

---

## 3–4.

Grim Monolith 126 (Reserved List) is over half the nonfoil rare value; foil ~$3484. No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ulg = []` | 0 | **apply** — empty, enables missing-set |
| `pulg` prerelease | 1 | none needed — auto-dropped (same art) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `122` | `pulg` | prerelease (datestamped, same art) | Beast of Burden |

---

## 7. Edge cases & gotchas

- **First set with foils.** [`usg`](usg.md) (four months earlier) is nonfoil-only.
- MTGJSON: 4 Theme Decks (Crusher, Phyrexian Assault, Radiant's Revenge, Time Drain) plus an `Enhanced Deck` version of each. No Fat Pack.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ulg.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ulg]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 (+ Enhanced) | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ulg --list-boosters` (2026-11-06): `draft` EV ~$31.86.
