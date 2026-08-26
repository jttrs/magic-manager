# `eoe` — Edge of Eternities

> Per-family memory doc. Read this before answering set-specific questions about
> `eoe` or working on `eoe`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `eoe`
**Family root type:** `expansion`
**Family released:** 2025 (Edge of Eternities)
**Last audit:** 2026-08-23 — **manual, partial.** Written to capture the
japanshowcase inclusion directive (§2 / §5 / §7); NOT a full `/characterize-set`
audit. Run `/characterize-set eoe` before relying on §3 / §4 / §6.

---

## 1. Family map

| Code | `set_type` | Cards | Notes |
|---|---|---:|---|
| `eoe` | expansion | 400 | parent |
| `eoc` | commander | 191 | Edge of Eternities Commander |
| `eos` | masterpiece | 180 | Edge of Eternities: Stellar Sights (bonus sheet) |
| `peoe` | promo | 160 | promos |
| `aeoe` | memorabilia | 54 | Art Series (not in default checklist) |
| `yeoe` | alchemy | 40 | Alchemy digital-only (globally filtered) |
| `teoe` | token | 12 | tokens (not in default checklist) |
| `teoc` | token | 16 | commander tokens (not in default checklist) |

Default `set:eoe+related` resolution works — no separately-rooted bonus sheet
gotcha observed. `eoc`/`eos`/`peoe` are all pulled into the default inventory
bundle (expansion/commander/masterpiece/promo); `eternal` n/a for this family.

---

## 2. Treatments

**⚠️ `japanshowcase` gap — the reason this doc exists (see §5, §7).**

`eoe` has **20 `japanshowcase` mythics** in two parallel CN ranges, same 10 card
names in each:

| CN range | promo_types | treatment | Notes |
|---|---|---|---|
| `eoe` 357–366 | `japanshowcase + boosterfun` | `b\|shw` | showcase art, foil-only |
| `eoe` 383–392 | `fracturefoil + japanshowcase + boosterfun` | `b\|shw\|ff` | same showcase art on a fracture-foil sheet (fancy-foil dupe of the 357–366 print) |

The 10 names: Anticausal Vestige, Exalted Sunborn, Starfield Vocalist, Sothera
the Supervoid, Devastating Onslaught, Icetill Explorer, Mutinous Massacre, The
Dominion Bracelet, The Endstone, Secluded Starforge. (357↔383 = Anticausal
Vestige, …, 366↔392 = Secluded Starforge — same order in both ranges.)

All are **mythic, foil-only** (`finishes: ["foil"]`).

**Why they're missing from the inventory checklist:** `japanshowcase` is in
`sets.EXCLUDED_PROMO_TYPES` (`src/magic_manager/sets.py`), so `mm set master-list`
drops every one of these 20 by design. **Do not change the checklist** (per user
direction) — the exclusion stays. The user catalogs any they own via a direct
`mm inventory add <scryfall_id> foil` (e.g. The Dominion Bracelet `eoe` 364,
added 2026-08-23). The gap to fix is the *missing-set* side (§5).

---

## 3. Chase variants

**Not yet audited.** Run `/characterize-set eoe`.

---

## 4. Scenes / posters / panoramas

**Not yet audited.** Run `/characterize-set eoe`.

---

## 5. Unobtainable rules — and the japanshowcase INCLUSION directive

`FAMILY_DUPE_FOIL_PROMO_TYPES["eoe"]` = `frozenset({"fracturefoil"})` — **configured 2026-08-23.**
`FAMILY_UNOBTAINABLE_RULES["eoe"]` = `{headliner, singularityfoil, galaxyfoil}`
(configured 2026-08-23) + a `{stamped}` rule (added 2026-08-26).

**User directive (2026-08-23):** when asked "what am I missing from EOE?", the
`japanshowcase` showcase mythics (`eoe` 357–366, treatment `b|shw`) **should be
included** in the missing-set output. They are distinct art the user wants to
complete — the checklist exclusion (§2) is about what the *generator* seeds, not
about what the user is allowed to want. **Honored:** `mm query missing-set eoe`
now surfaces 357–366 (357–363, 365, 366 currently; 364 owned) and drops the
383–392 fracturefoil dupes (verified 2026-08-23).

**Dupe-foil (`fracturefoil`).** The 383–392 range is the same showcase art as
357–366 on a fracture-foil sheet → dupe. Verified on The Dominion Bracelet:
`eoe` 364 (`b|shw`) and 390 (`b|shw|ff`) share art. The entry keeps 357–366 as
the "preferred" representative and drops 383–392. Mirrors the TMNT case exactly
(TMT also pairs `fracturefoil` dupe with kept-`japanshowcase`).

**Unobtainable chase (excluded from missing-set).** Without this rule the family
total was an absurd **$7,729.61 / 320 prints**; the rule brings it to the
realistic **$1,931.76 / 217 prints** (−$5,797.85). Excludes:

| Signal | What it catches | ~Value removed |
|---|---|---|
| `headliner` / `singularityfoil` | `eoe` 382 Sothera, the Supervoid — the set headline ultra-rare (poster + singularityfoil), 1 print. Analog of TLA's Avatar Aang headliner. | ~$1,223 |
| `galaxyfoil` | Stellar Sights (`eos`) premium foil masterpiece lands + a few `eoe` galaxyfoil mythics (Ancient Tomb, Mana Confluence, Gemstone Caverns, …), 105 prints across `eoe`+`eos`. The *non*-galaxyfoil EOS print of the same card stays in scope (e.g. `eos` 1/46 Ancient Tomb boosterfun). | ~$4,575 |
| `stamped` | promo-pack/prerelease STAMP variants (80 prints, mostly `peoe`) — same card as a kept base/boosterfun sibling, priced on scarcity (Quantum Riddler `peoe` 72p ~$38 vs base `eoe` 72 + boosterfun `eoe` 305, both kept). Added 2026-08-26, mirroring SNC. **Signal is `stamped` ONLY** — validated all 80 dupes carry `stamped`, while 5 borderless alt-arts (`eoe` 393-397, inverted frame) are `promopack` WITHOUT `stamped` and are KEPT. | ~$291 |

`any_of` within each rule. Effect of the `stamped` rule: **$1,951.95 / 217 →
~$1,641 / 137 prints.** (The bulk of the remaining total is the `eos` masterpiece
land sheet, intentionally KEPT — see the Note below.)

**Note:** the residual list is still topped by `eos` boosterfun masterpiece
lands (Ancient Tomb `eos` 46 ~$169, 1 ~$121, Gemstone Caverns ~$86, …) — the
"regular" (non-galaxyfoil) Stellar Sights sheet. Those are intentionally KEPT.
If the user later decides the whole `eos` masterpiece sheet is out of scope,
that's a set-code scope decision (drop `eos` from the family), not a
treatment-rule change — do not conflate.

---

## 6. PRM destinations

**Not yet audited.** Run `/characterize-set eoe`.

---

## 7. Edge cases & gotchas

- **japanshowcase mythics absent from the inventory checklist** — 20 cards
  (`eoe` 357–366 + 383–392), foil-only, excluded by
  `sets.EXCLUDED_PROMO_TYPES`. Checklist stays as-is; catalog owned copies via
  `mm inventory add`. See §2 / §5.
- **The two showcase ranges are art-identical, foil-differentiated** — 357–366
  is plain showcase foil (`b|shw`), 383–392 is the fracture-foil version of the
  same art (`b|shw|ff`). Treat 383–392 as fancy-foil dupes of 357–366 for
  missing-set purposes (§5 step 1).
- **`yeoe` Alchemy** — digital-only, globally filtered (rebalanced/alchemy). Not
  a physical concern.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["eoe"]` = `frozenset({"fracturefoil"})`
  — **configured 2026-08-23.** Unblocks `mm query missing-set eoe`; keeps the
  357–366 japanshowcase showcase prints, drops the 383–392 fracturefoil dupes.
  See §5.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["eoe"]` = two rules —
  `{"promo_types_any_of": {"headliner", "singularityfoil", "galaxyfoil"}}`
  (configured 2026-08-23; Sothera headliner + galaxyfoil masterpiece tier,
  $7,729→$1,952) and `{"promo_types_any_of": {"stamped"}}` (added 2026-08-26;
  80 promo-pack/prerelease stamps, mostly `peoe`, $1,952→~$1,641; `stamped` not
  `promopack`, sparing the 5 `eoe` 393-397 borderless alt-arts). See §5.
- `sets.py:EXCLUDED_PROMO_TYPES` — contains `japanshowcase`; this is why the 20
  showcase mythics are absent from `mm set master-list eoe`. Intentionally left
  unchanged (checklist-side exclusion per user direction).
- Full audit pending: run `/characterize-set eoe` to populate §3, §4, §6.
