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
| `pecl` | promo | 80 | promos (**no stamped scarcity tier** — see §5) |
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

`FAMILY_UNOBTAINABLE_RULES["ecl"]` = one rule excluding `headliner`/`serialized`
(added 2026-08-26).

**Rationale.** `ecl` 352 Bitterbloom Bearer is the set's headline serialized
ultra-rare (`doublerainbow + headliner + serialized`, foil-only) — the analog of
EOE's Sothera / TLA's Avatar Aang. The user doesn't shop for it. `any_of` catches
this single print (headliner and serialized co-occur here). The base/showcase
Bitterbloom Bearer prints (`ecl` 88, 310) remain in scope.

**No `stamped`/`promopack` scarcity rule** (unlike SNC/EOE). Verified: `pecl` has
**0 stamped** prints, and the only `promopack` cards (`ecl` 402-406) are
`promopack`-ONLY borderless alt-arts (inverted frame, no `stamped`) — distinct
art the user wants, NOT the scarcity-stamp tier. A `promopack` rule would wrongly
drop these 5; none is warranted.

Globally filtered (not via this rule): `alchemy`/`rebalanced` (digital),
`serialized` also caught by the global unobtainable set.

**Missing-set impact:** with the config, `set:ecl+related missing` ≈ **$697 /
272 prints** (the full unowned universe — the user owns 0 ECL as of this audit;
the number will shrink as inventory lands). No runaway chase/scarcity tier
inflating it — top prints are legit japanshowcase mythics (Bloom Tender `ecl` 390
~$62) + shocklands.

---

## 6. PRM destinations

| Physical stamp | Scryfall set | Channel |
|---|---|---|
| Promo-pack, CN 402-406 | `ecl` (in-set, `promopack` alt-art) | Promo pack (NOT a `p*` set) |
| Other promos | `pecl` | promos |

`pecl` carries no datestamped/stamped scarcity tier. Resolve a PRM-stamped ECL
card by name + artist per `.claude/skills/bulk-add/SKILL.md`.

---

## 7. Edge cases & gotchas

- **`fracturefoil` is the EOE-style dupe-foil** — same-art fracture-foil sheet
  over the japanshowcase showcase; maps to `ff`, so DUPE_FOIL (not
  UNOBTAINABLE_RULES) is correct. Contrast SNC `stepandcompleat` (treatment `b`,
  needed UNOBTAINABLE_RULES).
- **`promopack` alt-art trap (402-406)** — `promopack`-only inverted-frame alt-arts,
  NOT scarcity stamps. Do NOT add a `promopack` unobtainable rule; it would drop
  distinct art the user wants. (Same trap as EOE 393-397 / SNC 463-467.)
- **`ecc` is a genuine `set_type: commander`.** No topology gotcha.
- **Alchemy** (`yecl` + A-prefixed) — digital-only, globally filtered.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["ecl"]` = `frozenset({"fracturefoil"})`
  — **configured 2026-08-26.** Drops the 10 fracturefoil dupes, keeps the
  japanshowcase showcase prints. §2.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["ecl"]` = `[{"promo_types_any_of":
  frozenset({"headliner", "serialized"})}]` — **configured 2026-08-26.** Excludes
  the Bitterbloom Bearer headline serialized (`ecl` 352). §5.
- No `FAMILY_SCENES["ecl"]` (no panoramas — §4).
- No stamped/promopack unobtainable rule (no scarcity tier — §5).
