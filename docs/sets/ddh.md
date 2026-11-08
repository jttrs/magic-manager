# `ddh` — Duel Decks: Ajani vs. Nicol Bolas

> Per-family memory doc. Read this before answering set-specific questions about
> `ddh` or working on `ddh`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddh`
**Family root type:** `duel_deck`
**Family released:** 2011-09-02
**Last audit:** 2026-11-05 via `/characterize-set ddh` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Ajani Vengeant, Nicol Bolas, Planeswalker). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`ddi`](ddi.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddh` | duel_deck | 80 | 2011-09-02 | parent — Ajani Goldmane deck 1–41 (R/G/W; basics at the end), Nicol Bolas deck 42–80 (U/B/R; basics at the end) |
| `tddh` | token | 2 | 2011-09-02 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddh`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddh` 1 Ajani Vengeant (~$4.87, new art), 42 Nicol Bolas, Planeswalker (~$2.19, new art) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 78 | the rest (Essence Warden 3 ~$8, Undermine 62 ~$4, Titanic Ultimatum 31 ~$4) | `regular` | rarity sub-selectors — ≈ $39 |

**New art (local check):** Ajani 1, Behemoth Sledge 28, Nicol Bolas 42, Morgue Toad 47, Blazing Specter 52, Agonizing Demise 66. Configured `[dupe_foil] ddh = []` (2026-11-08) to enable
`mm query missing-set ddh`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] ddh = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Ajani Goldmane` / `Nicol Bolas` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ddh = []` — configured 2026-11-08 (enables `mm query missing-set ddh`).
- `config/families.toml` `[[unobtainable.ddh.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddh]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Ajani vs. Nicol Bolas | Duel deck | Ajani Goldmane 1–41, Nicol Bolas 42–80 |

**Booster types (for `sealed-value` EV):** none.
