# `dbl` — Innistrad: Double Feature

> Per-family memory doc. Read this before answering set-specific questions about
> `dbl` or working on `dbl`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `dbl`
**Family root type:** `draft_innovation`
**Family released:** 2022-01-28
**Last audit:** 2026-11-04 via `/characterize-set dbl` (one-at-a-time run — tier decisions pending owner review).

---

> **Whole-set reprint in a single treatment.** Double Feature reprints every
> card of Innistrad: Midnight Hunt (`dbl` 1–267) and Innistrad: Crimson Vow
> (`dbl` 268–534) in a black-and-white "silver screen" frame (black border,
> `inverted`). It is its own family (`parent_set_code: null`) — NOT linked to
> `mid` or `vow`, and their docs don't cover it.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dbl` | draft_innovation | 535 | 2022-01-28 | parent — MID reprints 1–267, VOW reprints 268–534, prerelease promo 535 |

No token, promo or memorabilia children. No `--only` needed.

---

## 2. Treatments

Survey (`survey_treatment_signature.py DBL`, 535 prints). **Every print computes
`b`** (black border + `inverted`), so in this family `b` IS the base frame, not
an alt tier.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| silver-screen base (MID half) | 267 | `dbl` 1–267 (foil + nonfoil; 47 `sunmoondfc` DFCs/legends) | `b` | **kept (default) — pending owner review.** The whole set; excluding it empties the family |
| silver-screen base (VOW half) | 267 | `dbl` 268–534 | `b` | same as above |
| prerelease promo | 1 | `dbl` 535 Endless Ranks of the Dead (`prerelease`, foil-only, not datestamped) | `b` | kept — no same-art sibling in `dbl` |

**`promo_types` dupe-foil / stamped signals:** only `prerelease` on CN 535.
No `boosterfun`, textured, stamped or serialized prints. Nothing to dedup →
proposed `[dupe_foil] dbl = []` just to enable `mm query missing-set dbl`.

**Art identity vs MID/VOW:** only 2 of 535 prints share an `illustration_id`
with a `mid`/`vow` print — Scryfall treats the grayscale renders as new
artworks, so art-tag and art-swap lookups see them as distinct.

**Full-art convention:** none (`full_art = 0` throughout).

---

## 3. Chase variants

None. One printing per card in-family.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] dbl = []` | 0 | **apply** — empty entry, enables missing-set |
| whole set (`b`) | 534 | keep — it's the base; the only choice is whether to track the family at all (it duplicates MID/VOW's card list in a different frame) |
| prerelease 535 | 1 | keep |

**Totals (local prices, 2026-11-04):** rare+mythic ≈ $452 nonfoil / $1,968 foil
(The Meathook Massacre 112 leads, $35 / $157 foil).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `535` | `dbl` | prerelease promo (foil) | Endless Ranks of the Dead |

---

## 7. Edge cases & gotchas

- **Not linked to `mid`/`vow`.** `set:mid+related` and `set:vow+related` don't
  include `dbl`; a Double Feature card never counts toward MID/VOW completion.
- **Every print is `b`.** Any rule keyed on border/`inverted` would wipe the
  family — don't copy a "black-border showcase" exclusion from another set here.
- 98 `sunmoondfc` transforming DFCs; the back face shares the row.
- Draft-only product: booster EV coverage is 85.5% (9 layouts).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.dbl.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.dbl]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | the only booster; no Set/Collector boosters, no precons |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py dbl --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$11.24, 85.5% coverage |
