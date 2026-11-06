# `mir` — Mirage

> Per-family memory doc. Read this before answering set-specific questions about
> `mir` or working on `mir`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mir`
**Family root type:** `expansion`
**Family released:** 1996-10-08
**Last audit:** 2026-11-06 via `/characterize-set mir` (one-at-a-time run — tier decisions pending owner review).

---

> **First Mirage-block set, old border, nonfoil only, no mythics.** 20 basics. No promo or token set. One German-only print (Ebony Charm `120†`) is on Scryfall but not local.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mir` | expansion | 350 (351 on Scryfall) | 1996-10-08 | parent — booster set 1–330 + basics 331–350 |

No children. The Scryfall-only row is Ebony Charm `120†` (`lang = de`), never synced.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 350 | `mir` 1–350 (110 C / 110 U / 110 R + 20 basics) | `regular` | rarity/base sub-selectors — R ≈ $1566 (Lion's Eye Diamond 307 ~$809, Phyrexian Dreadnought 315 ~$270, Shallow Grave 141 ~$109, Tombstone Stairwell 149 ~$52, Enlightened Tutor 14 ~$38, Worldly Tutor 255 ~$30) |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] mir = []` to enable `mm query missing-set mir`.

---

## 3–4.

Lion's Eye Diamond 307 (~$809) is ~52% of rare value. No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] mir = []` | 0 | **apply** — empty, enables missing-set |
| German-only `120†` | 1 (0 local) | **owner's call** — not syncable |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `120†` | `mir` | German-only variant | Ebony Charm |

---

## 7. Edge cases & gotchas

- **No foils.**
- MTGJSON: decks typed `MTGO Theme Deck` (Burning Sky, Jungle Jam, Night Terrors, Ride Like the Wind); Mirage Starter Deck (a `starter` booster type in `sealed-value`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.mir.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.mir]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Starter Deck | starter deck | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mir --list-boosters` (2026-11-06): `draft` EV ~$20.86, `starter` ~$83.12.
