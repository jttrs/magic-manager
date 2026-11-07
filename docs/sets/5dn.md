# `5dn` — Fifth Dawn

> Per-family memory doc. Read this before answering set-specific questions about
> `5dn` or working on `5dn`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `5dn`
**Family root type:** `expansion`
**Family released:** 2004-06-04
**Last audit:** 2026-11-06 via `/characterize-set 5dn` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Mirrodin set, pre-mythic.** Old border-era rarity: **no mythics** (C/U/R), no basics. The prerelease foil is Helm of Kaldra — the third piece of the Kaldra cycle (Sword in `pmrd`, Shield in `pdst`).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `5dn` | expansion | 165 | 2004-06-04 | parent — booster set 1–165 (no basics) |
| `p5dn` | promo | 1 | 2004-06-04 | prerelease Helm of Kaldra `131★` (alt art, `datestamped`) |

`set:5dn+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 165 | `5dn` 1–165, no basic lands (55 C / 55 U / 55 R) | `regular` | rarity/base sub-selectors — R+M ≈ $335 nonfoil / $1394 foil (Mycosynth Golem 137 ~$56, Doubling Cube 116 ~$33, Crucible of Worlds 114 ~$33, Beacon of Immortality 6 ~$18 / ~$102 foil, Vedalken Orrery 163 ~$17) |

**`promo_types`:** the prerelease Helm of Kaldra `131★` (~$5.32) has its own art. It carries `datestamped`, so missing-set drops it. No fancy-foil sheet →
proposed `[dupe_foil] 5dn = []` to enable `mm query missing-set 5dn`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] 5dn = []` | 0 | **apply** — empty, enables missing-set |
| `p5dn` promos | 1 | **owner's call** — its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `131★` | `p5dn` | prerelease (alt art) | Helm of Kaldra |

---

## 7. Edge cases & gotchas

- **No basic lands**, **no mythics**, no token set.
- Uncommons are unusually valuable (≈ $110 nonfoil / $874 foil).
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include `fat-pack`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.5dn.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.5dn]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py 5dn --list-boosters` (2026-11-06): `draft` EV ~$16.23, `fat-pack` ~$4.41.
