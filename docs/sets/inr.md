# `inr` — Innistrad Remastered

> Per-family memory doc. Read this before answering set-specific questions about
> `inr` or working on `inr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `inr`
**Family root type:** `masters` (reprint set — no expansion parent)
**Family released:** `2025-01-24`
**Last audit:** `2026-09-03` via `/characterize-set inr`.

---

## 1. Family map

3 Scryfall codes, all linked via `parent_set_code` (clean, tiny graph — a
Masters reprint set has no Commander/promo siblings, unlike a modern expansion).

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `inr` | masters | 495 | 2025-01-24 | parent — reprint-only remaster of the original Innistrad block |
| `ainr` | memorabilia | 25 | 2025-01-24 | Art Series (all `stamped`, signed/numbered art cards) |
| `tinr` | token | 27 | 2025-01-24 | tokens |

`mm set master-list inr` / `set:inr+related` resolve the whole family from the
parent — no `--only` needed. **No promo set** (`pinr`) exists: Innistrad
Remastered had no prerelease/promo-pack channel (draft-only reprint product), so
there is no `Ns`/`Np` PRM destination for this family (see §6).

**Sync note:** `mm set sync inr --include-related` pulls all 3 codes (547 prints).

---

## 2. Treatments

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `shw` / `b` / `ext` (frame-dependent) | n/a (structural) | showcase/borderless/extended frames; KEPT |
| `poster` (+`boosterfun`) | `shw` | **no — distinct showcase art, KEPT** | INR 481-490 — the borderless "poster" showcase mythics/rares (Avacyn 482, Emrakul 481, Edgar Markov, Griselbrand, Meathook Massacre 486, …). Distinct showcase illustration vs the base reprint (Avacyn 482 vs base 477). A normal collectible showcase tier the user shops for. Computes to `shw`, not `ff` |
| `serialized` + `headliner` + `doublerainbow` (+`poster`+`boosterfun`) | `shw\|ff` | scarcity → dropped by GLOBAL filter | INR 491 Edgar Markov — the family's headline ultra-rare, foil-only, ~$2,825. Carries `serialized`, which is in the GLOBAL `UNOBTAINABLE_PROMO_TYPES` — so it never reaches missing-set. **No per-family rule needed** (verified: a `headliner`/`serialized` rule has zero effect; the global filter already drops it) |
| `stamped` | `''` (no keyword) | art-series signature | AINR 11-35 — the 25 Art Series cards, all `stamped` (signed/numbered art prints). Compute to empty treatment; art-series memorabilia, not a card variant |
| `release` | (frame of base) | promo | INR 492 Deadeye Navigator — a release/promo print. Singleton |

**Full-art convention:** standard (borderless/showcase carry `border_color:
borderless` or `frame_effects: showcase`; `full_art` not relied upon).

**No same-art fancy-foil dupe sheet** — INR has no surgefoil/galaxyfoil/
manafoil/gilded-style treatment. The `poster` showcases are distinct art. So
`FAMILY_DUPE_FOIL_PROMO_TYPES["inr"]` is an **empty frozenset** — it satisfies
the `treatment=preferred` config requirement without filtering anything (same
pattern as TLA/SPM/SOS/MAT/NEO/BLB).

---

## 3. Chase variants

The bare `chase` modifier surfaces only **Sorin, Imperious Bloodlord** (INR 133
base, 322 showcase, 476 borderless — 3 distinct arts of the same card) plus the
`tinr` Zombie tokens (3 art variants). Neither is a scarcity tier — the Sorin
prints are the normal base/showcase/borderless trio, all shoppable.

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Sorin, Imperious Bloodlord | 3 | `inr` 133 / 322 / 476 | mythic | regular / shw / b |
| Zombie (token) | 3 | `tinr` 10-12 | common | regular |

No multi-art booster chase beyond these — a remaster's variety comes from the
base/showcase/borderless/poster tiers of *different* cards, not multi-art of one.

---

## 4. Scenes / posters / panoramas

**None.** The INR borderless-inverted block (INR ~298-321+) is a **mixed-artist**
run (Cynthia Sheppard, Winona Nelson, Aurore Folny, Marta Nael, Dave Kendall,
…) — individual borderless reprints, NOT a single-artist contiguous scene. The
`poster`-tagged prints (INR 481-490) are individual showcase cards, not a
panorama set (unlike LTR 731-750). Not encoded in `FAMILY_SCENES`.

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["inr"]` in `src/magic_manager/selectors.py`.

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {headliner, serialized}` | INR 491 Edgar Markov (serialized + headliner + doublerainbow, foil-only, ~$2,825) — the family's headline ultra-rare. Analog of EOE Sothera / ECL Bitterbloom Bearer / SOS Emeritus. **Documented no-op:** `serialized` is already in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so Edgar 491 is filtered before this rule applies (verified: identical 178-print/$940 result with and without it). Kept for parity/discoverability with the other headliner families |

- No `stamped` promo-pack tier to exclude — the 25 `stamped` prints are all AINR
  Art Series memorabilia (excluded from missing-set by the default family filter,
  which drops `memorabilia`), not main-set promo stamps.

**Missing-set baseline (recorded 2026-09-03):** with the empty-DUPE_FOIL config,
`missing-set inr` = **178 prints / ~$940**, top by value being normal reprint
mythics (Avacyn 482 ~$42, Edgar Markov 234 ~$42, Meathook Massacre 486 ~$38,
Emrakul 481 ~$38) — a clean list, no hidden scarcity tier.

---

## 6. PRM destinations

**None.** Innistrad Remastered shipped as a draft-only reprint set with **no
prerelease/promo-pack channel** — there is no `pinr` set, no `Ns`/`Np` stamped
promos. If a user presents a "PRM"-stamped Innistrad card, it's from an original
Innistrad-block set (ISD/DKA/SOI/EMN/MID/VOW) or a Secret Lair, not this family.

---

## 7. Edge cases & gotchas

- **Parent `set_type` is `masters`**, not `expansion` — a reprint remaster. It's
  still in `DEFAULT_INVENTORY_SET_TYPES`? No — `masters` is NOT in that frozenset
  ({expansion, commander, masterpiece, promo, eternal}), but the anchor is always
  included by `filtered_codes()` regardless, so `inr` itself is in scope; `ainr`
  (memorabilia) and `tinr` (token) are excluded by default (opt in via
  `--include memorabilia,token`). Confirmed master-list/missing-set operate on
  `inr` correctly.
- **No arena leak** — `set:inr+related missing | grep arena` returns nothing
  (verified); no alchemy child exists for a paper-only remaster.
- **DFC / meld:** original-Innistrad meld pairs (e.g. Bruna/Gisela → Brisela) and
  transform cards reprint normally; no meld-back-only CNs observed.
- **Edgar Markov appears 4×** in the family: base (234), showcase (328),
  borderless (428), and the serialized poster headliner (491). Only 491 is
  filtered (serialized); the other three are normal shoppable prints.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["inr"]` — **configured**: `frozenset()` (empty — no dupe-foil sheet; unblocks `treatment=preferred`).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["inr"]` — **configured** (documented no-op): `[{"promo_types_any_of": frozenset({"headliner", "serialized"})}]`. Edgar 491 is already caught by the global filter; kept for parity with ECL/SOS. See §5.
- `FAMILY_SCENES["inr"]` — not configured (no single-artist scene; see §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Innistrad Remastered Art Series | Art Series | `ainr` (25 cards, all `stamped`) |
| — (no Commander / Bundle / precon products) | — | A draft-only reprint set; no sealed precon/deck products, no promo channel |
