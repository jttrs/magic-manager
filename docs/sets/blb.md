# `blb` — Bloomburrow

> Per-family memory doc. Read this before answering set-specific questions about
> `blb` or working on `blb`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `blb`
**Family root type:** `expansion`
**Family released:** 2024-08-02 (Bloomburrow — the "woodland critters" Standard set)
**Last audit:** 2026-08-30 via `/characterize-set blb` (steps 1-9).

---

## 1. Family map

| Code | `set_type` | Cards (EN synced) | Notes |
|---|---|---:|---|
| `blb` | expansion | 398 | parent |
| `blc` | commander | 356 | Bloomburrow Commander (4 preconstructed decks) |
| `pblb` | promo | 160 | promos — **80 `promopack`+`stamped` (`Np`) + 80 `prerelease`+`datestamped` (`Ns`)**, both scarcity tiers excluded (see §2/§5) |
| `ablb` | memorabilia | 54 | Art Series (not in default checklist) |
| `yblb` | alchemy | 30 | Alchemy digital-only (globally filtered) |
| `tblb` | token | 30 | tokens |
| `tblc` | token | 41 | commander tokens |

Default `set:blb+related` resolution works. `blb`/`blc`/`pblb` are the
collectable bundle. **Sync gotcha:** a bare `mm set master-list blb` syncs only
`blb`/`blc`; `pblb`/`ablb`/`yblb`/`tblb`/`tblc` are NOT pulled. Run
`mm set sync blb --include-related` to pull the full family — **required before
missing-set is meaningful**, because the 80-card `pblb` `promopack`+`stamped`
scarcity tier is invisible (0 local) until then. The initial audit undercounted
the family for exactly this reason (echoing the ECL/SOS characterization misses).

---

## 2. Treatments

**No dupe-foil signal retained** — `FAMILY_DUPE_FOIL_PROMO_TYPES["blb"] = frozenset()`
(like TLA/SPM/SOS). `raisedfoil` is instead excluded WHOLESALE as a fancy-foil
chase tier via §5 (see the rationale there — a DUPE_FOIL entry would only catch
the 7 that dupe a `boosterfun`-showcase twin, leaving the 14 expensive
sole-showcase raisedfoils in the list).

| promo_type / treatment | Keyword | Dupe? | Notes |
|---|---|---|---|
| `raisedfoil` | `b\|shw\|ff` | n/a — **chase tier, excluded (§5)** | 21 prints, foil-only, the borderless-inverted showcase legends. A fancy-foil CHASE tier the user does not shop for (2026-08-30 — same stance as SNC gilded/stepandcompleat). 7 of them dupe a `boosterfun`-showcase twin (e.g. `blb` 344 Alania `b\|shw\|ff` shares `frame_effects [legendary, showcase, inverted]` with `blb` 327 Alania `b\|shw`), but the other 14 print ONLY in raisedfoil — no regular-foil of that art (Ms. Bumbleflower `blc` 103 ~$1,380, Lumra `blb` 343 ~$802). So DUPE_FOIL is insufficient; the §5 `{raisedfoil}` rule drops all 21. The base + `boosterfun`-showcase prints of each card stay in scope. |
| `boosterfun` (showcase) | `b\|shw` | **no — kept** | The base showcase treatment; the preferred representative. |
| `imagine` | `b` | **no — distinct art** | 28 prints, all in `blc` — borderless-inverted commander legend alt-arts (Ant Queen, Baleful Strix, Birds of Paradise, …). **0 non-imagine siblings** (unique art, not a dupe or a stamp) — KEPT. |
| `promopack` + `stamped` | (stamp) | n/a — scarcity | 80 `pblb` `Np` prints. Same card as a kept base sibling + a promo-pack stamp. Compute to `regular` treatment → grabbed by the rare/mythic-regular sub-selectors (bypass the `preferred` dedup); excluded via §5 `{stamped}` rule. |
| `promopack` (alone) | `b` | **no — distinct alt-art** | 5 prints (`blb` 381-385, inverted frame, NO `stamped`): Hop to It, Shoreline Looter, Fell, Wear Down, Stormcatch Mentor. Distinct borderless alt-arts (base siblings at `blb` 16/70/95/203/234) the user wants — KEPT. The §5 rule keys on `stamped`, sparing these. |
| `prerelease` + `datestamped` | (stamp) | n/a — scarcity | 80 `pblb` `Ns` prints. Auto-dropped by the generic Step-2 datestamped filter (each has a non-datestamped `blb` base sibling); no family rule needed. |
| `alchemy`/`rebalanced` | (digital) | n/a | `yblb` + A-prefixed, globally filtered. |

**Full-art convention:** borderless-inverted showcase (2024 Standard set). No
`textured`/`galaxyfoil`/`fracturefoil` tier.

---

## 3. Chase variants

No uncommon multi-variant chase surfaced. The premium tier is entirely the
borderless-showcase legends: the `raisedfoil` foils (excluded chase, §5) + the
`imagine` BLC commander alt-arts (distinct, kept). **No serialized/headliner
ultra-rare exists in this family** — unusual for a 2024+ set (contrast ECL
Bitterbloom Bearer / SOS Emeritus / TLA Avatar Aang, which all needed a
`{headliner, serialized}` rule); here the expensive tier is the `raisedfoil`
premium foils instead (§5).

---

## 4. Scenes / posters / panoramas

**None.** No contiguous single-artist borderless run ≥3. The `blb` 282-286
"Season of…" cycle spans five different artists (not a panorama); `blb` 337-340
Three Tree City is one card's four land arts by Andrew Mar (a variant set, not a
scene). No `FAMILY_SCENES["blb"]`.

---

## 5. Unobtainable rules

`FAMILY_UNOBTAINABLE_RULES["blb"]` = two rules — `{stamped}` + `{raisedfoil}`
(both added 2026-08-30).

**`{stamped}`** — all 80 `pblb` `promopack`+`stamped` (`Np`) promo-pack scarcity
variants (same card as a kept base sibling + a stamp). **Signal is `stamped`
ONLY** (the SNC/EOE/ECL/SOS lesson): validated all 80 promopack cards also carry
`stamped` (so the rule catches every one), while the 5 `promopack`-ONLY
inverted-frame alt-arts (`blb` 381-385, no `stamped`) are distinct art and KEPT.
A `{promopack}` rule would wrongly drop those 5.

**`{raisedfoil}`** — the 21 `raisedfoil` showcase-legend premium foils, a
fancy-foil CHASE tier the user does not shop for (same stance as SNC
gilded/stepandcompleat). This is why raisedfoil is NOT in DUPE_FOIL: a dupe-foil
entry only drops the 7 raisedfoils that dupe a `boosterfun`-showcase twin, but the
other 14 print ONLY in raisedfoil (no regular-foil of that art) and would survive
— Ms. Bumbleflower `blc` 103 (~$1,380), Lumra `blb` 343 (~$802), Bello `blc` 101
(~$559), Hazel `blc` 102 (~$475), Jace `blc` 93 (~$412), Baylen `blb` 345, Ral
`blb` 353, etc. — **$5,701 of the $7,016 total, 81%.** `any_of:{raisedfoil}`
catches all 21; each card stays in the buy-list via its base/`boosterfun`-showcase
print (Ms. Bumbleflower → `blc` 3 nonfoil ~$5, Lumra → `blb` 183/293/342).

**No serialized/headliner rule** — Bloomburrow has no such ultra-rare tier
(0 serialized/headliner prints in the family), so unlike ECL/SOS/TLA there is no
such rule.

**Missing-set impact:** the two rules drop the family from **484 → 390 prints
($7,302.66 → $1,352.26)** — the `{stamped}` rule removes 80 promo stamps and
`{raisedfoil}` removes the ~$5,700 premium-foil chase tier. The residual $1,352
across 390 prints (~$3.47/card) is a normal "complete the set" cost — legit
regular/showcase rares+mythics, no runaway tier.

Globally filtered (not via a rule): `alchemy`/`rebalanced` (digital); the
`prerelease`+`datestamped` `Ns` promos (auto-dropped by the Step-2 datestamped
filter, §2).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel |
|---|---|---|
| `Np` (e.g. `204p`, `81p`) | `pblb` | Promo pack — 80 `promopack`+`stamped` (excluded via §5) |
| `Ns` (e.g. `204s`, `41s`) | `pblb` | Prerelease datestamped — 80 `prerelease`+`datestamped` (auto-dropped, §2) |
| Borderless alt-art, `blb` 381-385 | `blb` (in-set, `promopack`-only, inverted frame) | Promo-pack alt-art; KEPT in missing-set |

Resolve a PRM-stamped BLB card by name + the `p`/`s` CN suffix per
`.claude/skills/bulk-add/SKILL.md`.

---

## 7. Edge cases & gotchas

- **`pblb` scarcity tier hidden until full sync** — `pblb`/`ablb`/`yblb`/`tblb`/
  `tblc` are all 0-local after a bare `master-list blb`; the 80 `promopack`+
  `stamped` promos only appear after `mm set sync blb --include-related`. The
  `promopack`+`stamped` tier compute to `regular` treatment, so they enter via the
  rare/mythic-regular sub-selectors — a DIFFERENT code path from the `preferred`
  dedup, which is why they must be checked against the ACTUAL missing-set output,
  not the `treatment=preferred` slice (which never sees them). Same trap as
  ECL/SOS.
- **`promopack` alt-art trap (381-385)** — `promopack`-only inverted-frame
  alt-arts (Hop to It / Shoreline Looter / Fell / Wear Down / Stormcatch Mentor),
  distinct art with base siblings, NOT scarcity stamps. The §5 `{stamped}` rule
  correctly spares them. (Same trap as ECL 402-406 / EOE 393-397 / SNC 463-467 /
  SOS 363-367.)
- **`raisedfoil` is a rule, NOT the dupe-foil** — although it computes to `ff`
  (so a DUPE_FOIL entry is *technically* applicable), it's the set's expensive
  chase tier: 14 of the 21 print ONLY in raisedfoil (no regular-foil twin of that
  art), so DUPE_FOIL would leave ~$5,700 of premium foil in the list. It's
  excluded wholesale via `{raisedfoil}` in §5 (same as SNC gilded/stepandcompleat).
  Lesson: "same-art fancy foil" (→ DUPE_FOIL) and "expensive fancy-foil chase the
  user won't buy" (→ UNOBTAINABLE_RULES) can be the SAME promo_type — decide by
  whether a cheaper same-art print of every card exists, not just by the treatment
  keyword. The scarcity-tier value scan (Step 9) is what surfaced this: the
  DUPE_FOIL-only config left an $7,016 total that was 81% raisedfoil foils.
- **No serialized/headliner ultra-rare** — atypical for a 2024+ set; the
  expensive tier is `raisedfoil` (§5) instead.
- **`blc` is a genuine `set_type: commander`.** No topology gotcha.
- **Alchemy** (`yblb` + A-prefixed) — digital-only, globally filtered. 31
  arena-stamped digital cards in the family DB; none leak into missing-set
  (validated via the arena-stamp check — Step 7).

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["blb"]` = `frozenset()`
  — **configured 2026-08-30.** No dupe-foil signal retained (empty set unblocks
  the `preferred` filter without filtering, like TLA/SPM/SOS); raisedfoil is
  excluded wholesale via UNOBTAINABLE_RULES instead. §2.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["blb"]` = two rules —
  `{"promo_types_any_of": {"stamped"}}` (80 `pblb` promo-pack stamps; `stamped`
  not `promopack`, sparing the 5 alt-arts `blb` 381-385) and
  `{"promo_types_any_of": {"raisedfoil"}}` (the 21 premium-foil showcase chases,
  ~$5,700). §5. **No `{headliner, serialized}` rule** — no such tier exists in
  this family.
- No `FAMILY_SCENES["blb"]` (no panoramas — §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific detail:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Bloomburrow Commander (4 decks) | Commander deck | Filed under `blc` (`set_type: commander`, 356 cards). Import via `import-precon`; `source_set_code` hard-links to `blb`. |
| Bloomburrow Art Series | Art Series | `ablb` (54 cards, memorabilia). Not in the default checklist. |
| Promo Pack | promo (`promopack`+`stamped`) | `pblb` `Np` — the 80-card scarcity tier excluded via §5. |
| Prerelease Pack | promo (`prerelease`+`datestamped`) | `pblb` `Ns` — 80-card datestamped tier, auto-dropped (§2). |
