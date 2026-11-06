# `6ed` — Classic Sixth Edition

> Per-family memory doc. Read this before answering set-specific questions about
> `6ed` or working on `6ed`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `6ed`
**Family root type:** `core`
**Family released:** 1999-04-21
**Last audit:** 2026-11-06 via `/characterize-set 6ed` (one-at-a-time run — tier decisions pending owner review).

---

> **Core set, white border, no foils, no mythics.** 20 basics. No promo or token set. One Simplified-Chinese alt-art print (`123s`) is on Scryfall but not local.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `6ed` | core | 350 (351 on Scryfall) | 1999-04-21 | parent — 1–330 + basics 331–350 |

No children. The Scryfall-only row is Drudge Skeletons `123s` (`schinesealtart`, `lang = zhs`), never synced.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 350 | `6ed` 1–350 (110 C / 110 U / 110 R + 20 basics) | `regular` | rarity/base sub-selectors — R ≈ $369 (Vampiric Tutor 161 ~$67, Enlightened Tutor 19 ~$37, Worldly Tutor 269 ~$27, City of Brass 321 ~$26, Birds of Paradise 217 ~$18); U ≈ $162 (Mystical Tutor 83 ~$19) |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] 6ed = []` to enable `mm query missing-set 6ed`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] 6ed = []` | 0 | **apply** — empty, enables missing-set |
| `zhs` alt-art `123s` | 1 (0 local) | **owner's call** — Chinese-only, not syncable |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `123s` | `6ed` | Simplified-Chinese alt art (`schinesealtart`) | Drudge Skeletons |

---

## 7. Edge cases & gotchas

- **No foils** — the last core set before foils ([`7ed`](7ed.md) has them).
- **The four tutors** (Vampiric, Enlightened, Worldly, Mystical) are most of the value.
- MTGJSON: Two Player Starter (decks `Deck A` / `Deck B`, `Starter Deck`), Tournament Pack.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.6ed.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.6ed]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Tournament Pack | starter-size sealed pack | — |
| Two Player Starter | starter set | Deck A / Deck B |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py 6ed --list-boosters` (2026-11-06): `draft` EV ~$10.67, `tournament` ~$47.15.
