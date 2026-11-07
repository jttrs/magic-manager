# `dpa` — Duels of the Planeswalkers

> Per-family memory doc. Read this before answering set-specific questions about
> `dpa` or working on `dpa`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `dpa`
**Family root type:** `box`
**Family released:** 2010-06-04
**Last audit:** 2026-11-05 via `/characterize-set dpa` (one-at-a-time run — tier decisions pending owner review).

---

> **Paper versions of the five decks from the *Duels of the Planeswalkers* video game: 113 nonfoil reprints, with one foil rare per deck. Standalone root, no children.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dpa` | box | 113 | 2010-06-04 | parent — CN 1–113 (basics 98–113) |

`box` isn't a default inventory set type, but the anchor is always
included by `mm set master-list dpa`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| deck foils (**foil-only**, rare) | 5 | `dpa` 10 Mahamoti Djinn, 19 Ascendant Evincar, 49 Kamahl, Pit Fighter, 70 Immaculate Magistrate, 87 Verdant Force | `regular` | rare-regular — ≈ $8 foil |
| deck cards (nonfoil-only) | 108 | the rest (55 C / 33 U / 20 R; Coat of Arms 90 ~$25, Elvish Champion 60 ~$19, Vigor 88 ~$17, Furnace of Rath 44, The Rack 95) | `regular` | rarity sub-selectors — ≈ $135 |

**New art (local check):** Counterbore 5, Crowd of Cinders 21, Moonglove Winnower 29, Elvish Warrior 64, Roughshod Mentor 81. Proposed `[dupe_foil] dpa = []` to enable
`mm query missing-set dpa`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] dpa = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **No mythics**; each deck's face card is a foil-only rare.
- MTGJSON decks (`type: Duel Of The Planeswalkers Deck` — not in `PRECON_MODERN_TYPES`): Ears of the Elves, Eyes of Shadow, Hands of Flame, Teeth of the Predator, Thoughts of the Wind.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.dpa.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.dpa]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duels of the Planeswalkers decks ×5 | theme deck (video-game tie-in) | one foil rare each |

**Booster types (for `sealed-value` EV):** none.
