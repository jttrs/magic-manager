# `dft` — Aetherdrift

> Per-family memory doc. Read this before answering set-specific questions about
> `dft` or working on `dft`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `dft`
**Family root type:** `expansion`
**Family released:** `2025-02-14`
**Last audit:** `2026-09-15` via `/characterize-set dft`.

---

## 1. Family map

7 Scryfall codes, all linked via `parent_set_code` (clean graph — no separately-
rooted bonus sheets). A standard modern expansion + Commander product. Aetherdrift
is the racing set (vehicles/mounts), so its "showcase" borderless prints are
vehicle art, not narrative scenes.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dft` | expansion | 553 | 2025-02-14 | parent |
| `drc` | commander | 184 | 2025-02-14 | Aetherdrift Commander decks |
| `pdft` | promo | 160 | 2025-02-14 | promos — 80 cards × (`p` promopack+stamped / `s` prerelease+datestamped) |
| `adft` | memorabilia | 54 | 2025-02-14 | Art Series |
| `ydft` | alchemy | 31 | 2025-02-14 | Alchemy: Aetherdrift (digital-only) |
| `tdft` | token | 14 | 2025-02-14 | tokens |
| `tdrc` | token | 17 | 2025-02-14 | Commander tokens |

`mm set master-list dft` / `set:dft+related` resolve the whole family from the
parent — **no `--only` needed** (clean `parent_set_code` graph). 737 prints in the
family that reach the local `cards` table (excludes tokens not synced); the
default value-bearing set is `dft` (expansion) + `drc` (commander).

---

## 2. Treatments

Which `promo_types` appear in this family, and how they map through
`treatments.compute_treatment()`.

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b` / `ext` / `shw` (frame-dependent) | n/a (structural) | showcase / extended-art frames; the preferred collectible print, KEPT. NB: a card's boosterfun sibling may be `b` (inverted, e.g. Aatchik 360) OR `ext` (extended-art, e.g. Afterburner 387) OR `shw` (showcase+inverted, e.g. Chandra 401) — the frame varies per card |
| `japanshowcase` (+`boosterfun`) | `b\|shw` | n/a (distinct showcase art) | 20 prints (DFT 397-406) — the Japanese-showcase mythics/rares. Distinct showcase art, KEPT as the preferred representative (mirrors EOE/ECL/FDN japanshowcase stance) |
| `fracturefoil` (+`japanshowcase`+`boosterfun`) | `b\|shw\|ff` | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | DFT 407-416, 10 prints (Chandra 411, Cursecloth Wrappings 410, Explosive Getaway 413, …), foil-only, ~$56-$74. Each shares its illustration_id with its japanshowcase sibling (Chandra 411↔401 `358754be`, Cursecloth 410↔400 `8cbe1848`) — same showcase art, fracture-foil sheet. Both key to `{b,shw}` (fracturefoil adds `ff`), so the sibling dedup pairs them cleanly. Drops the fracturefoil, keeps the japanshowcase. ~$563 total. Direct analog of EOE/ECL/FDN/TMT fracturefoil |
| `firstplacefoil`+`boxtopper` | `b\|ff` | **NO (frame mismatch) → `FAMILY_UNOBTAINABLE_RULES`** | DFT 427-553, 127 prints, the "First Place" foil box toppers (podium-frame `inverted` foils), foil-only, ~$1,041 total ($0.49-$96). **Same art as the BASE card** (Aatchik 473 illus `431eea63` = base 187, NOT boosterfun 360; Chandra 456 `b071fc1f` = base 116, NOT japanshowcase 401). They compute to `b\|ff` (the `b` comes from the `inverted` frame), but the base sibling computes to `` (empty) — so `codes-minus-ff` = `{b}` vs base `{}` **never pairs** under the sibling dedup (the MAT-halofoil / MSH-surgefoil trap). DUPE_FOIL would misfire → excluded WHOLESALE via `any_of:{firstplacefoil}` (§5). `firstplacefoil` appears only on `dft` + `spg` globally, so the rule is exact within the family |
| `serialized`+`headliner`+`rainbowfoil` (+`boosterfun`) | `ff` | scarcity → dropped by GLOBAL filter | DFT 376 The Aetherspark — the family's headline serialized chase, foil-only, ~$1,875. `serialized` is in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so it never reaches missing-set. Its base (DFT 231, ~$21) and box topper (496) are separate prints, KEPT. §5 lists a documented no-op rule for parity |
| `promopack`+`stamped` (on pdft) | `regular` | dupe (stamp) → NO rule needed | pdft `Np` prints — promo-pack stamped copies of base cards. Unlike TDM/SNC, these **never reach the preferred filter** (the base card dedups them first — verified 0 pdft rows in `missing treatment=preferred` even with no family rules), so NO `stamped` rule is required. See §5 |
| `prerelease`+`datestamped` (on pdft) | `regular` | dupe (stamp) → NO rule needed | pdft `Ns` prints — prerelease datestamped copies. Same as above: deduped by base, 0 leak |
| `bundle` | `ext` / `''` | promo | DFT 422 Lumbering Worldwagon, 424 Amonkhet Raceway, 425 Avishkar Raceway, 426 Muraganda Raceway — bundle promos, cheap ($0.26-$1.26). KEPT — distinct promos the user may want |
| `buyabox` | `''` | promo | DFT 423 Lifecraft Engine — buy-a-box promo, singleton (~$0.22). KEPT |

**Full-art convention:** standard (borderless/showcase carry `border_color:
borderless` or `frame_effects: showcase`/`inverted`/`extendedart`; `full_art` not
relied upon).

---

## 3. Chase variants

**None** by the `chase` modifier (0 rows for multi-art). No non-land card name has
≥3 distinct-art printings at the same `(name, treatment)` — only the full-art
basic lands (Island ×5, Forest ×5, …) have ≥3 distinct arts. The set's variety is
base / boosterfun / japanshowcase / fracturefoil / firstplacefoil-boxtopper tiers
of the *same* art, not multi-art of one card (same shape as TDM).

---

## 4. Scenes / posters / panoramas

**None.** The borderless-inverted block (DFT 292-351, the vehicle/mount showcases)
has NO contiguous same-artist run of ≥3 — every borderless card is a different
artist (292 SchmandrewART, 293 Francisco Badilla, 294 Arik Roper, …). These are
per-vehicle showcase art, not a narrative panorama. DFT ships no poster/panorama
series. Not encoded in `FAMILY_SCENES`.

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["dft"]` in `src/magic_manager/selectors.py`.

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {firstplacefoil}` | The 127 "First Place" foil box toppers (DFT 427-553, `firstplacefoil`+`boxtopper`, foil-only, ~$1,041 total). Same art as the BASE card but on a podium-`inverted`-frame foil sheet → compute to `b\|ff` while the base computes to `` (empty), so the DUPE_FOIL sibling dedup can't pair them (frame mismatch — same class as MAT halofoil / MSH surgefoil). All 127 have a same-art base sibling and the user doesn't chase box toppers, so `any_of:{firstplacefoil}` is exact and robust. `firstplacefoil` occurs only on `dft`+`spg` globally (spg isn't in this family). |
| `promo_types_any_of: {serialized, headliner, rainbowfoil}` | DFT 376 The Aetherspark (serialized+headliner+rainbowfoil+boosterfun, foil-only, ~$1,875) — the family's headline chase. **Documented no-op:** `serialized` is already in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so 376 is filtered before this rule applies. Kept for parity/discoverability with the TDM/INR/SOS/TMT headliner families. |

**No `stamped`/`datestamped` rule (differs from TDM).** The pdft promo-pack
(`Np`) and prerelease (`Ns`) stamp twins compute to `regular`, but they are
deduped onto their base sibling by the preferred filter and **never reach
missing-set**: verified 0 pdft rows in `set:dft+related missing treatment=preferred`
even with NO family rules configured. TDM needed a `{stamped}` rule because its
promo-pack twins leaked; DFT's do not, so no rule is added. (Watch-item: if a
future data refresh changes the base-dedup behavior and stamped prints start
leaking, add `promo_types_any_of: {stamped}` mirroring TDM.)

**Missing-set impact (recorded 2026-09-15):** the `{fracturefoil}` DUPE_FOIL
config + the `{firstplacefoil}` rule take `missing treatment=preferred` from
**231 prints / ~$1,834** (baseline with an empty DUPE_FOIL and no rules) down to
**104 prints / ~$229**. The 10 fracturefoil dupes (~$563) drop via DUPE_FOIL; the
127 firstplacefoil box toppers (~$1,041) drop via the rule; The Aetherspark 376
(~$1,875) was already global-filtered. Verified no `firstplacefoil` / `fracturefoil`
/ `stamped` / `arena` leak. The top of the remaining list is the KEPT japanshowcase
+ boosterfun prints (Radiant Lotus 406 $19.82, Chandra 401 $19.32, Riverpyre Verge
372 $19.07), not the dropped tiers. No scarcity-tier bloat.

---

## 6. PRM destinations

Standard modern promo channels; `pdft` holds them all (160 prints = 80 cards ×
two stamp variants):

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` (e.g. `116p`) | `pdft` | Promo Pack (promopack + stamped) | Chandra, Spark Hunter 116p |
| `Ns` (e.g. `116s`) | `pdft` | Prerelease (prerelease + datestamped) | Chandra, Spark Hunter 116s |

The `N` mirrors the main-set card. Resolve a presented PRM by name+stamp-type and
read the `pdft` CN off the match. No dft-specific PRM notes in the `bulk-add` skill.

---

## 7. Edge cases & gotchas

- **`ydft` (alchemy)** is digital-only (Alchemy: Aetherdrift, 31 cards) — globally
  filtered by the Arena/Alchemy `_is_digital_only` path. Verified no arena leak
  and 0 `ydft` rows in `missing treatment=preferred`.
- **The Aetherspark 376** is the serialized/rainbowfoil headliner (~$1,875) —
  global-filtered. Its base (DFT 231) is a normal mythic and stays in scope.
- **`drc` (commander)** is a normal `commander` set_type (184 cards) — no set_type
  mismatch like TMT's `tmc`.
- **`firstplacefoil` box toppers are same-art as the BASE, not the boosterfun
  showcase** — a gotcha for anyone assuming a fancy foil dupes the showcase. It
  dupes the plain art on a podium-frame foil sheet, which is why DUPE_FOIL can't
  pair it and the exclusion is a wholesale `any_of` rule.
- Two token sets (`tdft` main, `tdrc` commander) — both excluded from the default
  value scope.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["dft"]` — **PROPOSED**: `frozenset({"fracturefoil"})` (10 fracturefoil mythics dupe their japanshowcase siblings).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["dft"]` — **PROPOSED**: `[{"promo_types_any_of": frozenset({"firstplacefoil"})}, {"promo_types_any_of": frozenset({"serialized", "headliner", "rainbowfoil"})}]` (First Place box-topper tier + documented-no-op serialized headliner).
- `FAMILY_SCENES["dft"]` — not configured (no narrative scenes; §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Aetherdrift Commander decks | Commander deck | `drc` (184 cards); 3 commander decks (per `set_status`) |
| Aetherdrift Art Series | Art Series | `adft` (54 cards) |
| First Place box toppers | Box topper | `dft` 427-553 (127 prints, `firstplacefoil`+`boxtopper`), foil-only, same art as base; excluded from missing-set (§5) |
| Bundle / Buy-a-Box promos | Bundle / Buy-a-Box | Raceway lands 424/425/426 + Lumbering Worldwagon 422 (bundle), Lifecraft Engine 423 (buyabox) |

**Booster types (for `sealed-value` EV).** MTGJSON carries per-card WotC booster
weights for `dft`. Enumerate with `uv run python scripts/sealed_value.py dft --list-boosters`.

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `box-topper` | EV ~$11.25, coverage 100% — the First Place box-topper sheet (dft 427-553); 1 per box |
| `collector` | EV ~$16.18, coverage 100% (2 layouts) |
| `collector-sample` | EV ~$2.38, coverage 100% |
| `play` / `play-arena` | EV ~$5.55-$5.71 (4 / 2 layouts) |
| `prerelease` | EV ~$3.08, coverage 100% |
