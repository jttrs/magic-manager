# `pd3` — Premium Deck Series: Graveborn

> Per-family memory doc. Read this before answering set-specific questions about
> `pd3` or working on `pd3`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `pd3`
**Family root type:** `premium_deck`
**Family released:** 2011-11-18
**Last audit:** 2026-11-05 via `/characterize-set pd3` (one-at-a-time run — tier decisions pending owner review).

---

> **An all-foil 60-card reanimator deck** (Reanimate, Entomb, Animate Dead).
> 30 distinct foil-only reprints. Standalone root, no children.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `pd3` | premium_deck | 30 | 2011-11-18 | parent — CN 1–30 (creatures first, Swamps 27–30) |

`premium_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list pd3`.

---

## 2. Treatments

All `regular`, foil-only. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| reprints (foil) | 30 | `pd3` 1–30 (11 C / 11 U / 7 R / 1 M; Reanimate 15 ~$24, Entomb 14 ~$18, Crystal Vein 24 ~$17, Cabal Therapy 12 ~$10, Animate Dead 16 ~$7) | `regular` | rarity sub-selectors — ≈ $105 foil |

**New art (local check):** Entomb 14, Last Rites 21. Proposed
`[dupe_foil] pd3 = []`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] pd3 = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Much of the value is in uncommons** (Reanimate 15 and Animate Dead 16;
  uncommons total ~$67), which missing-set's rare/mythic sub-selectors skip.
- MTGJSON decklist `Graveborn` (`type: Premium Deck` — not in
  `PRECON_MODERN_TYPES`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.pd3.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.pd3]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Premium Deck Series: Graveborn | premium deck (all foil) | 60 cards, 30 distinct |

**Booster types (for `sealed-value` EV):** none.
