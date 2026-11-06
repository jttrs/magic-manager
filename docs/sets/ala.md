# `ala` — Shards of Alara

> Per-family memory doc. Read this before answering set-specific questions about
> `ala` or working on `ala`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ala`
**Family root type:** `expansion`
**Family released:** 2008-10-03
**Last audit:** 2026-11-05 via `/characterize-set ala` (one-at-a-time run — tier decisions pending owner review).

---

> **First Shards of Alara set — the first set with mythic rarity.** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ala` | expansion | 250 | 2008-10-03 | parent — booster set 1–249 (basics 230–249) + showcase Rafiq of the Many 250 (added 2022) |
| `pala` | promo | 2 | 2008-10-03 | prerelease Ajani Vengeant `154★` + resale Broodmate Dragon `A3` |
| `tala` | token | 10 | 2008-10-03 | tokens |

`set:ala+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 249 | `ala` 1–249 (121 C / 60 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $162 nonfoil / $956 foil (Tezzeret the Seeker 60 ~$36, Ad Nauseam 63 ~$11 / **$182** foil, Elspeth, Knight-Errant 9 ~$9, Relic of Progenitus 218, Memory Erosion 50 ~$37 foil) |
| showcase set extension | 1 | `ala` 250 Rafiq of the Many (paper, nonfoil, released 2022-04-29; `showcase`+`inverted`, promo_types `boosterfun`+`setextension`) | `b\|shw` | **kept by default** — ~$1.19 |

**`promo_types`:** the prerelease Ajani Vengeant `154★` has its own art; the resale `A3` reuses it. The prerelease and release promos carry `datestamped`, so `missing.drop_datestamped_with_sibling` drops them from missing-set (name + treatment match, not art). No fancy-foil sheet →
proposed `[dupe_foil] ala = []` to enable `mm query missing-set ala`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ala = []` | 0 | **apply** — empty, enables missing-set |
| `pala` promos | 2 | **owner's call** — 1 of 2 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `154★` | `pala` | prerelease (alt art) | Ajani Vengeant |
| `A3` | `pala` | resale (same art) | Broodmate Dragon |

---

## 7. Edge cases & gotchas

- **`ala` 250 was added in 2022** as a showcase "set extension" Rafiq (a paper card; Scryfall dates it 2022-04-29). A `released_at` filter on the family will split it from the rest.
- **Mythic rarity starts here.**
- MTGJSON lists `premium` (~$20) and `tournament` (~$29) booster types besides `draft` (~$6.30).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ala.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ala]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / tournament packs | booster product | — |
| Intro Packs ×5 | Intro pack | — |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ala --list-boosters` (2026-11-05): `draft` EV ~$6.30; `premium` ~$20.24; `tournament` ~$29.44.
