# `rav` — Ravnica: City of Guilds

> Per-family memory doc. Read this before answering set-specific questions about
> `rav` or working on `rav`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `rav`
**Family root type:** `expansion`
**Family released:** 2005-10-07
**Last audit:** 2026-11-06 via `/characterize-set rav` (one-at-a-time run — tier decisions pending owner review).

---

> **First Ravnica set (Boros, Dimir, Golgari, Selesnya), pre-mythic.** Old border-era rarity: **no mythics** (C/U/R). Shocklands Sacred Foundry, Watery Grave, Overgrown Tomb, Temple Garden; common bouncelands.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `rav` | expansion | 306 | 2005-10-07 | parent — booster set 1–306 (basics 287–306) |
| `prav` | promo | 2 | 2005-10-07 | prerelease Gleancrawler `247★` (alt art, `datestamped`) + release Dimir Guildmage `245★` (same art) |

`set:rav+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 306 | `rav` 1–306; basics 287–306 (110 C + 20 basics / 88 U / 88 R) | `regular` | rarity/base sub-selectors — R+M ≈ $287 nonfoil / $1676 foil (Doubling Season 158 ~$42 / ~$133 foil, Breath of Fury 116 ~$18, Watery Grave 286 ~$16 / ~$162, Sacred Foundry 280 ~$16, Cloudstone Curio 257 ~$16, Birds of Paradise 153 ~$14) |

**`promo_types`:** the prerelease Gleancrawler `247★` has its own art; the release Dimir Guildmage `245★` (~$1.07) reuses the booster art. Only the prerelease carries `datestamped` (dropped by missing-set); the same-art release foil is listed next to `rav` 245. No fancy-foil sheet →
configured `[dupe_foil] rav = []` (2026-11-08) to enable `mm query missing-set rav`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] rav = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `prav` promos | 2 | **owner's call** — 1 of 2 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `247★` | `prav` | prerelease (alt art) | Gleancrawler |
| `245★` | `prav` | release (same art) | Dimir Guildmage |

---

## 7. Edge cases & gotchas

- **No mythics**, no token set.
- MTGJSON: 4 Theme Decks, a Bundle Land Pack, MTGO Redemption.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] rav = []` — configured 2026-11-08 (enables `mm query missing-set rav`).
- `config/families.toml` `[[unobtainable.rav.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.rav]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft / tournament boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py rav --list-boosters` (2026-11-06): `draft` EV ~$8.53, `tournament` ~$32.63.
