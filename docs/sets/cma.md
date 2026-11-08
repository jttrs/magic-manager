# `cma` — Commander Anthology

> Per-family memory doc. Read this before answering set-specific questions about
> `cma` or working on `cma`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `cma`
**Family root type:** `commander`
**Family released:** 2017-06-09
**Last audit:** 2026-11-05 via `/characterize-set cma` (one-at-a-time run — tier decisions pending owner review).

---

> **A boxed reprint of four earlier Commander decks**, the first Anthology.
> Nothing is new: all 320 prints reuse earlier art. Standalone root. Same
> shape as [`cm2`](cm2.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cma` | commander | 320 | 2017-06-09 | parent — CN 1–320 (basics at the end, e.g. Forests 309–320) |
| `tcma` | token | 20 | 2017-06-09 | tokens + an Experience counter card (CN `0`) |

`set:cma+related` covers both.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`, no `full_art`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face commanders (**foil-only**, mythic) | 4 | `cma` 111 Freyalise, 176 Derevi, 180 Kaalia of the Vast, 186 Meren of Clan Nel Toth | `regular` | mythic-regular — ≈ $19 foil |
| deck cards (nonfoil-only) | 316 | the rest | `regular` | rarity sub-selectors — ≈ $431 nonfoil (Pathbreaker Ibex 132 ~$19, Thousand-Year Elixir 236 ~$16, Ezuri 108 ~$15, Pyrohemia 86 ~$14) |
| tokens | 20 | `tcma` | `regular` | tokens |

Rarity totals (`cma`): 105 C / 108 U / 92 R / 15 M.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] cma = []` to enable `mm query missing-set cma`.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] cma = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Pure reprint set:** every print shares its `illustration_id` with an
  earlier printing.
- **Commanders are spread through the CN range** (alphabetical within
  colour), not grouped at the front as in `cm2`.
- **`tcma` 0 Experience** is a counter card, not a token creature
  (~$4.91).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] cma = []` — configured 2026-11-08 (enables `mm query missing-set cma`).
- `config/families.toml` `[[unobtainable.cma.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.cma]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander Anthology | Commander deck ×4 in one box | Evasive Maneuvers (Derevi), Guided by Nature (Freyalise), Heavenly Inferno (Kaalia), Plunder the Graves (Meren); decks typed `Commander Deck` |

**Booster types (for `sealed-value` EV):** none.
