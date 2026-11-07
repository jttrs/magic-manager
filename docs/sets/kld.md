# `kld` — Kaladesh

> Per-family memory doc. Read this before answering set-specific questions about
> `kld` or working on `kld`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `kld`
**Family root type:** `expansion`
**Family released:** 2016-09-30
**Last audit:** 2026-11-05 via `/characterize-set kld` (one-at-a-time run — tier decisions pending owner review).

---

> **Base-frame expansion whose family holds the Kaladesh Inventions (`mps`)** —
> 54 foil masterpiece artifacts for both Kaladesh and [`aer`](aer.md), worth
> **~$12,400** (Sol Ring ~$1,600, Mana Vault ~$1,400, Mox Opal ~$1,220). All
> are rarity `special`, which makes them invisible to `mm query missing-set`
> (the [`tsr`](tsr.md) / [`akh`](akh.md) blind spot). Also: two Planeswalker
> Decks, a few alt-art event promos.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `kld` | expansion | 274 | 2016-09-30 | parent — booster set 1–264 (basics 250–264), PW-deck cards 265–274 |
| `pkld` | promo | 83 | 2016-09-30 | prerelease `Ns` datestamped (68) + Promo Pack `Np` stamped (9) + game day / release / buy-a-box / Gift Box / resale (6) |
| `mps` | masterpiece | 54 | 2016-09-30 | Kaladesh Inventions — KLD 1–30, AER 31–54 (foil-only, rarity `special`, black border) |
| `tkld` | token | 13 | 2016-09-30 | tokens (incl. full-art Energy Reserve 13) |

`set:kld+related` covers all four. (Scryfall's set metadata says 278 for
`kld`; 274 are local.)

---

## 2. Treatments

Survey (`survey_treatment_signature.py KLD`): every card computes `regular`
(the one `fa` print is the Energy Reserve token).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 264 | `kld` 1–264 (116 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $108 nonfoil / $257 foil (Aetherflux Reservoir 192 ~$22, Inventors' Fair 247 ~$19, Kambal 183 ~$8, Panharmonicon 226 ~$6) |
| Planeswalker-deck exclusives | 10 | `kld` 265 Chandra, Pyrogenius + 266–269; 270 Nissa, Nature's Artisan + 271–274 | `regular` | **unique cards** — keep; walkers foil-only, deck mates nonfoil-only |
| **Inventions** | 54 | `mps` 1–54 (Sol Ring 24 ~$1,601, Mana Vault 17 ~$1,396, Mox Opal 19 ~$1,222, Lotus Petal 15 ~$1,014, Chrome Mox 9 ~$989, Mana Crypt 16 ~$500) | `regular` | **⚠ never listed by missing-set** — rarity `special`. ~$12,419 foil; all new art |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 68 prints, auto-dropped (~$438 foil) |
| `promopack` + `stamped` | `regular` | **yes** — `pkld` `Np` = base + stamp | 9 prints, ~$44 nonfoil / ~$107 foil |
| `gameday` | — | **no** — own art | Cultivator of Blades 151, Essence Extraction 80 |
| `release` + `datestamped` | — | **no** — own art | Saheeli's Artistry 62 |
| `buyabox` | — | **no** — own art | Skyship Stalker 130 |
| `giftbox` | — | **no** — own art | Chief of the Foundry 200 (Kaladesh Gift Box) |
| `resale` | — | yes — same art | Bristling Hydra `147★` |
| `planeswalkerdeck` | — | unique cards | 265–274 |

No fancy-foil sheet → proposed `[dupe_foil] kld = []` to enable `mm query missing-set kld`.

**Full-art convention:** none on cards.

---

## 3. Chase variants

The Inventions (~$12,419 total, vs ~$4,265 for the Amonkhet Invocations). MTGJSON's
draft booster puts them on the foil sheet at about 1 in 144 packs
(`foilOrMasterpiece1In144`).

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] kld = []` | 0 | **apply** — empty, enables missing-set |
| `pkld` promo-pack stamped `Np` | 9 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$44 |
| `pkld` game day / release / buy-a-box / Gift Box / resale | 6 | **owner's call** — 5 have their own art |
| `mps` Inventions | 54 | **keep — but a CODE gap:** rarity `special` is never listed by missing-set (see [`tsr`](tsr.md) §5) |
| PW-deck 265–274 | 10 | keep — real cards |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pkld` | prerelease, datestamped (foil) | — |
| `Np` | `pkld` | Promo Pack, stamped | — |
| `80`, `151` | `pkld` | Game Day (alt art) | Cultivator of Blades 151 |
| `62` | `pkld` | Release (alt art, datestamped) | Saheeli's Artistry |
| `130` | `pkld` | Buy-a-Box (alt art) | Skyship Stalker |
| `200` | `pkld` | Gift Box (alt art) | Chief of the Foundry |
| `147★` | `pkld` | resale | Bristling Hydra |
| `1`–`30` | `mps` | Inventions (KLD boosters) | Mox Opal 19 |
| `31`–`54` | `mps` | Inventions (AER boosters) | Chalice of the Void 33 |
| `265`–`274` | `kld` | Planeswalker Decks | Chandra, Pyrogenius 265 |

---

## 7. Edge cases & gotchas

- **`mps` covers two sets**; Scryfall dates all 54 to 2016-09-30 even though
  31–54 shipped with Aether Revolt.
- **Inventions are black-bordered** (not borderless like `mp2`), but the
  rarity-`special` gap is the same.
- **`pkld` 200 Chief of the Foundry** is a CN above the 264-card booster set —
  a Gift Box exclusive art, not a booster card number.
- Saheeli's Artistry 62 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).
- MTGJSON lists `buyabox` and `showdown` booster types for KLD (multi-set
  promo pools, EV ~$9.82 / ~$9.67) — not retail packs.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.kld.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.kld]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | Invention foil slot |
| Planeswalker Decks ×2 | Planeswalker deck | Chandra / Nissa; cards at 265–274 |
| Kaladesh Gift Box | gift bundle (`gift_bundle`) | `pkld` 200 + Gift Box Land Pack (pool) |
| Bundle | Bundle | Bundle Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py kld --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$5.86, 99.9% coverage |
| `prerelease` | ~$5.74 |
| `buyabox` / `showdown` | MTGJSON promo pools, ~$9.82 / ~$9.67 — not retail packs |
