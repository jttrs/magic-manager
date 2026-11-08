# `cm2` — Commander Anthology Volume II

> Per-family memory doc. Read this before answering set-specific questions about
> `cm2` or working on `cm2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `cm2`
**Family root type:** `commander`
**Family released:** 2018-06-08
**Last audit:** 2026-11-05 via `/characterize-set cm2` (one-at-a-time run — tier decisions pending owner review).

---

> **A boxed reprint of four earlier Commander decks**, one each from Commander
> 2011, 2014, 2015 and 2016. Nothing is new: all 312 prints reuse art from an
> earlier printing. Standalone root (`parent_set_code: null`).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cm2` | commander | 312 | 2018-06-08 | parent — foil commanders 1–13, deck cards 14–312 |
| `tcm2` | token | 19 | 2018-06-08 | tokens |

`set:cm2+related` covers both.

---

## 2. Treatments

All `regular`. `frame_effects` `legendary` is cosmetic. No `promo_types`, no
`full_art`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| commanders (**foil-only**) | 13 | `cm2` 1–13 (10 mythic, 3 rare) | `regular` | rarity sub-selectors — ≈ $92 foil (Atraxa, Praetors' Voice 10 ~$31, Reyhan 13 ~$19, Kalemne 7 ~$12) |
| deck cards (nonfoil-only) | 299 | `cm2` 14–312 | `regular` | rarity sub-selectors — ≈ $397 nonfoil (Grave Pact 65 ~$39, Goblin Welder 101 ~$23, Urza's Incubator 228 ~$22, Ruby Medallion 212 ~$15) |
| tokens | 19 | `tcm2` | `regular` | tokens |

Rarity totals (`cm2`): 90 C / 92 U / 111 R / 19 M.

**Commanders by deck** (MTGJSON fileNames `<Deck>_CM2`):

| Deck | From | Foil commanders |
|---|---|---|
| Devour for Power | Commander 2011 | The Mimeoplasm 1, Damia 2, Vorosh 3 |
| Built From Scratch | Commander 2014 | Daretti, Scrap Savant 4, Bosh 5, Feldon 6 |
| Wade into Battle | Commander 2015 | Kalemne 7, Anya 8, Gisela 9 |
| Breed Lethality | Commander 2016 | Atraxa 10, Ikra Shidiqi 11, Ishai 12, Reyhan 13 |

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] cm2 = []` to enable `mm query missing-set cm2`.

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
| `[dupe_foil] cm2 = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **Pure reprint set:** every print shares its `illustration_id` with an earlier
  printing. A "missing from `cm2`" list is a list of `cm2` printings, not of
  cards you lack.
- **The commanders are the only foils**, and they are foil-only; every other
  card is nonfoil-only. No oversized commanders are listed for this set.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] cm2 = []` — configured 2026-11-08 (enables `mm query missing-set cm2`).
- `config/families.toml` `[[unobtainable.cm2.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.cm2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander Anthology Volume II | Commander deck ×4 in one box (MTGJSON `box_set` / `commander`, plus four `deck` items) | decks typed `Commander Deck`, so they appear in `mm set precon-list` |

**Booster types (for `sealed-value` EV):** none.
