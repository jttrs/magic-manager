# `gn2` — Game Night 2019

> Per-family memory doc. Read this before answering set-specific questions about
> `gn2` or working on `gn2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `gn2`
**Family root type:** `box` (standalone boxed product, `parent_set_code: null`)
**Family released:** 2019-11-15
**Last audit:** 2026-11-05 via `/characterize-set gn2` (one-at-a-time run — tier decisions pending owner review).

---

> **Boxed multiplayer product, not a booster set.** `gn2` is the contents of one
> sealed SKU, *Magic Game Night 2019*: five fixed decks plus tokens. Everything
> is base-frame nonfoil except the five deck-leader mythics (CN 1–5), which are
> **foil-only** and exist in no other set. Same shape as [`gn3`](gn3.md).
> Whole set ≈ $34 nonfoil + $16 foil.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `gn2` | box | 64 | 2019-11-15 | parent — new mythics 1–5, deck cards 6–54, basics 55–64 |
| `tgn2` | token | 3 | 2019-11-15 | Dragon ×2, Dinosaur; nonfoil, unpriced |

`set:gn2+related` covers both. Earlier/later Game Night products (`gnt` 2018,
`gn3` 2022) are separate standalone roots. `box` isn't a default inventory set
type, but the anchor is always included by `mm set master-list gn2`.

---

## 2. Treatments

Survey (`survey_treatment_signature.py GN2`, 67 prints): every print computes
`regular` (62 nonfoil, 5 foil). `frame_effects`: `legendary` 4, cosmetic. No
`promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| new deck-leader mythics (foil-only) | 5 | `gn2` 1–5 (Highcliff Felidar ~$7, Fiendish Duo ~$5, Earthshaker Giant, Calculating Lich, Sphinx of Enlightenment) | `regular` | mythic-regular — the only cards unique to `gn2` |
| deck reprints (nonfoil) | 49 | `gn2` 6–54 (10 rares; Engulf the Shore ~$4, River's Rebuke ~$3, Dramatic Reversal common ~$5) | `regular` | rarity sub-selectors; every one has an earlier printing |
| basics (two arts per type) | 10 | `gn2` 55–64 | `regular` | basics |
| tokens | 3 | `tgn2` 1–3 | `regular` | tokens, never in missing-set |

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] gn2 = []` to enable `mm query missing-set gn2`.

**Full-art convention:** none.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

n/a.

---

## 5. Unobtainable rules

None configured, none needed.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] gn2 = []` | 0 | **apply** — empty, enables missing-set (15 R/M ≈ $27) |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **Finish splits by band:** 1–5 are foil-only, 6–64 nonfoil-only. A "foil
  Ghalta" from this box doesn't exist.
- **The deck leaders are the only new cards.** 59 of 64 prints reprint cards
  that existed before 2019-11-15, so a missing-set run here is mostly a
  reprint list.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.gn2.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.gn2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Magic Game Night 2019 | box set (MTGJSON `sealedProduct` `box_set` / `game_night`) | 5 decks, MTGJSON `type: Game Night Deck`: Aerial Acrobatics, Draconic Fury, Endless Hordes, Glorious Combat, Massive Might |

**Booster types (for `sealed-value` EV):** none (`sealed_value.py gn2 --list-boosters` → no booster data).
