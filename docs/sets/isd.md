# `isd` — Innistrad

> Per-family memory doc. Read this before answering set-specific questions about
> `isd` or working on `isd`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `isd`
**Family root type:** `expansion`
**Family released:** 2011-09-30
**Last audit:** 2026-11-05 via `/characterize-set isd` (one-at-a-time run — tier decisions pending owner review).

---

> **Gothic-horror set that introduced transforming double-faced cards (`sunmoondfc`).** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `isd` | expansion | 264 | 2011-09-30 | parent — booster set 1–264 (basics 250–264) |
| `pisd` | promo | 5 | 2011-09-30 | prerelease Mayor of Avabruck `193★` + release Ludevic's Test Subject `64★` (both DFCs) + buy-a-box Devil's Play 140 + Game Day Elite Inquisitor 13 / Diregraf Ghoul 97 |
| `tisd` | token | 13 | 2011-09-30 | tokens |

`set:isd+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 264 | `isd` 1–264 (122 C / 67 U / 59 R / 16 M; 20 transforming DFCs) | `regular` | rarity/base sub-selectors — R+M ≈ $152 nonfoil / $637 foil (Parallel Lives 199 ~$37, Balefire Dragon 129 ~$17, Snapcaster Mage 78 ~$16 / $42, Liliana of the Veil 105 ~$10 / **$84** foil, Bloodline Keeper 90) |

**`promo_types`:** every `pisd` print has its own art. No `datestamped` token on these, so missing-set keeps them. No fancy-foil sheet →
proposed `[dupe_foil] isd = []` to enable `mm query missing-set isd`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] isd = []` | 0 | **apply** — empty, enables missing-set |
| `pisd` promos | 5 | **owner's call** — all have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pisd` | prerelease / release (alt art) | Mayor of Avabruck `193★` |
| `140` | `pisd` | Buy-a-Box (alt art) | Devil's Play |
| `13`, `97` | `pisd` | Game Day | Diregraf Ghoul 97 |

---

## 7. Edge cases & gotchas

- **Transforming DFCs** carry `sunmoondfc`; selectors match on the front name.
- **Foil premium is extreme** (Liliana of the Veil ~8×).
- MTGJSON lists a `six` booster type besides `draft`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.isd.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.isd]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | DFC slot |
| Intro Packs ×5 / Event Decks ×2 | Intro pack / Event deck | Deathfed, Hold the Line |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py isd --list-boosters` (2026-11-05): `draft` EV ~$4.72.
