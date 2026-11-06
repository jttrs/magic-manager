# `ddj` — Duel Decks: Izzet vs. Golgari

> Per-family memory doc. Read this before answering set-specific questions about
> `ddj` or working on `ddj`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddj`
**Family root type:** `duel_deck`
**Family released:** 2012-09-07
**Last audit:** 2026-11-05 via `/characterize-set ddj` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Niv-Mizzet, the Firemind, Jarad, Golgari Lich Lord). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`ddk`](ddk.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddj` | duel_deck | 90 | 2012-09-07 | parent — Izzet deck 1–44 (Islands 37–40, Mountains 41–44), Golgari deck 45–90 (Swamps 83–86, Forests 87–90) |
| `tddj` | token | 1 | 2012-09-07 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddj`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddj` 1 Niv-Mizzet, the Firemind (~$1.20, new art), 45 Jarad, Golgari Lich Lord (~$4.14) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 88 | the rest (Isochron Scepter 16 ~$12, Life from the Loam 69 ~$5, Elves of Deep Shadow 47 ~$5) | `regular` | rarity sub-selectors — ≈ $50 |

**New art (local check):** Niv-Mizzet 1, Train of Thought 19, Vacuumelt 24, Overwhelming Intellect 28, Gleancrawler 64, Ghoul's Feast 67, Twilight's Call 76, Life // Death 77. Proposed `[dupe_foil] ddj = []` to enable
`mm query missing-set ddj`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] ddj = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Izzet` / `Golgari` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ddj.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddj]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Izzet vs. Golgari | Duel deck | Izzet 1–44, Golgari 45–90 |

**Booster types (for `sealed-value` EV):** none.
