# `sum` — Summer Magic / Edgar

> Per-family memory doc. Read this before answering set-specific questions about
> `sum` or working on `sum`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `sum`
**Family root type:** `core`
**Family released:** 1994-06-21
**Last audit:** 2026-11-06 via `/characterize-set sum` (one-at-a-time run — tier decisions pending owner review).

---

> **A recalled 1994 printing of Revised** (the "Edgar" run), white border, nonfoil only. 306 prints, but **only 30 are priced** and those prices are sparse and erratic (Plains / Swamp / Mountain at ~$450). No children.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `sum` | core | 306 | 1994-06-21 | parent — 1–291 + basics 292–306 |

No children. `core` sets are inventory set types, so `mm set master-list sum` lists all 306.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| cards | 291 | `sum` 1–291 (75 C / 95 U / 121 R) | `regular` | rarity sub-selectors — priced prints are mostly uncommons (Ornithopter 270 ~$500, Thicket Basilisk 218 ~$500, Desert Twister 192 ~$450, Library of Leng 261 ~$400); **3 of 121 rares have a price** (≈ $2) |
| basics | 15 | `sum` 292–306 (Plains 293, Swamp 299, Mountain 301 ~$450 each) | `regular` | basics |

**`promo_types`:** none. No fancy-foil sheet →
configured `[dupe_foil] sum = []` (2026-11-08) to enable `mm query missing-set sum`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] sum = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| whole family | 306 | **owner's call** — a recalled print run collected as a rarity; prices unreliable; kept (default) — pending owner review |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Prices are unreliable**: 276 of 306 prints have no price, and the rest are thin-market listings. Value reports for this set mean little.
- **Same card list as [`3ed`](3ed.md)** (Revised) — 296 names, 306 prints; every print shares art with another local set.
- MTGJSON lists no decks or sealed products; `sealed-value` shows a `default` booster (EV ~$613, from those sparse prices).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] sum = []` — configured 2026-11-08 (enables `mm query missing-set sum`).
- `config/families.toml` `[[unobtainable.sum.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.sum]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py sum --list-boosters` (2026-11-06): `default` EV ~$613.42 (unreliable — few priced cards).
