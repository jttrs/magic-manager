# `mma` — Modern Masters

> Per-family memory doc. Read this before answering set-specific questions about
> `mma` or working on `mma`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `mma`
**Family root type:** `masters`
**Family released:** 2013-06-07
**Last audit:** 2026-11-05 via `/characterize-set mma` (one-at-a-time run — tier decisions pending owner review).

---

> **The first Masters set** (229 cards, smaller than later Masters): Modern
> reprints in the base frame, every card in both finishes. No promo child, no
> basics. Same shape as [`mm2`](mm2.md) / [`mm3`](mm3.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mma` | masters | 229 | 2013-06-07 | parent — CN 1–229 (lands at the end: Academy Ruins 219, City of Brass 221, Vivid lands 225–229) |
| `tmma` | token | 16 | 2013-06-07 | tokens |

`masters` isn't a default inventory set type, but the anchor is always
included by `mm set master-list mma`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`, no `full_art`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (foil + nonfoil) | 229 | `mma` 1–229 (101 C / 60 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $438 nonfoil / $1,138 foil |
| tokens | 16 | `tmma` | `regular` | tokens |

Top cards: Sword of Fire and Ice 216 (~$49), Doubling Season 141 (~$34),
Kokusho 89 (~$28), Arcbound Ravager 198, Pact of Negation 56 (~$19 / $65),
City of Brass 221 (~$18 / **$90** foil), Grand Arbiter Augustin IV 176,
Chalice of the Void 203.

**New art (local check):** 45 prints (Vendilion Clique 70, Arcbound Ravager
198, Tooth and Nail 170, Vedalken Shackles 218, Yosei 35, …) — upper bound.
Configured `[dupe_foil] mma = []` (2026-11-08).

---

## 3–6.

No chase variants, scenes or PRM destinations (no promo child). Unobtainable
rules: no rule is active;
`[dupe_foil] mma = []` — **applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **Only 60 uncommons** (later Masters sets have 80), so rarity totals differ
  from the 101/80/53/15 pattern.
- **Foil premium is high** (City of Brass ~5×, Pact of Negation ~3.5×).
- No basics; whole family is booster-obtainable.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] mma = []` — configured 2026-11-08 (enables `mm query missing-set mma`).
- `config/families.toml` `[[unobtainable.mma.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.mma]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / Booster Box | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mma --list-boosters` (2026-11-05): `draft` EV ~$15.25, 99.7% coverage.
