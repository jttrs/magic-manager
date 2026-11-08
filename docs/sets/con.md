# `con` — Conflux

> Per-family memory doc. Read this before answering set-specific questions about
> `con` or working on `con`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `con`
**Family root type:** `expansion`
**Family released:** 2009-02-06
**Last audit:** 2026-11-05 via `/characterize-set con` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Shards of Alara set (Noble Hierarch, Font of Mythos).** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `con` | expansion | 145 | 2009-02-06 | parent — booster set 1–145 (no basics) |
| `pcon` | promo | 2 | 2009-02-06 | prerelease Malfegor `117★` + release Obelisk of Alara `140★` |
| `tcon` | token | 2 | 2009-02-06 | tokens |

`set:con+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 145 | `con` 1–145 (60 C / 40 U / 35 R / 10 M) | `regular` | rarity/base sub-selectors — R+M ≈ $107 nonfoil / $529 foil (Paleoloth 88 ~$15, Font of Mythos 136 ~$15 / $39, Noble Hierarch 87 ~$13 / $50, Kederekt Parasite 48 ~$45 foil, Master Transmuter 31 ~$46 foil) |

**`promo_types`:** both `pcon` prints have their own art. The prerelease and release promos carry `datestamped`, so `missing.drop_datestamped_with_sibling` drops them from missing-set (name + treatment match, not art). No fancy-foil sheet →
configured `[dupe_foil] con = []` (2026-11-08) to enable `mm query missing-set con`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] con = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pcon` promos | 2 | **owner's call** — both have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pcon` | prerelease / release (alt art) | Malfegor `117★` |

---

## 7. Edge cases & gotchas

- **No basics**; boosters used [`ala`](ala.md) basics.
- `sealed-value` couldn't list CON booster types (the script errored on this set's MTGJSON data).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] con = []` — configured 2026-11-08 (enables `mm query missing-set con`).
- `config/families.toml` `[[unobtainable.con.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.con]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py con --list-boosters` (2026-11-05): not available (script error).
