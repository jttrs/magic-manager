# `btd` — Beatdown Box Set

> Per-family memory doc. Read this before answering set-specific questions about
> `btd` or working on `btd`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `btd`
**Family root type:** `box`
**Family released:** 2000-10-01
**Last audit:** 2026-11-06 via `/characterize-set btd` (one-at-a-time run — tier decisions pending owner review).

---

> **Two 45-card reprint decks (Aerodoom, Ground Pounder)** in a box with two foil-only uncommons. Standalone root, no tokens, no promos.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `btd` | box | 90 | 2000-10-01 | parent — 90 prints incl. 12 basics 79–90 |

No children. `box` isn't a default inventory set type, but the anchor is always included by `mm set master-list btd`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| deck cards (nonfoil-only) | 88 | `btd` 1–90 minus 29/54 (66 C / 12 U / 10 R) | `regular` | rarity sub-selectors — ≈ $85 nonfoil (Dark Ritual 21 ~$13, Dwarven Ruins 71 ~$11, Power Sink 14 ~$5, Counterspell 6 ~$5; rares ≈ $9 — Ball Lightning 35, Shivan Dragon 44) |
| foil-only uncommons | 2 | `btd` 29 Sengir Vampire (~$1.70), 54 Erhnam Djinn (~$0.97) | `regular` | uncommon |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] btd = []` to enable `mm query missing-set btd`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] btd = []` | 0 | **apply** — empty, enables missing-set |
| whole family | 90 | **owner's call** — a reprint box (30 prints whose art no other local set has); kept (default) — pending owner review |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **The two foils are the box's premium cards** and are foil-only; every other print is nonfoil-only.
- MTGJSON: sealed product *Beatdown* (`multiple_decks` / `other`) and decks `Aerodoom` / `Ground Pounder` typed `Theme Deck` (not in `mm set precon-list`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.btd.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.btd]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Beatdown box | box set (`multiple_decks` / `other`) | Aerodoom + Ground Pounder |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py btd --list-boosters` (2026-11-06): none.
