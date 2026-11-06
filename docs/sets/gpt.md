# `gpt` — Guildpact

> Per-family memory doc. Read this before answering set-specific questions about
> `gpt` or working on `gpt`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `gpt`
**Family root type:** `expansion`
**Family released:** 2006-02-03
**Last audit:** 2026-11-06 via `/characterize-set gpt` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Ravnica set (Gruul, Izzet, Orzhov), pre-mythic.** Old border-era rarity: **no mythics** (C/U/R), no basics. Shocklands Steam Vents, Godless Shrine, Stomping Ground.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `gpt` | expansion | 165 | 2006-02-03 | parent — booster set 1–165 (no basics) |
| `pgpt` | promo | 2 | 2006-02-03 | prerelease Djinn Illuminatus `142★` (alt art, `datestamped`) + release Gruul Guildmage `144★` (same art) |

`set:gpt+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 165 | `gpt` 1–165, no basic lands (55 C / 55 U / 55 R) | `regular` | rarity/base sub-selectors — R+M ≈ $132 nonfoil / $851 foil (Steam Vents 164 ~$26 / ~$161 foil, Godless Shrine 157 ~$16, Stomping Ground 165 ~$13, Spelltithe Enforcer 18 ~$11) |

**`promo_types`:** the prerelease Djinn Illuminatus `142★` has its own art; the release Gruul Guildmage `144★` (~$0.50) reuses the booster art. Only the prerelease carries `datestamped` (dropped by missing-set); the same-art release foil is listed next to `gpt` 144. No fancy-foil sheet →
proposed `[dupe_foil] gpt = []` to enable `mm query missing-set gpt`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] gpt = []` | 0 | **apply** — empty, enables missing-set |
| `pgpt` promos | 2 | **owner's call** — 1 of 2 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `142★` | `pgpt` | prerelease (alt art) | Djinn Illuminatus |
| `144★` | `pgpt` | release (same art) | Gruul Guildmage |

---

## 7. Edge cases & gotchas

- **No basic lands**, **no mythics**, no token set.
- Scryfall's set count is 167; 165 prints are local.
- MTGJSON: 3 Theme Decks + MTGO Redemption.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.gpt.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.gpt]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×3 | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py gpt --list-boosters` (2026-11-06): `draft` EV ~$5.76.
