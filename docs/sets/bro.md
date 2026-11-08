# `bro` — The Brothers' War

> Per-family memory doc. Read this before answering set-specific questions about
> `bro` or working on `bro`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `bro`
**Family root type:** `expansion`
**Family released:** 2022-11-18
**Last audit:** 2026-11-03 via `/characterize-set bro` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

14 Scryfall codes, all linked to `bro` via `parent_set_code`.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `bro` | expansion | 387 | 2022-11-18 | parent — booster set 1–287, extras 288–384, 12 `A-` Alchemy rebalances |
| `brr` | masterpiece | 189 | 2022-11-18 | **Retro Artifacts** — 63 artifacts × (retro original art 1–63, schematic art 64–126) + 63 serialized `Nz` |
| `brc` | commander | 209 | 2022-11-18 | 2 Commander decks (Urza / Mishra) + ext-art collector prints |
| `bot` | eternal | 29 | 2022-11-18 | **Transformers** — 15 regular + 14 borderless shattered-glass DFC bonus cards (Set/Collector Booster) |
| `pbro` | promo | 171 | 2022-11-18 | prerelease `Ns` datestamped + Promo Pack `Np` stamped + 2 Construct tokens `T1`/`T2` |
| `ybro` | alchemy | 31 | 2022-12 | digital-only (`security_stamp: arena`) |
| `tbro` / `tbrc` / `tbot` | token | 12 / 14 / 2 | 2022-11-18 | tokens |
| `ptbro` | token | 3 | 2022-11-18 | Southeast Asia full-art tokens |
| `sbro` | token | 1 | 2022-11-18 | Double-Faced Substitute Card |
| `mbro` | minigame | 3 | 2022-11-18 | minigame inserts |
| `abro` | memorabilia | 81 | 2022-11-18 | Art Series |
| `fbro` | memorabilia | 5 | 2022-11-18 | Jumpstart front cards |

**Separately-rooted bonus sheets:** none — `brr` and `bot` are both properly
parented to `bro`. `set:bro+related` covers the whole family; no `--only` needed.

---

## 2. Treatments

Survey (`survey_treatment_signature.py BRO`, 1,149 prints). No `boosterfun`
fancy-foil token exists in this family — the only `ff` class is the serialized
`brr` `Nz` sheet.

**Frame/finish treatment classes present:**

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 287 | `bro` 1–287 (basics 268–287) | `regular` | rarity/base sub-selectors |
| full-art basics | 10 | `bro` 278–287 (2 arts × 5) | `fa` | kept (commons; not in rare/mythic selectors) |
| post-set rares | 5 | `bro` 288–292 (Rescue Retriever, Geology Enthusiast, Terror Ballista, Artificer's Dragon, Woodcaller Automaton) | `regular` | rare-regular |
| borderless planeswalkers / legends | 4 | `bro` 293–296 (Teferi, Saheeli, Mishra, Urza) | `b` | **kept (default) — pending owner review.** Distinct art |
| borderless painlands | 4 | `bro` 297–300 | `b` | **kept (default) — pending owner review.** Distinct art |
| extended-art | 77 | `bro` 301–377, `brc` 41–67 | `ext` | auto-dropped (ext class) |
| buy-a-box / bundle promos | 2 | `bro` 378 Mishra's Foundry, 379 Queen Kayla bin-Kroog (foil-only) | `regular` | rare-regular — distinct art, kept |
| promo-pack inverted uncommons | 5 | `bro` 380–384 (Lay Down Arms, Flow of Knowledge, Corrupt, …) | `b` (black border, `inverted`) | kept by default — **same art** as the base print (380↔11, 384↔171); uncommon, so no rare/mythic selector picks them up; they only reach the `preferred` sub-selector |
| Retro Artifacts — retro original art | 63 | `brr` 1–63 | `regular` | rare/mythic-regular — **kept (default) — pending owner review** |
| Retro Artifacts — schematic art | 63 | `brr` 64–126 | `regular` | rare/mythic-regular — **kept (default) — pending owner review.** Distinct art from 1–63 |
| Retro Artifacts serialized | 63 | `brr` 64z–126z (`serialized`+`doublerainbow`, foil, same art as 64–126) | `ff` | globally dropped (`serialized`) |
| Transformers regular | 15 | `bot` 1–15 (convertdfc, black border) | `regular` | mythic-regular |
| Transformers shattered-glass | 14 | `bot` 16–29 (borderless, `shatteredglass`+`inverted`) | `b` | **kept (default) — pending owner review.** Distinct art; foils $200–$460 |
| tombstone | 6 | `brc` 17/116/147, `brr` 59/122/122z | `regular` (122z `ff`, serialized) | base |
| etched oversized commanders | 2 | `brc` 39–40 (`thick`) | `regular` [etched] | display cards |
| Alchemy rebalance | 12 | `bro` `A-*` (arena stamp) | — | dropped by `_is_digital_only` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes — `pbro` `Ns` = base + datestamp | auto-dropped by the Step-2 datestamped filter |
| `promopack` + `stamped` | `regular` | yes — `pbro` `Np` = base + stamp (80 prints) | leaks via rare/mythic-regular (~$216 nonfoil / ~$242 foil); propose `stamped` rule (ONE/NEO/TDM precedent) |
| `promopack` (alone) | `b` | same art as base | `bro` 380–384 uncommons; signal is `stamped` ONLY, so the rule above spares them |
| `serialized` + `doublerainbow` | `ff` | same art as `brr` 64–126 | globally filtered |
| `buyabox` / `bundle` | — | no — distinct art | `bro` 378 / 379 |
| `thick` | etched | n/a | `brc` 39–40 |
| `universesbeyond` | — | n/a | all 31 `bot`/`tbot` prints |

No `[dupe_foil]` token is needed (no same-art fancy foil computes to `ff`
except the globally filtered serialized sheet) → configured `[dupe_foil] bro = []` (2026-11-08)
just to enable `treatment=preferred` / `mm query missing-set bro`.

**Full-art convention:** `full_art = 1` on `bro` 278–287 and the tokens
(`pbro` T1–T2, `ptbro` 1–3, `sbro` 1); 0 elsewhere, including the borderless prints.

---

## 3. Chase variants

No uncommon chase in the booster set. `set:bro+related missing rarity=uncommon
treatment=regular chase` returns only `brc` reprints that ship in both decks
(Ichor Wellspring 143, Swiftfoot Boots 166) — a multi-printing artefact, not a
distinct-art chase. The bare `chase` modifier (449 rows) is dominated by the
basics and the `brr` retro/schematic pairs — every Retro Artifact has 2 arts
(+ the serialized third), so `chase` is not a useful signal for this family.

---

## 4. Scenes / posters / panoramas

None. The 8 `bro` borderless prints (293–300) are 2+2+4 by different artists;
`bot` 16–29 shattered-glass are individual character cards, not a panorama.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `pbro` promo-pack stamped `Np` | 80 | **exclude** — `promo_types_any_of = ["stamped"]`, same as ONE/NEO/TDM (base+stamp dupes that compute `regular` and bypass `preferred`). Spares the 5 `promopack`-only `bro` 380–384 |
| `brr` schematic art (64–126) | 63 | unsure — distinct art, booster-sheet alternate of each Retro Artifact (~$357 nonfoil total); keep if you collect both arts |
| `brr` retro original art (1–63) | 63 | keep — the primary Retro Artifact print (~$290 nonfoil total) |
| `bot` shattered-glass borderless (16–29) | 14 | keep — distinct-art Transformers alternates; nonfoil $7–$84, foils $200–$460 (concentrated if foils are counted) |
| `bro` borderless 293–300 | 8 | keep — ordinary borderless tier |
| `brr` serialized `Nz` | 63 | n/a — globally filtered (Mox Amber 98z ~$2,782 is the top) |

**Scarcity check:** `set_status.py bro` can't compute missing $ until a
`[dupe_foil]` entry exists. By inspection the only high-$ non-serialized tier is
the `bot` shattered-glass foils (~$2,900 for 14); the nonfoils are ~$300.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` (e.g. `75s`) | `pbro` | prerelease, datestamped (foil) | Arcane Proxy 75s |
| `Np` (e.g. `84p`) | `pbro` | Promo Pack, stamped | Ashnod, Flesh Mechanist 84p |
| `T1`, `T2` | `pbro` | Construct token promos | Construct T1 |
| `378` | `bro` | Buy-a-Box (foil) | Mishra's Foundry |
| `379` | `bro` | Bundle (foil) | Queen Kayla bin-Kroog |
| `380`–`384` | `bro` | Promo Pack inverted uncommons | Lay Down Arms 380 |

No `bulk-add` skill references to `pbro`/`brr` yet.

---

## 7. Edge cases & gotchas

- **Meld cards:** `bro` 163/163b (Phyrexian Dragon Engine → Mishra, Lost to
  Phyrexia), 238/238b (The Mightstone and Weakstone → Urza, Planeswalker),
  256/256b (Argoth → Titania, Gaea Incarnate). The `b` backs are separate rows;
  meld backs are dropped from Collection unless owned. The meld fronts carry no
  oval security stamp.
- **`brr` has three prints per artifact**: retro (1–63), schematic (64–126) and
  serialized schematic (64z–126z, same `illustration_id` as 64–126).
- **`bot` is `set_type: eternal`**, not a token/promo set — it is a real
  booster-slot sheet; every card is a convert-DFC (front robot / back vehicle).
- `A-` Alchemy rebalances sit inside `bro` itself (12 prints, arena stamp) in
  addition to the `ybro` set (31) — both dropped by `_is_digital_only`.
- `pbro` CN `T1`/`T2` cast to 0 in numeric sorts.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] bro = []` — configured 2026-11-08 (enables `mm query missing-set bro`).
- `config/families.toml` `[[unobtainable.bro.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.bro]]` — none (no scenes).

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander decks ×2 | Commander deck | Urza's Iron Alliance / Mishra's Burnished Banner (`brc`) |
| Jumpstart boosters | Jumpstart | value as fixed decks; front cards in `fbro` |
| Bundle / Transformers bundle | Bundle | `bro` 379 promo; `bundle-transformers` / `gift-bundle-transformers` boosters have 0% EV coverage |
| Retro Artifacts | masterpiece sheet | `brr`, one per Set/Collector Booster slot |
| Transformers | bonus sheet | `bot`, Set/Collector Boosters |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py bro --list-boosters` (2026-11-03):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$6.82, 100% coverage |
| `set` | EV ~$8.31, 99.2% |
| `collector` | EV ~$23.17, 93.3% |
| `jumpstart` | EV ~$5.06 — fixed decks, value as decks |
| `prerelease` / `promo` / `promo-foil` | ~$4.09 / ~$8.70 / ~$10.04 |
| `arena` | digital code card, ignore |
| `bundle-transformers`, `gift-bundle-transformers` | 0% coverage — not resolvable locally |
