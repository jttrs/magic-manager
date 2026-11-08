# `unh` — Unhinged

> Per-family memory doc. Read this before answering set-specific questions about
> `unh` or working on `unh`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `unh`
**Family root type:** `funny`
**Family released:** 2004-11-19
**Last audit:** 2026-11-06 via `/characterize-set unh` (one-at-a-time run — tier decisions pending owner review).

---

> **Second silver-bordered Un-set, pre-mythic.** Full-art basics, a partial
> finish split (27 cards have a foil-only `N★` twin), and a foil-only secret
> rare (Super Secret Tech 141).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `unh` | funny | 168 | 2004-11-19 | parent — 1–140 (full-art basics 136–140) + 141 Super Secret Tech + 27 foil-only `N★` |
| `punh` | promo | 1 | 2004-11-20 | release Ass Whuppin' `117★` (same art, `datestamped`) |

`set:unh+related` covers both. No token set. `funny` isn't a default inventory
set type, but the anchor is always included by `mm set master-list unh`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base, both finishes | 108 | `unh` (41 C / 36 U / 31 R incl. 120 full-art Who // What // When // Where // Why, playtest 17, upside-down 47) | `regular` | rarity/base sub-selectors |
| full-art basics | 5 | `unh` 136–140 (common, `full_art = 1`) | `regular` | basics — ≈ $52 nonfoil / $316 foil |
| nonfoil half of a split | 27 | `unh` `N` (14 C / 4 U / 9 R; City of Ass 134 ~$57) | `regular` | rarity/base sub-selectors |
| **foil-only `N★` half** | 27 | `unh` `N★` (Richard Garfield, Ph.D. `44★` ~$340, Mox Lotus `124★` ~$315, Gleemax `121★` ~$114) | `regular` | same art as `N` for 25 of 27 — a second printing for the foil |
| secret rare | 1 | `unh` 141 Super Secret Tech (foil-only, rare, ~$31) | `regular` | rare-regular |

**`promo_types`:** `playtest` (17 Look at Me, I'm R&D) and `upsidedown` (47
Topsy Turvy) are cosmetic. The `punh` release foil carries `datestamped`, so
`missing.drop_datestamped_with_sibling` drops it (name + treatment match). No
fancy-foil sheet → configured `[dupe_foil] unh = []` (2026-11-08) to enable
`mm query missing-set unh`.

---

## 3. Chase variants

The foil-only `N★` rares: Richard Garfield, Ph.D. (~$340), Mox Lotus (~$315),
Gleemax (~$114).

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] unh = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `N★` foil halves | 27 | **owner's call** — the foil printing of a nonfoil `N`; same finish-split pattern as `9ed`/`10e` |
| `punh` 117★ | 1 | already dropped (datestamped) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `117★` | `punh` | release (same art) | Ass Whuppin' |

---

## 7. Edge cases & gotchas

- **Partial finish split:** only 27 cards have a separate `N★` foil printing;
  the other 113 base cards (incl. basics) are one printing with both finishes. Owning a
  nonfoil `44` still leaves `44★` "missing".
- **Two `N★` rows don't share art id with their `N` twin** in Scryfall's data:
  Aesthetic Consultation `48★` and Cardpecker `4★` (not checked visually).
- **No mythics**: rare-regular is the top sub-selector.
- MTGJSON: no deck lists; booster `draft` only.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] unh = []` — configured 2026-11-08 (enables `mm query missing-set unh`).
- `config/families.toml` `[[unobtainable.unh.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.unh]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | foils at `N★` for 27 cards |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py unh --list-boosters` (2026-11-06): `draft` EV ~$22.47.
