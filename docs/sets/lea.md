# `lea` — Limited Edition Alpha

> Per-family memory doc. Read this before answering set-specific questions about
> `lea` or working on `lea`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `lea`
**Family root type:** `core`
**Family released:** 1993-08-05
**Last audit:** 2026-11-06 via `/characterize-set lea` (one-at-a-time run — tier decisions pending owner review).

---

> **The first Magic set, black border, rounder corners, nonfoil only.** 295 prints: 285 cards + 10 basics (2 arts per land). **Volcanic Island and Circle of Protection: Black are missing** (left out of Alpha). 98 prints, incl. all of the Power Nine, are unpriced.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `lea` | core | 295 | 1993-08-05 | parent — 1–285 + basics 286–295 |

No children. CNs are one lower than [`leb`](leb.md) / [`2ed`](2ed.md) from CN 10 on (Circle of Protection: Blue is 10 here, 11 there), because Beta adds Circle of Protection: Black at 10.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| cards | 285 | `lea` 1–285 (74 C / 95 U / 116 R) | `regular` | rarity/base sub-selectors — priced R ≈ $16,452 (Wheel of Fortune 183 ~$3850, Time Vault 274 ~$2950, Sol Ring 269 ~$1540, Nightmare 118 ~$1400, Cyclopean Tomb 240 ~$990, Braingeyser 50 ~$833); U ≈ $14,430; C ≈ $5139 (Lord of Atlantis 62 ~$880) |
| basics | 10 | `lea` 286–295 (2 arts per land) | `regular` | basics |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] lea = []` to enable `mm query missing-set lea`.

---

## 3–4.

The Power Nine (all unpriced here). No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] lea = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **98 of 295 prints are unpriced** — every Power Nine card (Black Lotus 232, Moxen 261–265, Ancestral Recall 47, Time Walk 83, Timetwister 84) among them. Value totals are far below real value.
- **CN offsets vs Beta:** from CN 10 on, a card's Alpha CN is one lower than its Beta CN (Black Lotus 232 vs 233), so never pair a CN with the wrong set code.
- **No foils.** MTGJSON: Alpha Starter Deck (a `starter` booster type in `sealed-value`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.lea.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.lea]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |
| Starter Deck | starter deck | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py lea --list-boosters` (2026-11-06): `default` EV ~$1154.08, `starter` ~$4525.11 (both undercount — key cards unpriced).
