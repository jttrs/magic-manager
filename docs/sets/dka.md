# `dka` — Dark Ascension

> Per-family memory doc. Read this before answering set-specific questions about
> `dka` or working on `dka`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `dka`
**Family root type:** `expansion`
**Family released:** 2012-02-03
**Last audit:** 2026-11-05 via `/characterize-set dka` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Innistrad set — transforming DFCs (`sunmoondfc`), Mikaeus, Grafdigger's Cage.** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dka` | expansion | 158 | 2012-02-03 | parent — booster set 1–158 (no basics) |
| `pdka` | promo | 5 | 2012-02-03 | prerelease Ravenous Demon `71★` + release Mondronen Shaman `98★` (both DFCs, `datestamped`) + buy-a-box Gravecrawler `64★` (~$15) + Game Day Zombie Apocalypse 80 (~$13) / Strangleroot Geist 127 |
| `tdka` | token | 4 | 2012-02-03 | tokens |

`set:dka+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 158 | `dka` 1–158 (64 C / 44 U / 38 R / 12 M; 13 transforming DFCs) | `regular` | rarity/base sub-selectors — R+M ≈ $73 nonfoil / $326 foil (Mikaeus, the Unhallowed 70 ~$23 / $66, Elbrus 147, Havengul Lich 139, Grafdigger's Cage 149 ~$19 foil, Geralf's Messenger 63) |

**`promo_types`:** every `pdka` print has its own art; Gravecrawler `64★` and Zombie Apocalypse 80 are worth more than most of the set. The prerelease and release promos carry `datestamped`, so `missing.drop_datestamped_with_sibling` drops them from missing-set (name + treatment match, not art). No fancy-foil sheet →
configured `[dupe_foil] dka = []` (2026-11-08) to enable `mm query missing-set dka`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] dka = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pdka` promos | 5 | **owner's call** — all have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pdka` | prerelease / release / Buy-a-Box (alt art) | Gravecrawler `64★` |
| `80`, `127` | `pdka` | Game Day | Zombie Apocalypse 80 |

---

## 7. Edge cases & gotchas

- **Its prerelease/release promos carry `datestamped`**, while the later `avr` and `m13` ones don't — Scryfall's tagging isn't chronological.
- No basics; boosters used [`isd`](isd.md) basics.
- MTGJSON lists a `six` booster type besides `draft`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] dka = []` — configured 2026-11-08 (enables `mm query missing-set dka`).
- `config/families.toml` `[[unobtainable.dka.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.dka]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 / Event Decks ×2 | Intro pack / Event deck | Gleeful Flames, Spiraling Doom |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py dka --list-boosters` (2026-11-05): `draft` EV ~$3.98.
