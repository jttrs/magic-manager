# `md1` — Modern Event Deck 2014

> Per-family memory doc. Read this before answering set-specific questions about
> `md1` or working on `md1`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `md1`
**Family root type:** `box`
**Family released:** 2014-05-30
**Last audit:** 2026-11-05 via `/characterize-set md1` (one-at-a-time run — tier decisions pending owner review).

---

> **A ready-to-play Modern tokens deck** (*March of the Multitudes*): 26
> distinct nonfoil reprints. Standalone root.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `md1` | box | 26 | 2014-05-30 | parent — CN 1–26 (Plains 19, Swamp 20) |
| `tmd1` | token | 4 | 2014-05-30 | tokens |

`box` isn't a default inventory set type, but the anchor is always included by
`mm set master-list md1`.

---

## 2. Treatments

All `regular`, nonfoil-only. No `frame_effects`, no `promo_types` on cards.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| reprints (nonfoil) | 26 | `md1` 1–26 (5 C / 12 U / 7 R / 2 M; Sword of Feast and Famine 10 ~$40, City of Brass 15 ~$18, Elspeth, Knight-Errant 13 ~$9, Relic of Progenitus 21 ~$7) | `regular` | rarity sub-selectors — ≈ $97 |
| tokens | 4 | `tmd1` | `regular` | tokens |

**New art (local check):** City of Brass 15 only. Proposed
`[dupe_foil] md1 = []`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] md1 = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **One card per name:** Scryfall lists 26 distinct cards; the 75-card deck's
  copy counts live only in MTGJSON's `March of the Multitudes` decklist
  (`type: Modern Event Deck` — not in `PRECON_MODERN_TYPES`, so `precon-list`
  shows it only with `--all-physical`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] md1 = []` — configured 2026-11-08 (enables `mm query missing-set md1`).
- `config/families.toml` `[[unobtainable.md1.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.md1]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Modern Event Deck: March of the Multitudes | event deck (MTGJSON `Modern Event Deck`) | 75 cards incl. sideboard |

**Booster types (for `sealed-value` EV):** none.
