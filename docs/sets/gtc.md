# `gtc` — Gatecrash

> Per-family memory doc. Read this before answering set-specific questions about
> `gtc` or working on `gtc`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `gtc`
**Family root type:** `expansion`
**Family released:** 2013-02-01
**Last audit:** 2026-11-05 via `/characterize-set gtc` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Return to Ravnica set — the other five guilds and shocklands.** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `gtc` | expansion | 249 | 2013-02-01 | parent — booster set 1–249 (guildgates + shocklands 239–249; **no basics**) |
| `pgtc` | promo | 10 | 2013-02-01 | prerelease `N★` (5) + release Skarrg Goliath `133★` + buy-a-box Nightveil Specter `222★` + Game Day Firemane Avenger 163 / Zameck Guildmage 209 + resale Angelic Skirmisher `A11` |
| `tgtc` | token | 8 | 2013-02-01 | tokens |

`set:gtc+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 249 | `gtc` 1–249 (101 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $141 nonfoil / $428 foil (Crypt Ghast 61 ~$15, Watery Grave 249 ~$11, Sacred Foundry 245 ~$11, Breeding Pool 240 ~$10, Lord of the Void 71, Godless Shrine 242 ~$23 foil) |

**`promo_types`:** every `pgtc` print except the resale `A11` has its own art (Firemane Avenger 163 ~$8). The prerelease and release promos carry
`datestamped`, so `missing.drop_datestamped_with_sibling` drops them from
missing-set (name + treatment match, not art). No fancy-foil sheet →
proposed `[dupe_foil] gtc = []` to enable `mm query missing-set gtc`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] gtc = []` | 0 | **apply** — empty, enables missing-set |
| `pgtc` promos | 10 | **owner's call** — 9 of 10 have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pgtc` | prerelease / release / Buy-a-Box (alt art) | Nightveil Specter `222★` |
| `163`, `209` | `pgtc` | Game Day | Firemane Avenger 163 |
| `A11` | `pgtc` | resale (same art) | Angelic Skirmisher |

---

## 7. Edge cases & gotchas

- **No basics**: boosters used RTR basics; the land slot holds guildgates/shocklands.
- **Prerelease packs are per-guild** (`prerelease-<guild>`, EV ~$3.41–$4.79); MTGJSON also lists a `six` booster type.
- `A11` is a letter-prefixed resale CN (sorts as 0).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.gtc.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.gtc]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 / Event Decks ×2 / Welcome Decks ×5 | Intro pack / Event deck / Welcome deck | Event Decks: Rally and Rout, Thrive and Thrash |
| Booster Battle Pack | two-player pack | — |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py gtc --list-boosters` (2026-11-05): `draft` EV ~$4.71; `prerelease-<guild>` ~$3.41–$4.79.
