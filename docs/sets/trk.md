# `trk` — `Star Trek`

> Per-family memory doc. Read this before answering set-specific questions about
> `trk` or working on `trk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `trk`
**Family root type:** `expansion` (Universes Beyond, `parent_set_code: null`)
**Family released:** 2026-11-13 (all 7 codes)
**Last audit:** 2026-11-02 via `/characterize-set trk` (non-interactive batch run).

---

> **Pre-release snapshot.** Audited 11 days before release: almost every print
> is unpriced, MTGJSON has the set file but **no booster data and no decklists**
> yet, and there are CN gaps (trk 327–331; trc 131, 134–136, 143–144, 149–150,
> 154–160, 164, 167, 169–171, 174, 176, 178–179, 578, 581) still to be filled by
> Scryfall. Re-run `/characterize-set trk` after release (prices, decks,
> boosters, any `ptrk` promo set) and refresh §3/§5/§9.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `trk` | expansion | 581 | 2026-11-13 | parent — base 1–326, boosterfun 332–579, headliners 1701–1706 |
| `trc` | commander | 556 | 2026-11-13 | Star Trek Commander (4 face commanders trc 1–4) |
| `sds` | masterpiece | 30 | 2026-11-13 | **Stardates** — borderless reprint masterpiece sheet (all mythic) |
| `ttrk` | token | 27 | 2026-11-13 | set tokens |
| `ttrc` | token | 14 | 2026-11-13 | commander tokens (8–14 surgefoil) |
| `atrk` | memorabilia | 54 | 2026-11-13 | Art Series |
| `atrc` | memorabilia | 12 | 2026-11-13 | Commander Art Series |

**Separately-rooted bonus sheets:** none. Scryfall `/sets` 2026-10-01 → 2026-12-31
shows only these 7 codes linked to `trk`/`trc`; no `ptrk` promo set exists yet.
Off-family Star Trek promos live in generic promo sets (see §6).

No `--only` needed: `mm set master-list trk` resolves the whole family.

---

## 2. Treatments

Survey (`survey_treatment_signature.py TRK`, 1,274 prints). Umbrella token
`universesbeyond` on 1,168; real structure is in `frame_effects`/`finishes`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 306 | `trk` 1–306 | `regular` | rarity/base sub-selectors |
| full-art basics | 10 | `trk` 307–316 (2 arts × 5) | `fa` | kept (commons; not in rare/mythic selectors) |
| regular basics | 10 | `trk` 317–326 | `regular` | base |
| borderless (inverted) | 31 | `trk` 332–362 (Odo, Quark, Jadzia Dax, Quark's Bar, Starfleet Academy, …) | `b` | **kept (default) — pending owner review** |
| showcase, black border | 73 | `trk` 363–391, 402–435 | `shw` | **kept (default) — pending owner review** (see note) |
| showcase full-art shocklands | 10 | `trk` 392–401 | `shw` (fa suppressed) | **kept (default) — pending owner review** |
| **Klingon-language showcase foils** | 10 | `trk` 436–445 (`lang: tlh`, foil-only) | `shw` | **kept (default) — pending owner review**; recommended exclude (see §5) |
| extended-art | 36 | `trk` 446–481 | `ext` | auto-dropped (ext class) |
| surgefoil dupes | 89 | `trk` 482–486 (fa basics), 487–496 (showcase shocks), 497–549 (showcase), 559–579 (basics + commons/uncommons) | `fa\|ff` / `shw\|ff` / `ff` | dupe-foil collapse once `trk = ["surgefoil"]` (verified: every one shares `illustration_id` with a non-surge sibling) |
| poster / bundle showcase | 8 | `trk` 550–557 (starships: Enterprise-A/D, Bounty, Reliant, D-7, Discovery, Borg Cube, DS9), borderless, foil-only | `shw` | **kept (default) — pending owner review** |
| bundle promo | 1 | `trk` 558 Dr. Leonard "Bones" McCoy, black border, foil-only, distinct art | `regular` | lands in rare-regular |
| headliner | 7 | `trk` 1701, 1701D, 1702–1706 (Kirk, Picard, Spock, Data, Janeway, Seven, La Forge), borderless, foil-only, distinct art | `fa` (1701, 1704) / empty (others) | **kept (default)** — the 5 empty-treatment ones leak into mythic-regular; recommended exclude (§5) |
| `trc` face commanders, borderless | 4 | `trc` 1–4 | `b` | kept |
| `trc` face commanders, surgefoil | 4 | `trc` 5–8 (same art as 1–4, foil-only) | `b\|ff` | dupe-foil collapse |
| `trc` deck cards (nonfoil + surgefoil foil) | 282 | `trc` 9–130, 418–577 | nonfoil `regular` / foil `ff` | finish-aware: nonfoil row kept, surgefoil foil collapses |
| `trc` borderless characters | 22 | `trc` 180–191, 202–211 | `b` | **kept (default) — pending owner review** |
| `trc` nonfoil-only | 38 | `trc` 132–177, 192–201, 579–582 | `regular` | base |
| `trc` extended-art | 206 | `trc` 212–417 (nonfoil-only) | `ext` | auto-dropped |
| `sds` Stardates masterpieces | 30 | `sds` 1–30 (borderless inverted, all mythic) | `b` | **kept (default) — pending owner review** |
| Art Series / tokens | 54+12 / 27+14 | `atrk`, `atrc`, `ttrk`, `ttrc` | `regular` / `ff` | memorabilia off by default; tokens hard-excluded from missing-set |

Showcase note: the black-bordered showcase spans sub-themes by CN —
363–391 TNG/DS9/Voyager-era characters, 392–401 shocklands, 402–425 TOS/films
(Kirk, Spock, Khan, Genesis Device), 426–435 Klingon. Scryfall does not name the
frames; verify visually before deciding keep/exclude. 20 of the 83 showcase
prints share art with each other only because 426–435 ↔ 436–445 are the
English/Klingon twins.

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `surgefoil` | `ff` | **yes** — all 381 share art with a non-surge sibling (trk 89, trc 286, ttrc 6) | propose `[dupe_foil] trk = ["surgefoil"]`; keys line up (fa↔fa, shw↔shw, b↔b, ''↔''), simulated: all trk/trc surge prints drop |
| `headliner` | — (not ff) | no — distinct art | 7 prints, see §5 |
| `poster` + `bundle` | — | no — distinct art | 8 starship showcase prints 550–557 |
| `bundle` (alone) | — | no — distinct art | 558 Bones McCoy |

**Full-art convention:** `full_art = 1` on trk 307–316, 392–401, 482–496,
1701, 1704; `false` elsewhere.

---

## 3. Chase variants

No true chase. `mm query show 'set:trk+related chase'` returns only:

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| General Chang, Cold Warrior | 3 | `trk` 415, 427, 437 | rare | shw (437 = Klingon-language twin of 427) |
| Worf, Honor-Bound Warrior | 3 | `trk` 390, 435, 445 | uncommon | shw (445 = Klingon twin of 435) |
| Klingon Warrior / Officer tokens | 3 / 10 | `ttrk` 3–5 / 6–15 | token | regular (tokens never in missing-set) |

`missing rarity=uncommon treatment=regular chase` → 0 rows.

---

## 4. Scenes / posters / panoramas

None detected. The 31 borderless-inverted `trk` prints (332–362) are not
contiguous same-artist runs worth grouping; the 8 `poster`-tagged prints
(550–557) are individual starship showcase cards (bundle), not a multi-card
panorama. Re-check after release if Scryfall groups any as "Scene Cards".

---

## 5. Unobtainable rules

None configured. Kept-by-default tiers awaiting an owner keep/exclude decision
(all "kept (default) — pending owner review"):

| Tier | Prints | Recommendation |
|---|---:|---|
| headliner (trk 1701–1706, borderless foil-only) | 7 | exclude — analog of TLA/TMT/MSH/HOB headliner rules; 5 compute to empty treatment and leak into mythic-regular. Proposed `promo_types_any_of = ["headliner"]` |
| Klingon-language showcase foils (trk 436–445) | 10 | exclude — same art as 426–435, only the language differs (precedent: ONE Phyrexian step-and-compleat). No distinguishing promo_type → proposed `collector_numbers` 436–445 + `frame_effects_all_of = ["showcase"]` (frame clause needed: `trc` also has CNs 436–445) |
| poster/bundle starship showcase (trk 550–557) | 8 | unsure — bundle-exclusive distinct art (LTR's `poster` tier was excluded, but those were sealed poster inserts) |
| black-bordered showcase (trk 363–435) | 73 | keep — the set's main boosterfun frame (not the D&D rulebook frame) |
| borderless (trk 332–362, trc 1–4/180–191/202–211) | 57 | keep — ordinary borderless treatment |
| `sds` Stardates masterpieces | 30 | keep — masterpiece sheet (Sheoldred, the Apocalypse $199.99 is the only priced high card so far) |

**Scarcity check:** `set_status.py trk` prints no ⚠ concentration note (family
not configured → missing $ not computed; nearly all prints unpriced pre-release).
Re-run after release.

**Missing-set baseline (2026-11-02):** 0 owned; `mm query missing-set trk`
refuses (no `[dupe_foil]` entry). Simulated with `trk = ["surgefoil"]`:
`preferred` = 190 rows (73 trk shw + 31 trk b + 30 sds + 26 trc b + 10 fa basics
+ 10 Klingon + 8 poster + 2 headliner), rare-regular 293, mythic-regular 48
(incl. 5 headliners).

---

## 6. PRM destinations

No `ptrk` set yet. Star Trek promos found elsewhere (all `universesbeyond`):

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `2026-22`…`2026-24` | `pmei` | Media insert (same art as trc nonfoil-only prints) | Picard, Steadfast Captain → `pmei` 2026-22 (= trc 193); Spock, Logical Choice 2026-23 (= trc 194); Benjamin Sisko, Besieged 2026-24 (= trc 200) |
| `2026-2` | `purl` | Convention promo (foil, ext-art, 2026-07-23) | Kirk, Enterprising Captain → `purl` 2026-2 (same art as trc 198) |
| `14` | `pspl` | Spotlight Series (ext-art, released 2027-01-09) | Jean-Luc Picard, Luminary → `pspl` 14 (distinct art from trc 3/7) |

---

## 7. Edge cases & gotchas

- **Klingon-language cards** (trk 436–445, `lang: tlh`) are stored as separate
  printings with English names — same name/art as 426–435. When adding by
  name, confirm language.
- **Headliner CNs are non-numeric/large** (`1701`, `1701D`, `1702`…`1706` —
  starship registry numbers). `1701D` sorts between 1701 and 1702.
- **Surgefoil shares CN with nonfoil in `trc`** (9–130, 418–577 are
  `[nonfoil, foil]` + `surgefoil`): the foil finish IS the surgefoil; there is no
  plain-foil version.
- **trc nonfoil-only band 132–177** (25 commons/uncommons, e.g. Head of
  Security, Kolinahr Priest) and 192–201 (rares/mythics incl. pmei twins) —
  product unknown pre-release; check MTGJSON decks after release.
- Same-name pairs across bands: e.g. Captain Jean-Luc Picard trk 7 / 363 /
  497 / 1701D; The Unicomplex 304 / 337; Vulcan 305 / 579 (surge).
- No arena/digital-only leaks (`mm query show 'set:trk+related missing' | grep -ci arena` → 0).
- No serialized, meld, or etched prints.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.trk.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.trk]]` — none (no scenes).

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Star Trek Commander decks | Commander deck | 4 face commanders: The Borg Queen, Commander Spock, Jean-Luc Picard, Luminary, Worf, Defiant Commander (trc 1–4; surgefoil twins 5–8). MTGJSON has no decklists yet (`mm mtgjson decks --set trc` empty). |
| Bundle | Bundle | bundle-tagged promos trk 550–558 (8 poster starships + Bones McCoy 558) |
| Stardates | masterpiece sheet | `sds` 1–30, borderless reprints |

**Booster types (for `sealed-value` EV):** none yet — `sealed_value.py trk
--list-boosters` → "no booster data in MTGJSON" (pre-release). Re-run after
release.
