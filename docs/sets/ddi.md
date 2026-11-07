# `ddi` — Duel Decks: Venser vs. Koth

> Per-family memory doc. Read this before answering set-specific questions about
> `ddi` or working on `ddi`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddi`
**Family root type:** `duel_deck`
**Family released:** 2012-03-30
**Last audit:** 2026-11-05 via `/characterize-set ddi` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Venser, the Sojourner, Koth of the Hammer). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`ddj`](ddj.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddi` | duel_deck | 77 | 2012-03-30 | parent — Venser deck 1–43 (W/U; basics at the end), Koth deck 44–77 (mono-red; Mountains at the end) |
| `tddi` | token | 2 | 2012-03-30 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddi`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddi` 1 Venser, the Sojourner (~$4.69, new art), 44 Koth of the Hammer (~$2.04, new art) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 75 | the rest (Sigil of Sleep 25 ~$10, Path to Exile 23 ~$4, Steel of the Godhead 30 ~$3) | `regular` | rarity sub-selectors — ≈ $35 |

**New art (local check):** 13 prints incl. Venser 1, Koth 44, Path to Exile 23, Minamo Sightbender 5, Greater Stone Spirit 61. Proposed `[dupe_foil] ddi = []` to enable
`mm query missing-set ddi`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] ddi = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Venser` / `Koth` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ddi.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddi]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Venser vs. Koth | Duel deck | Venser 1–43, Koth 44–77 |

**Booster types (for `sealed-value` EV):** none.
