# `one` — Phyrexia: All Will Be One

> Per-family memory doc. Read this before answering set-specific questions about
> `one` or working on `one`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `one`
**Family root type:** `expansion`
**Family released:** `2023-02-10`
**Last audit:** `2026-09-03` via `/characterize-set one`.

---

## 1. Family map

10 Scryfall codes, all linked via `parent_set_code` (clean graph).

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `one` | expansion | 479 | 2023-02-10 | parent |
| `onc` | commander | 174 | 2023-02-10 | 2 Commander decks |
| `pone` | promo | 160 | 2023-02-10 | promos: 80 promo-pack `stamped` (`Np`) + 80 prerelease `datestamped` (`Ns`) |
| `aone` | memorabilia | 81 | 2023-02-10 | Art Series |
| `fone` | memorabilia | 5 | 2023-02-10 | **Jumpstart Front Cards** (the theme/title cards, memorabilia type) |
| `mone` | minigame | 5 | 2023-02-10 | **Minigames** — 5 punch-out minigame cards (unusual set_type) |
| `yone` | alchemy | 31 | — | Alchemy: Phyrexia (digital-only) |
| `tone` | token | 14 | 2023-02-10 | tokens |
| `tonc` | token | 23 | 2023-02-10 | commander tokens |
| `wone` | token | 6 | 2023-02-10 | ONE Japanese Promo Tokens |

`mm set master-list one` / `set:one+related` resolve the whole family. **Sync
note:** `mm set sync one` pulls the parent; sync `onc pone` for the value-bearing
children (790 family prints total).

---

## 2. Treatments

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b` / `shw` / `ext` | n/a (structural) | showcase (`ichor`/borderless), inverted, extended frames; KEPT |
| `oilslick` (+`raisedfoil`) | `b\|ff` | **no — DISTINCT art, routed to UNOBTAINABLE** | ONE 352-371 — the 20 iconic "oil slick raised foil" borderless mythics (Atraxa 357 $135, Mondrak 346 $117, Elesh Norn 345, ~$796 total). DISTINCT art (352 illustration `42a8abb5` ≠ base 118 `a7d41f5b`), foil-only — so the dupe filter would KEEP them; excluded via `any_of` as a premium tier the user doesn't chase (2026-09-03 directive) |
| `stepandcompleat` | `b\|shw` | **no — DISTINCT Phyrexian-text art, routed to UNOBTAINABLE** | ONE 417-473 — the 57 Phyrexian-language "step-and-compleat" showcase foils (Elesh Norn 419 $366, Mondrak 424 $79, ~$1,000+ total). Foil-only. Computes to `b\|shw` (NOT `ff`) — so a DUPE_FOIL entry would silently MISS it (same trap as SNC stepandcompleat, verified). Excluded via `any_of` UNOBTAINABLE instead (per 2026-09-03 directive) |
| `concept` | `b` | **no — distinct concept-praetor art, KEPT** | ONE 416/421 — the "concept art" praetor variants (Elesh Norn 416 $44). Distinct art the user may want; NOT excluded |
| `stamped` (+`promopack`) | `regular` | scarcity variant → UNOBTAINABLE | 80 `pone` promo-pack stamps (`Np`). Same card + a stamp; compute to `regular` so the rare/mythic-regular sub-selectors pick them up (bypassing the `preferred` dedup) — the `any_of:{stamped}` rule removes them. Signal is `stamped` ONLY (see the promopack trap below) |
| `datestamped` + `prerelease` | (frame of base) | dropped by GLOBAL filter | 80 `pone` prerelease `Ns` prints; all have a non-stamped sibling → dropped by the global preferred filter. No per-family rule |
| `promopack` (WITHOUT `stamped`) | `b` | **no — distinct alt-art, KEPT** | ONE 277-281 (Ossification, Sheoldred's Edict, Slaughter Singer, Bladehold War-Whip, Experimental Augury) — inverted-frame promo-pack alt-arts. This is why the stamped rule keys on `stamped` ONLY, not `promopack` |
| `serialized` | (varies) | scarcity → GLOBAL filter | serialized 1-of-N prints; already in the global `UNOBTAINABLE_PROMO_TYPES`. §5 lists a parity no-op rule |
| `bundle` / `buyabox` / `thick` | (varies) | promo | ONE 273-282 bundle basics + Karumonix (buyabox), thick display cards. Niche; not excluded |

**Full-art convention:** standard. **No same-art fancy-foil dupe sheet** — ONE's
premium tiers (oilslick, stepandcompleat) are all DISTINCT art, so
`FAMILY_DUPE_FOIL_PROMO_TYPES["one"]` is an **empty frozenset** (unblocks
`treatment=preferred`); the premium tiers are handled by UNOBTAINABLE §5.

---

## 3. Chase variants

The `chase` modifier over-matches on this freshly-synced family (410 rows —
every card with its base+showcase+oilslick+stepandcompleat tiers). Not a useful
signal here; ONE's variety is multi-tier printings of *different* cards, and the
premium tiers are handled explicitly in §2/§5.

---

## 4. Scenes / posters / panoramas

**None.** No single-artist contiguous borderless scene run. The borderless
mythics are the oilslick/showcase tiers of individual cards, not a narrative
panorama.

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["one"]` in `src/magic_manager/selectors.py`.

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {stamped}` | 80 `pone` promo-pack `Np` stamps — same card as a kept base/showcase sibling + a stamp, priced on scarcity. Compute to `regular` (bypass the `preferred` dedup). Signal is `stamped` ONLY: the 5 `promopack`-WITHOUT-`stamped` inverted alt-arts (ONE 277-281) carry no `stamped` and are KEPT (verified: 5 traps survive the rule) |
| `promo_types_any_of: {oilslick, stepandcompleat}` | The two premium DISTINCT-ART foil tiers the user does not chase (2026-09-03 directive): oilslick raised-foil borderless mythics (ONE 352-371, ~$796) + step-and-compleat Phyrexian showcase foils (ONE 417-473, ~$1,000+). Both distinct art (dupe filter would keep them); `any_of` catches all 77. Kept: the base/boosterfun/concept prints of each card |
| `promo_types_any_of: {serialized}` | **Documented no-op** — serialized is already in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`. Kept for parity with INR/ACR/ECL/SOS headliner families |

**Missing-set impact (recorded 2026-09-03):** empty config = **398 prints /
~$2,975**. Final config = **241 prints / ~$860** — the ~$2,100 drop is the 80
stamped scarcity promos + the oilslick (~$796) and stepandcompleat (~$1,000+)
premium tiers. Top after config: normal nonfoil rares/mythics (Elesh Norn 415
$98, Mondrak 299 $46, concept Elesh Norn 416 $44) — clean list.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` (e.g. `23p`) | `pone` | Promo-pack `stamped` | Mondrak 23p → `pone` 23p |
| `Ns` (e.g. `82s`) | `pone` | Prerelease `datestamped` | Archfiend of the Dross 82s → `pone` 82s |

`pone` mirrors the main-set CN in both `Np` and `Ns` variants. `wone` holds the 6
Japanese promo tokens (niche).

---

## 7. Edge cases & gotchas

- **`mone` (minigame)** and **`fone` (Jumpstart Front Cards, memorabilia)** are
  unusual set_types — both excluded from the default bundle (opt in via
  `--include minigame,memorabilia`).
- **No arena leak** — `set:one+related missing | grep arena` returns nothing
  (verified); `yone` alchemy prints filtered globally.
- **`stepandcompleat` computes to `b|shw`, NOT `ff`** — so it can ONLY be
  excluded via UNOBTAINABLE (a DUPE_FOIL entry would silently miss it). Same trap
  as SNC stepandcompleat. Recorded here so a future editor doesn't try DUPE_FOIL.
- **`concept` praetors (416/421)** are distinct art, KEPT — don't confuse with
  the excluded oilslick/stepandcompleat premium tiers.
- Praetors (Elesh Norn, Sheoldred, Jin-Gitaxias, Urabrask, Vorinclex) each have
  many tiers: base, showcase (ichor), borderless, oilslick, stepandcompleat,
  concept — only the oilslick + stepandcompleat foils are excluded.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["one"]` — **configured**: `frozenset()` (empty — no same-art fancy-foil dupe; premium tiers are distinct art, handled in §5).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["one"]` — **configured**: `[{stamped}, {oilslick, stepandcompleat}, {serialized}]` (the serialized rule is a documented no-op).
- `FAMILY_SCENES["one"]` — not configured (no narrative scene; see §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Phyrexia: All Will Be One Commander (×2) | Commander deck | `onc` (174 cards) |
| ONE Jumpstart | Jumpstart | `fone` (5 Jumpstart Front Cards, memorabilia type — the theme/title cards) |
| Art Series | Art Series | `aone` (81 cards) |
| Minigames | (minigame — novel) | `mone` (5 punch-out minigame cards) |
| Bundle / Buy-a-Box promos | Bundle / Buy-a-Box | bundle basics (ONE 273-282) + Karumonix buyabox — filed in `one` |
