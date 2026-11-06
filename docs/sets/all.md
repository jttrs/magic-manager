# `all` — Alliances

> Per-family memory doc. Read this before answering set-specific questions about
> `all` or working on `all`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `all`
**Family root type:** `expansion`
**Family released:** 1996-06-10
**Last audit:** 2026-11-06 via `/characterize-set all` (one-at-a-time run — tier decisions pending owner review).

---

> **Ice Age-block expansion, old border, nonfoil only, no basics, no promos.** **55 commons come in two arts** (`Na` / `Nb`), so 144 cards are 199 prints.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `all` | expansion | 199 | 1996-06-10 | parent — CN 1–144; 55 commons split into `Na` / `Nb` |

No children.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| single-art cards | 89 | `all` (46 R / 43 U) | `regular` | rarity/base sub-selectors — R ≈ $398 (Lake of the Dead 140 ~$124, Force of Will 28 ~$67, Dystopia 47 ~$45, Phyrexian Devourer 125 ~$31, Thawing Glaciers 144 ~$27, Helm of Obedience 121 ~$27) |
| two-art commons | 110 | `all` `Na` / `Nb` for 55 names (all common) | `regular` | commons — **different art** per letter, both distinct printings; ≈ $30 total |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] all = []` to enable `mm query missing-set all`.

---

## 3–4.

Lake of the Dead 140 (~$124). No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] all = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **`a`/`b` CNs are separate arts**, not finishes or languages — every common appears twice (Arcane Denial 22a / 22b, Soldevi Adnate 60a / 60b, …).
- **No basics, no foils.**
- MTGJSON lists no decks or sealed products besides boosters (`default` booster).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.all.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.all]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py all --list-boosters` (2026-11-06): `default` EV ~$15.37.
