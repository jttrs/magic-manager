# `ddo` — Duel Decks: Elspeth vs. Kiora

> Per-family memory doc. Read this before answering set-specific questions about
> `ddo` or working on `ddo`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddo`
**Family root type:** `duel_deck`
**Family released:** 2015-02-27
**Last audit:** 2026-11-05 via `/characterize-set ddo` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only planeswalkers. Standalone root, **no
> token set**: the Soldier and Kraken tokens are `ddo` 66–67. Same shape as
> [`ddp`](ddp.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddo` | duel_deck | 67 | 2015-02-27 | parent — Elspeth deck 1–33, Kiora deck 34–65 (Islands 60–62, Forests 63–65), tokens 66–67 |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddo`.

---

## 2. Treatments

All `regular` except the two full-art tokens (`fa`).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face planeswalkers (**foil-only**, mythic) | 2 | `ddo` 1 Elspeth, Sun's Champion (~$3.79), 34 Kiora, the Crashing Wave (~$1.44, new art) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 63 | the rest (Mother of Runes 20 ~$10, Whelming Wave 44, Kor Skyfisher 16) | `regular` | rarity sub-selectors — ≈ $26 |
| tokens | 2 | `ddo` 66 Soldier, 67 Kraken (`is_token = 1`, full-art) | `fa` | tokens — dropped by missing-set |

**New art (local check):** Kiora 34, Gempalm Avenger 9, Accumulated
Knowledge 35. Proposed `[dupe_foil] ddo = []`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] ddo = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Tokens live in the parent set** (66–67); the survey's `fa` class is them.
- MTGJSON decks `Elspeth` / `Kiora` (`type: Duel Deck`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ddo.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddo]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Elspeth vs. Kiora | Duel deck | Elspeth 1–33, Kiora 34–65 |

**Booster types (for `sealed-value` EV):** none.
