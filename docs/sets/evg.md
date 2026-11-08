# `evg` — Duel Decks Anthology: Elves vs. Goblins

> Per-family memory doc. Read this before answering set-specific questions about
> `evg` or working on `evg`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `evg`
**Family root type:** `duel_deck`
**Family released:** 2014-12-05
**Last audit:** 2026-11-05 via `/characterize-set evg` (one-at-a-time run — tier decisions pending owner review).

---

> **A 2014 reprint of the 2007 Duel Deck [`dd1`](dd1.md)**, one of four
> decks pairs in the *Duel Decks Anthology* box ([`jvc`](jvc.md),
> [`gvl`](gvl.md), [`evg`](evg.md), [`dvd`](dvd.md)). Every print reuses the
> original's art. Standalone root.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `evg` | duel_deck | 62 | 2014-12-05 | parent — Elves deck 1–31, Goblins deck 32–62 |
| `tevg` | token | 3 | 2014-12-05 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list evg`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, rare) | 2 | `evg` 1 Ambush Commander, 32 Siege-Gang Commander | `regular` | rare-regular — ~$1.40 foil |
| deck cards (nonfoil-only) | 60 | the rest (Wirewood Lodge 27 ~$12, Elvish Promenade 20 ~$10, Elvish Harbinger 4 ~$6) | `regular` | rarity sub-selectors — ≈ $77 |
| tokens | 3 | `tevg` | `regular` | tokens |

**Art:** 0 new — every print shares its illustration with the original
`dd1` (or an earlier printing).

Configured `[dupe_foil] evg = []` (2026-11-08) to enable `mm query missing-set evg`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] evg = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **Same cards and art as `dd1`**, different set code and frame year — a
  "missing from `evg`" list is a list of reprint printings.
- **Only the two face cards are foil** (foil-only), as in the original.
- MTGJSON decks `Elves` / `Goblins` (`type: Duel Deck`); the Anthology box itself
  isn't a separate MTGJSON product — each set lists its two decks.
- **The face cards are rare, not mythic** (the original predates mythic rarity).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] evg = []` — configured 2026-11-08 (enables `mm query missing-set evg`).
- `config/families.toml` `[[unobtainable.evg.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.evg]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks Anthology (box of 4 pairs) | Duel deck | Elves 1–31, Goblins 32–62 |

**Booster types (for `sealed-value` EV):** none.
