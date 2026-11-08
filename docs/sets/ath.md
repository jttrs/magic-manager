# `ath` — Anthologies

> Per-family memory doc. Read this before answering set-specific questions about
> `ath` or working on `ath`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ath`
**Family root type:** `box`
**Family released:** 1998-11-01
**Last audit:** 2026-11-06 via `/characterize-set ath` (one-at-a-time run — tier decisions pending owner review).

---

> **Five-year anniversary box (1998): two 40-card reprint decks** (Dark Alliance, Defenders of the Cause), nonfoil only. Standalone root. Several cards come in two arts.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ath` | box | 85 | 1998-11-01 | parent — deck cards 1–77, basics 78–85 |

No children. `box` isn't a default inventory set type, but the anchor is always included by `mm set master-list ath`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| deck cards | 77 | `ath` 1–77 (43 C / 25 U / 9 R) | `regular` | rarity sub-selectors — ≈ $126 total (Strip Mine 77 ~$19, Armageddon 1 ~$13, Goblin Recruiter 38 ~$10, Hypnotic Specter 24 ~$6) |
| basics | 8 | `ath` 78–85 (pairs with different art) | `regular` | basics |

**`promo_types`:** none. No fancy-foil sheet →
configured `[dupe_foil] ath = []` (2026-11-08) to enable `mm query missing-set ath`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ath = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| whole family | 85 | **owner's call** — a reprint box (only Forest 84 has art no other local set has); kept (default) — pending owner review |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Basics come in pairs with different art** (78/79, 80/81, 82/83, 84/85).
- MTGJSON: sealed product *Anthologies* (`multiple_decks` / `other`) and decks `Dark Alliance` / `Defenders of the Cause` (`Theme Deck`, not in `mm set precon-list`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ath = []` — configured 2026-11-08 (enables `mm query missing-set ath`).
- `config/families.toml` `[[unobtainable.ath.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ath]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Anthologies box | box set (`multiple_decks` / `other`) | two 40-card decks |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ath --list-boosters` (2026-11-06): none.
