# `gnt` — Game Night

> Per-family memory doc. Read this before answering set-specific questions about
> `gnt` or working on `gnt`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `gnt`
**Family root type:** `box` (standalone boxed product, `parent_set_code: null`)
**Family released:** 2018-11-16
**Last audit:** 2026-11-05 via `/characterize-set gnt` (one-at-a-time run — tier decisions pending owner review).

---

> **The first Game Night box:** five fixed mono-colour decks. Everything is
> base-frame **nonfoil**, including the five new deck-leader mythics (CN 1–5),
> which exist in no other set. Same shape as [`gn2`](gn2.md) / [`gn3`](gn3.md),
> except that those make their leaders foil-only. Whole set ≈ $58 nonfoil.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `gnt` | box | 68 | 2018-11-16 | parent — new mythics 1–5, deck cards 6–58, basics 59–68 |

No children; the box's tokens have no Scryfall token set. `box` isn't a default
inventory set type, but the anchor is always included by
`mm set master-list gnt`.

---

## 2. Treatments

Survey (`survey_treatment_signature.py GNT`, 68 prints): every print computes
`regular` `[nonfoil]`. No `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| new deck-leader mythics | 5 | `gnt` 1 Militant Angel, 2 Inspired Sphinx, 3 Rot Hulk ~$3, 4 Goblin Goliath, 5 Avatar of Growth ~$25 | `regular` | mythic-regular — the only cards unique to `gnt` |
| deck reprints | 53 | `gnt` 6–58 (10 R / 25 U / 18 C; Zulaport Cutthroat 36 ~$2) | `regular` | rarity sub-selectors |
| basics | 10 | `gnt` 59–68 | `regular` | basics |

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] gnt = []` to enable `mm query missing-set gnt`.

**Full-art convention:** none.

---

## 3. Chase variants

None. Avatar of Growth 5 carries most of the value.

---

## 4. Scenes / posters / panoramas

n/a.

---

## 5. Unobtainable rules

None configured, none needed.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] gnt = []` | 0 | **apply** — empty, enables missing-set (15 R/M ≈ $37) |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **No foils at all.** Unlike `gn2`/`gn3`, the leaders are nonfoil.
- Zahid, Djinn of the Lamp 26 has no local price.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.gnt.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.gnt]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Magic Game Night | box set (MTGJSON `box_set` / `game_night`) | 5 decks, MTGJSON `type: Game Night Deck`: White, Blue, Black, Red, Green |

**Booster types (for `sealed-value` EV):** none.
