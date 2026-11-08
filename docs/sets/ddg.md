# `ddg` — Duel Decks: Knights vs. Dragons

> Per-family memory doc. Read this before answering set-specific questions about
> `ddg` or working on `ddg`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddg`
**Family root type:** `duel_deck`
**Family released:** 2011-04-01
**Last audit:** 2026-11-05 via `/characterize-set ddg` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Knight of the Reliquary, Bogardan Hellkite). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`ddh`](ddh.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddg` | duel_deck | 81 | 2011-04-01 | parent — Knights deck 1–46 (G/W; Plains/Forests ~39–46), Dragons deck 47–81 (red; Mountains at the end) |
| `tddg` | token | 1 | 2011-04-01 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddg`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddg` 1 Knight of the Reliquary (~$2.88), 47 Bogardan Hellkite (~$0.93, new art) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 79 | the rest (Seething Song 70 ~$14, Kinsbaile Cavalier 17 ~$11, Knight Exemplar 14 ~$5, Loxodon Warhammer 31) | `regular` | rarity sub-selectors — ≈ $67 |

**New art (local check):** 19 prints incl. Bogardan Hellkite 47, Silver Knight 8, Oblivion Ring 34, Loxodon Warhammer 31 and five basics. Proposed `[dupe_foil] ddg = []` to enable
`mm query missing-set ddg`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] ddg = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Knights` / `Dragons` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ddg.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddg]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Knights vs. Dragons | Duel deck | Knights 1–46, Dragons 47–81 |

**Booster types (for `sealed-value` EV):** none.
