# `dis` — Dissension

> Per-family memory doc. Read this before answering set-specific questions about
> `dis` or working on `dis`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `dis`
**Family root type:** `expansion`
**Family released:** 2006-05-05
**Last audit:** 2026-11-06 via `/characterize-set dis` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Ravnica set (Azorius, Rakdos, Simic), pre-mythic.** Old border-era rarity: **no mythics** (C/U/R), no basics. Shocklands Blood Crypt, Breeding Pool, Hallowed Fountain.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dis` | expansion | 180 | 2006-05-05 | parent — booster set 1–180 (no basics) |
| `pdis` | promo | 2 | 2006-05-05 | prerelease Avatar of Discord `140★` (alt art, `datestamped`) + release Azorius Guildmage `141★` (same art) |

`set:dis+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 180 | `dis` 1–180, no basic lands (60 C / 60 U / 60 R) | `regular` | rarity/base sub-selectors — R+M ≈ $201 nonfoil / $1646 foil (Blood Crypt 171 ~$21 / ~$219 foil, Breeding Pool 172 ~$19 / ~$300, Hallowed Fountain 174 ~$19 / ~$385, Grand Arbiter Augustin IV 112 ~$19) |

**`promo_types`:** the prerelease Avatar of Discord `140★` has its own art; the release Azorius Guildmage `141★` (~$1.90) reuses the booster art. Only the prerelease carries `datestamped` (dropped by missing-set); the same-art release foil is listed next to `dis` 141. No fancy-foil sheet →
configured `[dupe_foil] dis = []` (2026-11-08) to enable `mm query missing-set dis`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] dis = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pdis` promos | 2 | **owner's call** — 1 of 2 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `140★` | `pdis` | prerelease (alt art) | Avatar of Discord |
| `141★` | `pdis` | release (same art) | Azorius Guildmage |

---

## 7. Edge cases & gotchas

- **No basic lands**, **no mythics**, no token set.
- Foil shocklands dominate the foil value (~$900 for three).
- MTGJSON: 3 Theme Decks + MTGO Redemption.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] dis = []` — configured 2026-11-08 (enables `mm query missing-set dis`).
- `config/families.toml` `[[unobtainable.dis.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.dis]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×3 | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py dis --list-boosters` (2026-11-06): `draft` EV ~$8.48.
