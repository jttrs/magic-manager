# `bfz` — Battle for Zendikar

> Per-family memory doc. Read this before answering set-specific questions about
> `bfz` or working on `bfz`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `bfz`
**Family root type:** `expansion`
**Family released:** 2015-10-02
**Last audit:** 2026-11-05 via `/characterize-set bfz` (one-at-a-time run — tier decisions pending owner review).

---

> **Base-frame expansion whose family holds the Zendikar Expeditions (`exp`)**
> — 45 foil full-art lands for both BFZ and [`ogw`](ogw.md), worth **~$5,774**.
> Unlike the later Invocations/Inventions ([`akh`](akh.md), [`kld`](kld.md)),
> the Expeditions are rated **mythic**, so missing-set **does** list them —
> a `set:bfz` gap list includes every Expedition you lack. Also: 50 full-art
> basics in two printings each, and the first Standard Showdown lands.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `bfz` | expansion | 299 | 2015-10-02 | parent — booster set 1–249, full-art basics 250–274 + `250a`–`274a` |
| `pbfz` | promo | 90 | 2015-10-02 | prerelease `Ns` datestamped (68) + Promo Pack `Np` stamped (11) + Intro Pack foils (5) + game day / release / buy-a-box / Gift Box / resale (6) |
| `exp` | masterpiece | 45 | 2015-10-02 / 2016-01-22 | Zendikar Expeditions — BFZ 1–25, OGW 26–45 (foil-only, mythic) |
| `pss1` | promo | 5 | 2015-10-02 | BFZ Standard Series: the five battle lands with new art (nonfoil) |
| `tbfz` | token | 14 | 2015-10-02 | tokens |

`set:bfz+related` covers all five. OGW's Expeditions are reached only here.

---

## 2. Treatments

Survey (`survey_treatment_signature.py BFZ`): `regular` except the 25 full-art
basics 250–274 (`fa`). `devoid` (55 colourless Eldrazi prints) is cosmetic.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 249 | `bfz` 1–249 (101 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $90 nonfoil / $247 foil (Void Winnower 17 ~$23, Ulamog 15 ~$22, Conduit of Ruin 4, Drana 109 ~$22 foil) |
| full-art basics | 25 | `bfz` 250–274 (foil + nonfoil) | `fa` | **kept by default** |
| full-art basics, `a` prints | 25 | `bfz` `250a`–`274a` (nonfoil-only, **same art** as the unlettered CN) | `regular` | distinct printings — missing-set lists them |
| **Expeditions** | 45 | `exp` 1–45 (Polluted Delta 17 ~$456, Flooded Strand 16 ~$411, Ancient Tomb 36 ~$378, Scalding Tarn 22 ~$343) | `regular` | **listed by missing-set** (mythic-regular) — BFZ half ~$4,239, OGW half ~$1,534 |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 68 prints, auto-dropped (~$528 foil) |
| `promopack` + `stamped` | `regular` | **yes** — `pbfz` `Np` = base + stamp | 11 prints incl. the battle lands, ~$61 nonfoil / ~$88 foil |
| `intropack` | — | **no** — own art | 5 foil rares (Hero of Goma Fada 31 ~$16, Drowner of Hope 57, Defiant Bloodlord 107, Barrage Tyrant 127, Oran-Rief Hydra 181) |
| `gameday` / `release` / `buyabox` / `giftbox` | — | **no** — own art | Stasis Snare 50, Radiant Flames 151, Blight Herder 2, Ruinous Path 123, Scythe Leopard 188 |
| `resale` | — | yes — same art | Felidar Sovereign `26★` (~$4.61) |
| `standardshowdown` + `instore` | — | **no** — own art | `pss1` battle lands (~$23 total) |

No fancy-foil sheet → configured `[dupe_foil] bfz = []` (2026-11-08) to enable `mm query missing-set bfz`.

**Full-art convention:** all booster basics are full-art (both prints).

---

## 3. Chase variants

The Expeditions — about 1 in 144 boosters (MTGJSON sheet
`foilOrMasterpiece1In144`).

## 4. Scenes / posters / panoramas

None configured.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] bfz = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `exp` Expeditions | 45 | **owner's call** — they WILL appear in missing-set (~$5,774). Exclude with a set-scoped rule if you don't collect masterpieces; keep if you do. Note the inconsistency with `mp2`/`mps`, which are hidden by rarity `special` |
| `pbfz` promo-pack stamped `Np` | 11 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$61 |
| `pbfz` Intro Pack foils + event promos | 10 | **owner's call** — 10 of the 11 non-prerelease promos have their own art |
| basics `250a`–`274a` | 25 | **owner's call** — same art as 250–274 |
| `pss1` battle lands | 5 | keep — own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` / `Np` | `pbfz` | prerelease / Promo Pack | Void Winnower `17p` |
| `31`, `57`, `107`, `127`, `181` | `pbfz` | Intro Pack foil (alt art) | Hero of Goma Fada 31 |
| `50`, `151` | `pbfz` | Game Day | Stasis Snare 50 |
| `2` / `123` / `188` | `pbfz` | Release / Buy-a-Box / Gift Box | Ruinous Path 123 |
| `26★` | `pbfz` | resale | Felidar Sovereign |
| `234`–`249` (5) | `pss1` | Standard Showdown | Sunken Hollow 249 |
| `1`–`25` / `26`–`45` | `exp` | Expeditions (BFZ / OGW boosters) | Polluted Delta 17 |

---

## 7. Edge cases & gotchas

- **`exp` spans two release dates** (BFZ 1–25 2015-10-02, OGW 26–45
  2016-01-22) and is only reachable through `bfz`.
- **Expeditions are mythic, the later masterpieces are `special`** — so
  missing-set treats the three masterpiece series differently.
- **50 basics:** each full-art basic has an unlettered (foil + nonfoil) and an
  `a` (nonfoil) print of the same art; OGW boosters also use these basics.
- Blight Herder 2 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] bfz = []` — configured 2026-11-08 (enables `mm query missing-set bfz`).
- `config/families.toml` `[[unobtainable.bfz.rules]]` — 4 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.bfz]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | Expedition foil slot |
| Intro Packs ×5 | Intro pack | each with a foil `pbfz` rare |
| Gift Box / Fat Pack / Deck Builder's Toolkit | gift bundle / Bundle / kit | `pbfz` 188 in the Gift Box |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py bfz --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$4.31, 100% coverage |
| `prerelease` | ~$6.08 |
