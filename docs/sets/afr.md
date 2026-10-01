# `AFR` — Adventures in the Forgotten Realms

> Per-family memory doc. Read this before answering set-specific questions about
> `AFR` or working on `AFR`-related commands. When new peculiarities
> emerge in chat, update the appropriate section here so the knowledge outlives
> the session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `afr`
**Family root type:** `expansion`
**Family released:** `2021-07-23` (standard Standard-legal premier set; the first full D&D crossover)
**Last audit:** `2026-09-30` via `/characterize-set afr`.

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `afr` | expansion | 402 | 2021-07-23 | parent. CN 1-281 base, 282-395 boosterfun, 396-402 promos (buyabox/bundle/promopack) |
| `pafr` | promo | 241 | 2021-07-23 | prerelease (`Ns`), promo-pack (`Np`), promo-stamp/instore (`Na`); see §6 |
| `afc` | commander | 331 | 2021-07-23 | Forgotten Realms Commander — 4 preconstructed decks (see §9) |
| `aafr` | memorabilia | 81 | 2021-07-23 | Art Series (double-faced art cards, not real singles) |
| `oafc` | memorabilia | 4 | 2021-07-23 | Commander Display Commanders — oversized `thick` display cards (Galea / Prosper / Sefris / Vrondiss) |
| `oafr` | memorabilia | 3 | 2021-07-23 | Oversized Dungeon cards (Dungeon of the Mad Mage / Lost Mine of Phandelver / Tomb of Annihilation) |
| `tafr` | token | 22 | 2021-07-23 | main-set tokens |
| `tafc` | token | 13 | 2021-07-23 | commander tokens |
| `mafr` | minigame | 5 | 2021-07-23 | the 5 "minigame" insert cards (Booster Blitz, Mimic Match, Roll for Initiative, …) — novelty, not real singles |

**Separately-rooted bonus sheets:** none. AFR predates the UB separately-rooted-bonus-sheet pattern (`mar`/`spm`); every related code carries a proper `parent_set_code → afr`. `mm set list-related afr` resolves all 9 codes with no manual `--only`.

**`mm` invocations that need `--only`:** none — the standard `set:afr+related` resolution is complete.

---

## 2. Treatments

AFR is a **2021 pre-fancy-foil-era set**: there are NO named fancy-foil-sheet
tokens (no `surgefoil` / `etched` / `manafoil` / `fracturefoil` / `gilded` /
`raisedfoil`). The ONLY treatment token in the family is `boosterfun`, which
marks genuinely **distinct frames**, not a same-art foil overlay. Premium
foils in AFR are just the ordinary foil finish of these same distinct-art
prints — there is no second "fancy sheet" print to dedup against.

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` (borderless, no frame_effect) | `b` | **no — distinct art** | 5 borderless planeswalkers (CN 282-286: Grand Master of Flowers, Mordenkainen, Lolth, Zariel, Ellywick) |
| `boosterfun` + `inverted` | `b` | **no — distinct art** | 11 borderless D&D monsters/dragons (CN 287-298: Tiamat, Old Gnawbone, the mono-color Dragons, Ebondeath, …) |
| `boosterfun` + `showcase` | `shw` | **no — distinct art** | 60 "module/rulebook showcase" frame prints (CN 299-358) — the D&D parchment-panel frame; distinct showcase art |
| `boosterfun` + `extendedart` | `ext` | **no — distinct art** | 37 extended-art mythics/rares (CN 359-395) |
| `prerelease` + `datestamped` | (promo) | yes — stamped reprint of base art | `pafr Ns`; same art as base, date stamp only (filtered as a promo, not a distinct print) |
| `embossed` + `instore` | (promo) | yes — stamped reprint | `pafr Na`; "promo stamp" art, same base art |
| `promopack` + `stamped` | (promo) | yes — stamped reprint | `pafr Np`; promo-pack stamp, same base art |
| `promopack` (afr 398-402) | (promo) | yes | the 5 Promo Pack cards in the parent set — `inverted`-frame, same art |
| `buyabox` (afr 396) | (promo) | — | Vorpal Sword buy-a-box |
| `bundle` (afr 397) | (promo) | — | Treasure Chest bundle promo |
| `rebalanced` + `alchemy` (`A-` CNs) | — | — | 22 Arena Alchemy rebalances — digital-only, filtered globally by `UNOBTAINABLE_PROMO_TYPES` |

**Full-art convention:** `full_art` is FALSE across the family (the borderless
prints are `border_color: borderless` but `full_art: false`, the normal
modern-borderless convention). No full-art basics beyond the showcase lands.

**No `FAMILY_DUPE_FOIL_PROMO_TYPES` dupe signal.** AFR mirrors the
TLA/SPM/SOS/MAT/NEO/BLB "empty frozenset" pattern: there is nothing to dedup,
but `treatment=preferred` / `mm query missing-set` refuse to run until the
anchor is present in the config. Proposed entry is an **empty frozenset** (see
§8). The `pafr` stamped promos (datestamped/embossed/promopack) are not distinct
art and are already dropped as promos by the treatment filter — they do not need
a dupe-foil rule.

---

## 3. Chase variants

`chase:5` returns 0 rows — no AFR card has ≥5 distinct-art printings. The
default `chase` (threshold 3) matches broadly because the base + borderless +
foil combinations push many prints over 3, but these are the ordinary
boosterfun variants catalogued in §2, not a special chase tier. There is no
`uncommon-chase`-only phenomenon in AFR worth pinning.

The genuine high-value distinct-art prints (all boosterfun, all KEPT in
missing-set) are the borderless dragons/PWs:

| Card name | Count | CN | Rarity | Treatment |
|---|---:|---|---|---|
| `Old Gnawbone` | borderless | `afr` 296 | mythic | `b` (boosterfun+inverted) — ~$68, top missing-$ card |
| `Tiamat` | borderless | `afr` 298 | mythic | `b` — ~$40 |
| `Xorn` | module-showcase | `afr` 322 | rare | `shw` — ~$10 |
| `Ebondeath, Dracolich` / `Iymrith` / `Inferno of the Star Mounts` | borderless | `afr` 287-293 | mythic | `b` — $3-5 |

---

## 4. Scenes / posters / panoramas

**None.** AFR has NO scene/poster/panorama groupings. The 16 `border:borderless`
prints (CN 282-298) are individual planeswalkers (5) and D&D monsters/dragons
(11) — each a standalone card by a different artist, NOT an artist-contiguous
scene run. `is:poster` returns 0 in the family. No `FAMILY_SCENES["afr"]` entry
is warranted, and `scripts/scene_table.py afr` would be empty.

---

## 5. Unobtainable rules

**None proposed.** `scripts/set_status.py afr` did NOT fire a concentration ⚠
(it stopped at the "not configured" gate). Inspecting the missing picture via
the `treatment=collectible-alt` bypass (`set:afr+related missing
treatment=collectible-alt`, 77 rows), the top of the list is Old Gnawbone
(~$68) and Tiamat (~$40) — genuine distinct-art borderless chases the user
WOULD want, not a scarcity-junk tier. There is no stamped-promo-only or
fancy-foil-sheet tier dominating the missing $ (the `pafr` stamped promos are
already dropped as promos). No `FAMILY_UNOBTAINABLE_RULES["afr"]` entry.

| Rule | Rationale |
|---|---|
| (none) | No scarcity tier the user has ruled out; the costly prints are wanted distinct-art borderless mythics. |

---

## 6. PRM destinations

AFR's promo channels all live in `pafr`, keyed by the CN **letter suffix** on a
base-set collector number N:

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` (e.g. `87s`) | `pafr` | Prerelease, datestamped | Acererak 87s → `pafr` 87s (`prerelease,datestamped`) |
| `Na` (e.g. `87a`) | `pafr` | Promo stamp / in-store | Acererak 87a → `pafr` 87a (`embossed,instore`) |
| `Np` (e.g. `87p`) | `pafr` | Promo Pack, stamped | Acererak 87p → `pafr` 87p (`promopack,stamped`) |
| 396-402 (no suffix) | `afr` | buy-a-box / bundle / promo-pack in the PARENT set | Vorpal Sword 396 (buyabox), Treasure Chest 397 (bundle), Magic Missile 401 (promopack) |

The three stamped twins (`s`/`a`/`p`) share the base art — resolve a loose
PRM-stamped AFR promo by name + which stamp it carries, then read the matching
`pafr` CN suffix. There is NO `pw21`/WPN-play-promo or regional (`rafr`) channel
in this family. The buy-a-box card was **Vorpal Sword** (there is no "Ampersand"
promo card — the D&D ampersand `&` is the set's watermark/expansion symbol, not a
printed card).

`bulk-add` SKILL.md has no AFR-specific prose yet; the standard letter-suffix
resolution above covers it.

---

## 7. Edge cases & gotchas

- **Alchemy `A-` prints** (22, `rebalanced,alchemy`, e.g. `A-Acererak the
  Archlich`): digital-only Arena rebalances, filtered globally by
  `UNOBTAINABLE_PROMO_TYPES`. `set:afr+related missing | grep arena` → 0 rows
  (no leak). The AFR Alchemy cards carry `rebalanced` so the stamp-based
  `_is_digital_only` path isn't even needed.
- **Minigame cards (`mafr`, 5)**: novelty inserts (Booster Blitz, Mimic Match,
  Roll for Initiative, Totally Lost in Translation, Magic and Minions) — not
  real singles; `set_type: minigame`.
- **Oversized Dungeons (`oafr`, 3)** and **Display Commanders (`oafc`, 4,
  `thick`)**: memorabilia, not tradeable singles.
- **Art Series (`aafr`, 81)**: double-faced art cards (`Name // Name`),
  memorabilia.
- **Dungeon cards**: the three Dungeon cards (Lost Mine of Phandelver, Dungeon
  of the Mad Mage, Tomb of Annihilation) exist as normal `afr` cards AND as
  `oafr` oversized memorabilia — the oversized versions are the collision, not
  real product.
- **`afc` extended-art**: the commander set has 30 `extendedart` prints (CN
  283+) but NO `boosterfun`/showcase — standard commander-deck alt treatment.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["afr"]` — **configured: empty `frozenset()`** (applied 2026-09-30; no dupe-foil signal; unblocks `treatment=preferred`, mirrors TLA/SPM/SOS/MAT/NEO/BLB/INR).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["afr"]` — not configured, and none needed (§5).
- `selectors.FAMILY_SCENES["afr"]` — not configured; no scenes exist (§4).
- Related test data: none.

---

## 9. Product types

Archetype definitions (Scene Box, Beginner Box, Jumpstart, Commander/Welcome/other
constructed decks, Art Series, masterpiece sheet, Bundle/Buy-a-Box, Secret Lair,
Collector's Edition) live in [`../product-types.md`](../product-types.md).
Family specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Forgotten Realms Commander decks | Commander deck | 4 decks (`afc`): Aura of Courage, Draconic Rage, Dungeons of Death, Planar Portal; MTGJSON `type: Commander Deck`, display commanders in `oafc` |
| AFR Bundle / Gift Bundle | Bundle/Buy-a-Box | Treasure Chest (afr 397) is the bundle promo |
| Vorpal Sword buy-a-box | Buy-a-Box | afr 396, `buyabox` |
| 2021 Arena Starter Kit | Starter Kit | per MTGJSON sealedProduct |
| Art Series (`aafr`, 81) | Art Series | not real singles |

**Booster types (for `sealed-value` EV).** All 11 types have 100% EV coverage
(family fully synced). AFR is a draftable Standard set with the classic
Draft/Set/Collector booster lineup PLUS color-themed Theme Boosters and the
D&D "Dungeons" theme booster:

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `draft` | standard draft booster, EV ~$6.24 (2 layouts) |
| `set` | set booster, EV ~$7.22 (24 layouts) |
| `collector` | collector booster, EV ~$21.10 (highest-value pack) |
| `prerelease` | prerelease pack, EV ~$5.19 — includes the `pafr` datestamped promo |
| `arena` | 2021 Arena Starter Kit pack, EV ~$5.76 |
| `theme-w` / `theme-u` / `theme-b` / `theme-r` / `theme-g` | the 5 mono-color Theme Boosters (EV ~$9-14) |
| `theme-dungeons` | the D&D-flavored "Dungeons" theme booster, EV ~$8.36 — AFR-unique product line |
