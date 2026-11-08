# `dmr` — Dominaria Remastered

> Per-family memory doc. Read this before answering set-specific questions about
> `dmr` or working on `dmr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `dmr`
**Family root type:** `masters` (reprint set — no expansion parent)
**Family released:** `2023-01-13`
**Last audit:** `2026-11-02` via `/characterize-set dmr` (non-interactive batch run — tier decisions pending owner review).

---

## 1. Family map

2 Scryfall codes, linked via `parent_set_code` — the smallest possible graph: a
draft-only Masters reprint set with no Commander, promo, Art Series or alchemy
sibling.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dmr` | masters | 457 | 2023-01-13 | parent — reprints from across Dominaria's history; CN bands in §2 |
| `tdmr` | token | 14 | 2023-01-13 | tokens (Bird, Griffin, Cat ×2, Marit Lage, Zombie, Elemental, Goblin, Elephant, Insect, Saproling, Sheep, Squirrel, Construct) |

**Separately-rooted bonus sheets:** none. The `/sets` scan for 2022-12-20 → 2023-02-15
shows only unrelated products (`pw23`, `p23`, `pr23`, the ONE family, `pl23`, `unk`).
No `pdmr` / `admr` exists.

`mm set master-list dmr` / `set:dmr+related` resolve the whole family from the
parent — no `--only` needed. `tdmr` is excluded by default (`token`); opt in
with `--include token`.

---

## 2. Treatments

`promo_types` is almost silent (195 × `boosterfun`, 1 × `release`); the real
structure is CN-banded and lives in `border_color` + the (un-stored) Scryfall
`frame` field:

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 261 | `dmr` 1–261 | `regular` | handled by rarity/base sub-selectors (101 C / 80 U / 60 R / 20 M) |
| **retro frame** (1997 frame, black border, `boosterfun`) | 150 | `dmr` 262–411 | `regular` (frame is invisible to `compute_treatment` — the `cards` table has no `frame` column) | **KEPT (default) — pending owner review.** Same illustration as the base print for all 140 non-basic cards (illustration_id match 140/140); 262–401 are retro twins of base cards, 402–411 are 10 retro basics (2 per type). Because it computes to `regular`, every retro rare/mythic (60 R + 20 M, ~$476 nonfoil) is listed by the rare-/mythic-regular sub-selectors **in addition to** its base twin. 8 carry `frame_effects: tombstone` (Chainer's Edict 300, Dread Return 302, Glory 264, Momentary Blink 268, Necrosavant 307, Pyre Zombie 362, Sevinne's Reclamation 273, Undead Gladiator 313) |
| borderless (`inverted`, some `+legendary`) | 45 | `dmr` 412–456 | `b` | **KEPT (default) — pending owner review.** Distinct art (0/45 share an illustration with the base print); the family's "chase" tier (Force of Will 418, Vampiric Tutor 430, Enlightened Tutor 412, Urza's Incubator 453, Sylvan Library 441, Yawgmoth 431, …) |
| release promo | 1 | `dmr` 457 | `regular` (foil-only, retro frame) | kept — Counterspell, Mark Poole original art, distinct from base 45 / retro 281 |
| showcase / extended-art / etched / fancy foil | 0 | — | — | none in this family |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `regular` (retro) / `b` (borderless) | n/a (umbrella) | tags both the retro and borderless bands |
| `release` | (base frame) | no — unique art | DMR 457 Counterspell, foil-only |

**No fancy-foil sheet** — no surgefoil/galaxyfoil/etched etc.; every print is
`foil+nonfoil` except 457 (`foil`). So the dupe-foil list should be **empty**
(`dmr = []`), which only unblocks `treatment=preferred` (proposal pending).

**Full-art convention:** `full_art` is FALSE on every `dmr`/`tdmr` print.
**Security stamp:** 120 oval-stamped prints (rares/mythics); rest none.

---

## 3. Chase variants

The bare `chase` modifier surfaces only **Counterspell** (common 45 + retro 281,
which share art, + the release promo 457 with Mark Poole art). Nothing at
`missing rarity=uncommon treatment=regular chase` (0 rows).

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Counterspell | 3 | `dmr` 45 / 281 / 457 | common / common / rare (promo) | regular (base / retro / release) |

46 names appear 3× in `dmr` (base + retro + borderless — e.g. Force of Will,
Vampiric Tutor, Sylvan Library, the Tutors, Lyra Dawnbringer) but these are the
normal base/retro/borderless trio, not a multi-art booster chase.

---

## 4. Scenes / posters / panoramas

**None.** The borderless band (412–456) is individual borderless reprints by
many artists, not a single-artist contiguous scene; no `poster` promo_type.
Not encoded in `[[scenes.dmr]]`.

---

## 5. Unobtainable rules

**No rule is active.** Tiers that need a
keep/exclude decision:

| Tier | Disposition | Rationale |
|---|---|---|
| retro frame (`boosterfun` + `border_color: black`, CN 262–411) | kept (default) — pending owner review | Same art as base; only the frame differs. Computes to `regular`, so `missing-set`'s rare/mythic sub-selectors would list each of 80 retro rares/mythics beside its base twin (~$476 nonfoil, roughly doubling the rare/mythic regular list). Exclude rule would be `{promo_types_any_of = ["boosterfun"], border_color = "black"}` — matches exactly the 150 retro prints and nothing else |
| borderless (`inverted`, CN 412–456) | kept (default) — pending owner review | Distinct art, the family's chase tier (45 prints, ~$434 nonfoil). Recommend keep |

**Scarcity check:** `scripts/set_status.py dmr` printed no ⚠ concentration note
(missing-set was not available at this audit, before `[dupe_foil]` was configured). Top
collectible-alt missing value is a flat curve of borderless staples (Force of
Will 418 ~$55, Vampiric Tutor 430 ~$51, Enlightened Tutor 412 ~$34) — no
serialized/headliner/stamped scarcity tier exists in this family.

---

## 6. PRM destinations

**None.** Dominaria Remastered had no prerelease / promo-pack channel — there is
no `pdmr` set and no `Ns`/`Np` stamped promos. The only promo is `dmr` 457
Counterspell (`release`, foil-only), which lives in the parent itself. A
"PRM"-stamped Dominaria card belongs to an original Dominaria-plane set
(DOM/DMU/…) or a WPN/Secret Lair channel, not this family.

---

## 7. Edge cases & gotchas

- **Parent `set_type` is `masters`** — not in `DEFAULT_INVENTORY_SET_TYPES`, but
  the anchor is always included by `filtered_codes()`; `tdmr` (token) is
  excluded by default.
- **Retro frame is invisible to the code.** The `cards` table doesn't store
  Scryfall's `frame` (1997 vs 2015), so retro twins look identical to base prints
  to `compute_treatment` (`regular`). The only distinguishing fields are
  `promo_types: boosterfun` + `border_color: black` (and the CN band). Any
  frame-based handling has to key on those.
- **Basics only exist retro:** `dmr` 402–411 (2 each of Plains/Island/Swamp/
  Mountain/Forest) are the set's only basic lands — there are no base-frame basics.
- **Tombstone flag** appears only on 8 retro prints (§2), not on their base twins.
- **No arena leak** — `set:dmr+related missing | grep -i arena` returns nothing;
  no alchemy child exists for this paper-only remaster.
- **Marit Lage** token is `tdmr` 4 (`frame_effects: legendary`) — pairs with Dark
  Depths (base / retro / borderless).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] dmr = []` — configured 2026-11-08 (enables `mm query missing-set dmr`).
- `config/families.toml` `[[unobtainable.dmr.rules]]` — None configured yet (proposals pending owner review).
- `[[scenes.dmr]]` — not configured (no scene; see §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Draft Booster (pack / box / case) | booster | MTGJSON `sealedProduct` subtype `draft` |
| Collector Booster (pack / box / case) | booster | MTGJSON subtype `collector` |
| — (no Commander / Bundle / precon / Art Series) | — | `mm mtgjson decks --set dmr` → no decks |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py dmr --list-boosters`:

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `draft` | EV ~$9.76, coverage 97.5%, 8 layouts |
| `collector` | EV ~$35.58, coverage 98.3%, 1 layout |
