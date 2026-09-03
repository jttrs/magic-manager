# `otj` — Outlaws of Thunder Junction

> Per-family memory doc. Read this before answering set-specific questions about
> `otj` or working on `otj`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the session.
> See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `otj`
**Family root type:** `expansion`
**Family released:** `2024-04-19` (main wave); `yotj` 2024-05-07 (Alchemy); `pbig` 2025-08-01
**Last audit:** `2026-09-03` via `/characterize-set otj`.

---

## 1. Family map

12 Scryfall codes, all linked via `parent_set_code` (no separately-rooted bonus
sheets — the graph is clean here, unlike SPM/`mar`).

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `otj` | expansion | 374 | 2024-04-19 | parent |
| `big` | expansion | 95 | 2024-04-19 | **The Big Score** — the bonus-sheet expansion (mythic reprints, `vault` showcase tier) |
| `otc` | commander | 342 | 2024-04-19 | 4 Commander decks |
| `otp` | masterpiece | 80 | 2024-04-19 | **Breaking News** — showcase masterpiece sheet (CN 1-65 showcase + 66-80 textured twins) |
| `potj` | promo | 160 | 2024-04-19 | promos: 80 promo-pack `stamped` + 80 prerelease `datestamped` |
| `pbig` | promo | 14 | 2025-08-01 | The Big Score promo-pack `stamped` promos |
| `aotj` | memorabilia | 54 | 2024-04-19 | Art Series |
| `yotj` | alchemy | 30 | 2024-05-07 | Alchemy (digital-only) |
| `totj` | token | 19 | 2024-04-19 | tokens |
| `totc` | token | 41 | 2024-04-19 | commander tokens |
| `totp` | token | 5 | 2024-04-19 | Breaking News tokens |
| `tbig` | token | 7 | 2024-04-19 | The Big Score tokens |

No `--only` gymnastics needed — `mm set master-list otj` / `set:otj+related` resolve
the whole family from the parent.

**Sync note:** `mm set sync otj` only pulls the parent. To populate the whole family
locally (needed for a full audit / missing-set), sync the value-bearing children
individually: `big otp otc potj pbig aotj` (the tokens/alchemy add nothing to
missing-set). 716 → 1149 family prints after syncing big/otp/potj/pbig/aotj/yotj.

---

## 2. Treatments

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `shw` / `ext` (frame-dependent) | n/a (structural) | showcase or extended-art frame; KEPT |
| `vault` | `shw` | **no — distinct showcase art** | The Big Score "Vault" showcase (BIG 46-60). Illustration `486388b6` ≠ base `5fbc04c1` (Vaultborn Tyrant). KEPT |
| `raisedfoil` | `shw\|ff` | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | BIG 61-65 — the raised-foil sheet over the `vault` showcase art. All 5 pair cleanly with their vault sibling (61↔50, etc.). Drops the raisedfoil, keeps the vault showcase |
| `textured` | `b\|ff` | same art, but **routed to UNOBTAINABLE** | OTP 66-80 — textured foil of the OTP showcase masterpiece. Same illustration as the `shw` sibling (74↔35, `f4d16fc6`) but the textured print is `b` (inverted) vs sibling `shw`, so DUPE_FOIL's codes-minus-ff key can't pair them (frame-mismatch class — cf. MAT halofoil / MSH surgefoil). Excluded via `any_of:{textured}` |
| `stamped` | (frame of base) | scarcity variant → UNOBTAINABLE | 94 promo-pack stamps (pbig 14 + potj 80). Same card + a stamp; `any_of:{stamped}` |
| `datestamped` + `prerelease` | (frame of base) | dropped by GLOBAL filter | 80 potj prerelease prints; all have a non-stamped OTJ sibling → dropped by `_filter_treatment_preferred` Step 2. No per-family rule needed |
| `promopack` (WITHOUT `stamped`) | `b` | **no — distinct alt-art, KEPT** | OTJ 368-372 (Frontier Seeker, Honest Rutstein, Make Your Own Luck, Ruthless Lawbringer, Scorching Shot) — inverted-frame promo-pack alt-arts. This is why the stamped rule keys on `stamped` ONLY, not `promopack` |

**Full-art convention:** standard (borderless/showcase carry `border_color: borderless`
or `frame_effects: showcase`; `full_art` not relied upon here).

**No `serialized` / `headliner` / `poster` chase** in this family (all 0) — unlike
SNC/EOE/ECL/SOS, OTJ has no single ultra-rare headline print to pin.

---

## 3. Chase variants

**None.** No card name has ≥3 distinct-art printings at the same `(name, treatment)`
in the family — OTJ's variety comes from cross-set reprints (base/showcase/extended/
vault/textured tiers of *different* cards), not multi-art chases of one card. The
bare `chase` modifier over-matches on a freshly-synced family (every rare/mythic has
its nonfoil+foil pair); it's not signal here.

---

## 4. Scenes / posters / panoramas

**None.** The borderless cards cluster as:
- OTJ 287-299 — the villains **showcase legends** (one distinct artist each: Pedro
  Potier, Greg Staples, Michael Walsh, …), NOT a single-artist contiguous scene run.
- OTJ 300-304 — the **fastland cycle** (Blooming Marsh … Spirebluff Canal, all Piotr
  Dura) — a 5-art land cycle, not a panorama.

No `FAMILY_SCENES["otj"]` entry; `scripts/scene_table.py otj` is not applicable.

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["otj"]` in `src/magic_manager/selectors.py`.

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {textured}` | The 15 OTP "Breaking News" textured-foil masterpieces (CN 66-80). Same art as their `shw` masterpiece siblings but DUPE_FOIL can't pair them (frame mismatch `b` vs `shw`). Fancy-foil masterpiece tier the user doesn't chase |
| `promo_types_any_of: {stamped}` | 94 promo-pack STAMP variants (pbig 14 + potj 80). Same card + a stamp, priced on scarcity. Keyed on `stamped` ONLY so the 5 `promopack`-without-`stamped` alt-arts (OTJ 368-372) stay in scope. datestamped prerelease prints (80) are already dropped by the global preferred filter |

**Impact:** `treatment=preferred` missing count 146 (collectible-alt) → **127** with the
rules applied (2026-09-03 prices). No arena-stamped / digital leak. Top of the missing
list is legitimate wantable singles (The Big Score mythics $90-$7, OTP regular showcase
masterpieces Mana Drain/Reanimate/Thoughtseize) — no runaway scarcity tier.

---

## 6. PRM destinations

For the "I have a PRM-stamped card" flow ([[bulk-add]] skill). OTJ's promo channels:

| Physical CN pattern | Scryfall set | Channel | Notes |
|---|---|---|---|
| `Ns` (e.g. `189s`) | `potj` | Prerelease **datestamped** | mirrors the main-set CN + `s`; e.g. Akul the Unrepentant → `potj` 189s. Dropped by preferred (has OTJ 189 sibling) |
| `Np` (e.g. `29p`) | `pbig` / `potj` | Promo-pack **stamped** | The Big Score cards → `pbig` (Fomori Vault → `pbig` 29p); main-set → `potj`. Excluded via `any_of:{stamped}` |
| `368-372` | `otj` | Promo-pack alt-art (inverted frame, NO stamp) | distinct art, KEPT — not a PRM dupe |

No `pw25`/`pw26` WPN or regional (`rXXX`) promos observed in this family.

---

## 7. Edge cases & gotchas

- **`big` "The Big Score" is a bonus-sheet expansion, not a set-booster set** — 95
  cards of high-value reprints (Mana Drain, Grand Abolisher, Sword of Wealth and
  Power). It carries the `vault` showcase tier + its `raisedfoil` premium. Filed
  under `otj` via `parent_set_code`.
- **`otp` "Breaking News" masterpieces** — CN 1-65 are the showcase (`shw`) prints;
  CN 66-80 are `textured` twins of 15 of them (Anguished Unmaking at both 35 and 74).
  The regular showcases stay in missing-set; the textured twins are excluded (§5).
- **`vault` vs `raisedfoil` distinction** — `vault` (BIG 46-60) is distinct showcase
  art and KEPT; `raisedfoil` (BIG 61-65) is the raised-foil dupe of the vault art and
  dropped via DUPE_FOIL. Don't conflate them.
- **Arena Starter Decks** (`AncientDiscovery_OTJ`, `SaddleUp_OTJ`, … 11 decks) are
  DIGITAL products — never listed by `precon-list` (`Arena Starter Deck` type), and
  their cards don't enter the physical missing-set notion. Also `yotj` (Alchemy) is
  digital-only, globally filtered.
- **Name collisions across siblings** are common (a card at OTJ + BIG + OTC + OTP with
  different CNs) — the preferred filter's sibling index keys on `(name, codes-minus-ff)`
  within the family, so this is handled.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["otj"]` — **configured** `frozenset({"raisedfoil"})` (added 2026-09-03).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["otj"]` — **configured** `any_of:{textured}` + `any_of:{stamped}` (added 2026-09-03).
- No `FAMILY_SCENES["otj"]` (no scenes).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md). OTJ specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| 4 Commander Decks | Commander Deck | `DesertBloom_OTC`, `GrandLarceny_OTC`, `MostWanted_OTC`, `QuickDraw_OTC` (all `_OTC`) |
| The Big Score | bonus-sheet expansion | `big` set code, not a sealed SKU of its own — cards appear in OTJ Collector Boosters |
| Breaking News | masterpiece sheet | `otp` — showcase masterpieces (Collector Booster inserts) |
| Bundle Land Pack | Bundle | `OutlawsOfThunderJunctionBundleLandPack_OTJ` |
| Arena Starter Decks (11) | digital | `Arena Starter Deck` type — NEVER listed by `precon-list`; digital-only |
| MTGO Redemption | digital | `…Redemption_OTJ` / `…FoilRedemption_OTJ` — digital, excluded |
