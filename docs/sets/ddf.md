# `ddf` — Duel Decks: Elspeth vs. Tezzeret

> Per-family memory doc. Read this before answering set-specific questions about
> `ddf` or working on `ddf`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddf`
**Family root type:** `duel_deck`
**Family released:** 2010-09-03
**Last audit:** 2026-11-05 via `/characterize-set ddf` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Elspeth, Knight-Errant, Tezzeret the Seeker). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`ddg`](ddg.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddf` | duel_deck | 79 | 2010-09-03 | parent — Elspeth deck 1–38 (white; Plains ~35–38), Tezzeret deck 39–79 (blue artifacts; Islands at the end) |
| `tddf` | token | 1 | 2010-09-03 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddf`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddf` 1 Elspeth, Knight-Errant (~$10.64, new art), 39 Tezzeret the Seeker (~$22.66, new art) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 77 | the rest (Energy Chamber 64 ~$7, Thoughtcast 71 ~$4, Foil 70 ~$3, Seat of the Synod 74) | `regular` | rarity sub-selectors — ≈ $43 |

**New art (local check):** Elspeth 1, Mosquito Guard 6, Burrenton Bombardier 11, Crusade 27, Rustic Clachan 34, Tezzeret 39, Energy Chamber 64, Trip Noose 65, Foil 70. Configured `[dupe_foil] ddf = []` (2026-11-08) to enable
`mm query missing-set ddf`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] ddf = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Elspeth` / `Tezzeret` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ddf = []` — configured 2026-11-08 (enables `mm query missing-set ddf`).
- `config/families.toml` `[[unobtainable.ddf.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddf]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Elspeth vs. Tezzeret | Duel deck | Elspeth 1–38, Tezzeret 39–79 |

**Booster types (for `sealed-value` EV):** none.
