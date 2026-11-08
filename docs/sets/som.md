# `som` — Scars of Mirrodin

> Per-family memory doc. Read this before answering set-specific questions about
> `som` or working on `som`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `som`
**Family root type:** `expansion`
**Family released:** 2010-10-01
**Last audit:** 2026-11-05 via `/characterize-set som` (one-at-a-time run — tier decisions pending owner review).

---

> **First Scars of Mirrodin set — infect, metalcraft, Mox Opal.** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `som` | expansion | 249 | 2010-10-01 | parent — booster set 1–249 (basics 230–249) |
| `psom` | promo | 4 | 2010-10-01 | prerelease Wurmcoil Engine `223★` (~$11) + release Steel Hellkite `205★` + buy-a-box Memoricide `69★` + resale Sunblast Angel `A8` |
| `tsom` | token | 10 | 2010-10-01 | tokens |

`set:som+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 249 | `som` 1–249 (121 C / 60 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $461 nonfoil / $1306 foil (Mox Opal 179 ~$226 / **$500** foil, Ezuri 119 ~$23, Sword of Body and Mind 208 ~$20, Platinum Emperion 193, Skithiryx 79 ~$62 foil) |

**`promo_types`:** 3 of 4 `psom` prints have their own art (resale `A8` reuses it). The prerelease and release promos carry `datestamped`, so `missing.drop_datestamped_with_sibling` drops them from missing-set (name + treatment match, not art). No fancy-foil sheet →
configured `[dupe_foil] som = []` (2026-11-08) to enable `mm query missing-set som`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] som = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `psom` promos | 4 | **owner's call** — 3 of 4 have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `psom` | prerelease / release / Buy-a-Box (alt art) | Wurmcoil Engine `223★` |
| `A8` | `psom` | resale (same art) | Sunblast Angel |

---

## 7. Edge cases & gotchas

- **Mox Opal 179 is most of the set's value** (~$226 nonfoil, ~$500 foil).
- The prerelease Wurmcoil Engine `223★` (~$11) is hidden by the datestamped drop.
- MTGJSON lists a `six` booster type besides `draft`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] som = []` — configured 2026-11-08 (enables `mm query missing-set som`).
- `config/families.toml` `[[unobtainable.som.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.som]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | — |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py som --list-boosters` (2026-11-05): `draft` EV ~$10.40.
