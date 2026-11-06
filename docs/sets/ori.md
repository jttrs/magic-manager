# `ori` — Magic Origins

> Per-family memory doc. Read this before answering set-specific questions about
> `ori` or working on `ori`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ori`
**Family root type:** `core`
**Family released:** 2015-07-17
**Last audit:** 2026-11-05 via `/characterize-set ori` (one-at-a-time run — tier decisions pending owner review).

---

> **The last core set of the M-era, base frame only**, with the five
> transforming Origins planeswalkers (`originpwdfc`). Extras: a Sample Deck
> reprint band (273–288), the Clash Pack child `cp3` (6 alt-art foils), Intro
> Pack foils and event promos.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ori` | core | 288 | 2015-07-17 | parent — booster set 1–272 (basics 253–272), Sample Deck band 273–288 |
| `pori` | promo | 54 | 2015-07-17 | prerelease `Ns` datestamped (40) + Promo Pack `Np` stamped (4) + Intro Pack foils (5) + game day / release / buy-a-box / resale (5) |
| `cp3` | starter | 6 | 2015-07-17 | Magic Origins Clash Pack — 6 foil alt-art cards (Siege Rhino, Dromoka, …) |
| `tori` | token | 15 | 2015-07-17 | tokens |

`set:ori+related` covers all four.

---

## 2. Treatments

Survey (`survey_treatment_signature.py ORI`): every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 272 | `ori` 1–272 (121 C / 80 U / 55 R / 16 M; 5 transforming walkers) | `regular` | rarity/base sub-selectors — R+M ≈ $125 nonfoil / $474 foil (Starfield of Nyx 33 ~$13 / $60, Jace, Vryn's Prodigy 60 ~$11, Alhammarret's Archive 221 ~$10 / $48, Liliana 106 ~$8 / $39) |
| Sample Deck reprints | 16 | `ori` 273–288 (`starterdeck`, nonfoil-only; Serra Angel 276, Shivan Dragon 285, Mahamoti Djinn 278) | `regular` | keep — cheap reprints in ORI frame (~$2) |
| Clash Pack foils | 6 | `cp3` 1–6 (foil-only, **own art**) | `regular` | keep — ~$4.50 |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 40 prints, auto-dropped (~$172 foil) |
| `promopack` + `stamped` | `regular` | **yes** | 4 prints, ~$23 / $43 |
| `intropack` | — | **no** — own art | 5 foil rares (Hixus 19, Alhammarret 43, Kothophed 104, Pia and Kiran 157, Dwynen 172) |
| `gameday` | — | Conclave Naturalists 171 own art; Languish 105 same art | 2 prints |
| `release` / `buyabox` | — | **no** — own art | Mizzium Meddler 64, Relic Seeker 29 |
| `resale` | — | same art | Outland Colossus `193★` |
| `starterdeck` | — | product band | 273–288 |

No fancy-foil sheet → proposed `[dupe_foil] ori = []` to enable `mm query missing-set ori`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ori = []` | 0 | **apply** — empty, enables missing-set |
| `pori` promo-pack stamped `Np` | 4 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$23 |
| `pori` Intro Pack foils + event promos | 10 | **owner's call** — 8 have their own art |
| Sample Deck band 273–288, `cp3` | 22 | keep |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` / `Np` | `pori` | prerelease / Promo Pack | — |
| `19`, `43`, `104`, `157`, `172` | `pori` | Intro Pack foil (alt art) | Dwynen 172 |
| `105`, `171` | `pori` | Game Day | Languish 105 |
| `64` / `29` | `pori` | Release / Buy-a-Box | Relic Seeker 29 |
| `193★` | `pori` | resale | Outland Colossus |
| `1`–`6` | `cp3` | Clash Pack | Siege Rhino 5 |
| `273`–`288` | `ori` | Sample Decks | Shivan Dragon 285 |

---

## 7. Edge cases & gotchas

- **`cp3` is the Clash Pack, not a promo set** (`set_type` `starter`); its 6
  cards are Khans-block reprints with new art.
- **Prerelease packs are per-planeswalker** (`prerelease-<walker>` booster
  types, EV ~$2.35–$6.20).
- Mizzium Meddler 64 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ori.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ori]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | each with a foil `pori` rare |
| Clash Pack *Armed and Dangerous* | Clash pack | `cp3` |
| Sample Decks ×5 | sample deck (MTGJSON `Sample Deck`) | band 273–288 |
| Fat Pack / Deck Builder's Toolkit | Bundle / kit | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ori --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$3.47, 99.6% coverage |
| `prerelease-<walker>` | ~$2.35 (Liliana) – ~$6.20 (Chandra) |
