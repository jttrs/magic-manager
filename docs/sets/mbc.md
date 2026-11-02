# `mbc` — Mystery Booster Commander Edition

> Per-family memory doc. Read this before answering set-specific questions about
> `mbc` or working on `mbc`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mbc`
**Family root type:** `draft_innovation`
**Family released:** 2026-10-19
**Last audit:** 2026-11-01 via `/characterize-set mbc` (steps 1-9).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mbc` | draft_innovation | 80 | 2026-10-19 | parent — the ONLY code; no token, promo or art-series child |

**Single-code family.** `parent_set_code` is null and no set names `mbc` as its
parent (checked 2026-11-01 against every Scryfall set released 2026-09-15 →
2026-11-30). `set:mbc+related` = `set:mbc`.

**Not linked to the other Mystery Booster sets.** `mb2` (Mystery Booster 2,
2024, `masters`) and `cmb1`/`cmb2` (playtest cards, `funny`) are each their own
family root. The booster still *pulls* printings from `mb2` and `plst` (§9) —
those printings belong to those families, not this one.

**Too new to be settled:** released ~2 weeks before this audit. Re-check for a
late `tmbc` token / `pmbc` promo child and for price drift.

---

## 2. Treatments

**No alternate treatments.** Every print computes to `regular`
(`survey_treatment_signature.py MBC`: 77 `regular [foil]`, 73
`regular [nonfoil]`). No showcase, borderless, extended-art, etched, or
fancy-foil prints. The preferred preview is empty (nothing in an alt class).

Three structural bands by CN (all black-bordered):

| Band | CNs | Count | Frame | Stamp | Finishes | Rarity | Commander-legal |
|---|---|---:|---|---|---|---|---|
| New commanders | 1–60 | 60 | 2015 (`legendary` frame effect on the 52 legendary non-planeswalkers) | `oval` | nonfoil + foil | rare | **no** (playtest-style new cards) |
| Acorn "conjure" cards | 61–70 | 10 | 2015 (`enchantment` on 62/67, `legendary` on 70) | `acorn` | foil only (7) / none (3 digital) | uncommon | no (acorn) |
| Future Sight-frame staples | 71–80 | 10 | `future` | none | nonfoil + foil | common/uncommon/rare | yes (reprints: Chaos Warp, Chromatic Lantern, Exotic Orchard, Path of Ancestry, Fellwar Stone, Mind Stone, Swiftfoot Boots, Thought Vessel, Jeweled Amulet, Dust to Dust) |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `alchemy` | (none) | n/a | 3 prints — CN 62 Case of the Lost Witness, 64 Oracle of the Alpha, 66 Perforator Crocodile. `games: [arena]`, `digital: true`, empty `finishes`. Dropped globally by `selectors._is_digital_only` (`alchemy` ∈ `UNOBTAINABLE_PROMO_TYPES`). |

No fancy-foil token → nothing for `[dupe_foil]`; the entry is an empty list
only so the `preferred` filter runs (§8).

**Full-art convention:** `full_art` false everywhere. No textless prints.

**Auto-dropped classes:** none present (no `ext`, no pure `ff`, no etched).

---

## 3. Chase variants

**None.** Every card name has one printing in the family
(`mm query show 'set:mbc+related chase'` → 0 rows).

---

## 4. Scenes / posters / panoramas

**None.** No borderless prints at all.

---

## 5. Unobtainable rules

**None — `[[unobtainable.mbc.rules]]` not configured.** No scarcity tier: the
most expensive nonfoil is Ekthi, Contaminator Priest 1 at ~$44; everything is a
booster card.

**Missing-set impact** (0 owned, prices 2026-11-01): `mm query missing-set mbc`
= **63 printings / $831.50** — the 60 new commanders (CN 1–60) + the 3 rare
Future Sight reprints (72 Chaos Warp, 73 Chromatic Lantern, 79 Exotic Orchard).
The acorn cards (61–70) and the uncommon/common reprints (71, 74–78, 80) are not
listed because missing-set only takes rares/mythics from regular prints.
`set_status.py mbc` raises no `⚠ concentrated` note.

---

## 6. PRM destinations

**None.** No promo child set; no prerelease, promo-pack or store-promo channel
found for MBC as of 2026-11-01.

---

## 7. Edge cases & gotchas

- **Arena-only cards in a paper set.** CN 62/64/66 are digital (`games: [arena]`,
  no finishes), on BOTH Scryfall and MTGJSON (`availability: [arena]`,
  `isOnlineOnly`). MTGJSON nonetheless lists them on the paper
  `alchemyAcorn` booster sheet (weight 1 each, beside the 7 paper acorn
  foils). They're unpriced, so they add nothing to booster EV; missing-set and
  Collection drop them via `_is_digital_only`. **The bare selector does not:**
  `mm query show 'set:mbc missing'` still lists all three (the digital filter
  runs inside `missing.missing_printings` / `collection_view`, not in the
  selector itself) — a global behavior, not an MBC rule.
- **Acorn cards that "conjure".** The 7 paper acorn cards print Alchemy-style
  `conjure` text (e.g. Ruby Collector conjures Mox Ruby). They're real paper
  foils, not digital — don't mistake the text for a digital signal.
- **CN 1–60 aren't Commander-legal** despite being legendary creatures /
  planeswalkers: Scryfall `legalities.commander = not_legal` (oval-stamped
  playtest-style designs, like `mb2`'s playtest cards).
- **Foil-only acorn prices are thin.** Most acorn foils have no Scryfall price
  yet; Overcooked 67 (~$75) and Euru 70 (~$101) are the only priced ones.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["mbc"]` = `frozenset()` (`config/families.toml`
  `[dupe_foil] mbc = []`) — **configured 2026-11-01.** No fancy-foil signal; the
  empty list unblocks the `preferred` filter for `mm query missing-set mbc`.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["mbc"]` — not configured (no scarcity tier, §5).
- No `FAMILY_SCENES["mbc"]` (§4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific detail:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Mystery Booster Commander Edition Booster Pack | draft booster (`draft_set`) | 20 cards; see the sheet table below. |
| … Booster Box | booster_box | MTGJSON `contents` is empty — box/case pack counts aren't in the data. |
| … Booster Box Case | booster_case | same — empty `contents`. |

**Booster types (for `sealed-value` EV).** One type, `draft`
(`sealed_value.py mbc --list-boosters`: EV **$28.48**, coverage **78.7%**, 6
layouts). **Most of the pack is NOT `mbc` cards** — sheets draw from three
families, so valuing it syncs `mb2` + `plst` first:

| Sheet | Per pack | Cards | Source set |
|---|---:|---:|---|
| `white`/`blue`/`black`/`red`/`green` | 3 each | 358 each | `plst` (The List) |
| `commander` | 1 | 121 | `plst` |
| `wildcard` | 1 | 111 | `plst` |
| `playtest` | 1 | 120 | `mb2` CN 501–621 (MB2 playtest cards) |
| `newCommander` / `newCommanderFoil` | 1 | 60 | `mbc` CN 1–60 (foil in ~4.75% of packs) |
| `futureSight` / `futureSightFoil` | 1 | 119 / 134 | `mb2` CN 122–257 + `mbc` CN 71–80 (foil in ~4.4% of packs) |
| `alchemyAcorn` | replaces the Future Sight slot | 10 | `mbc` CN 61–70 (~0.3% of packs; includes the 3 digital prints) |

Coverage < 100% is mostly unpriced `plst` and acorn printings, not an unsynced
set.
