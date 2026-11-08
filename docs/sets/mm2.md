# `mm2` — Modern Masters 2015

> Per-family memory doc. Read this before answering set-specific questions about
> `mm2` or working on `mm2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `mm2`
**Family root type:** `masters`
**Family released:** 2015-05-22
**Last audit:** 2026-11-05 via `/characterize-set mm2` (one-at-a-time run — tier decisions pending owner review).

---

> **Modern-format Masters reprint set** (Mox Opal, the Eldrazi titans). All
> 249 cards are reprints in the base frame, every one in both finishes. No
> promo child, no basics. Same shape as [`mm3`](mm3.md) / [`ema`](ema.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mm2` | masters | 249 | 2015-05-22 | parent — CN 1–249 (lands at the end: bounce lands 237–249, Eye of Ugin 242) |
| `tmm2` | token | 16 | 2015-05-22 | tokens |

`masters` isn't a default inventory set type, but the anchor is always
included by `mm set master-list mm2`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`, no `full_art`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (foil + nonfoil) | 249 | `mm2` 1–249 (101 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $642 nonfoil / $965 foil |
| tokens | 16 | `tmm2` | `regular` | tokens |

Top cards: Mox Opal 223 (~$242), Eye of Ugin 242 (~$50), Kozilek, Butcher of
Truth 5 (~$43), Ulamog, the Infinite Gyre 6 (~$37), Bitterblossom 71 (~$34),
Tezzeret the Seeker 62, Elesh Norn 16, Emrakul, the Aeons Torn 3.

**New art (local check, 16):** Fulminator Mage 193, Hikari 18, Tribal Flames
132, Waxmane Baku 38, Skyreach Manta 229, … (upper bound — the local catalog
undercounts older sets).

Proposed `[dupe_foil] mm2 = []` to enable `mm query missing-set mm2`.

---

## 3–6.

No chase variants, scenes or PRM destinations (no promo child). Unobtainable
rules: none configured yet (proposals pending owner review);
`[dupe_foil] mm2 = []` — **apply**.

---

## 7. Edge cases & gotchas

- **Rarities are re-assigned for the Masters set** (Mox Opal is mythic here).
- No basics; whole family is booster-obtainable.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.mm2.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.mm2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / Booster Box | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mm2 --list-boosters` (2026-11-05): `draft` EV ~$11.83, 99.8% coverage.
