# `ddk` — Duel Decks: Sorin vs. Tibalt

> Per-family memory doc. Read this before answering set-specific questions about
> `ddk` or working on `ddk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddk`
**Family root type:** `duel_deck`
**Family released:** 2013-03-15
**Last audit:** 2026-11-05 via `/characterize-set ddk` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Sorin, Lord of Innistrad, Tibalt, the Fiend-Blooded). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`ddl`](ddl.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddk` | duel_deck | 80 | 2013-03-15 | parent — Sorin deck 1–40 (W/B; Swamps 35–37, Plains 38–40), Tibalt deck 41–80 (B/R; Mountains 75–77, Swamps 78–80) |
| `tddk` | token | 1 | 2013-03-15 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddk`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddk` 1 Sorin, Lord of Innistrad (~$2.04, new art), 41 Tibalt, the Fiend-Blooded (~$0.62) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 78 | the rest (Mesmeric Fiend 7 ~$1, Sulfuric Vortex 68, Corpse Connoisseur 54, Faithless Looting 59) | `regular` | rarity sub-selectors — ≈ $18 |

**New art (local check):** Sorin 1, Revenant Patriarch 16, Decompose 20, Blazing Salvo 58, Browbeat 66, Breaking Point 67, Blightning 69. Proposed `[dupe_foil] ddk = []` to enable
`mm query missing-set ddk`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] ddk = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Sorin` / `Tibalt` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ddk.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddk]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Sorin vs. Tibalt | Duel deck | Sorin 1–40, Tibalt 41–80 |

**Booster types (for `sealed-value` EV):** none.
