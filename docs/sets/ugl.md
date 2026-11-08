# `ugl` — Unglued

> Per-family memory doc. Read this before answering set-specific questions about
> `ugl` or working on `ugl`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ugl`
**Family root type:** `funny`
**Family released:** 1998-08-11
**Last audit:** 2026-11-06 via `/characterize-set ugl` (one-at-a-time run — tier decisions pending owner review).

---

> **First Un-set, silver border, nonfoil only.** Five full-art basics, a two-card B.F.M., and a token set.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ugl` | funny | 88 | 1998-08-11 | parent — cards 1–83 + full-art basics 84–88 |
| `tugl` | token | 6 | 1998-08-11 | tokens 89–94 (Pegasus, Soldier, Zombie, Goblin, Sheep, Squirrel) |

`set:ugl+related` covers both. `funny` isn't a default inventory set type, but the anchor is always included by `mm set master-list ugl`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 83 | `ugl` 1–83 (33 C / 22 U / 28 R) | `regular` | rarity sub-selectors — R ≈ $124 (Blacker Lotus 70 ~$25, B.F.M. 28 / 29 ~$18–19 each, Ashnod's Coupon 69 ~$14) |
| full-art basics | 5 | `ugl` 84–88 (`full_art = 1`, ~$7–11 each) | `regular` | basics |
| tokens | 6 | `tugl` | `regular` | tokens |

**`promo_types`:** none. No fancy-foil sheet →
configured `[dupe_foil] ugl = []` (2026-11-08) to enable `mm query missing-set ugl`.

---

## 3–4.

Blacker Lotus 70 (~$25). No scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ugl = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| whole family | 88 | **owner's call** — silver-bordered; kept (default) — pending owner review |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **B.F.M. is two cards** (28 left half, 29 right half), different art, same name — a missing-set list needs both.
- **Full-art basics** carry `full_art = 1` and cost more than most rares.
- **No MTGJSON decks or sealed products** besides boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ugl = []` — configured 2026-11-08 (enables `mm query missing-set ugl`).
- `config/families.toml` `[[unobtainable.ugl.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ugl]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ugl --list-boosters` (2026-11-06): `draft` EV ~$18.82.
