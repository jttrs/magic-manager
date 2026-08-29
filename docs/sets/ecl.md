# `ecl` — Lorwyn Eclipsed

> Per-family memory doc. Read this before answering set-specific questions about
> `ecl` or working on `ecl`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ecl`
**Family root type:** `expansion`
**Family released:** 2025 (Lorwyn Eclipsed — a Lorwyn/Shadowmoor-callback set)
**Last audit:** 2026-08-26 via `/characterize-set ecl` (steps 1-9).

---

## 1. Family map

| Code | `set_type` | Cards | Notes |
|---|---|---:|---|
| `ecl` | expansion | 408 | parent |
| `ecc` | commander | 176 | Lorwyn Eclipsed Commander |
| `pecl` | promo | 80 | promos — **all 80 are `promopack`+`stamped`** scarcity variants (excluded via §5) |
| `aecl` | memorabilia | 54 | Art Series (not in default checklist) |
| `yecl` | alchemy | 30 | Alchemy digital-only (globally filtered) |
| `tecc` | token | 13 | commander tokens |
| `tecl` | token | 13 | tokens |

Default `set:ecl+related` resolution works. `ecl`/`ecc`/`pecl` are the collectable
bundle (expansion/commander/promo). No separately-rooted bonus sheet gotcha.

---

## 2. Treatments

**`fracturefoil` is ECL's fancy-foil dupe signal** (same pattern as EOE).

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `fracturefoil` | `ff` (+`b`/`shw`) | **yes** → `FAMILY_DUPE_FOIL_PROMO_TYPES` | 10 prints, foil-only, `fracturefoil+japanshowcase` on a showcase+inverted frame. Every one has an exact same-name **japanshowcase-only** sibling (`b|shw`) — same showcase art, just the fracture-foil sheet. Verified on Bloodline Bidding: 385 (`b\|shw`, japanshowcase) ↔ 395 (`b\|shw\|ff`, fracturefoil). Computes to `ff`, so DUPE_FOIL catches it. Keeps the japanshowcase print. |
| `japanshowcase` | `b`/`shw` | **no — distinct showcase art** | 20 prints. The showcase mythics/rares; kept as the preferred representative (its fracturefoil twin is the dupe). |
| `promopack` (alone) | `b` | **no — distinct alt-art** | 5 prints (`ecl` 402-406, inverted frame, NO `stamped`). Borderless alt-arts the user wants — NOT a scarcity stamp. See §5. |
| `promopack` + `stamped` | (stamp) | n/a — scarcity | 80 `pecl` `Np` prints. Same card as a kept base/showcase sibling + a promo stamp. Excluded via the §5 `{stamped}` rule (signal is `stamped`, sparing the 5 `promopack`-only alt-arts above). |
| `headliner` + `serialized` + `doublerainbow` | (chase) | n/a | 1 print (`ecl` 352 Bitterbloom Bearer) — the set headline serialized ultra-rare. §5. |
| `alchemy`/`rebalanced` | (digital) | n/a | yecl + A-prefixed, globally filtered. |

**Full-art convention:** borderless-inverted showcase cards — verify if a
question arises; this is a 2025 UB-style set.

---

## 3. Chase variants

No uncommon multi-variant chase surfaced at threshold 3. The borderless-inverted
range (`ecl` 284-296) is the showcase/legendary alt-art run; the japanshowcase
(20) + fracturefoil (10) mythics are the premium chases, handled via §2.

---

## 4. Scenes / posters / panoramas

**None.** The borderless-inverted range (`ecl` 284-296, 347-351) is individual
showcase cards + shockland reprints by mixed artists (Greg Staples, Jesper
Ejsing, …) — not a contiguous single-artist panorama. No `FAMILY_SCENES["ecl"]`.

---

## 5. Unobtainable rules

`FAMILY_UNOBTAINABLE_RULES["ecl"]` = a `{headliner, serialized}` rule + a
`{stamped}` rule
(added 2026-08-26).

**Rationale.** `ecl` 352 Bitterbloom Bearer is the set's headline serialized
ultra-rare (`doublerainbow + headliner + serialized`, foil-only) — the analog of
EOE's Sothera / TLA's Avatar Aang. The user doesn't shop for it. `any_of` catches
this single print (headliner and serialized co-occur here). The base/showcase
Bitterbloom Bearer prints (`ecl` 88, 310) remain in scope.

**`stamped` scarcity rule (added 2026-08-28 — corrects a characterization
error).** The original audit wrongly claimed "`pecl` has 0 stamped"; in fact
**all 80 `pecl` cards are `promopack`+`stamped`** — the promo-pack scarcity tier,
same as SNC/EOE. They surfaced in `missing-set` (80 of 252 prints) until the
`{stamped}` rule was added. Validated: all 80 have a non-stamped base/showcase
sibling (safe to drop), and the **signal is `stamped` ONLY** — the 5
`promopack`-ONLY alt-arts (`ecl` 402-406, inverted frame, no `stamped`) are
distinct art and are KEPT (a `promopack` rule would wrongly drop them).

Globally filtered (not via a rule): `alchemy`/`rebalanced` (digital),
`serialized` (caught by the global unobtainable set).

**Missing-set impact:** the `{stamped}` rule drops the family from **252 → 172
prints ($731 → ~$491)** at 427 owned. Top remaining prints are legit
japanshowcase mythics (Bloom Tender `ecl` 390) + shocklands — no runaway
scarcity tier.

---

## 6. PRM destinations

| Physical stamp | Scryfall set | Channel |
|---|---|---|
| Promo-pack alt-art, CN 402-406 | `ecl` (in-set, `promopack`-only, inverted frame) | Promo pack alt-art (NOT a `p*` set); KEPT in missing-set |
| Promo-pack STAMP, CN `Np` (e.g. `20p`, `242p`) | `pecl` | Promo pack — all 80 are `promopack`+`stamped` (excluded via §5) |

`pecl` is entirely the `promopack`+`stamped` scarcity tier (§5). Resolve a
PRM-stamped ECL card by name + artist per `.claude/skills/bulk-add/SKILL.md`.

---

## 7. Edge cases & gotchas

- **`fracturefoil` is the EOE-style dupe-foil** — same-art fracture-foil sheet
  over the japanshowcase showcase; maps to `ff`, so DUPE_FOIL (not
  UNOBTAINABLE_RULES) is correct. Contrast SNC `stepandcompleat` (treatment `b`,
  needed UNOBTAINABLE_RULES).
- **`promopack` alt-art trap (402-406)** — `promopack`-only inverted-frame alt-arts,
  NOT scarcity stamps. The `{stamped}` §5 rule correctly spares them (they lack
  `stamped`); a `promopack` rule would wrongly drop them. (Same trap as EOE
  393-397 / SNC 463-467.)
- **Characterization miss (2026-08-28):** the initial audit reported "`pecl` has
  0 stamped" and skipped the scarcity rule — wrong; all 80 `pecl` are
  `promopack`+`stamped` and leaked into missing-set until the `{stamped}` rule
  was added. Lesson: re-run the Step-9 scarcity check against the ACTUAL
  missing-set output, not just a promo_types frequency scan (the frequency scan
  is what misled here — likely run before `pecl` was fully synced).
- **`ecc` is a genuine `set_type: commander`.** No topology gotcha.
- **Alchemy** (`yecl` + A-prefixed) — digital-only, globally filtered.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["ecl"]` = `frozenset({"fracturefoil"})`
  — **configured 2026-08-26.** Drops the 10 fracturefoil dupes, keeps the
  japanshowcase showcase prints. §2.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["ecl"]` = two rules —
  `{"promo_types_any_of": {"headliner", "serialized"}}` (Bitterbloom Bearer
  headline serialized `ecl` 352, configured 2026-08-26) and
  `{"promo_types_any_of": {"stamped"}}` (the 80 `pecl` promo-pack stamps, added
  2026-08-28 to fix the characterization miss; `stamped` not `promopack`, sparing
  the 5 alt-arts `ecl` 402-406). §5.
- No `FAMILY_SCENES["ecl"]` (no panoramas — §4).
