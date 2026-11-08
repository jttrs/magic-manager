# `scg` — Scourge

> Per-family memory doc. Read this before answering set-specific questions about
> `scg` or working on `scg`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `scg`
**Family root type:** `expansion`
**Family released:** 2003-05-26
**Last audit:** 2026-11-06 via `/characterize-set scg` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Onslaught set, pre-mythic.** Old border-era rarity: **no mythics** (C/U/R). Before 2003-10 the prerelease foil has a **plain CN** (no `★`) and **reuses the booster art**. No basics.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `scg` | expansion | 143 | 2003-05-26 | parent — booster set 1–143 (no basics) |
| `pscg` | promo | 1 | 2003-05-26 | prerelease Soul Collector `74` (same art, `datestamped`) |

`set:scg+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `scg` 1–143, no basic lands (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R+M ≈ $215 nonfoil / $2493 foil (Stifle 52 ~$38 / ~$400 foil, Sliver Overlord 139 ~$37 / ~$250, Decree of Silence 32 ~$21, Decree of Justice 8 ~$19, Goblin Warchief 97 ~$11 / ~$94) |

**`promo_types`:** the prerelease Soul Collector `74` (~$5.85) reuses the booster art, on the same CN as `scg` 74. It carries `datestamped`, so `missing.drop_datestamped_with_sibling` drops it — here it really is a same-art foil. No fancy-foil sheet →
configured `[dupe_foil] scg = []` (2026-11-08) to enable `mm query missing-set scg`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] scg = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pscg` promos | 1 | **owner's call** — same art as the booster card |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `74` | `pscg` | prerelease (same art) | Soul Collector |

---

## 7. Edge cases & gotchas

- **Promo CN equals the booster CN** (`pscg` 74 = `scg` 74); pair CN with set code.
- **No basic lands**, **no mythics**, no token set.
- Uncommons carry a big foil premium (≈ $994 foil).
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include `fat-pack`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] scg = []` — configured 2026-11-08 (enables `mm query missing-set scg`).
- `config/families.toml` `[[unobtainable.scg.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.scg]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py scg --list-boosters` (2026-11-06): `draft` EV ~$16.01, `fat-pack` ~$10.29.
