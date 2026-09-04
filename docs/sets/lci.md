# `lci` — The Lost Caverns of Ixalan

> Per-family memory doc. Read this before answering set-specific questions about
> `lci` or working on `lci`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `lci`
**Family root type:** `expansion`
**Family released:** `2023-11-17` (main wave); `rex` (Jurassic World Collection) same window
**Last audit:** `2026-09-03` via `/characterize-set lci`.

---

## 1. Family map

10 Scryfall codes, all linked via `parent_set_code` (clean graph — no
separately-rooted bonus sheets, unlike SPM/`mar`).

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `lci` | expansion | 416 | 2023-11-17 | parent |
| `lcc` | commander | 370 | 2023-11-17 | 4 Commander decks + `boxtopper` box-toppers (LCC 101-120, borderless inverted) |
| `plci` | promo | 136 | 2023-11-17 | promos: promo-pack `stamped` (`Np`) + prerelease `datestamped` (`Ns`) |
| `rex` | eternal | 45 | 2023-11-17 | **Jurassic World Collection** — the UB crossover "Eternal" bonus product; `universesbeyond`, base `boosterfun` + `embossed` fancy-foil twins |
| `alci` | memorabilia | 81 | 2023-11-17 | Art Series |
| `ylci` | alchemy | 31 | — | Alchemy: Ixalan (digital-only) |
| `tlci` | token | 19 | 2023-11-17 | tokens |
| `tlcc` | token | 18 | 2023-11-17 | commander tokens |
| `trex` | token | 2 | 2023-11-17 | Jurassic World tokens |
| `slci` | token | 1 | 2023-11-17 | substitute/emblem card |

`mm set master-list lci` / `set:lci+related` resolve the whole family from the
parent — no `--only` gymnastics needed.

**Sync note:** `mm set sync lci` pulls only the parent. For a full audit /
missing-set, sync the value-bearing children: `lcc plci rex` (tokens/alchemy add
nothing to missing-set). 786 family prints after syncing.

---

## 2. Treatments

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b` / `shw` / `ext` (frame-dependent) | n/a (structural) | showcase/borderless/extended frames; KEPT |
| `embossed` | `b\|ff` | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | rex 27-45 — the Jurassic World "embossed" collector-foil sheet over the `boosterfun` art. All 19 pair cleanly with a same-illustration `boosterfun` base sibling (Blue 33↔8, Compy Swarm 34↔9, etc.). Computes to `b\|ff`, base sibling to `b`, so the codes-minus-ff key `{b}` matches → sibling dedup drops the embossed. KEPT sibling: the `boosterfun` print |
| `neonink` | `b\|ff` | **no — distinct art, routed to UNOBTAINABLE** | LCI 410a-f — 6 serialized neon-ink Cavern of Souls colorways (foil-only, $74-$4,900 each, ~$7,200 total). Distinct art, not a dupe of the boosterfun showcase (LCI 345) or base (LCI 269). The user won't chase this tier → excluded via `any_of:{neonink}` |
| `boxtopper` | `b` | **no — distinct borderless art, KEPT** | LCC 101-120 — Commander box-topper borderless inverted prints. Distinct showcase art (Arcane Signet box-topper 104 vs base 299), a normal collectible tier the user shops for |
| `stamped` (+`promopack`) | (frame of base) | scarcity variant → dropped by GLOBAL filter | plci `Np` promo-pack stamps. Same card + a stamp; every one has a non-stamped base/showcase sibling in the family, so the global `_filter_treatment_preferred` Step 2 drops them. **No per-family `stamped` rule needed** (verified: 0 promopack-without-stamped trap prints in plci, unlike SNC/EOE) |
| `datestamped` + `prerelease` | (frame of base) | dropped by GLOBAL filter | plci `Ns` prerelease prints; all have a non-stamped sibling → dropped by the global preferred filter. No per-family rule |
| `neonink` + `wizardsplaynetwork` | `b\|ff` | (see neonink) | LCI 410b is the one neonink also carrying `wizardsplaynetwork`; still caught by the `neonink` rule |

**Full-art convention:** standard (borderless/showcase carry `border_color:
borderless` or `frame_effects: showcase`/`inverted`; `full_art` not relied upon).

**No `serialized`/`headliner` ultra-rare** in the *core* set — the neonink
Caverns are the family's headline chase (some serialized), handled via §5.

---

## 3. Chase variants

The bare `chase` modifier surfaces only **Cavern of Souls** (LCI 410a-f, 6
distinct neon-ink colorways). This is the neonink premium tier, not a
multi-art-per-name booster chase — it's excluded from missing-set via §5, so it
won't appear in buy lists. No other card has ≥3 distinct-art prints at the same
`(name, treatment)` in the family.

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Cavern of Souls | 6 | `lci` 410a-f | mythic | `b\|ff` (neonink; §5-excluded) |

---

## 4. Scenes / posters / panoramas

**One borderless scene detected** — the LCI dinosaur showcase run, all by a
single artist (Sidharth Chaturvedi), borderless-inverted, contiguous CN:

| Scene / poster | CN range | Cards | Detection |
|---|---|---:|---|
| Dinosaur showcase (Sidharth Chaturvedi) | `lci` 320-332 | 13 | borderless-inverted + single-artist contiguous run |

LCI 333-351 continue the borderless block but are a mixed-artist set of
individual borderless legends/lands (Get Lost, the Restless lands, the Ojer
gods, etc.) — NOT a single-artist scene. Not encoded in `FAMILY_SCENES` (a
13-card single-scene family doesn't need the per-scene completion table the way
LTR's multi-scene poster set does); revisit if the user wants `scene_table.py`
coverage.

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["lci"]` in `src/magic_manager/selectors.py`.

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {neonink}` | The 6 serialized neon-ink Cavern of Souls (LCI 410a-f), foil-only, $74-$4,900 each (~$7,200 total). DISTINCT art (so the dupe-foil filter would KEEP them) but a chase tier the user does not shop for. Direct analog of TLA/NEO neonink. `any_of` catches exactly these 6 prints |

**No `stamped` rule** — unlike SNC/EOE/ECL/SOS/BLB/FDN/MAT, every plci
promo-pack/prerelease stamp has a non-stamped sibling in the family graph, so
the GLOBAL preferred filter already drops them; a per-family rule would be
redundant. (Verified: 0 promopack-without-stamped alt-art trap prints in plci.)

**Missing-set impact (recorded 2026-09-03):** with the DUPE_FOIL `{embossed}`
+ UNOBTAINABLE `{neonink}` config, `missing-set lci` goes from **425 prints /
~$18,258** (empty config) to **400 prints / ~$1,888**. The ~$16,400 drop is the
6 neonink Caverns (~$7,200) + the 19 embossed rex dupe foils (high foil prices).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` (e.g. `269p`) | `plci` | Promo-pack `stamped` | Cavern of Souls 269p → `plci` 269p |
| `Ns` (e.g. `269s`) | `plci` | Prerelease `datestamped` | Cavern of Souls 269s → `plci` 269s |

`plci` mirrors the main-set CN in both the `Np` and `Ns` variants (269 base →
269p promo-pack / 269s prerelease). No `pw25`/special-insert channel observed
for this family (2023 release predates the current WPN Play Promo scheme's
family linkage). Resolve any PRM-stamped card by name+CN off `plci`.

---

## 7. Edge cases & gotchas

- **`rex` (Jurassic World Collection)** is a `set_type: eternal` UB crossover
  bonus product filed under LCI (like TMT's `tmc`). Its cards are all
  `universesbeyond`; the `embossed` foils are same-art dupes of the `boosterfun`
  base (§2). Its 2 tokens live in `trex`.
- **No arena-stamp leak** — `set:lci+related missing | grep arena` returns
  nothing; `ylci` alchemy prints are correctly filtered globally.
- **`boxtopper` (LCC 101-120)** is a legit collectible borderless tier (KEPT),
  not a dupe — don't confuse with the embossed/neonink fancy foils.
- Meld/DFC: the Ojer gods (LCI 314/317, `//` transform lands) and Huatli/Kellan
  DFCs are normal transform cards, no meld-back-only CNs.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["lci"]` — **configured**: `frozenset({"embossed"})` (rex Jurassic World collector foils).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["lci"]` — **configured**: `[{"promo_types_any_of": frozenset({"neonink"})}]` (6 serialized Cavern of Souls).
- `FAMILY_SCENES["lci"]` — not configured (single 13-card scene; see §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| The Lost Caverns of Ixalan Commander (×4) | Commander deck | `lcc`; box-toppers LCC 101-120 (`boxtopper`, borderless inverted) |
| Jurassic World Collection | Eternal / UB crossover | `rex` (45 cards) + `trex` (2 tokens); `embossed` foils are §2 dupes |
| The Lost Caverns of Ixalan Art Series | Art Series | `alci` (81 cards) |
