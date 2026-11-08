# `lrw` — Lorwyn

> Per-family memory doc. Read this before answering set-specific questions about
> `lrw` or working on `lrw`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `lrw`
**Family root type:** `expansion`
**Family released:** 2007-10-12
**Last audit:** 2026-11-05 via `/characterize-set lrw` (one-at-a-time run — tier decisions pending owner review).

---

> **Tribal set (kithkin, elves, merfolk, giants…), pre-mythic.** Old border-era rarity: **no mythics** (C/U/R only). Small promo set: an alt-art prerelease foil and a **same-art** release foil.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `lrw` | expansion | 301 | 2007-10-12 | parent — booster set 1–301 (basics 282–301) |
| `plrw` | promo | 3 | 2007-10-12 | prerelease Wren's Run Packmaster `244★` (alt art, `datestamped`) + release Shriekmaw `139★` (same art) + resale Brion Stoutarm `A2` |
| `tlrw` | token | 11 | 2007-10-12 | tokens |

`set:lrw+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 301 | `lrw` 1–301 (141 C / 80 U / 80 R) | `regular` | rarity/base sub-selectors — R+M ≈ $401 nonfoil / $1974 foil (Wort, Boggart Auntie 252 ~$29, Dolmen Gate 256 ~$29, Timber Protector 238 ~$23, Knucklebone Witch 120 ~$21, Vigor 240, Thousand-Year Elixir 263 ~$104 foil) |

**`promo_types`:** the prerelease Packmaster `244★` has its own art; the release Shriekmaw `139★` (~$6.72) and resale `A2` reuse the booster art. Only the prerelease carries `datestamped` (so `missing.drop_datestamped_with_sibling` drops it); the same-art release foil has no dupe signal, so missing-set lists it next to `lrw` 139. No fancy-foil sheet →
configured `[dupe_foil] lrw = []` (2026-11-08) to enable `mm query missing-set lrw`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] lrw = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `plrw` promos | 3 | **owner's call** — 1 of 3 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `244★` | `plrw` | prerelease (alt art) | Wren's Run Packmaster |
| `139★` | `plrw` | release (same art) | Shriekmaw |
| `A2` | `plrw` | resale (same art) | Brion Stoutarm |

---

## 7. Edge cases & gotchas

- **No mythics**: rare-regular is the top sub-selector; the mythic list is empty.
- **Foil premium is extreme** (rares ~$401 nonfoil vs ~$1,974 foil).
- MTGJSON has 5 `Theme Deck` lists (not in `PRECON_MODERN_TYPES`) and a `tournament` booster type (~$67.60).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] lrw = []` — configured 2026-11-08 (enables `mm query missing-set lrw`).
- `config/families.toml` `[[unobtainable.lrw.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.lrw]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / tournament packs | booster product | — |
| Theme Decks ×5 | theme deck | — |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py lrw --list-boosters` (2026-11-05): `draft` EV ~$13.68; `tournament` ~$67.60.
