# `mor` — Morningtide

> Per-family memory doc. Read this before answering set-specific questions about
> `mor` or working on `mor`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mor`
**Family root type:** `expansion`
**Family released:** 2008-02-01
**Last audit:** 2026-11-05 via `/characterize-set mor` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Lorwyn set — class tribal (Bitterblossom, Scapeshift).** **No mythics.** Two promos: an alt-art prerelease foil and a same-art release foil.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mor` | expansion | 150 | 2008-02-01 | parent — booster set 1–150 (no basics) |
| `pmor` | promo | 2 | 2008-02-01 | prerelease Door of Destinies `143★` (~$18, alt art, `datestamped`) + release Earwig Squad `60★` (same art) |
| `tmor` | token | 3 | 2008-02-01 | tokens |

`set:mor+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 150 | `mor` 1–150 (60 C / 40 U / 50 R) | `regular` | rarity/base sub-selectors — R+M ≈ $305 nonfoil / $1640 foil (Scapeshift 136 ~$55 / **$246** foil, Bitterblossom 58 ~$36 / $139, Maralen 65 ~$31, Thornbite Staff 145, Idyllic Tutor 12 ~$122 foil) |

**`promo_types`:** the prerelease Door of Destinies `143★` has its own art; the release Earwig Squad `60★` reuses the booster art. The prerelease is `datestamped` (dropped by `missing.drop_datestamped_with_sibling`); the release foil isn't, so missing-set lists it. No fancy-foil sheet →
proposed `[dupe_foil] mor = []` to enable `mm query missing-set mor`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] mor = []` | 0 | **apply** — empty, enables missing-set |
| `pmor` promos | 2 | **owner's call** — 1 of 2 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `143★` | `pmor` | prerelease (alt art) | Door of Destinies |
| `60★` | `pmor` | release (same art) | Earwig Squad |

---

## 7. Edge cases & gotchas

- **No mythics, no basics** (boosters used [`lrw`](lrw.md) basics).
- MTGJSON has 4 `Theme Deck` lists.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.mor.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.mor]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mor --list-boosters` (2026-11-05): `draft` EV ~$13.89.
