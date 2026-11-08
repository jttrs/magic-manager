# `akh` — Amonkhet

> Per-family memory doc. Read this before answering set-specific questions about
> `akh` or working on `akh`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `akh`
**Family root type:** `expansion`
**Family released:** 2017-04-28
**Last audit:** 2026-11-05 via `/characterize-set akh` (one-at-a-time run — tier decisions pending owner review).

---

> **Base-frame expansion whose family also holds the Amonkhet Invocations
> (`mp2`)** — 54 borderless foil masterpieces for both Amonkhet and
> [`hou`](hou.md), worth ~$4,265, all rated rarity `special`. That rarity makes
> them invisible to `mm query missing-set` (the same blind spot as
> [`tsr`](tsr.md)'s timeshifts). Also: full-art basics, two Planeswalker Decks.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `akh` | expansion | 287 | 2017-04-28 | parent — booster set 1–269 (full-art basics 250–254), PW-deck cards 270–287 |
| `pakh` | promo | 77 | 2017-04-28 | prerelease `Ns` datestamped (68) + Promo Pack `Np` stamped (4) + game day / buy-a-box / release / resale (5) |
| `mp2` | masterpiece | 54 | 2017-04-28 | Amonkhet Invocations — AKH 1–30, HOU 31–54 (borderless, foil-only, rarity `special`) |
| `takh` | token | 26 | 2017-04-28 | tokens |

`set:akh+related` covers all four. `mp2` is the only family that holds HOU's
Invocations.

---

## 2. Treatments

Survey (`survey_treatment_signature.py AKH`): `regular` except the 5 full-art
basics (`fa`). The Invocations are borderless but carry no `inverted` frame
effect, so they compute `regular` too.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 269 | `akh` 1–269 (116+5 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $125 nonfoil / $292 foil (Anointed Procession 2 ~$59, Throne of the God-Pharaoh 237 ~$7) |
| full-art basics | 5 | `akh` 250–254 | `fa` | **kept by default** — ~$1.60 / $8.90 |
| Planeswalker-deck exclusives | 18 | `akh` 270 Gideon, Martial Paragon + 271–274, 275 Liliana, Death Wielder + 276–279, gain lands 280–287 | `regular` | **unique cards** (walkers + deck mates) — keep; walkers foil-only |
| **Invocations** | 54 | `mp2` 1–54 (Force of Will 14 ~$366, The Scarab God 53 ~$276, Daze 12 ~$230, Pact of Negation 16 ~$207, Omniscience 34 ~$168) | `regular` (borderless, no `inverted`) | **⚠ never listed by missing-set** — rarity `special` matches none of its sub-selectors. ~$4,265 foil; all new art |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 68 prints, auto-dropped (~$460 foil) |
| `promopack` + `stamped` | `regular` | **yes** — `pakh` `Np` = base + stamp | 4 prints, ~$9 nonfoil / ~$18 foil |
| `gameday` | — | **no** — own art | Glorybringer 134, Trueheart Duelist 35 |
| `buyabox` | — | **no** — own art | Archfiend of Ifnir 78 (~$5) |
| `release` + `datestamped` | — | **no** — own art | Oracle's Vault 234 |
| `resale` | — | yes — same art | Curator of Mysteries `49★` |
| `planeswalkerdeck` | — | unique cards | 270–287 |

No fancy-foil sheet → configured `[dupe_foil] akh = []` (2026-11-08) to enable `mm query missing-set akh`.

**Full-art convention:** the 5 basics at 250–254.

---

## 3. Chase variants

The Invocations (`mp2`) are the chase — about 1 in 129 boosters replaced the
foil slot with one (MTGJSON sheet `foilOrMasterpiece1In129`).

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] akh = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pakh` promo-pack stamped `Np` | 4 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$9 |
| `pakh` game day / buy-a-box / release / resale | 5 | **owner's call** — 4 have their own art |
| `mp2` Invocations | 54 | **keep — but a CODE gap, not config:** rarity `special` is never listed by missing-set (see [`tsr`](tsr.md) §5). Owner decision on a `special` sub-selector |
| PW-deck 270–287 | 18 | keep — real cards |

**Scarcity check:** not run yet (written before `[dupe_foil]` was added).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pakh` | prerelease, datestamped (foil) | — |
| `Np` | `pakh` | Promo Pack, stamped | Aven Mindcensor `5p` |
| `35`, `134` | `pakh` | Game Day (alt art) | Glorybringer 134 |
| `78` | `pakh` | Buy-a-Box (alt art) | Archfiend of Ifnir |
| `234` | `pakh` | Release (alt art, datestamped) | Oracle's Vault |
| `49★` | `pakh` | resale | Curator of Mysteries |
| `1`–`30` | `mp2` | Invocations (AKH boosters) | Force of Will 14 |
| `31`–`54` | `mp2` | Invocations (HOU boosters) | The Scarab God 53 |
| `270`–`287` | `akh` | Planeswalker Decks | Liliana, Death Wielder 275 |

---

## 7. Edge cases & gotchas

- **`mp2` covers two sets.** Scryfall dates all 54 Invocations 2017-04-28,
  though 31–54 shipped in HOU boosters months later.
- **Rarity `special`** on `mp2` hides it from missing-set; Collection still
  shows it.
- **Borderless without `inverted` computes `regular`** — the recurring gap
  (`eld`, `med`, `cmr`, …); a `b` rule won't touch the Invocations.
- **280–287 are eight common gain lands** (Cinder Barrens, Woodland Stream, …)
  tagged `planeswalkerdeck`, past the two decks' own 270–279.
- Oracle's Vault 234 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] akh = []` — configured 2026-11-08 (enables `mm query missing-set akh`).
- `config/families.toml` `[[unobtainable.akh.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.akh]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | foil slot can be an Invocation (`mp2` 1–30) |
| Planeswalker Decks ×2 | Planeswalker deck | Gideon / Liliana; cards at 270–287 |
| Booster Battle Pack | two-player pack | — |
| Deck Builder's Toolkit / Land Station | kit | many 2-colour toolkit decklists in MTGJSON |
| Bundle | Bundle | Bundle Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py akh --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$5.40, 97.6% coverage |
| `prerelease` / `showdown` | ~$5.73 / ~$4.04 |
