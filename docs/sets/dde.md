# `dde` — Duel Decks: Phyrexia vs. the Coalition

> Per-family memory doc. Read this before answering set-specific questions about
> `dde` or working on `dde`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `dde`
**Family root type:** `duel_deck`
**Family released:** 2010-03-19
**Last audit:** 2026-11-05 via `/characterize-set dde` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Phyrexian Negator, Urza's Rage). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`ddf`](ddf.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dde` | duel_deck | 71 | 2010-03-19 | parent — Phyrexia deck 1–35 (black; Swamps 32–35), The Coalition deck 36–71 (five-colour; basics at the end) |
| `tdde` | token | 3 | 2010-03-19 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list dde`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `dde` 1 Phyrexian Negator (~$12.38, new art), 36 Urza's Rage (~$0.48) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 69 | the rest (Phyrexian Arena 27 ~$6, Lightning Greaves 19 ~$6, Carrion Feeder 2 ~$5, Voltaic Key 17, Dark Ritual 18) | `regular` | rarity sub-selectors — ≈ $55 |

**New art (local check):** 28 prints (Phyrexian Negator 1, Phyrexian Totem 20, Darigaaz 47, Treva 49, the three Charms 59–61, …). Proposed `[dupe_foil] dde = []` to enable
`mm query missing-set dde`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] dde = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Phyrexia` / `The Coalition` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.
- **The Coalition's face card is a spell, Urza's Rage 36**, not a creature or planeswalker.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.dde.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.dde]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Phyrexia vs. the Coalition | Duel deck | Phyrexia 1–35, The Coalition 36–71 |

**Booster types (for `sealed-value` EV):** none.
