# `ddn` — Duel Decks: Speed vs. Cunning

> Per-family memory doc. Read this before answering set-specific questions about
> `ddn` or working on `ddn`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddn`
**Family root type:** `duel_deck`
**Family released:** 2014-09-05
**Last audit:** 2026-11-05 via `/characterize-set ddn` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Zurgo Helmsmasher, Arcanis
> the Omnipotent). Standalone root, **no token set**: the Goblin token is
> `ddn` 82. Same shape as [`ddo`](ddo.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddn` | duel_deck | 82 | 2014-09-05 | parent — Speed deck 1–41, Cunning deck 42–81 (Islands 75–77, Mountain 78, Plains 79–81), Goblin token 82 |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddn`.

---

## 2. Treatments

All `regular` except the full-art Goblin token (`fa`).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddn` 1 Zurgo Helmsmasher (~$0.59, new art), 42 Arcanis the Omnipotent (~$0.43) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 79 | the rest (Fury of the Horde 30 ~$6, Goblin Bombardment 24 ~$3, Goblin Warchief 9, Krenko 15) | `regular` | rarity sub-selectors — ≈ $29 |
| token | 1 | `ddn` 82 Goblin (`is_token = 1`, full-art) | `fa` | token — dropped by missing-set |

**New art (local check):** Zurgo 1, Fury of the Horde 30, Swamp 39,
Aquamorph Entity 54, Hold the Line 66. Configured `[dupe_foil] ddn = []` (2026-11-08).

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] ddn = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **The token is in the parent set** (82).
- MTGJSON decks `Speed` / `Cunning` (`type: Duel Deck`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ddn = []` — configured 2026-11-08 (enables `mm query missing-set ddn`).
- `config/families.toml` `[[unobtainable.ddn.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddn]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Speed vs. Cunning | Duel deck | Speed 1–41, Cunning 42–81 |

**Booster types (for `sealed-value` EV):** none.
