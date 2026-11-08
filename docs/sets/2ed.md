# `2ed` — Unlimited Edition

> Per-family memory doc. Read this before answering set-specific questions about
> `2ed` or working on `2ed`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `2ed`
**Family root type:** `core`
**Family released:** 1993-12-01
**Last audit:** 2026-11-06 via `/characterize-set 2ed` (one-at-a-time run — tier decisions pending owner review).

---

> **Third printing of the original card set, white border, nonfoil only.** 302 prints: 287 cards + 15 basics (3 arts each). Nearly all priced (298 / 302); only Black Lotus, Mox Jet and Mox Sapphire lack a price.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `2ed` | core | 302 | 1993-12-01 | parent — 1–287 + basics 288–302 |

No children.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| cards | 287 | `2ed` 1–287 (75 C / 95 U / 117 R) | `regular` | rarity/base sub-selectors — R ≈ $45,532 (Timetwister 85 ~$6400, Time Walk 84 ~$5720, Ancestral Recall 48 ~$5000, Mox Pearl 264 ~$3513, Mox Emerald 262 ~$3005, Mox Ruby 265 ~$2500, Volcanic Island 287 ~$1400) |
| basics | 15 | `2ed` 288–302 (3 arts per land) | `regular` | basics |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] 2ed = []` to enable `mm query missing-set 2ed`.

---

## 3–4.

The Power Nine (Black Lotus 233, Moxen 262–266, Ancestral Recall 48, Time Walk 84, Timetwister 85). No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] 2ed = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Unpriced power:** Black Lotus 233, Mox Jet 263, Mox Sapphire 266 have no Scryfall price, so value totals undercount by several thousand dollars.
- **Same card list and CNs as [`leb`](leb.md)**; every print shares art with `lea` / `leb` or a later set.
- **No foils.** MTGJSON: Unlimited Starter Deck (a `starter` booster type in `sealed-value`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.2ed.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.2ed]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |
| Starter Deck | starter deck | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py 2ed --list-boosters` (2026-11-06): `default` EV ~$448.40, `starter` ~$1056.64.
