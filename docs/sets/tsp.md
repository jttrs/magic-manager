# `tsp` — Time Spiral

> Per-family memory doc. Read this before answering set-specific questions about
> `tsp` or working on `tsp`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `tsp`
**Family root type:** `expansion`
**Family released:** 2006-10-06
**Last audit:** 2026-11-06 via `/characterize-set tsp` (one-at-a-time run — tier decisions pending owner review).

---

> **Nostalgia block opener, pre-mythic, with a 121-card "timeshifted" bonus sheet (`tsb`).** Old border-era rarity: **no mythics** in `tsp` (C/U/R). `tsb` reprints older cards in the old (pre-8th) frame and is rated `special`, so the rare/mythic sub-selectors never see it.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `tsp` | expansion | 301 | 2006-10-06 | parent — booster set 1–301 (basics 282–301) |
| `ptsp` | promo | 3 | 2006-10-06 | prerelease Lotus Bloom `259★` (alt art, `datestamped`) + release Sudden Shock `179★` (same art) + resale Jaya Ballard `A1` |
| `tsb` | expansion | 121 | 2006-10-06 | **Timeshifted** sheet, 1–121, all rarity `special`, old frame (2 with `tombstone`) |

`set:tsp+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 301 | `tsp` 1–301; basics 282–301 (141 C / 80 U / 80 R) | `regular` | rarity/base sub-selectors — R+M ≈ $267 nonfoil / $1714 foil (Gemstone Caverns 274 ~$64 / ~$332 foil, Reiterate 175 ~$20, Norin the Wary 171 ~$18; common Ophidian Eye 70 ~$15 / ~$186 foil) |
| timeshifted (`tsb`) | 121 | `tsb` 1–121 (rarity `special`) | `regular` | **invisible to rarity sub-selectors** — ≈ $225 nonfoil / $2,153 foil (Darkness 40 ~$24, Claws of Gix 107 ~$217 foil, Akroma, Angel of Wrath 1) |

**`promo_types`:** the prerelease Lotus Bloom `259★` has its own art; the release Sudden Shock `179★` (~$5.84) and resale `A1` reuse the booster art. Only the prerelease carries `datestamped` (dropped by `missing.drop_datestamped_with_sibling`); the same-art release foil has no dupe signal, so missing-set lists it next to `tsp` 179. No fancy-foil sheet →
configured `[dupe_foil] tsp = []` (2026-11-08) to enable `mm query missing-set tsp`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] tsp = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `ptsp` promos | 3 | **owner's call** — 1 of 3 has its own art |
| `tsb` timeshifted | 121 | **keep** — real cards; but rarity `special` means missing-set's rare/mythic sub-selectors skip them (code gap — same as the masterpiece `special` problem) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `259★` | `ptsp` | prerelease (alt art) | Lotus Bloom |
| `179★` | `ptsp` | release (same art) | Sudden Shock |
| `A1` | `ptsp` | resale (same art) | Jaya Ballard, Task Mage |

---

## 7. Edge cases & gotchas

- **`tsb` is rated `special`**: `mm query missing-set tsp` (rare-regular + mythic-regular + treatment-class) never lists a timeshifted card, though they are booster cards (one per pack). Same gap as `mps`/`mp2`.
- **No mythics** in `tsp`.
- 62 of the 121 `tsb` cards have art not used outside the TSP block locally; the rest reuse their original art.
- Commons can be pricey in foil (Ophidian Eye ~$186).
- MTGJSON: Theme Decks and MTGO Redemption lists only (not in `PRECON_MODERN_TYPES`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] tsp = []` — configured 2026-11-08 (enables `mm query missing-set tsp`).
- `config/families.toml` `[[unobtainable.tsp.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.tsp]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft / tournament boosters | booster product | one `tsb` timeshifted card per booster |
| Theme Decks | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py tsp --list-boosters` (2026-11-06): `draft` EV ~$11.97, `tournament` ~$46.13.
