# `leb` — Limited Edition Beta

> Per-family memory doc. Read this before answering set-specific questions about
> `leb` or working on `leb`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `leb`
**Family root type:** `core`
**Family released:** 1993-10-04
**Last audit:** 2026-11-06 via `/characterize-set leb` (one-at-a-time run — tier decisions pending owner review).

---

> **Second printing of the original card set, black border, nonfoil only.** 302 prints: Alpha's 295 plus Volcanic Island and Circle of Protection: Black, and a third art for each basic. **Pricing is sparse at the top:** 55 prints, incl. 7 of the Power Nine, have no price.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `leb` | core | 302 | 1993-10-04 | parent — 1–287 + basics 288–302 |

No children.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| cards | 287 | `leb` 1–287 (75 C / 95 U / 117 R) | `regular` | rarity/base sub-selectors — R ≈ $32,958 priced (Mox Ruby 265 ~$6400, Mox Jet 263 ~$4000, Badlands 278 ~$2500, Scrubland 282 ~$2100, Taiga 283 ~$1990, Mind Twist 116 ~$1200, Birds of Paradise 187 ~$1000) |
| basics | 15 | `leb` 288–302 (3 arts per land) | `regular` | basics |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] leb = []` to enable `mm query missing-set leb`.

---

## 3–4.

The Power Nine — only Mox Ruby and Mox Jet are priced locally. No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] leb = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **55 of 302 prints are unpriced**, including Black Lotus 233, Ancestral Recall 48, Time Walk 84, Timetwister 85, Mox Pearl / Emerald / Sapphire, Bayou 279, Balance 3, Chaos Orb 236, Fastbond 193. Value reports undercount heavily.
- **Every print shares art with `lea` or `2ed`** (no art unique to Beta).
- **No foils.** MTGJSON: Beta Starter Deck (a `starter` booster type in `sealed-value`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.leb.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.leb]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |
| Starter Deck | starter deck | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py leb --list-boosters` (2026-11-06): `default` EV ~$816.88, `starter` ~$2825.14 (both undercount — key cards unpriced).
