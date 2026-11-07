# `emn` — Eldritch Moon

> Per-family memory doc. Read this before answering set-specific questions about
> `emn` or working on `emn`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `emn`
**Family root type:** `expansion`
**Family released:** 2016-07-22
**Last audit:** 2026-11-05 via `/characterize-set emn` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Shadows over Innistrad set, base frame only**, with meld cards and
> transforming DFCs. No basics of its own, no Planeswalker Decks (this era used
> Intro Packs). The Intro Packs' foil rares and several event promos have
> their own art.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `emn` | expansion | 208 | 2016-07-22 | parent — booster set 1–205 + meld backs `15b` Brisela, `96b` Chittering Host, `130b` Hanweir, the Writhing Township |
| `pemn` | promo | 77 | 2016-07-22 | prerelease `Ns` (64, incl. 2 meld backs) + Promo Pack `Np` stamped (3) + Intro Pack foils (5) + game day / release / buy-a-box / resale (5) |
| `temn` | token | 11 | 2016-07-22 | tokens |

`set:emn+related` covers all three.

---

## 2. Treatments

Survey (`survey_treatment_signature.py EMN`): every print computes `regular`.
`frame_effects` `mooneldrazidfc` / `sunmoondfc` are DFC/meld markers.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 205 | `emn` 1–205 (75 C / 70 U / 48 R / 15 M; no basics) | `regular` | rarity/base sub-selectors — R+M ≈ $125 nonfoil / $265 foil (Emrakul, the Promised End 6 ~$31, Gisela 28 ~$21, Sigarda's Aid 41 ~$16, Liliana, the Last Hope 93) |
| meld backs | 3 | `emn` `15b`, `96b`, `130b` (unpriced) | `regular` | dropped by `missing._drop_meld_back_faces` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` (+ `datestamped`) | `regular` | yes | 64 prints, auto-dropped (~$451 foil); the meld backs `15bs`/`130bs` have no `datestamped` |
| `promopack` + `stamped` | `regular` | **yes** — `pemn` `Np` = base + stamp | 3 prints, ~$31 |
| `intropack` | — | **no** — own art | 5 foil rares, one per Intro Pack (Niblis of Frost 72, Ulvenwald Observer 176, …) |
| `gameday` | — | **no** — own art | Heron's Grace Champion 185, Unsubstantiate 79 |
| `release` + `datestamped` | — | **no** — own art | Identity Thief 64 |
| `buyabox` | — | **no** — own art | Thalia, Heretic Cathar 46 (~$2.51) |
| `resale` | — | yes — same art | Thalia's Lancers `47★` |

No fancy-foil sheet → proposed `[dupe_foil] emn = []` to enable `mm query missing-set emn`.

**Full-art convention:** none.

---

## 3. Chase variants

None among uncommons.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] emn = []` | 0 | **apply** — empty, enables missing-set |
| `pemn` promo-pack stamped `Np` | 3 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$31 |
| `pemn` Intro Pack foils | 5 | **owner's call** — own art, came in a retail product |
| `pemn` game day / release / buy-a-box / resale | 5 | **owner's call** — 4 have their own art |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pemn` | prerelease (foil) | Gisela `28s` |
| `Np` | `pemn` | Promo Pack, stamped | — |
| `39`, `72`, `98`, `117`, `176` | `pemn` | Intro Pack foil (alt art) | Niblis of Frost 72 |
| `79`, `185` | `pemn` | Game Day (alt art) | Heron's Grace Champion 185 |
| `64` | `pemn` | Release (alt art, datestamped) | Identity Thief |
| `46` | `pemn` | Buy-a-Box (alt art) | Thalia, Heretic Cathar |
| `47★` | `pemn` | resale | Thalia's Lancers |

---

## 7. Edge cases & gotchas

- **Meld backs have their own `b` CNs** (`15b`, `96b`, `130b`), unpriced; the
  missing-set pipeline drops them. Each back follows its first half's CN
  (Bruna 15, Midnight Scavengers 96, Hanweir Garrison 130); both halves of
  every meld pair are in `emn`.
- **No basics** — boosters used Shadows over Innistrad basics.
- Identity Thief 64 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.emn.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.emn]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | Dangerous Knowledge, Shallow Graves, Unlikely Alliances, Untamed Wild, Weapons and Wards; each with a foil `pemn` rare |
| Fat Pack | Bundle (MTGJSON `fat_pack`) | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py emn --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$3.56, 94.5% coverage |
| `prerelease` | ~$5.80 |
