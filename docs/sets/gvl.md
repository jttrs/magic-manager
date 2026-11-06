# `gvl` — Duel Decks Anthology: Garruk vs. Liliana

> Per-family memory doc. Read this before answering set-specific questions about
> `gvl` or working on `gvl`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `gvl`
**Family root type:** `duel_deck`
**Family released:** 2014-12-05
**Last audit:** 2026-11-05 via `/characterize-set gvl` (one-at-a-time run — tier decisions pending owner review).

---

> **A 2014 reprint of the 2009 Duel Deck [`ddd`](ddd.md)**, one of four
> decks pairs in the *Duel Decks Anthology* box ([`jvc`](jvc.md),
> [`gvl`](gvl.md), [`evg`](evg.md), [`dvd`](dvd.md)). Every print reuses the
> original's art. Standalone root.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `gvl` | duel_deck | 63 | 2014-12-05 | parent — Garruk deck 1–31, Liliana deck 32–63 |
| `tgvl` | token | 4 | 2014-12-05 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list gvl`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `gvl` 1 Garruk Wildspeaker, 32 Liliana Vess | `regular` | mythic-regular — ~$15 foil |
| deck cards (nonfoil-only) | 61 | the rest (Snuff Out 53 ~$13, Faerie Macabre 42 ~$6, Nature's Lore 17 ~$6) | `regular` | rarity sub-selectors — ≈ $57 |
| tokens | 4 | `tgvl` | `regular` | tokens |

**Art:** 0 new — every print shares its illustration with the original
`ddd` (or an earlier printing).

Proposed `[dupe_foil] gvl = []` to enable `mm query missing-set gvl`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] gvl = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Same cards and art as `ddd`**, different set code and frame year — a
  "missing from `gvl`" list is a list of reprint printings.
- **Only the two face cards are foil** (foil-only), as in the original.
- MTGJSON decks `Garruk` / `Liliana` (`type: Duel Deck`); the Anthology box itself
  isn't a separate MTGJSON product — each set lists its two decks.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.gvl.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.gvl]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks Anthology (box of 4 pairs) | Duel deck | Garruk 1–31, Liliana 32–63 |

**Booster types (for `sealed-value` EV):** none.
