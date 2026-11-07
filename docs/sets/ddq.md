# `ddq` — Duel Decks: Blessed vs. Cursed

> Per-family memory doc. Read this before answering set-specific questions about
> `ddq` or working on `ddq`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddq`
**Family root type:** `duel_deck`
**Family released:** 2016-02-26
**Last audit:** 2026-11-05 via `/characterize-set ddq` (one-at-a-time run — tier decisions pending owner review).

---

> **Two Innistrad-themed reprint decks** led by foil-only mythics (Geist of
> Saint Traft, Mindwrack Demon). Standalone root, **no token set**: the four
> tokens are inside `ddq` (CN 77–80). Same shape as [`ddr`](ddr.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddq` | duel_deck | 80 | 2016-02-26 | parent — Blessed deck 1–40 (W/U, basics 36–40), Cursed deck 41–76 (U/B, basics 71–76), tokens 77–80 |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddq`.

---

## 2. Treatments

All `regular` except two full-art tokens (`fa`). No `frame_effects`, no
`promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddq` 1 Geist of Saint Traft (~$0.39), 41 Mindwrack Demon (~$0.34) | `regular` | mythic-regular — both new art |
| deck cards (nonfoil-only) | 74 | `ddq` 2–40, 42–76 (Eerie Interlude 8 ~$7, Gravecrawler 59 ~$2.47) | `regular` | rarity sub-selectors — ≈ $27 nonfoil |
| tokens | 4 | `ddq` 77 Angel, 78 Human, 79 Spirit, 80 Zombie (`is_token = 1`; 78 and 80 full-art) | `regular` / `fa` | tokens — dropped by missing-set |

Rarity totals (cards): 39 C / 25 U / 10 R / 2 M.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] ddq = []` to enable `mm query missing-set ddq`.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ddq = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Tokens live in the parent set** at 77–80 (no `tddq`); the survey's `fa`
  class is the two full-art tokens.
- **Only the two face mythics are foil** (foil-only).
- MTGJSON names the decks `Blessed` and `Cursed` (`type: Duel Deck`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ddq.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddq]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Blessed vs. Cursed | Duel deck (MTGJSON `multiple_decks` / `duel`, plus two `deck` items) | Blessed 1–40, Cursed 41–76 |

**Booster types (for `sealed-value` EV):** none.
