# `dmu` — Dominaria United

> Per-family memory doc. Read this before answering set-specific questions about
> `dmu` or working on `dmu`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `dmu`
**Family root type:** `expansion`
**Family released:** 2022-09-09
**Last audit:** 2026-11-03 via `/characterize-set dmu` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

11 Scryfall codes, all parented to `dmu`.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dmu` | expansion | 436 | 2022-09-09 | parent — booster set 1–286, boosterfun 287–436, 17 `A-` Alchemy rebalances |
| `dmc` | commander | 240 | 2022-09-09 | 2 Commander decks (Painbow — Jared Carthalion; Legends' Legacy — Dihada) + collector prints |
| `pdmu` | promo | 161 | 2022-09-09 | prerelease `Ns` datestamped (80) + Promo Pack `Np` stamped (80) + 1 `resale` |
| `ydmu` | alchemy | 39 | 2022-09 | digital-only (arena stamp) |
| `tdmu` / `tdmc` | token | 26 / 12 | 2022-09-09 | tokens |
| `ptdmu` | token | 3 | 2022-09-09 | Southeast Asia full-art tokens |
| `wdmu` | token | 5 | 2022-09-09 | Japanese promo tokens |
| `mdmu` | minigame | 3 | 2022-09-09 | minigame inserts |
| `admu` | memorabilia | 81 | 2022-09-09 | Art Series |
| `fdmu` | memorabilia | 10 | 2022-09-09 | Jumpstart front cards |

**Separately-rooted bonus sheets:** none. `set:dmu+related` covers the family;
no `--only` needed.

---

## 2. Treatments

Survey (`survey_treatment_signature.py DMU`, 1,009 prints).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 286 | `dmu` 1–286 (basics 262–281) | `regular` | rarity/base sub-selectors |
| full-art basics | 5 | `dmu` 277–281 | `fa` | kept (commons) |
| **stained-glass legends showcase (black border)** | 41 | `dmu` 287–327 (`showcase`+`inverted`+`legendary`) | `b\|shw` | **kept (default) — pending owner review.** The set's signature showcase frame (black border — the high-risk class); distinct art from base |
| stained-glass textured foil | 41 | `dmu` 328–368 (foil-only, `textured`) | `b\|shw\|ff` | same art as 287–327 → dupe foil (configured `[dupe_foil] dmu = ["textured"]` (2026-11-08)); ~$215 total |
| showcase planeswalker | 1 | `dmu` 371 Ajani, Sleeper Agent (`showcase`, black border) | `shw` | kept (default) — pending owner review |
| borderless planeswalkers | 5 | `dmu` 372–376 (Karn, Liliana of the Veil, Jaya, Ajani ×2) | `b` | **kept (default) — pending owner review.** Distinct art (375/376 are two further Ajani arts) |
| borderless painlands | 6 | `dmu` 377–382 (`inverted`) | `b` | **kept (default) — pending owner review** |
| extended-art | 46 + 26 | `dmu` 383–428, `dmc` 71–96 | `ext` | auto-dropped |
| buy-a-box | 1 | `dmu` 428 Llanowar Loamspeaker (ext, foil) | `ext` | auto-dropped with the ext class |
| bundle | 1 | `dmu` 429 Herd Migration (foil, distinct art) | `regular` | rare-regular |
| promo-pack inverted uncommons | 5 | `dmu` 430–434 | `b` (black border, `inverted`) | same art as base (430↔29); uncommon, only the `preferred` sub-selector sees them |
| **Sheoldred concept art** | 2 | `dmu` 435 (borderless, `concept`+`setextension`), 436 (same art, `stepandcompleat` foil) | `b` | 435 **kept (default) — pending owner review** ($147 / $204 foil). 436 is a same-art foil that does NOT compute `ff` → dupe_foil misses it ($311) |
| etched commanders | 22 | `dmc` 49–70 (`etched`+`inverted`; 49–50 `thick` display) | `b\|ff` [etched] | auto-dropped |
| Alchemy rebalance | 17 | `dmu` `A-*` | — | dropped by `_is_digital_only` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `textured` | `ff` | **yes** — 328–368 share `illustration_id` with 287–327 | → `[dupe_foil] dmu = ["textured"]` |
| `stepandcompleat` (+`concept`, `setextension`) | none (computes `b`) | **yes** — 436 shares art with 435 | SNC/ONE pattern — dupe_foil can't catch it → `promo_types_any_of = ["stepandcompleat"]` |
| `prerelease` + `datestamped` | `regular` | yes | auto-dropped (datestamped filter) |
| `promopack` + `stamped` | `regular` | yes — `pdmu` `Np` = base + stamp | 80 prints, ~$259 rare/mythic; ONE/NEO/TDM `stamped` rule |
| `promopack` (alone) | `b` | same art as base | `dmu` 430–434 — spared by a `stamped`-only rule |
| `buyabox` / `bundle` / `resale` | — | distinct art | kept |
| `thick` | etched | n/a | `dmc` 49–50 |

**Full-art convention:** `full_art = 1` on `dmu` 277–281 and the `ptdmu` tokens only.

---

## 3. Chase variants

None. `set:dmu+related missing rarity=uncommon treatment=regular chase` → 0 rows.
The only many-printing card is Sheoldred, the Apocalypse (107 / 290 / 331 /
435 / 436 + `pdmu`) — one base, one showcase, one textured, two concept.

---

## 4. Scenes / posters / panoramas

None detected.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] dmu = ["textured"]` | 41 | **applied 2026-11-08** — same-art textured foils of the stained-glass legends |
| `pdmu` promo-pack stamped `Np` | 80 | **exclude** — `promo_types_any_of = ["stamped"]` (ONE/NEO/TDM precedent); ~$259 |
| `dmu` 436 Sheoldred stepandcompleat | 1 | **exclude** — `promo_types_any_of = ["stepandcompleat"]`; same art as 435, computes `b` so dupe-foil misses it ($311) |
| stained-glass legends showcase 287–327 | 41 | keep — distinct-art showcase, cheap (the textured twins go via dupe-foil) |
| Sheoldred concept 435 | 1 | keep or exclude — owner's call; $147 nonfoil is the family's top kept print |
| borderless planeswalkers 372–376 + painlands 377–382 | 11 | keep — ordinary borderless tier |
| showcase Ajani 371 | 1 | keep |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists (`set_status.py`
can't compute missing $). By inspection, Sheoldred's prints dominate the $.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pdmu` | prerelease, datestamped | — |
| `Np` | `pdmu` | Promo Pack, stamped | — |
| `1` (resale) | `pdmu` | resale promo | — |
| `428` | `dmu` | Buy-a-Box (ext-art foil) | Llanowar Loamspeaker |
| `429` | `dmu` | Bundle (foil) | Herd Migration |
| `430`–`434` | `dmu` | Promo Pack inverted uncommons | Resolute Reinforcements 430 |
| `435`–`436` | `dmu` | Sheoldred concept-art (Collector Booster / set extension) | Sheoldred, the Apocalypse |

---

## 7. Edge cases & gotchas

- **No CN 369–370** in `dmu` (Scryfall has 287–368, then 371).
- **Sheoldred, the Apocalypse** has five `dmu` prints (107 base, 290 stained-glass,
  331 textured, 435 concept, 436 concept stepandcompleat) — confirm the CN when adding.
- `dmu` 430 Resolute Reinforcements shares art with `fdn` 145 and `plst DMU-29`.
- `A-` Alchemy rebalances sit inside `dmu` (17) plus `ydmu` (39) — both dropped
  by `_is_digital_only`.
- `dmc` 146 carries the `enchantment` frame effect (nyx frame).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] dmu = ["textured"]` — configured 2026-11-08 (enables `mm query missing-set dmu`).
- `config/families.toml` `[[unobtainable.dmu.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.dmu]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander decks ×2 | Commander deck | Painbow (Jared Carthalion, `dmc` 2) / Legends' Legacy (Dihada, `dmc` 1); etched display commanders `dmc` 49–50 |
| Jumpstart boosters | Jumpstart | fixed decks; front cards in `fdmu` |
| Bundle | Bundle | `dmu` 429 promo |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py dmu --list-boosters` (2026-11-03):

| Booster type | Notes |
|---|---|
| `draft` / `set` | EV ~$5.13 / ~$6.50, 100% coverage |
| `collector` | EV ~$18.85, 91.9% |
| `jumpstart` | EV ~$7.68 — value as decks |
| `prerelease` / `promo` / `promo-foil` | ~$3.96 / ~$8.54 / ~$10.76 |
| `box-topper` | EV ~$0.76 |
| `arena` | digital code card, ignore |
