# `nem` — Nemesis

> Per-family memory doc. Read this before answering set-specific questions about
> `nem` or working on `nem`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `nem`
**Family root type:** `expansion`
**Family released:** 2000-02-14
**Last audit:** 2026-11-06 via `/characterize-set nem` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Masques-block set, old border, no mythics, no basics.** Its English prerelease foil (`pnem` Rathi Assassin 67) reuses the booster card's CN and art.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `nem` | expansion | 143 | 2000-02-14 | parent — booster set 1–143 (no basics) |
| `pnem` | promo | 1 | 2000-02-14 | prerelease Rathi Assassin `67` — foil, `datestamped`, same art as `nem` 67, ~$5 |

`set:nem+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `nem` 1–143 (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R ≈ $186 nonfoil / $2214 foil (Parallax Wave 17 ~$33 / ~$437 foil, Tangle Wire 139 ~$27 / ~$350 foil, Kor Haven 141 ~$18, Parallax Tide 37 ~$14, Moggcatcher 96 ~$14) |
| prerelease | 1 | `pnem` 67 | `regular` | **same art** — auto-dropped |

**`promo_types`:** `pnem` 67 carries `prerelease` + `datestamped` and shares art with `nem` 67, so missing-set drops it correctly. No fancy-foil sheet →
configured `[dupe_foil] nem = []` (2026-11-08) to enable `mm query missing-set nem`.

---

## 3–4.

Foil Daze 30 (common, ~$331) is the costliest common foil. No scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] nem = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pnem` prerelease | 1 | none needed — auto-dropped (same art) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `67` | `pnem` | prerelease (datestamped, same art) | Rathi Assassin |

---

## 7. Edge cases & gotchas

- **Foil commons are pricey** (Daze 30 ~$331 foil); foil common total ~$804 vs nonfoil ~$16.
- MTGJSON: 4 Theme Decks (Breakdown, Eruption, Mercenaries, Replicator) plus an `Enhanced Deck` version of each, Fat Pack.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] nem = []` — configured 2026-11-08 (enables `mm query missing-set nem`).
- `config/families.toml` `[[unobtainable.nem.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.nem]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 (+ Enhanced) | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py nem --list-boosters` (2026-11-06): `draft` EV ~$11.65, `fat-pack` ~$14.61.
