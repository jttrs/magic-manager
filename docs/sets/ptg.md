# `ptg` — Ponies: The Galloping

> Per-family memory doc. Read this before answering set-specific questions about
> `ptg` or working on `ptg`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ptg`
**Family root type:** `funny` (silver-bordered, not tournament-legal)
**Family released:** 2019-10-22
**Last audit:** 2026-11-05 via `/characterize-set ptg` (one-at-a-time run — tier decisions pending owner review).

---

> **Three My Little Pony crossover cards sold as one convention-exclusive
> 3-card box** (MTGJSON sealed product *Ponies The Galloping*, `box_set` /
> `convention_exclusive`), not a retail set. Silver-bordered,
> foil-only, mythic, each a card that exists nowhere else. Small but pricey:
> ≈ $417 foil for all three. Standalone (`parent_set_code: null`); same
> "special one-offs" shape as the Heroes of the Realm sets ([`ph19`](ph19.md)).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ptg` | funny | 3 | 2019-10-22 | parent — the only set, CN 1–3 |

No children, no tokens.

---

## 2. Treatments

Survey (`survey_treatment_signature.py PTG`, 3 prints): all `regular` `[foil]`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| pony legends (foil-only, silver border) | 3 | `ptg` 1 Nightmare Moon // Princess Luna (~$91, transforming DFC), 2 Princess Twilight Sparkle (~$217), 3 Rarity (~$109) | `regular` | mythic-regular |

`frame_effects`: `legendary` on all three; `waxingandwaningmoondfc` on CN 1
(DFC marker, cosmetic). No `promo_types`.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] ptg = []` to enable `mm query missing-set ptg`.

---

## 3. Chase variants

None — every card is a single printing.

---

## 4. Scenes / posters / panoramas

n/a.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ptg = []` | 0 | **apply** — empty, enables missing-set |
| whole family | 3 | **owner's call** — silver-bordered collectibles, ≈ $417; track only if collecting Un/crossover one-offs |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Foil-only.** A nonfoil copy doesn't exist; a nonfoil buy line would be wrong.
- **Sold together.** The three cards are one sealed product, so the box and
  the cards price separately (TCGplayer product 200379); a complete set of
  singles is the same three cards.
- CN 1 is a transforming DFC: search by the front name `Nightmare Moon`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ptg.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ptg]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Ponies The Galloping | box set (MTGJSON `box_set` / `convention_exclusive`) | 3 cards; MTGJSON deck *Ponies: The Galloping* (`set: ptg`) |

**Booster types (for `sealed-value` EV):** none.
