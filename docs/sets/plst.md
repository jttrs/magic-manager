# `plst` — The List

> Per-family memory doc. Read this before answering set-specific questions about
> `plst` or working on `plst`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `plst`
**Family root type:** `masters`
**Family released:** 2020-09-26
**Last audit:** 2026-11-04 via `/characterize-set plst` (one-at-a-time run — tier decisions pending owner review).

---

> **Not a set you complete.** The List is a rolling pool of reprints with a
> small planeswalker-symbol stamp in the lower-left, inserted ~1 in 4 Set /
> Play boosters (and some Collector boosters) since Zendikar Rising. Every
> print reuses the ORIGINAL printing's art and frame, and its collector number
> is `<ORIGINAL SET>-<ORIGINAL CN>` (e.g. `TMP-315` Ancient Tomb). WotC rotates
> the pool every few sets; Scryfall keeps every card that was ever on it.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `plst` | masters | 5,658 local (5,741 Scryfall) | 2020-09-26 | parent — reprints from 301 source sets, CN `<SET>-<CN>`; black border; mostly nonfoil |
| `ulst` | funny | 62 | 2022-10-07 | The List (Unfinity Foil Edition) — 51 rare / 11 mythic, foil-only, CN 1–108 (gaps) |

`set:plst+related` covers both. Top source sets by count: DOM 92, A25 86,
CLB 81, AKH 81, BBD 80, ELD 79, IMA 77, ORI 75. Release dates on rows are
2020-09-26 for nearly all (Scryfall stamps the List's own date), with outliers
2020-03-13 and 2023-05-08.

---

## 2. Treatments

Survey (`survey_treatment_signature.py PLST`, 5,720 prints). There is no
alt-treatment sheet: frames follow the source printing (283 `legendary`, 45
`enchantment`, 21 `tombstone`, 16 `colorshifted`, 14 `devoid` frame effects —
all inherited), so every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| List reprints (nonfoil) | 5,519 | `plst` `<SET>-<CN>` | `regular` | rarity/base sub-selectors — 1,581 R+M ≈ $6.5k nonfoil |
| List reprints (foil-only) | 135 | `plst` mostly old sets (CSP 9, CHK 7, MRD 6, TSB/M11/8ED 5…) | `regular` | rarity/base sub-selectors |
| showcase-black (inherited) | 29 | `plst` reprints of showcase-frame source printings (THB 5, AFR/ELD/ZNR 4 each, IKO/M21 2, ALA/KHM/MAT/MH2/MID/MUL/NEO/ONE 1) | `shw` | kept — this IS the List print of that card, not an alt of another `plst` row; 5 are R+M |
| rarity `special` | 4 | `plst` TSR-302 Silence, TSR-306 Baral, TSR-366 Reclamation Sage, TSB-91 Coalition Victory | `regular` | **never listed by missing-set** (rarity `special` blind spot, see [`tsr`](tsr.md)) |
| product-origin reprints | ~44 | `plst` (`planeswalkerdeck` 14, `starterdeck` 7, `beginnerbox` 7, `startercollection` 5, `brawldeck` 4, `themepack` 3, `gameday` 3, `setextension` 1) | `regular` | promo_types carried from the source printing; not a List-specific variant |
| `ripplefoil` | 4 | `plst` | `regular` | inherited from the source (MB2-era) printing |
| Unfinity Foil Edition | 62 | `ulst` 1–108 | `regular` | foil-only; ~$41 foil total (Earl of Squirrel 108 ~$12) |

**`promo_types` dupe-foil / stamped signals:** none that mark a List-specific
duplicate. Each `plst` row has exactly one physical version (the List stamp).

No `[dupe_foil]` needed for treatments; whether missing-set should run on this
family at all is the real question (§5).

**Full-art convention:** none.

---

## 3. Chase variants

62 uncommons flag as `chase` (`set:plst+related missing rarity=uncommon
treatment=regular chase`) — e.g. Lightning Greaves 2XM-267 foil. The chase
heuristic is price-relative within a family; with 1,948 uncommons from 301
sources it isn't meaningful here.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] plst` | — | **do not add** — leave missing-set disabled for this family. A 1,581-row R+M buy list of stamped reprints (≈ $6.5k) isn't a completion target; the List is collected opportunistically |
| `ulst` Unfinity Foil Edition | 62 | n/a while missing-set is off |
| `special` TSR/TSB 4 | 4 | n/a |

**Scarcity check:** n/a. Top nonfoil: Ancient Tomb TMP-315 ~$128, Rhystic
Study PCY-45 ~$69, Esper Sentinel MH2-12 ~$68, Demonic Tutor UMA-93 / DDC-49
~$65 / ~$62.

---

## 6. PRM destinations

n/a — the List is itself the destination. A stamped reprint in hand goes to
`plst` `<source set>-<source CN>`, NOT to the source set; check for the small
planeswalker icon in the lower-left corner.

---

## 7. Edge cases & gotchas

- **Identify by stamp, file by source CN.** `plst` `M19-312` is the List copy
  of M19 312; it shares art with `m19` 312 but is a distinct printing.
- **The same card can appear under several source CNs** (Demonic Tutor
  UMA-93 and DDC-49): 5,658 prints over 5,319 oracle cards.
- **Local catalog lags Scryfall** (5,658 vs 5,741) — the pool grows with each
  new set; re-sync before checking a newly opened List card.
- `ulst` is a separate code with plain CNs, not `<SET>-<CN>`.
- Mystery Booster's "playtest"/`cmb*` cards and Secret Lair are NOT here.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.plst.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.plst]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| The List slot | booster slot (in other sets' Set/Play/Collector boosters) | ~1 in 4 Set/Play boosters, ZNR onward; Unfinity Collector boosters carry `ulst` |

**Booster types (for `sealed-value` EV):** none (`sealed_value.py plst
--list-boosters` → "no booster data in MTGJSON"). List odds live in the host
sets' booster sheets.
