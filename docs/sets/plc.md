# `plc` — Planar Chaos

> Per-family memory doc. Read this before answering set-specific questions about
> `plc` or working on `plc`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `plc`
**Family root type:** `expansion`
**Family released:** 2007-02-02
**Last audit:** 2026-11-06 via `/characterize-set plc` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Time Spiral set, pre-mythic, with 45 colorshifted cards.** Old border-era rarity: **no mythics** (C/U/R). The colorshifted cards are booster-set CNs flagged `frame_effects = ["colorshifted"]`, not a separate sheet.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `plc` | expansion | 165 | 2007-02-02 | parent — booster set 1–165 (no basics) |
| `pplc` | promo | 2 | 2007-02-02 | prerelease Oros, the Avenger `161★` (alt art, `datestamped`) + release Hedge Troll `151★` (same art) |

`set:plc+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 165 | `plc` 1–165, no basic lands (60 C / 55 U / 50 R) | `regular` | rarity/base sub-selectors — R+M ≈ $191 nonfoil / $929 foil (Urborg, Tomb of Yawgmoth 165 ~$59 / ~$205 foil, Temporal Extortion 81 ~$31, Damnation 85 ~$22, Retether 13 ~$18) |
| colorshifted | 45 | `plc` (scattered CNs; `frame_effects = ["colorshifted"]`) | `regular` | part of base — `colorshifted` is cosmetic |

**`promo_types`:** the prerelease Oros `161★` has its own art; the release Hedge Troll `151★` (~$0.46) reuses the booster art. Only the prerelease carries `datestamped` (dropped by missing-set); the same-art release foil is listed next to `plc` 151. No fancy-foil sheet →
configured `[dupe_foil] plc = []` (2026-11-08) to enable `mm query missing-set plc`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] plc = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pplc` promos | 2 | **owner's call** — 1 of 2 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `161★` | `pplc` | prerelease (alt art) | Oros, the Avenger |
| `151★` | `pplc` | release (same art) | Hedge Troll |

---

## 7. Edge cases & gotchas

- **No basic lands** and **no mythics**.
- `colorshifted` doesn't change the computed treatment, so colorshifted cards aren't a separate class for missing-set.
- No token set.
- MTGJSON: 3 Theme Decks + MTGO Redemption (not in `PRECON_MODERN_TYPES`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] plc = []` — configured 2026-11-08 (enables `mm query missing-set plc`).
- `config/families.toml` `[[unobtainable.plc.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.plc]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×3 | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py plc --list-boosters` (2026-11-06): `draft` EV ~$13.51.
