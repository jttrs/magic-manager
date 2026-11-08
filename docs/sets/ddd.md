# `ddd` — Duel Decks: Garruk vs. Liliana

> Per-family memory doc. Read this before answering set-specific questions about
> `ddd` or working on `ddd`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddd`
**Family root type:** `duel_deck`
**Family released:** 2009-10-30
**Last audit:** 2026-11-05 via `/characterize-set ddd` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Garruk Wildspeaker, Liliana Vess). Standalone root,
> base frame. Same shape as the other Duel Decks (e.g. [`dde`](dde.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddd` | duel_deck | 63 | 2009-10-30 | parent — Garruk deck 1–31 (green; Forests at the end), Liliana deck 32–63 (black; Swamps at the end) |
| `tddd` | token | 3 | 2009-10-30 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddd`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddd` 1 Garruk Wildspeaker (~$11.78), 32 Liliana Vess (~$11.60) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 61 | the rest (Snuff Out 53 ~$10, Faerie Macabre 42 ~$7, Nature's Lore 17 ~$4, Bad Moon 48) | `regular` | rarity sub-selectors — ≈ $43 |

**New art (local check):** none counted — its art is shared with the 2014 reprint [`gvl`](gvl.md), so a local check can't tell which came first. The planeswalker faces were new art here. Configured `[dupe_foil] ddd = []` (2026-11-08) to enable
`mm query missing-set ddd`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] ddd = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **Only the two face cards are foil** (foil-only).
- MTGJSON decks `Garruk` / `Liliana` (`type: Duel Deck`), so they appear in
  `mm set precon-list`.
- **Reprinted in 2014** as [`gvl`](gvl.md) (Duel Decks Anthology) with the same art.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ddd = []` — configured 2026-11-08 (enables `mm query missing-set ddd`).
- `config/families.toml` `[[unobtainable.ddd.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddd]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Garruk vs. Liliana | Duel deck | Garruk 1–31, Liliana 32–63 |

**Booster types (for `sealed-value` EV):** none.
