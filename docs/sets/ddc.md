# `ddc` — Duel Decks: Divine vs. Demonic

> Per-family memory doc. Read this before answering set-specific questions about
> `ddc` or working on `ddc`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddc`
**Family root type:** `duel_deck`
**Family released:** 2009-04-10
**Last audit:** 2026-11-05 via `/characterize-set ddc` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Akroma, Angel of Wrath, Lord of the Pit). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`ddd`](ddd.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddc` | duel_deck | 62 | 2009-04-10 | parent — Divine deck 1–29 (white; Plains 26–29), Demonic deck 30–62 (black; Swamps at the end) |
| `tddc` | token | 3 | 2009-04-10 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddc`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddc` 1 Akroma, Angel of Wrath (~$4.68), 30 Lord of the Pit (~$0.45, new art) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 60 | the rest (Demonic Tutor 49 ~$83, Dark Ritual 45 ~$5, Reya Dawnbringer 13 ~$3) | `regular` | rarity sub-selectors — ≈ $113 |

**New art (local check):** 26 prints first seen here (Demonic Tutor 49, Kuro 44, Twilight Shepherd 11, …), counting only earlier-or-same-date printings. Proposed `[dupe_foil] ddc = []` to enable
`mm query missing-set ddc`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] ddc = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Divine` / `Demonic` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.
- **Demonic Tutor 49 (~$83, uncommon here)** is ~75% of the value.
- **Reprinted in 2014** as [`dvd`](dvd.md) with the same art.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ddc.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddc]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Divine vs. Demonic | Duel deck | Divine 1–29, Demonic 30–62 |

**Booster types (for `sealed-value` EV):** none.
