# `usg` — Urza's Saga

> Per-family memory doc. Read this before answering set-specific questions about
> `usg` or working on `usg`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `usg`
**Family root type:** `expansion`
**Family released:** 1998-10-12
**Last audit:** 2026-11-06 via `/characterize-set usg` (one-at-a-time run — tier decisions pending owner review).

---

> **First Urza-block set, old border, no mythics, nonfoil only.** 20 basics. Its English prerelease Lightning Dragon (`pusg` 202) is the **only foil Urza's Saga card**, same art and CN as the booster print. Seven Simplified-Chinese alt-art prints (`Ns`) are on Scryfall but not local.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `usg` | expansion | 350 (357 on Scryfall) | 1998-10-12 | parent — booster set 1–330 + basics 331–350 |
| `pusg` | promo | 1 | 1998-10-12 | prerelease Lightning Dragon `202` — foil, `datestamped`, same art as `usg` 202, ~$154 |

`set:usg+related` covers all. The 7 Scryfall-only rows are `schinesealtart` prints (`lang = zhs`): Bog Raiders 119s, Diabolic Servitude 130s, Looming Shade 139s, No Rest for the Wicked 142s, Unworthy Dead 163s, Vampiric Embrace 164s, Fire Ants 187s.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 350 | `usg` 1–350 (110 C / 110 U / 110 R + 20 basics) | `regular` | rarity/base sub-selectors — R ≈ $3668 (Gaea's Cradle 321 ~$1650, Serra's Sanctum 325 ~$522, Yawgmoth's Will 171 ~$239, Gilded Drake 76 ~$215, Tolarian Academy 330 ~$184, Time Spiral 103 ~$96) |
| prerelease foil | 1 | `pusg` 202 Lightning Dragon (~$154) | `regular` | **same art** — dropped by `drop_datestamped_with_sibling` |

**`promo_types`:** `pusg` 202 carries `prerelease` + `datestamped` and shares art with `usg` 202, so missing-set drops it — although it's the set's only foil. No fancy-foil sheet →
configured `[dupe_foil] usg = []` (2026-11-08) to enable `mm query missing-set usg`.

---

## 3–4.

Gaea's Cradle 321 (~$1650) is ~45% of rare value. No scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] usg = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pusg` prerelease foil | 1 | **owner's call** — auto-dropped as a same-art dupe, but it's the only foil of the set (~$154) |
| `zhs` alt-art `Ns` | 7 (0 local) | **owner's call** — Chinese-only, not syncable |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `202` | `pusg` | prerelease (datestamped, same art; the set's only foil) | Lightning Dragon |
| `Ns` | `usg` | Simplified-Chinese alt art (`schinesealtart`) | Vampiric Embrace 164s |

---

## 7. Edge cases & gotchas

- **Nonfoil-only booster set**; foils start with [`ulg`](ulg.md).
- **Reserved List lands** (Gaea's Cradle, Serra's Sanctum, Tolarian Academy) are ~65% of rare value.
- MTGJSON: 4 Theme Decks (Sleeper, Special Delivery, The Plague, Tombstone) plus an `Enhanced Deck` version of each, Tournament Pack.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] usg = []` — configured 2026-11-08 (enables `mm query missing-set usg`).
- `config/families.toml` `[[unobtainable.usg.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.usg]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Tournament Pack | starter-size sealed pack | — |
| Theme Decks ×4 (+ Enhanced) | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py usg --list-boosters` (2026-11-06): `draft` EV ~$41.99, `tournament` ~$159.70.
