# `tmp` — Tempest

> Per-family memory doc. Read this before answering set-specific questions about
> `tmp` or working on `tmp`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `tmp`
**Family root type:** `expansion`
**Family released:** 1997-10-14
**Last audit:** 2026-11-06 via `/characterize-set tmp` (one-at-a-time run — tier decisions pending owner review).

---

> **First Tempest-block set, old border, nonfoil only, no mythics.** 20 basics. Its prerelease Dirtcowl Wurm (`ptmp` 221) is nonfoil, same CN and art as the booster card.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `tmp` | expansion | 350 | 1997-10-14 | parent — booster set 1–330 + basics 331–350 |
| `ptmp` | promo | 1 | 1997-10-14 | prerelease Dirtcowl Wurm `221` — nonfoil, `datestamped`, same art as `tmp` 221, ~$25 |

`set:tmp+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 350 | `tmp` 1–350 (110 C / 110 U / 110 R + 20 basics) | `regular` | rarity/base sub-selectors — R ≈ $1527 (Intuition 70 ~$357, Earthcraft 222 ~$297, Ancient Tomb 315 ~$135, Cursed Scroll 281 ~$92, Aluren 213 ~$89, Eladamri, Lord of Leaves 224 ~$78); U ≈ $283 |
| prerelease | 1 | `ptmp` 221 | `regular` | **same art** — auto-dropped |

**`promo_types`:** `ptmp` 221 carries `prerelease` + `datestamped` and shares art with `tmp` 221, so missing-set drops it correctly. No fancy-foil sheet →
proposed `[dupe_foil] tmp = []` to enable `mm query missing-set tmp`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] tmp = []` | 0 | **apply** — empty, enables missing-set |
| `ptmp` prerelease | 1 | none needed — auto-dropped (same art) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `221` | `ptmp` | prerelease (nonfoil, datestamped, same art) | Dirtcowl Wurm |

---

## 7. Edge cases & gotchas

- **Pre-foil era:** every print is nonfoil.
- MTGJSON: 4 Theme Decks (Deep Freeze, The Flames of Rath, The Slivers, The Swarm) plus an `Advanced Deck` version of each; Tempest Starter Deck (a `starter` booster type in `sealed-value`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.tmp.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.tmp]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Starter Deck | starter deck (`limited_aid_tool` / `starter_deck`) | — |
| Theme Decks ×4 (+ Advanced) | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py tmp --list-boosters` (2026-11-06): `draft` EV ~$30.04, `starter` ~$96.03.
