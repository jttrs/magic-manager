# `rqs` — Rivals Quick Start Set

> Per-family memory doc. Read this before answering set-specific questions about
> `rqs` or working on `rqs`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `rqs`
**Family root type:** `box`
**Family released:** 1996-07-01
**Last audit:** 2026-11-06 via `/characterize-set rqs` (one-at-a-time run — tier decisions pending owner review).

---

> **Two-player beginner box of white-bordered Fourth Edition reprints**, nonfoil, **entirely unpriced** on Scryfall. Standalone root. No new art.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `rqs` | box | 65 | 1996-07-01 | parent — cards 1–51 + basics 52–65 |

No children. `box` isn't a default inventory set type, but the anchor is always included by `mm set master-list rqs`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| cards | 51 | `rqs` 1–51 (30 C / 15 U / 6 R) | `regular` | rarity sub-selectors — no prices |
| basics | 14 | `rqs` 52–65 | `regular` | basics |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] rqs = []` to enable `mm query missing-set rqs`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] rqs = []` | 0 | **apply** — empty, enables missing-set |
| whole family | 65 | **owner's call** — reprints with no new art and no prices; likely exclude — pending owner review |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Same decks as [`itp`](itp.md)** (Kazz's / Zakk's First and Second Deck, MTGJSON `Intro Pack`), sold earlier under the Rivals name.
- **No prices at all**, so value reports show $0.
- MTGJSON: sealed *Rivals Quick Start Set* (`box_set` / `other`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.rqs.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.rqs]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Rivals Quick Start Set | box set (`box_set` / `other`) | same decks as `itp` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py rqs --list-boosters` (2026-11-06): none.
