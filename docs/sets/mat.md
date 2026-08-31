# `mat` — March of the Machine: The Aftermath

> Per-family memory doc. Read this before answering set-specific questions about
> `mat` or working on `mat`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mat`
**Family root type:** `expansion`
**Family released:** 2023-05-12 (March of the Machine: The Aftermath — a 50-card "epilogue" micro-set sold in Play/Collector boosters)
**Last audit:** 2026-08-30 via `/characterize-set mat` (steps 1-9).

---

## 1. Family map

| Code | `set_type` | Cards (EN synced) | Notes |
|---|---|---:|---|
| `mat` | expansion | 230 | parent (50 unique cards × several treatments) |
| `pmat` | promo | 8 | promos — all 8 are `promopack`+`stamped` (`Np`) scarcity variants (excluded via §5) |

Tiny two-code family. Default `set:mat+related` resolution works. **Sync gotcha:**
`pmat` is 0-local after a bare `master-list mat`; run `mm set sync mat
--include-related` to pull it — the 8 `promopack`+`stamped` promos are invisible
until then (the SNC/ECL/SOS/BLB/FDN trap, in miniature).

---

## 2. Treatments

**No dupe-foil signal retained** — `FAMILY_DUPE_FOIL_PROMO_TYPES["mat"] = frozenset()`.
`halofoil` is the family's only fancy foil and is excluded WHOLESALE via §5
(not DUPE_FOIL) because of a frame-effect edge case (see below).

| promo_type / treatment | Keyword | Dupe? | Notes |
|---|---|---|---|
| `halofoil` | `shw\|ff` / `b\|shw\|ff` | **yes — excluded via §5** | 43 prints (+`boosterfun`), the "halo foil" premium sheet over the showcase art. Verified: Arni Metalbrow 200 (`halofoil`) shares `illustration_id 732292ff` with the boosterfun-showcase 66. All 43 have a same-art non-halofoil sibling. Excluded via the §5 `{halofoil}` rule rather than DUPE_FOIL — see the Tyvar caveat below. |
| `boosterfun` | `b` / `b\|shw` / `ext` | **no — distinct alt-art** | 178 prints. Standard showcase / borderless-inverted / extended-art alt-arts, KEPT. |
| `ravnicacity` | `shw` | **no — distinct showcase art** | 1 print: Niv-Mizzet, Supreme `mat` 90 (Ravnica-City showcase). KEPT. Its halofoil twin (219, `shw\|ff`) is caught by the §5 halofoil rule. |
| `promopack` + `stamped` | (stamp) | n/a — scarcity | 8 `pmat` `Np` prints. Same card as a kept base sibling + a promo-pack stamp. Excluded via §5 `{stamped}` rule. |

**Full-art convention:** boosterfun showcase/borderless (2023 set). No scenes.

**Tyvar caveat (why halofoil is a §5 rule, not DUPE_FOIL):** DUPE_FOIL drops 42
of 43 halofoils, but MISSES Tyvar the Bellicose 227. Its halofoil is a `showcase`
frame (computes `shw|ff`), while its same-art sibling 98 is `showcase`+`inverted`
(computes `b|shw`). The dupe-foil Step-3 matches siblings by `(name,
codes-minus-ff)`; `{shw}` ≠ `{b,shw}`, so the pair never matches and 227 survives
as a false non-dupe (a $42 foil leak). Excluding the whole `halofoil` treatment
in §5 is exact (all 43 are same-art) and sidesteps the frame-effect mismatch.

---

## 3. Chase variants

No uncommon multi-variant chase surfaced. **No serialized/headliner ultra-rare**
in this family (0 such prints) — it's a small epilogue set. The premium tier is
just the halofoil showcase foils (excluded, §5).

---

## 4. Scenes / posters / panoramas

**None.** Only 11 borderless prints, 5 with `inverted` frames — scattered
(CN 55/82/100/212/228), different artists, non-contiguous. No `FAMILY_SCENES["mat"]`.

---

## 5. Unobtainable rules

`FAMILY_UNOBTAINABLE_RULES["mat"]` = two rules — `{stamped}` + `{halofoil}`
(both added 2026-08-30).

**`{stamped}`** — all 8 `pmat` `promopack`+`stamped` (`Np`) promo-pack scarcity
variants. Validated: all 8 have a non-stamped base sibling in `mat` (50p→50,
4p→4, 22p→22, 23p→23, 43p→43, 6p→6, 34p→34, 9p→9), and all 8 carry BOTH
`promopack`+`stamped` (no `promopack`-only alt-art trap), so `{stamped}` is exact.

**`{halofoil}`** — all 43 same-art fancy-foil showcase prints. A DUPE_FOIL entry
would drop 42 but miss Tyvar 227 (frame-effect codes mismatch, §2); a wholesale
`{halofoil}` exclusion catches all 43. Each card's boosterfun/showcase/base
prints stay in scope.

**No serialized/headliner rule** — no such tier in this family.

**Missing-set impact:** the two rules drop the `preferred` slice from **93 → 51
prints**; full `missing-set mat` ≈ **86 prints / $344** at 0 owned — top prints
are legit mythics (Tyvar 98 ~$26, Nissa Resurgent Animist 72 ~$29, Karn Legacy
Reforged), no scarcity artifact.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel |
|---|---|---|
| `Np` (e.g. `22p`, `4p`) | `pmat` | Promo pack — 8 `promopack`+`stamped` (excluded via §5) |

`pmat` is entirely the 8-card promo-pack tier. Resolve a PRM-stamped MAT card by
name + the `p` CN suffix per `.claude/skills/bulk-add/SKILL.md`.

---

## 7. Edge cases & gotchas

- **halofoil frame-effect mismatch (Tyvar 227)** — the reason halofoil is a §5
  rule not a DUPE_FOIL entry. A same-art fancy foil whose frame_effects differ
  from its base sibling (showcase vs showcase+inverted) computes to different
  treatment codes, breaking the `(name, codes-minus-ff)` sibling match. When a
  DUPE_FOIL entry leaves exactly one straggler, check for this; a wholesale
  `promo_types_any_of` exclusion is the robust fix.
- **`ravnicacity` is a distinct showcase treatment** (Niv-Mizzet, Supreme 90) —
  KEPT. Its halofoil twin 219 is dropped by the halofoil rule.
- **`pmat` hidden until full sync** — 0-local after a bare master-list; the 8
  promo-pack stamps only appear after `--include-related` (SNC/ECL/SOS/BLB/FDN
  trap).
- **Small family, no j25-style companion** — unlike FDN, MAT has no Jumpstart /
  Commander sibling; just the expansion + its promo pack.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["mat"]` = `frozenset()`
  — **configured 2026-08-30.** No dupe-foil signal retained (empty set unblocks
  the `preferred` filter); halofoil is excluded wholesale via UNOBTAINABLE_RULES
  because of the Tyvar frame-effect mismatch. §2.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["mat"]` = two rules —
  `{"promo_types_any_of": {"stamped"}}` (8 `pmat` promo-pack stamps) and
  `{"promo_types_any_of": {"halofoil"}}` (43 same-art fancy foils). §5. **No
  `{headliner, serialized}` rule** — no such tier in this family.
- No `FAMILY_SCENES["mat"]` (no panoramas — §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific detail:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| The Aftermath booster cards | (epilogue micro-set) | 50 unique cards sold in MOM Play/Collector boosters; `mat` expansion code. |
| Promo Pack | promo (`promopack`+`stamped`) | `pmat` `Np` — 8-card scarcity tier excluded via §5. |
