# `zen` — Zendikar

> Per-family memory doc. Read this before answering set-specific questions about
> `zen` or working on `zen`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `zen`
**Family root type:** `expansion`
**Family released:** 2009-10-02
**Last audit:** 2026-11-05 via `/characterize-set zen` (one-at-a-time run — tier decisions pending owner review).

---

> **Landfall set with the enemy fetchlands and 40 full-art basics.** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `zen` | expansion | 269 | 2009-10-02 | parent — booster set 1–249 (full-art basics 230–249) + `230a`–`249a` (nonfoil, same art) |
| `pzen` | promo | 4 | 2009-10-02 | prerelease Rampaging Baloths `178★` + release Valakut, the Molten Pinnacle `228★` (~$21) + buy-a-box Day of Judgment `9★` + resale Terra Stomper `A5` |
| `tzen` | token | 11 | 2009-10-02 | tokens |

`set:zen+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 249 | `zen` 1–249 + 20 `Na` (141 C (incl. 40 basics) / 60 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $486 nonfoil / $1899 foil (Scalding Tarn 223 ~$45 / $113, Misty Rainforest 220 ~$40 / $118, Marsh Flats 219, Arid Mesa 211, Verdant Catacombs 229, Bloodchief Ascension 82 ~$24) |
| full-art basics | 20 | `zen` 230–249 (foil + nonfoil) | `fa` | **kept by default** — ~$12 nonfoil / **~$192 foil** |
| full-art basics, `a` prints | 20 | `zen` `230a`–`249a` (nonfoil-only, **same art** as the unlettered CN) | `regular` | distinct printings — missing-set lists them |

**`promo_types`:** 3 of 4 `pzen` prints have their own art (resale `A5` reuses it). The prerelease and release promos carry `datestamped`, so `missing.drop_datestamped_with_sibling` drops them from missing-set (name + treatment match, not art). No fancy-foil sheet →
proposed `[dupe_foil] zen = []` to enable `mm query missing-set zen`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] zen = []` | 0 | **apply** — empty, enables missing-set |
| `pzen` promos | 4 | **owner's call** — 3 of 4 have their own art |
| basics `230a`–`249a` | 20 | **owner's call** — same art as 230–249; same pattern as [`bfz`](bfz.md) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pzen` | prerelease / release / Buy-a-Box (alt art) | Valakut `228★` |
| `A5` | `pzen` | resale (same art) | Terra Stomper |

---

## 7. Edge cases & gotchas

- **40 basics:** each full-art basic has an unlettered (foil + nonfoil, `fa`) and an `a` (nonfoil, not flagged full-art) print of the same art — the [`bfz`](bfz.md) pattern started here.
- **Foil premium is extreme** (R+M ~$486 nonfoil vs ~$1,899 foil).
- MTGJSON lists a `six` booster type besides `draft`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.zen.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.zen]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | full-art basic slot |
| Intro Packs ×5 | Intro pack | — |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py zen --list-boosters` (2026-11-05): `draft` EV ~$12.00.
