# `ddr` — Duel Decks: Nissa vs. Ob Nixilis

> Per-family memory doc. Read this before answering set-specific questions about
> `ddr` or working on `ddr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddr`
**Family root type:** `duel_deck`
**Family released:** 2016-09-02
**Last audit:** 2026-11-05 via `/characterize-set ddr` (one-at-a-time run — tier decisions pending owner review).

---

> **Two 60-card reprint decks** led by foil-only planeswalkers. Standalone
> root, **no token set**: the six tokens/emblem are inside `ddr` itself
> (CN 71–76). Same shape as [`dds`](dds.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddr` | duel_deck | 76 | 2016-09-02 | parent — Nissa deck 1–35 (Forests 31–35), Ob Nixilis deck 36–70 (Swamps 66–70), tokens 71–76 |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddr`.

---

## 2. Treatments

All `regular` except three full-art tokens (`fa`). No `frame_effects`, no
`promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face planeswalkers (**foil-only**, mythic) | 2 | `ddr` 1 Nissa, Voice of Zendikar (~$3.17), 36 Ob Nixilis Reignited (~$0.55) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 68 | `ddr` 2–35, 37–70 (Crop Rotation 7 ~$3.64, Khalni Garden 28 ~$2.32) | `regular` | rarity sub-selectors — ≈ $22 nonfoil |
| tokens + emblem | 6 | `ddr` 71–76 (`is_token = 1`; Zombie Giant 73, Elemental 74, Plant 75 full-art; Ob Nixilis Reignited Emblem 76 ~$2.54) | `regular` / `fa` | tokens — dropped by missing-set |

Rarity totals (cards): 42 C / 16 U / 10 R / 2 M.

**New art (local check):** Nissa 1, Ob Nixilis 36, Gaea's Blessing 10,
Gilt-Leaf Seer 11, Thicket Elemental 21, Doom Blade 47 (+ the emblem).

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] ddr = []` to enable `mm query missing-set ddr`.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ddr = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Tokens live in the parent set** at 71–76 (no `tddr`), so `set:ddr`
  includes them unless tokens are filtered; the survey's `fa` class is the
  three full-art tokens, not cards.
- **Only the two walkers are foil** (foil-only).
- MTGJSON names the decks `Nissa` and `Ob Nixilis` (`type: Duel Deck`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ddr = []` — configured 2026-11-08 (enables `mm query missing-set ddr`).
- `config/families.toml` `[[unobtainable.ddr.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddr]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Nissa vs. Ob Nixilis | Duel deck (MTGJSON `multiple_decks` / `duel`, plus two `deck` items) | Nissa 1–35, Ob Nixilis 36–70 |

**Booster types (for `sealed-value` EV):** none.
