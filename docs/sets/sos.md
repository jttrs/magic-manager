# `sos` — Secrets of Strixhaven

> Per-family memory doc. Read this before answering set-specific questions about
> `sos` or working on `sos`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `sos`
**Family root type:** `expansion`
**Family released:** 2025 (Secrets of Strixhaven — a Strixhaven-callback set with a Mystical Archive reprint sheet)
**Last audit:** 2026-08-28 via `/characterize-set sos` (steps 1-9).

---

## 1. Family map

| Code | `set_type` | Cards (EN synced) | Notes |
|---|---|---:|---|
| `sos` | expansion | 368 | parent |
| `soc` | commander | 426 | Secrets of Strixhaven Commander |
| `soa` | masterpiece | 65 EN (195 w/ JP) | **Mystical Archive** reprint sheet — borderless-showcase spell reprints (Force of Will, Vampiric Tutor, Cyclonic Rift, …). The ~130 non-English JP-alt-art prints are NOT synced (English-only sync filter) — expected. |
| `psos` | promo | 80 | promos — **all 80 are `promopack`+`stamped`** scarcity variants (excluded via §5) |
| `asos` | memorabilia | 54 | Art Series (not in default checklist) |
| `ysos` | alchemy | 30 | Alchemy digital-only (globally filtered) |
| `tsoc` | token | 30 | commander tokens |
| `tsos` | token | 14 | tokens |

Default `set:sos+related` resolution works. `sos`/`soc`/`soa`/`psos` are the
collectable bundle. **Sync gotcha:** `soa` is a separate masterpiece code — a
bare `mm set master-list sos` syncs sos/psos/soc but NOT soa/ysos/asos; run
`mm set sync sos --include-related` to pull the full family (needed before
missing-set is meaningful — the audit initially missed soa entirely).

---

## 2. Treatments

**No fancy-foil dupe signal** — `FAMILY_DUPE_FOIL_PROMO_TYPES["sos"] = frozenset()`
(like TLA/SPM). The entry is required to unblock the `treatment=preferred` filter
even though it filters nothing.

| promo_type / treatment | Keyword | Dupe? | Notes |
|---|---|---|---|
| `soa` Mystical Archive | `b\|shw` | **no — distinct art** | 65 EN borderless-showcase spell reprints, nonfoil+foil. Each is unique art (the whole point of the Archive); no etched-foil dupe pattern in the English prints. Kept. |
| `promopack` + `stamped` | (stamp) | n/a — scarcity | 80 `psos` `Np` prints. Same card as a kept base sibling + a promo stamp. Excluded via §5 `{stamped}` rule. |
| `promopack` (alone) | `b` | **no — distinct alt-art** | 5 prints (`sos` 363-367, the guild Charms, inverted frame, NO `stamped`). Alt-arts the user wants — KEPT. The §5 rule keys on `stamped`, sparing these. |
| `headliner`+`serialized`+`rainbowfoil` | (chase) | n/a | 1 print (`sos` 306 Emeritus of Ideation // Ancestral Recall, ~$2,900). §5. |
| `alchemy`/`rebalanced` | (digital) | n/a | ysos + A-prefixed, globally filtered. |

---

## 3. Chase variants

No uncommon multi-variant chase surfaced. The premium tier is the `soa` Mystical
Archive (distinct-art reprints, kept) + the single serialized headliner (§5).

---

## 4. Scenes / posters / panoramas

**None.** No contiguous single-artist borderless run. No `FAMILY_SCENES["sos"]`.

---

## 5. Unobtainable rules

`FAMILY_UNOBTAINABLE_RULES["sos"]` = a `{headliner, serialized}` rule + a
`{stamped}` rule (added 2026-08-28).

**`{headliner, serialized}`** — `sos` 306 Emeritus of Ideation // Ancestral Recall,
the serialized headline chase (`headliner + rainbowfoil + serialized`, foil-only,
~$2,900). Analog of EOE Sothera / TLA Avatar Aang / ECL Bitterbloom Bearer.

**`{stamped}`** — all 80 `psos` cards are `promopack`+`stamped` promo-pack
scarcity variants (same card as a kept base sibling + a stamp). **Signal is
`stamped` ONLY** (the SNC/EOE/ECL lesson): validated all 80 have a non-stamped
sibling (safe to drop), while the 5 `promopack`-ONLY guild Charm alt-arts
(`sos` 363-367, no `stamped`) are distinct art and KEPT.

**Missing-set impact:** at 0 owned, `set:sos+related missing` ≈ **456 prints /
~$944** (full unowned universe; shrinks as inventory lands). Top prints are the
`soa` Mystical Archive reprints (Force of Will ~$64, Vampiric Tutor ~$56) — legit,
kept. No runaway scarcity tier after the two rules.

Globally filtered (not via a rule): `alchemy`/`rebalanced` (digital); `serialized`
(also caught by the global unobtainable set + the headliner rule).

---

## 6. PRM destinations

| Physical stamp | Scryfall set | Channel |
|---|---|---|
| Promo-pack STAMP, CN `Np` (e.g. `140p`, `7p`) | `psos` | Promo pack — all 80 are `promopack`+`stamped` (excluded via §5) |
| Guild Charm alt-art, `sos` 363-367 | `sos` (in-set, `promopack`-only) | Promo-pack alt-art; KEPT in missing-set |

Resolve a PRM-stamped SOS card by name + the `p` CN suffix per
`.claude/skills/bulk-add/SKILL.md`.

---

## 7. Edge cases & gotchas

- **`soa` (Mystical Archive) is a separate masterpiece code** — not synced by a
  bare `master-list sos`; use `--include-related`. The initial audit undercounted
  the family because soa/psos were empty until the full sync (echoing the ECL
  characterization miss). Lesson reinforced: verify the family is fully synced
  AND check the actual missing-set output before trusting a promo_types scan.
- **JP-alternate-art Mystical Archive prints not synced** — soa is 195 total but
  only 65 English; the ~130 JP-alt prints are excluded by the English-only sync.
  Not a concern for a physical English collection.
- **`promopack` alt-art trap (363-367)** — the guild Charms are `promopack`-only
  (no `stamped`); the §5 `{stamped}` rule correctly spares them. (Same trap as
  ECL 402-406 / EOE 393-397 / SNC 463-467.)
- **`soc` is a genuine `set_type: commander`.** No topology gotcha.
- **Alchemy** (`ysos` + A-prefixed) — digital-only, globally filtered.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["sos"]` = `frozenset()` —
  **configured 2026-08-28.** No dupe-foil signal (empty set unblocks the
  `preferred` filter, filters nothing). §2.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["sos"]` = two rules —
  `{"promo_types_any_of": {"headliner", "serialized"}}` (sos 306 serialized
  headliner) and `{"promo_types_any_of": {"stamped"}}` (80 psos promo-pack
  stamps; `stamped` not `promopack`, sparing the 5 Charm alt-arts sos 363-367).
  §5.
- No `FAMILY_SCENES["sos"]` (no panoramas — §4).
