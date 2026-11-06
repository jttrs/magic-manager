# `itp` — Introductory Two-Player Set

> Per-family memory doc. Read this before answering set-specific questions about
> `itp` or working on `itp`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `itp`
**Family root type:** `starter`
**Family released:** 1996-12-31
**Last audit:** 2026-11-06 via `/characterize-set itp` (one-at-a-time run — tier decisions pending owner review).

---

> **Two-player beginner box of white-bordered Fourth Edition reprints**, nonfoil only. Standalone root. Only 2 prints have art no other local set has.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `itp` | starter | 67 | 1996-12-31 | parent — cards 1–52 + basics 53–67 |

No children. `starter` isn't a default inventory set type, but the anchor is always included by `mm set master-list itp`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| cards | 52 | `itp` 1–52 (30 C / 16 U / 6 R) | `regular` | rarity sub-selectors — ≈ $105 (Elven Riders 40 ~$15, Dark Ritual 19 ~$13, Wall of Bone 27 ~$12, Jayemdae Tome 51 ~$6) |
| basics | 15 | `itp` 53–67 (~$109, ~$7 each) | `regular` | basics |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] itp = []` to enable `mm query missing-set itp`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] itp = []` | 0 | **apply** — empty, enables missing-set |
| whole family | 67 | **owner's call** — a reprint starter box (new art only on Phantom Monster 11 and Island 56); kept (default) — pending owner review |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Basics are half the value** (15 basics ≈ $109 of ≈ $214).
- Many prints are unpriced.
- MTGJSON: *Introductory Two Player Set* and a *Gift Edition*; decks Kazz's / Zakk's First and Second Deck, typed `Intro Pack`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.itp.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.itp]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Introductory Two Player Set | starter set (`multiple_decks` / `two_player_starter`) | + Gift Edition |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py itp --list-boosters` (2026-11-06): none.
