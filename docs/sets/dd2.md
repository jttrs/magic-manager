# `dd2` — Duel Decks: Jace vs. Chandra

> Per-family memory doc. Read this before answering set-specific questions about
> `dd2` or working on `dd2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `dd2`
**Family root type:** `duel_deck`
**Family released:** 2008-11-07
**Last audit:** 2026-11-05 via `/characterize-set dd2` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Jace Beleren, Chandra Nalaar). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`ddc`](ddc.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dd2` | duel_deck | 64 | 2008-11-07 | parent — Jace deck 1–33 (blue; Islands 30–33), Chandra deck 34–64 (red; Mountains at the end) |
| `tdd2` | token | 1 | 2008-11-07 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list dd2`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `dd2` 1 Jace Beleren (~$3.49, new art), 34 Chandra Nalaar (~$1.12, new art) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 62 | the rest (Counterspell 24 ~$6, Terrain Generator 29 ~$3, Gush 27, Ancestral Vision 21, Daze 23) | `regular` | rarity sub-selectors — ≈ $30 |

**New art (local check):** 45 prints first seen here (Jace 1, Chandra 34, Counterspell 24, Daze 23, Fireball 56, …). Configured `[dupe_foil] dd2 = []` (2026-11-08) to enable
`mm query missing-set dd2`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] dd2 = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Jace` / `Chandra` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.
- **MTGJSON also lists Japanese-language versions** of both decks (`Jace Japanese`, `Chandra Japanese`); Scryfall's `dd2` is English.
- **Reprinted in 2014** as [`jvc`](jvc.md) with the same art.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] dd2 = []` — configured 2026-11-08 (enables `mm query missing-set dd2`).
- `config/families.toml` `[[unobtainable.dd2.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.dd2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Jace vs. Chandra | Duel deck | Jace 1–33, Chandra 34–64 |

**Booster types (for `sealed-value` EV):** none.
