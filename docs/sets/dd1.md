# `dd1` — Duel Decks: Elves vs. Goblins

> Per-family memory doc. Read this before answering set-specific questions about
> `dd1` or working on `dd1`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `dd1`
**Family root type:** `duel_deck`
**Family released:** 2007-11-16
**Last audit:** 2026-11-05 via `/characterize-set dd1` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only rares (Ambush Commander, Siege-Gang Commander). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`dd2`](dd2.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dd1` | duel_deck | 62 | 2007-11-16 | parent — Elves deck 1–31 (green; Forests 28–31), Goblins deck 32–62 (red; Mountains at the end) |
| `tdd1` | token | 3 | 2007-11-16 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list dd1`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, rare) | 2 | `dd1` 1 Ambush Commander (~$1.70), 32 Siege-Gang Commander (~$0.79) | `regular` | rare-regular |
| deck cards (nonfoil-only) | 60 | the rest (Wirewood Lodge 26 ~$13, Elvish Promenade 20 ~$10, Elvish Harbinger 4 ~$8, Boggart Shenanigans 54 ~$6) | `regular` | rarity sub-selectors — ≈ $83 |

**New art (local check):** 21 prints first seen here (counting only earlier-or-same-date printings). Configured `[dupe_foil] dd1 = []` (2026-11-08) to enable
`mm query missing-set dd1`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] dd1 = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Elves` / `Goblins` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.
- **The first Duel Deck**; the face cards are rare (pre-mythic).
- **Reprinted in 2014** as [`evg`](evg.md) with the same art.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] dd1 = []` — configured 2026-11-08 (enables `mm query missing-set dd1`).
- `config/families.toml` `[[unobtainable.dd1.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.dd1]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Elves vs. Goblins | Duel deck | Elves 1–31, Goblins 32–62 |

**Booster types (for `sealed-value` EV):** none.
