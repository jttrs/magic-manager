# `nph` — New Phyrexia

> Per-family memory doc. Read this before answering set-specific questions about
> `nph` or working on `nph`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `nph`
**Family root type:** `expansion`
**Family released:** 2011-05-13
**Last audit:** 2026-11-05 via `/characterize-set nph` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Scars of Mirrodin set — Phyrexian mana, the Praetors, and the highest foil premiums in this run (uncommons ~$743 foil).** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `nph` | expansion | 175 | 2011-05-13 | parent — booster set 1–175 (basics 166–175) |
| `pnph` | promo | 4 | 2011-05-13 | prerelease Sheoldred `73★` (~$17) + release Phyrexian Metamorph `42★` (~$21) + buy-a-box Surgical Extraction `74★` (~$10) + Game Day Pristine Talisman 151 (same art) |
| `tnph` | token | 5 | 2011-05-13 | tokens |

`set:nph+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 175 | `nph` 1–175 (70 C / 60 U / 35 R / 10 M) | `regular` | rarity/base sub-selectors — R+M ≈ $238 nonfoil / $996 foil (Elesh Norn 9 ~$24 / $92, Sheoldred 73 ~$21 / $71, Unwinding Clock 164 ~$21, Vorinclex 127, Jin-Gitaxias 37, Phyrexian Obliterator 68) |

**`promo_types`:** 3 of 4 `pnph` prints have their own art (Game Day Pristine Talisman 151 reuses the booster art). The prerelease and release promos carry `datestamped`, so `missing.drop_datestamped_with_sibling` drops them from missing-set (name + treatment match, not art). No fancy-foil sheet →
proposed `[dupe_foil] nph = []` to enable `mm query missing-set nph`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] nph = []` | 0 | **apply** — empty, enables missing-set |
| `pnph` promos | 4 | **owner's call** — 3 of 4 have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pnph` | prerelease / release / Buy-a-Box (alt art) | Phyrexian Metamorph `42★` |
| `151` | `pnph` | Game Day (same art) | Pristine Talisman |

---

## 7. Edge cases & gotchas

- **Foil premium is extreme**: uncommons total ~$70 nonfoil vs ~$743 foil.
- The prerelease Sheoldred `73★` and release Metamorph `42★` are worth $17–21 each and are hidden by the datestamped drop.
- MTGJSON lists a `six` booster type besides `draft`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.nph.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.nph]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 / Event Decks ×2 | Intro pack / Event deck | Rot from Within, War of Attrition |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py nph --list-boosters` (2026-11-05): `draft` EV ~$12.70.
