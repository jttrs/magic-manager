# `arb` — Alara Reborn

> Per-family memory doc. Read this before answering set-specific questions about
> `arb` or working on `arb`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `arb`
**Family root type:** `expansion`
**Family released:** 2009-04-30
**Last audit:** 2026-11-05 via `/characterize-set arb` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Shards of Alara set — every card multicoloured.** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `arb` | expansion | 145 | 2009-04-30 | parent — booster set 1–145 (no basics) |
| `parb` | promo | 3 | 2009-04-30 | prerelease Dragon Broodmother `53★` + release Knight of New Alara `70★` + resale Retaliator Griffin `A4` |
| `tarb` | token | 4 | 2009-04-30 | tokens |

`set:arb+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 145 | `arb` 1–145 (60 C / 40 U / 35 R / 10 M) | `regular` | rarity/base sub-selectors — R+M ≈ $84 nonfoil / $421 foil (Sen Triplets 109 ~$10 / $37, Time Sieve 31 ~$8, Dragon Broodmother 53, Lich Lord of Unx 24, Karrthus 117) |

**`promo_types`:** 2 of 3 `parb` prints have their own art (resale `A4` reuses it). No buy-a-box promo. The prerelease and release promos carry `datestamped`, so `missing.drop_datestamped_with_sibling` drops them from missing-set (name + treatment match, not art). No fancy-foil sheet →
proposed `[dupe_foil] arb = []` to enable `mm query missing-set arb`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] arb = []` | 0 | **apply** — empty, enables missing-set |
| `parb` promos | 3 | **owner's call** — 2 of 3 have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `parb` | prerelease / release (alt art) | Dragon Broodmother `53★` |
| `A4` | `parb` | resale (same art) | Retaliator Griffin |

---

## 7. Edge cases & gotchas

- **No basics**; boosters used [`ala`](ala.md) basics.
- MTGJSON lists a `six` booster type besides `draft`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.arb.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.arb]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py arb --list-boosters` (2026-11-05): `draft` EV ~$5.96.
