# `mkm` — Murders at Karlov Manor

> Per-family memory doc. Read this before answering set-specific questions about
> `mkm` or working on `mkm`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mkm`
**Family root type:** `expansion`
**Family released:** `2024-02-09`
**Last audit:** `2026-09-15` via `/characterize-set mkm`.

---

## 1. Family map

11 Scryfall codes, all linked via `parent_set_code` (clean graph — no separately-
rooted bonus sheets). A standard modern expansion + Commander product, plus the
`clu`/`fclu` **Ravnica: Clue Edition** companion product (a Jumpstart-style
standalone that Scryfall parents to `mkm`). 1267 prints in the family total.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mkm` | expansion | 451 | 2024-02-09 | parent |
| `mkc` | commander | 358 | 2024-02-09 | Murders at Karlov Manor Commander decks |
| `pmkm` | promo | 180 | 2024-02-09 | promos — 90 cards × (`p` promopack+stamped / `s` prerelease+datestamped) |
| `amkm` | memorabilia | 49 | 2024-02-09 | Art Series |
| `clu` | draft_innovation | 284 | 2024-02-23 | **Ravnica: Clue Edition** — standalone product (mystery/board-game tie-in); reprints + the boxtopper shocklands |
| `fclu` | memorabilia | 10 | 2024-02-23 | Ravnica: Clue Edition "Front Cards" (character/box-front memorabilia) |
| `pss4` | promo | 5 | 2024-02-09 | MKM Standard Showdown premiums |
| `tmkm` | token | 22 | 2024-02-09 | tokens |
| `tmkc` | token | 31 | 2024-02-09 | Commander tokens |
| `wmkm` | token | 4 | 2024-02-09 | Japanese promo tokens |
| `ymkm` | alchemy | 30 | 2024-02-09 | Alchemy: Murders at Karlov Manor (digital-only) |

`mm set master-list mkm` / `set:mkm+related` resolve the whole family from the
parent (no `--only` needed). Default value-bearing scope is `mkm` (expansion) +
`mkc` (commander) + `clu` (Clue Edition draft_innovation).

---

## 2. Treatments

MKM is a **detective-themed** set — its alternate-treatment vocabulary is unusually
rich, but every "fancy" token is either **structural showcase art** (KEPT as the
preferred collectible) or a **serialized/stamp dupe**. There is **NO fancy-foil
sheet** in this family (no `surgefoil`/`halofoil`/`textured`/`gilded`/`raisedfoil`),
so `FAMILY_DUPE_FOIL_PROMO_TYPES["mkm"]` is an **empty frozenset** (like TLA/SPM/
SOS/MAT/NEO/MSH/ONE) — it only unblocks the `treatment=preferred` filter.

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b`/`shw` (frame-dependent) | n/a (structural) | the umbrella booster-fun tag; the preferred collectible print. KEPT |
| `dossier` (+`boosterfun`) | `shw` | **no — distinct showcase art** | 55 prints (MKM 354-408). The "case file / dossier" showcase frame — the set's signature showcase. KEPT (preferred) |
| `magnified` (+`boosterfun`) | `b\|shw` | **no — distinct showcase art** | 30 prints (MKM 287-316). "Magnifying-glass" borderless showcase (`showcase`+`inverted` frame). KEPT |
| `ravnicacity` (+`boosterfun`) | `shw` | **no — distinct showcase art** | 8 prints (MKM 317-323) — the Ravnica-City skyline showcase for the 7 guild legends (+ Aurelia twin). KEPT. (`ravnicacity` also appears in MUL/MAT/MOM; the MKM 8 are the KEPT city-showcase art.) |
| `invisibleink` (+`dossier`+`boosterfun`) | `shw` | **YES — same art → `FAMILY_UNOBTAINABLE_RULES`** | 14 prints (MKM 377-389, 433). A "hidden-clue" glow-ink FOIL overlay of the **dossier showcase** — same illustration_id as the plain `dossier` sibling (Delney 378↔337 `60545283`, Massacre Girl 380↔344 `34bd17fa`, Anzrag 385↔356 `ed337669`, Vein Ripper 433↔346 `4d3fd983`). A same-art dupe, foil-only ($1-$67). **Computes to `shw`, NOT `ff`** — the SNC `stepandcompleat` / MSH `surgefoil` trap: the DUPE_FOIL gate (which only inspects `ff` prints) can't catch it, so it's excluded via `any_of:{invisibleink}` in §5 instead. MKM-exclusive (14 prints, DB) → the rule is exact. Total dropped ~$133 |
| `boxtopper` | `b` | **no — distinct borderless art** | CLU 274-283 — the 10 Ravnica shock lands as Clue-Edition box-topper borderless-inverted prints ($22-$34 foil, ~$285 total). Distinct collectible art the user may want. KEPT |
| `promopack` (on MKM 423-427, inverted frame) | `b` | dupe of base | 5 in-set promo-pack cards (Long Goodbye 423, Gleaming Geardrake 424, Kraul Whipcracker 425, Lightning Helix 426, No More Lies 427) — inverted-frame promo-pack variants of base cards. Low value; each has a plain base sibling |
| `promopack`+`stamped` (on `pmkm` `Np`) | `regular` (empty) | dupe (stamp) → `FAMILY_UNOBTAINABLE_RULES` | 90 `pmkm` promo-pack stamped copies of base cards. Same card + a stamp; compute to bare `regular` so they bypass the preferred dedup and leak into missing-set. Excluded via the `stamped` rule (§5) |
| `prerelease`+`datestamped` (on `pmkm` `Ns`) | `regular` (empty) | dupe (stamp) → same rule via `datestamped` | 90 `pmkm` prerelease datestamped copies. NOTE: these carry `datestamped`, NOT `stamped` — so the rule keys on **both** `{stamped, datestamped}` to catch all 180 pmkm prints (see §5; this is the TDM watch-item, resolved here) |
| `serialized`+`doublerainbow` (+`ravnicacity`/`boosterfun`) | `shw\|ff` / `ff` | scarcity → dropped by GLOBAL filter | MKM 317z-323z — 7 serialized foil chase prints of the 7 guild legends (Aurelia 317z $700, Niv-Mizzet 319z $632, Vannifar 323z $600, …; ~$3,205 total). `serialized` is in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so they never reach missing-set. §5 lists a documented no-op rule for parity with the headliner families |

**Full-art convention:** standard (borderless/showcase carry `border_color:
borderless` or `frame_effects: showcase`/`inverted`; `full_art` not relied upon).

---

## 3. Chase variants

**None** by the `chase` modifier — `set:mkm+related missing rarity=uncommon
treatment=regular chase` returns **0 rows**. No card name has ≥3 distinct-art
printings at the same `(name, treatment)`. The set's variety is base / magnified /
dossier / ravnicacity / invisibleink tiers of the *same* card, not multi-art of
one card. (The bare `chase` modifier reports 514 rows across the family, but those
are the many-printing basic lands / high-count reprints, not narrative chases.)

---

## 4. Scenes / posters / panoramas

**None.** The borderless artist-run heuristic flags **MKM 324-333** — 10
contiguous borderless lands all by **Sergey Glushakov** — but these are the 10
**borderless surveil dual lands** (Commercial District, Elegant Parlor, Hedge Maze,
Lush Portico, Meticulous Archive, Raucous Theater, Shadowy Backstreet, Thundering
Falls, Undercity Sewers, Underground Mortuary): a themed art *group*, NOT a
connected panorama or narrative scene (each is a standalone land illustration).
A false-positive of the artist-run heuristic (same class as TDM's Tomas Duchek
run). No `poster`/`panorama` promo_type exists anywhere in the MKM family. Not
encoded in `FAMILY_SCENES`.

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["mkm"]` in `src/magic_manager/selectors.py`.

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {stamped, datestamped}` | `pmkm` promo-pack/prerelease STAMP variants — all 180 `pmkm` prints (90 `Np` promopack+stamped, 90 `Ns` prerelease+datestamped) are the same card as a kept base/showcase sibling + a stamp; they compute to bare `regular` (bypass the preferred dedup) and leak ~$825 of duplicate stamped prints into missing-set. **Both tokens** are needed: `Np` carries `stamped` but `Ns` carries only `datestamped` (no `stamped`) — matching either catches all 180. (Resolves the TDM `{stamped}`-only watch-item: MKM's prerelease prints ARE `datestamped` and would leak under a `stamped`-only rule.) |
| `promo_types_any_of: {invisibleink}` | MKM 377-389, 433 — the 14 `invisibleink` "hidden-clue" glow-ink FOIL overlays of the **dossier showcase**. Same illustration_id as the plain `dossier` sibling (verified: Delney 378↔337, Massacre Girl 380↔344, Anzrag 385↔356, Vein Ripper 433↔346), so a pure same-art dupe. **Computes to `shw`, not `ff`** → the DUPE_FOIL gate can't catch it (the SNC/MSH trap), so it's excluded here instead. `invisibleink` is MKM-exclusive (14 prints, DB) → `any_of:{invisibleink}` is exact. Keeps the `dossier` showcase print, drops the invisibleink dupe. ~$133 dropped |
| `promo_types_any_of: {serialized, doublerainbow, ravnicacity}` | MKM 317z-323z — the 7 serialized guild-legend chase foils (~$3,205 total). **Documented no-op:** `serialized` is already in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so 317z-323z are filtered before this rule applies. Kept for parity/discoverability with INR/ACR/ECL/SOS/TDM headliner families. NOTE: `ravnicacity` is listed here for documentation only but the rule as written would ALSO match the KEPT non-serialized `ravnicacity` city-showcases (MKM 317-323) — **so this specific rule is NOT proposed for the code** (see §9); the serialized prints are covered by the global filter. Retained in the doc as an explanation of the tier only. |

**Missing-set impact (recorded 2026-09-15):** with the empty `{}` DUPE_FOIL config
+ the `{stamped, datestamped}` rule + the `{invisibleink}` rule, the two active
rules drop **194 prints** (180 pmkm stamped/datestamped ~$825 + 14 invisibleink
~$133 = ~$958) that would otherwise leak into `treatment=preferred`. The 7
serialized `z` chases (~$3,205) were already global-filtered. No scarcity-tier
bloat remains: the top of the kept list is the `dossier`/`magnified`/`ravnicacity`
showcases and CLU boxtopper shocklands (real distinct-art collectibles the user
may want), not stamp dupes or serialized chases.

---

## 6. PRM destinations

Standard modern promo channels; `pmkm` holds them all (180 prints = 90 cards ×
two stamp variants). `pss4` holds the Standard Showdown premiums.

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` (e.g. `3p`) | `pmkm` | Promo Pack (promopack + stamped) | Assemble the Players 3p |
| `Ns` (e.g. `3s`) | `pmkm` | Prerelease (prerelease + datestamped) | Assemble the Players 3s |
| `N` (small, 1-5) | `pss4` | Standard Showdown premium | (5 prints) |

The `N` mirrors the main-set card. Resolve a presented PRM by name+stamp-type and
read the `pmkm` CN off the match. (No `pmkm` mentions currently exist in the
`bulk-add` skill.)

---

## 7. Edge cases & gotchas

- **`ymkm` (alchemy)** is digital-only (Alchemy: Murders at Karlov Manor, 30
  cards) — globally filtered by the Arena/Alchemy `_is_digital_only` path.
  Verified no arena leak: `set:mkm+related missing | grep -i arena` returns only
  "Phyrexian Arena" (a card NAME, `mkc` 133), not an arena security stamp.
- **`clu`/`fclu` — Ravnica: Clue Edition** is a standalone product (a mystery/
  board-game tie-in Jumpstart-style set), `set_type: draft_innovation` — NOT a
  bonus sheet. It reprints Ravnica staples and adds the 10 boxtopper shock lands
  (CLU 274-283, distinct borderless-inverted art, KEPT). `fclu` is its 10-card
  "Front Cards" memorabilia set.
- **`invisibleink` (14)** dupes the `dossier` showcase art (illustration_id
  match) but computes to `shw` not `ff` → excluded via §5 UNOBTAINABLE, not
  DUPE_FOIL (the SNC/MSH trap).
- **Serialized guild legends 317z-323z** (~$3,205) are global-filtered.
- Three token sets (`tmkm` main, `tmkc` commander, `wmkm` Japanese promo) — all
  excluded from the default value scope.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["mkm"]` — **configured**: `frozenset()` (empty — no fancy-foil sheet in the family; unblocks `treatment=preferred` without filtering, like TLA/SPM/SOS/MAT/NEO/MSH/ONE).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["mkm"]` — **configured**: `[{"promo_types_any_of": frozenset({"stamped", "datestamped"})}, {"promo_types_any_of": frozenset({"invisibleink"})}]` (pmkm stamp/prerelease dupe tier + the invisibleink same-art dossier dupe). The serialized guild-legend chase is covered by the GLOBAL filter (no per-family rule).
- `FAMILY_SCENES["mkm"]` — not configured (no narrative scenes/panoramas; §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Murders at Karlov Manor Commander decks | Commander deck | `mkc` (358 cards); the "Deadly Disguise" / "Blame Game" / "Deadly Disguise" style crime-themed decks |
| Ravnica: Clue Edition | standalone / Jumpstart-style product | `clu` (284, draft_innovation) + `fclu` (10 front-card memorabilia); reprints + 10 boxtopper shocklands (CLU 274-283) |
| Murders at Karlov Manor Art Series | Art Series | `amkm` (49 cards) |
| MKM Standard Showdown | Standard Showdown premium | `pss4` (5 cards) |

**Booster types (for `sealed-value` EV).** MTGJSON carries per-card WotC booster
weights for `mkm`. Enumerate with `uv run python scripts/sealed_value.py mkm --list-boosters`.

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `collector` | EV ~$25; coverage 98.7% |
| `collector-sample` | EV ~$4.45; coverage 99.4% |
| `play` | EV ~$6.55; coverage 98.5% — MKM launched as a Play-Booster set |
| `play-arena` | EV ~$6.09; coverage 98.4% |
| `prerelease` | EV ~$8.97; coverage 99.4% — the prerelease pack (points at `pmkm` prerelease promos) |

---
