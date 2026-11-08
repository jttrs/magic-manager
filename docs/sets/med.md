# `med` — Mythic Edition

> Per-family memory doc. Read this before answering set-specific questions about
> `med` or working on `med`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `med`
**Family root type:** `masterpiece`
**Family released:** 2018-10-05 (three releases through 2019-05-03)
**Last audit:** 2026-11-05 via `/characterize-set med` (one-at-a-time run — tier decisions pending owner review).

---

> **24 borderless foil planeswalker reprints with new art**, sold in three
> premium "Mythic Edition" boxes alongside Guilds of Ravnica, Ravnica Allegiance
> and War of the Spark. One Scryfall set holds all three runs; the CN prefix
> says which. Standalone root, so not reached by `set:grn/rna/war+related`.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `med` | masterpiece | 24 | 2018-10-05 / 2019-01-25 / 2019-05-03 | `GR1`–`GR8` (GRN Mythic Edition), `RA1`–`RA8` (RNA), `WS1`–`WS8` (WAR) |
| `tmed` | token | 16 | — | tokens and emblems, CNs prefixed `W`/`R`/`G` (Dack Fayden Emblem R2, …) |

`set:med+related` covers both. `masterpiece` is a default inventory set type.

---

## 2. Treatments

Survey (`survey_treatment_signature.py MED`, 40 print-rows): all `regular`
(24 foil, 16 nonfoil tokens). No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| GRN Mythic Edition | 8 | `med` GR1–GR8 (Elspeth, Knight-Errant GR1 ~$51, Teferi GR6 ~$58, Vraska GR8 ~$35) | `regular` (borderless without `inverted` — the recurring gap, see [`eld`](eld.md) §7) | mythic-regular — ~$225 foil |
| RNA Mythic Edition | 8 | `med` RA1–RA8 (Tamiyo RA2 ~$38, Sorin Markov RA3 ~$33) | `regular` | mythic-regular — ~$154 foil |
| WAR Mythic Edition | 8 | `med` WS1–WS8 (Nicol Bolas, Dragon-God WS6 ~$94, Tezzeret the Seeker WS4 ~$63, Jace, the Mind Sculptor WS3 ~$60, Ugin WS1 ~$53, Sarkhan Unbroken WS8 ~$48) | `regular` | mythic-regular — ~$348 foil |
| tokens / emblems | 16 | `tmed` | `regular` | tokens |

All 24 are foil-only, borderless, mythic, with art found nowhere else (0 of 24
share an illustration with another set).

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] med = []` to enable `mm query missing-set med` (≈ $727 foil for all
24).

---

## 3. Chase variants

The whole set is a chase sheet; WAR's WS run is the most valuable.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] med = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| whole family | 24 | keep — distinct art, a real collectible run; owner may prefer to track it per release (`cn` prefix) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `GR1`–`GR8` | `med` | Guilds of Ravnica Mythic Edition | Elspeth, Knight-Errant GR1 |
| `RA1`–`RA8` | `med` | Ravnica Allegiance Mythic Edition | Tamiyo, the Moon Sage RA2 |
| `WS1`–`WS8` | `med` | War of the Spark Mythic Edition | Nicol Bolas, Dragon-God WS6 |

---

## 7. Edge cases & gotchas

- **One set code, three release dates.** `released_at` differs per block
  (GR 2018-10-05, RA 2019-01-25, WS 2019-05-03). Don't take the set's
  2018 date for every card.
- **Letter-prefixed CNs** sort as 0 under a numeric cast — select a block by
  string prefix, not `cn>=`.
- **Borderless without `inverted` computes `regular`**, so a `b`-keyed rule
  won't match these.
- **MTGJSON files the decklists under the parent sets**, not `med`:
  `GuildsOfRavnicaMythicEdition_GRN`, `RavnicaAllegianceMythicEdition_RNA`,
  `WarOfTheSparkMythicEdition_WAR` (`type: Box Set`, which is in
  `PRECON_MODERN_TYPES`, so they show up in `mm set precon-list`). Each sealed
  product (`premium`) bundles the 8-walker deck with 24 boosters of the parent
  set (per MTGJSON's WAR entry).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] med = []` — configured 2026-11-08 (enables `mm query missing-set med`).
- `config/families.toml` `[[unobtainable.med.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.med]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Guilds of Ravnica / Ravnica Allegiance / War of the Spark Mythic Edition | premium box (MTGJSON `sealedProduct` `premium`; decklist `type: Box Set` under `grn`/`rna`/`war`) | 8 walkers each + boosters of the parent set |

**Booster types (for `sealed-value` EV):** none for `med` itself; the
Mythic Edition sealed products are valued under their parent set codes.
