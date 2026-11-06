# `dst` — Darksteel

> Per-family memory doc. Read this before answering set-specific questions about
> `dst` or working on `dst`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `dst`
**Family root type:** `expansion`
**Family released:** 2004-02-06
**Last audit:** 2026-11-06 via `/characterize-set dst` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Mirrodin set, pre-mythic.** Old border-era rarity: **no mythics** (C/U/R), no basics. The prerelease foil is Shield of Kaldra (Kaldra cycle: Sword `pmrd`, Helm `p5dn`).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dst` | expansion | 165 | 2004-02-06 | parent — booster set 1–165 (no basics) |
| `pdst` | promo | 1 | 2004-02-06 | prerelease Shield of Kaldra `139★` (alt art, `datestamped`, ~$19) |

`set:dst+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 165 | `dst` 1–165, no basic lands (55 C / 55 U / 55 R) | `regular` | rarity/base sub-selectors — R+M ≈ $331 nonfoil / $1267 foil (Sword of Fire and Ice 148 ~$44, Darksteel Forge 110 ~$43 / ~$130 foil, Trinisphere 154 ~$39, Mycosynth Lattice 130 ~$37, Panoptic Mirror 136 ~$26, Arcbound Ravager 100 ~$20) |

**`promo_types`:** the prerelease Shield of Kaldra `139★` (~$19.20) has its own art. It carries `datestamped`, so missing-set drops it (a ~$19 alt-art card hidden). No fancy-foil sheet →
proposed `[dupe_foil] dst = []` to enable `mm query missing-set dst`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] dst = []` | 0 | **apply** — empty, enables missing-set |
| `pdst` promos | 1 | **owner's call** — its own art (~$19) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `139★` | `pdst` | prerelease (alt art) | Shield of Kaldra |

---

## 7. Edge cases & gotchas

- **No basic lands**, **no mythics**, no token set.
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include `fat-pack`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.dst.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.dst]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py dst --list-boosters` (2026-11-06): `draft` EV ~$13.09, `fat-pack` ~$3.56.
