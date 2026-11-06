# `ons` — Onslaught

> Per-family memory doc. Read this before answering set-specific questions about
> `ons` or working on `ons`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ons`
**Family root type:** `expansion`
**Family released:** 2002-10-07
**Last audit:** 2026-11-06 via `/characterize-set ons` (one-at-a-time run — tier decisions pending owner review).

---

> **First Onslaught set (morph, tribal), pre-mythic, home of the original fetchlands.** Old border-era rarity: **no mythics** (C/U/R). Before 2003-10 the prerelease foil has a **plain CN** (no `★`) and **reuses the booster art**.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ons` | expansion | 350 local (Scryfall 351) | 2002-10-07 | parent — booster set 1–350 (basics 331–350) |
| `pons` | promo | 1 | 2002-10-07 | prerelease Silent Specter `169` (same art, `datestamped`) |

`set:ons+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 350 | `ons` 1–350; basics 331–350 (130 C incl. basics / 110 U / 110 R) | `regular` | rarity/base sub-selectors — R+M ≈ $1132 nonfoil / $10250 foil (Wooded Foothills 330 ~$120 / ~$1,400 foil, Polluted Delta 321 ~$118 / ~$1,350, Flooded Strand 316 ~$116 / ~$1,194, Windswept Heath 328 ~$85, Bloodstained Mire 313 ~$85, Mana Echoes 218 ~$56) |
| nonfoil-only uncommon | 1 | `ons` 200 Embermage Goblin (its foil is a separate own-art variation `200★`, not local) | `regular` | part of base |

**`promo_types`:** the prerelease Silent Specter `169` (~$3.10) reuses the booster art, on the same CN. It carries `datestamped`, so missing-set drops it — a same-art foil. No fancy-foil sheet →
proposed `[dupe_foil] ons = []` to enable `mm query missing-set ons`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ons = []` | 0 | **apply** — empty, enables missing-set |
| `pons` promos | 1 | **owner's call** — same art as the booster card |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `169` | `pons` | prerelease (same art) | Silent Specter |

---

## 7. Edge cases & gotchas

- **A foil Embermage Goblin `200★` with its own art** exists on Scryfall but isn't local. Scryfall's search leaves out `variation` prints, so `mm set sync` never fetches them.
- **The five fetchlands are about half the rare value** (≈ $524 nonfoil / $5,480 foil of $1,132 / $10,250).
- **Embermage Goblin 200 is nonfoil-only locally**: its foil is the variation print `200★` above.
- **Promo CN equals the booster CN.**
- No mythics, no token set.
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include `fat-pack` and `tournament`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ons.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ons]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft / tournament boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ons --list-boosters` (2026-11-06): `draft` EV ~$17.36, `tournament` ~$75.22, `fat-pack` ~$11.41.
