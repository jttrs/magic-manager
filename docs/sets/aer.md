# `aer` — Aether Revolt

> Per-family memory doc. Read this before answering set-specific questions about
> `aer` or working on `aer`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `aer`
**Family root type:** `expansion`
**Family released:** 2017-01-20
**Last audit:** 2026-11-05 via `/characterize-set aer` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Kaladesh set, base frame only.** No basics of its own (boosters use
> Kaladesh basics), two Planeswalker Decks, and a few alt-art event promos.
> Its 24 Inventions are `mps` 31–54, in the [`kld`](kld.md) family.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `aer` | expansion | 194 | 2017-01-20 | parent — booster set 1–184, PW-deck cards 185–194 |
| `paer` | promo | 65 | 2017-01-20 | prerelease `Ns` datestamped (54) + Promo Pack `Np` stamped (7) + game day / release / buy-a-box (4) |
| `taer` | token | 4 | 2017-01-20 | tokens |

`set:aer+related` covers all three. (Scryfall's set metadata says 197 for
`aer`; 194 are local.)

---

## 2. Treatments

Survey (`survey_treatment_signature.py AER`): every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 184 | `aer` 1–184 (70 C / 60 U / 42 R / 12 M) | `regular` | rarity/base sub-selectors — R+M ≈ $78 nonfoil / $186 foil (Heroic Intervention 109 ~$15, Walking Ballista 181 ~$9, Paradox Engine 169 ~$6 / $19) |
| Planeswalker-deck exclusives | 10 | `aer` 185 Ajani, Valiant Protector + 186–189; 190 Tezzeret, Master of Metal + 191–194 | `regular` | **unique cards** — keep; walkers foil-only, deck mates nonfoil-only |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 54 prints, auto-dropped (~$309 foil) |
| `promopack` + `stamped` | `regular` | **yes** — `paer` `Np` = base + stamp | 7 prints, ~$52 nonfoil / ~$53 foil (Heroic Intervention `109p`) |
| `gameday` | — | Yahenni's Expertise 75 **own art**; Trophy Mage 48 same art | 2 prints |
| `release` + `datestamped` | — | **no** — own art | Quicksmith Rebel 93 |
| `buyabox` | — | **no** — own art | Scrap Trawler 175 (~$2) |
| `planeswalkerdeck` | — | unique cards | 185–194 |

No fancy-foil sheet → configured `[dupe_foil] aer = []` (2026-11-08) to enable `mm query missing-set aer`.

**Full-art convention:** none.

---

## 3. Chase variants

None in `aer`. The Inventions (`mps` 31–54) replace the foil slot about 1 in
144 packs (MTGJSON sheet `foilOrMasterpiece1In144`).

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] aer = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `paer` promo-pack stamped `Np` | 7 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$52 |
| `paer` game day / release / buy-a-box | 4 | **owner's call** — 3 have their own art |
| PW-deck 185–194 | 10 | keep — real cards |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `paer` | prerelease, datestamped (foil) | — |
| `Np` | `paer` | Promo Pack, stamped | Heroic Intervention `109p` |
| `48`, `75` | `paer` | Game Day | Yahenni's Expertise 75 (alt art) |
| `93` | `paer` | Release (alt art) | Quicksmith Rebel |
| `175` | `paer` | Buy-a-Box (alt art) | Scrap Trawler |
| `185`–`194` | `aer` | Planeswalker Decks | Tezzeret, Master of Metal 190 |
| `31`–`54` | `mps` | Inventions (AER boosters) | — |

---

## 7. Edge cases & gotchas

- **No AER basics:** the booster basic slot (and the basic-land foils) come
  from Kaladesh, so `set:aer` has no basics.
- **Inventions are filed under `kld`** (`mps` covers both sets).
- Quicksmith Rebel 93 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] aer = []` — configured 2026-11-08 (enables `mm query missing-set aer`).
- `config/families.toml` `[[unobtainable.aer.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.aer]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | KLD basics; Invention foil slot |
| Planeswalker Decks ×2 | Planeswalker deck | Ajani / Tezzeret; cards at 185–194 |
| Bundle | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py aer --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$4.53, 99.9% coverage |
| `prerelease` | ~$5.29 |
