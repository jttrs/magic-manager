# `pd2` — Premium Deck Series: Fire and Lightning

> Per-family memory doc. Read this before answering set-specific questions about
> `pd2` or working on `pd2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `pd2`
**Family root type:** `premium_deck`
**Family released:** 2010-11-19
**Last audit:** 2026-11-05 via `/characterize-set pd2` (one-at-a-time run — tier decisions pending owner review).

---

> **An all-foil 60-card red burn deck — 34 distinct foil reprints (Lightning Bolt, Chain Lightning, Price of Progress).** Standalone root, no children. All foil-only.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `pd2` | premium_deck | 34 | 2010-11-19 | parent — CN 1–34 |

Not a default inventory set type, but the anchor is always included by
`mm set master-list pd2`.

---

## 2. Treatments

All `regular`, foil-only. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| reprints (foil) | 34 | `pd2` 1–34 (13 C / 15 U / 6 R; Price of Progress 18 ~$9, Reverberate 20 ~$4, Chain Lightning 16, Fireblast 26, Lightning Bolt 17; Mountains 31–34) | `regular` | rarity sub-selectors — ≈ $31 foil |

**New art (local check):** Thunderbolt 19 only. Proposed `[dupe_foil] pd2 = []` to enable
`mm query missing-set pd2`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] pd2 = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **No mythics; the priciest cards are uncommons**, which missing-set's rare/mythic sub-selectors skip.
- MTGJSON decklist `Fire and Lightning` (`type: Premium Deck` — not in `PRECON_MODERN_TYPES`).
- Same shape as [`pd3`](pd3.md).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.pd2.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.pd2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Premium Deck Series: Fire and Lightning | premium deck (all foil) | 34 distinct cards |

**Booster types (for `sealed-value` EV):** none.
