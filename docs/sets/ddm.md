# `ddm` — Duel Decks: Jace vs. Vraska

> Per-family memory doc. Read this before answering set-specific questions about
> `ddm` or working on `ddm`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddm`
**Family root type:** `duel_deck`
**Family released:** 2014-03-14
**Last audit:** 2026-11-05 via `/characterize-set ddm` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only planeswalkers (Jace, Architect of
> Thought; Vraska the Unseen). Standalone root. Same shape as
> [`ddn`](ddn.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddm` | duel_deck | 88 | 2014-03-14 | parent — Jace deck 1–41 (Islands 37–41), Vraska deck 42–88 (Swamps 79–83, Forests 84–88) |
| `tddm` | token | 1 | 2014-03-14 | token |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddm`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face planeswalkers (**foil-only**, mythic) | 2 | `ddm` 1 Jace, Architect of Thought (~$0.51), 42 Vraska the Unseen (~$0.76) | `regular` | mythic-regular — both new art |
| deck cards (nonfoil-only) | 86 | the rest (Ohran Viper 57 ~$1.84, Control Magic 30 ~$1.58) | `regular` | rarity sub-selectors — ≈ $23 |

**New art (local check):** Jace 1, Memory Lapse 24, Vraska 42, Putrid Leech
51, Hypnotic Cloud 67. Configured `[dupe_foil] ddm = []` (2026-11-08).

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] ddm = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- MTGJSON decks `Jace` / `Vraska` (`type: Duel Deck`).
- Cheapest Duel Deck in this run (~$24 for everything).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ddm = []` — configured 2026-11-08 (enables `mm query missing-set ddm`).
- `config/families.toml` `[[unobtainable.ddm.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddm]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Jace vs. Vraska | Duel deck | Jace 1–41, Vraska 42–88 |

**Booster types (for `sealed-value` EV):** none.
