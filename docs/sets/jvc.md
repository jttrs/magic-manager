# `jvc` — Duel Decks Anthology: Jace vs. Chandra

> Per-family memory doc. Read this before answering set-specific questions about
> `jvc` or working on `jvc`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `jvc`
**Family root type:** `duel_deck`
**Family released:** 2014-12-05
**Last audit:** 2026-11-05 via `/characterize-set jvc` (one-at-a-time run — tier decisions pending owner review).

---

> **A 2014 reprint of the 2008 Duel Deck [`dd2`](dd2.md)**, one of four
> decks pairs in the *Duel Decks Anthology* box ([`jvc`](jvc.md),
> [`gvl`](gvl.md), [`evg`](evg.md), [`dvd`](dvd.md)). Every print reuses the
> original's art. Standalone root.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `jvc` | duel_deck | 62 | 2014-12-05 | parent — Jace deck 1–33, Chandra deck 34–62 |
| `tjvc` | token | 1 | 2014-12-05 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list jvc`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `jvc` 1 Jace Beleren, 34 Chandra Nalaar | `regular` | mythic-regular — ~$3.50 foil |
| deck cards (nonfoil-only) | 60 | the rest (Gush 27 ~$3.85, Counterspell 24 ~$3.39, Daze 23) | `regular` | rarity sub-selectors — ≈ $32 |
| tokens | 1 | `tjvc` | `regular` | tokens |

**Art:** 0 new — every print shares its illustration with the original
`dd2` (or an earlier printing).

Proposed `[dupe_foil] jvc = []` to enable `mm query missing-set jvc`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] jvc = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Same cards and art as `dd2`**, different set code and frame year — a
  "missing from `jvc`" list is a list of reprint printings.
- **Only the two face cards are foil** (foil-only), as in the original.
- MTGJSON decks `Jace` / `Chandra` (`type: Duel Deck`); the Anthology box itself
  isn't a separate MTGJSON product — each set lists its two decks.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.jvc.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.jvc]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks Anthology (box of 4 pairs) | Duel deck | Jace 1–33, Chandra 34–62 |

**Booster types (for `sealed-value` EV):** none.
