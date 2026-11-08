# `wwk` — Worldwake

> Per-family memory doc. Read this before answering set-specific questions about
> `wwk` or working on `wwk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `wwk`
**Family root type:** `expansion`
**Family released:** 2010-02-05
**Last audit:** 2026-11-05 via `/characterize-set wwk` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Zendikar set — Jace, the Mind Sculptor, Stoneforge Mystic, the manlands.** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `wwk` | expansion | 145 | 2010-02-05 | parent — booster set 1–145 (no basics) |
| `pwwk` | promo | 4 | 2010-02-05 | prerelease Comet Storm `76★` + release Joraga Warcaller `106★` (~$15) + buy-a-box Celestial Colonnade 133 (alt art) + resale Terastodon `A6` |
| `twwk` | token | 6 | 2010-02-05 | tokens |

`set:wwk+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 145 | `wwk` 1–145 (60 C / 40 U / 35 R / 10 M) | `regular` | rarity/base sub-selectors — R+M ≈ $253 nonfoil / $1011 foil (Eye of Ugin 136 ~$53, Amulet of Vigor 121 ~$48, Stoneforge Mystic 20 ~$29 / $72, Jace, the Mind Sculptor 31 ~$27 / **$222** foil) |

**`promo_types`:** 3 of 4 `pwwk` prints have their own art (resale `A6` reuses it); the buy-a-box Celestial Colonnade is at plain CN 133, not `133★`. The prerelease and release promos carry `datestamped`, so `missing.drop_datestamped_with_sibling` drops them from missing-set (name + treatment match, not art). No fancy-foil sheet →
proposed `[dupe_foil] wwk = []` to enable `mm query missing-set wwk`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] wwk = []` | 0 | **apply** — empty, enables missing-set |
| `pwwk` promos | 4 | **owner's call** — 3 of 4 have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pwwk` | prerelease / release (alt art) | Joraga Warcaller `106★` |
| `133` | `pwwk` | Buy-a-Box (alt art) | Celestial Colonnade |
| `A6` | `pwwk` | resale (same art) | Terastodon |

---

## 7. Edge cases & gotchas

- **No basics**; boosters used [`zen`](zen.md) basics.
- **Foil Jace, the Mind Sculptor 31 (~$222)** dwarfs the rest.
- MTGJSON lists a `six` booster type besides `draft`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.wwk.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.wwk]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py wwk --list-boosters` (2026-11-05): `draft` EV ~$11.58.
