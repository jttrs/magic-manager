# `dds` — Duel Decks: Mind vs. Might

> Per-family memory doc. Read this before answering set-specific questions about
> `dds` or working on `dds`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `dds`
**Family root type:** `duel_deck`
**Family released:** 2017-03-31
**Last audit:** 2026-11-05 via `/characterize-set dds` (one-at-a-time run — tier decisions pending owner review).

---

> **Two 60-card reprint decks**, each led by a foil-only mythic (Jhoira of the
> Ghitu, Lovisa Coldeyes). Standalone root. Base frame only. Same shape as
> [`ddt`](ddt.md) / [`ddu`](ddu.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dds` | duel_deck | 65 | 2017-03-31 | parent — Mind deck 1–33 (blue-red, Mountains 31–33), Might deck 34–65 (red-green) |
| `tdds` | token | 7 | 2017-03-31 | tokens |

`set:dds+related` covers both. `duel_deck` isn't a default inventory set type,
but the anchor is always included by `mm set master-list dds`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types` on the cards.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `dds` 1 Jhoira of the Ghitu (~$0.81), 34 Lovisa Coldeyes (~$1.55) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 63 | `dds` 2–33, 35–65 (Coat of Arms 58 ~$19, Zo-Zu the Punisher 41 ~$9, Desperate Ritual 14 ~$6) | `regular` | rarity sub-selectors — ≈ $57 nonfoil |
| tokens | 7 | `tdds` | `regular` | tokens |

Rarity totals (`dds`): 32 C / 12 U / 19 R / 2 M.

**New art (local check, 8):** Beacon of Tomorrows 2, Peer Through Depths 5,
Reach Through Mists 7, Sift Through Sands 9, Mountain 31, Lovisa Coldeyes 34,
Zo-Zu the Punisher 41, Cloudcrown Oak 45.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] dds = []` to enable `mm query missing-set dds`.

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
| `[dupe_foil] dds = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Only the two face mythics are foil** (foil-only).
- MTGJSON names the decks `Mind` and `Might` (`type: Duel Deck`), so they
  appear in `mm set precon-list`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.dds.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.dds]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Mind vs. Might | Duel deck (MTGJSON `multiple_decks` / `duel`, plus two `deck` items) | Mind 1–33, Might 34–65 |

**Booster types (for `sealed-value` EV):** none.
