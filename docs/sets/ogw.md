# `ogw` — Oath of the Gatewatch

> Per-family memory doc. Read this before answering set-specific questions about
> `ogw` or working on `ogw`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ogw`
**Family root type:** `expansion`
**Family released:** 2016-01-22
**Last audit:** 2026-11-05 via `/characterize-set ogw` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Battle for Zendikar set, base frame only.** Introduced Wastes, the
> colourless basic, in four prints. Intro Packs, alt-art event promos. Its
> Zendikar Expeditions live in `exp`, a child of `bfz`, not of `ogw`.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ogw` | expansion | 186 local (Scryfall set metadata says 187) | 2016-01-22 | parent — booster set 1–184 + Wastes `183a`/`184a` |
| `pogw` | promo | 65 | 2016-01-22 | prerelease `Ns` datestamped (54) + Promo Pack `Np` stamped (2) + Intro Pack foils (5) + game day / release / buy-a-box (4) |
| `togw` | token | 11 | 2016-01-22 | tokens |

`set:ogw+related` covers all three. OGW's Expeditions are in `exp`
(`set:bfz+related`).

---

## 2. Treatments

Survey (`survey_treatment_signature.py OGW`): `regular` except the two
full-art Wastes 183/184 (`fa`). `frame_effects` `devoid` (43 colourless
Eldrazi prints) is cosmetic.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 182 | `ogw` 1–182 | `regular` | rarity/base sub-selectors |
| Wastes, full-art | 2 | `ogw` 183, 184 (foil + nonfoil) | `fa` | **kept by default** — the set's basics |
| Wastes, `a` prints | 2 | `ogw` `183a`, `184a` (nonfoil-only, `full_art = 0`, **same art** as 183/184; ~$2) | `regular` | distinct printings — missing-set lists them |

Rarity totals (`ogw`): 72 C / 60 U / 42 R / 12 M. R+M ≈ $46 nonfoil / $176
foil (Kozilek, the Great Distortion 4 ~$5 / $17, Thought-Knot Seer 9,
Kalitas 86, Mirrorpool 174 ~$15 foil).

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 54 prints, auto-dropped (~$272 foil) |
| `promopack` + `stamped` | `regular` | **yes** — `pogw` `Np` = base + stamp | 2 prints, ~$7 / $14 |
| `intropack` | — | **no** — own art | 5 foil rares (Deepfathom Skulker 43, Dread Defiler 68, Munda's Vanguard 29, Tyrant of Valakut 119, Gladehart Cavalry 132) |
| `gameday` | — | **no** — own art | Jori En, Ruin Diver 155 (~$5), Immolating Glare 20 |
| `release` + `datestamped` | — | **no** — own art | Endbringer 3 |
| `buyabox` | — | **no** — own art | Goblin Dark-Dwellers 110 |

No fancy-foil sheet → configured `[dupe_foil] ogw = []` (2026-11-08) to enable `mm query missing-set ogw`.

**Full-art convention:** Wastes 183/184 only.

---

## 3. Chase variants

None among uncommons.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ogw = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pogw` promo-pack stamped `Np` | 2 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$7 |
| `pogw` Intro Pack foils | 5 | **owner's call** — own art |
| `pogw` game day / release / buy-a-box | 4 | **owner's call** — all have their own art |
| Wastes `183a`/`184a` | 2 | **owner's call** — same art as 183/184, not full-art frame; keep unless the owner wants one Wastes per art |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pogw` | prerelease, datestamped (foil) | — |
| `Np` | `pogw` | Promo Pack, stamped | — |
| `29`, `43`, `68`, `119`, `132` | `pogw` | Intro Pack foil (alt art) | Tyrant of Valakut 119 |
| `20`, `155` | `pogw` | Game Day (alt art) | Jori En, Ruin Diver 155 |
| `3` | `pogw` | Release (alt art, datestamped) | Endbringer |
| `110` | `pogw` | Buy-a-Box (alt art) | Goblin Dark-Dwellers |

---

## 7. Edge cases & gotchas

- **Four Wastes prints, two arts:** 183 and 183a share an illustration, as do
  184 and 184a. The `a` prints are nonfoil-only and not flagged full-art.
  Scryfall/MTGJSON record no separate distribution for them.
- **Expeditions are under `bfz`** (`exp` spans 2015-10-02 to 2016-01-22).
- **The booster basic slot uses Battle for Zendikar basics** (MTGJSON's
  `basic` sheet is 25 BFZ cards); the foil slot can be any of the 45
  Expeditions (`foilOrMasterpiece1In144`).
- Endbringer 3 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ogw = []` — configured 2026-11-08 (enables `mm query missing-set ogw`).
- `config/families.toml` `[[unobtainable.ogw.rules]]` — 4 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.ogw]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | Expedition slot (`exp`, BFZ family) |
| Intro Packs ×5 | Intro pack | Concerted Effort, Desperate Stand, Surge of Resistance, Twisted Reality, Vicious Cycle; each with a foil `pogw` rare |
| Fat Pack | Bundle (`fat_pack`) | Fat Pack Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ogw --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$3.38, 99.9% coverage |
| `prerelease` | ~$4.18 |
