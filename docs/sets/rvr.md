# `rvr` — Ravnica Remastered

> Per-family memory doc. Read this before answering set-specific questions about
> `rvr` or working on `rvr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `rvr`
**Family root type:** `masters` (reprint set — no expansion parent)
**Family released:** `2024-01-12`
**Last audit:** `2026-11-01` via `/characterize-set rvr` (non-interactive batch run — tier decisions pending owner review).

---

## 1. Family map

2 Scryfall codes, linked via `parent_set_code` — a draft + collector-booster
Masters reprint set with no Commander, promo, Art Series or alchemy sibling.
Same shape as [`dmr.md`](dmr.md) (base / retro / borderless / serialized).

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `rvr` | masters | 531 | 2024-01-12 | parent — Ravnica-plane reprints; CN bands in §2 (467 numbered CNs + 64 `Nz` serialized) |
| `trvr` | token | 20 | 2024-01-12 | 19 tokens (incl. legendary Voja, `trvr` 19) + Domri Rade Emblem (`trvr` 20) |

**Separately-rooted bonus sheets:** none. The `/sets` scan for 2023-12-20 → 2024-02-28
shows only unrelated products (`pw24`, `pf24`, `pl24`, the MKM family, `clu`/`fclu`
Ravnica: Clue Edition — a separate MKM-rooted product, not RVR — and `punk`).
No `prvr` / `arvr` exists.

`mm set master-list rvr` / `set:rvr+related` resolve the whole family from the
parent — no `--only` needed. `trvr` is excluded by default (`token`); opt in
with `--include token`.

---

## 2. Treatments

`promo_types` carries only the `boosterfun` umbrella (240), the serialized
`serialized`+`doublerainbow` pair (64) and one `release`; the real structure is
CN-banded and lives in `border_color` + the (un-stored) Scryfall `frame` field
(1997 = retro, 2015 = borderless/base).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 291 | `rvr` 1–291 | `regular` | handled by rarity/base sub-selectors (110 C / 90 U / 71 R / 20 M). 19 carry `frame_effects: legendary`. No basic lands anywhere in the set |
| borderless shocklands (`inverted`) | 10 | `rvr` 292–301 | `b` | **KEPT (default) — pending owner review.** The 10 Ravnica shocks, new art (0/10 share an illustration with base or retro) |
| **retro frame** (1997 frame, black border, `boosterfun`) — twins | 114 | `rvr` 302–415 | `regular` (frame is invisible to `compute_treatment` — the `cards` table has no `frame` column) | **KEPT (default) — pending owner review.** Same illustration as the base print for all 114 (illustration_id match 114/114). Booster sheets `retroCommonUncommon` (50) + `retroRareMythic` (64) in Draft boosters. Because it computes to `regular`, every retro rare/mythic is listed by the rare-/mythic-regular sub-selectors **in addition to** its base twin. Tombstone flag on Golgari Thug 325, Arclight Phoenix 331, Golgari Grave-Troll 348, Life from the Loam 350, Moldervine Cloak 352 |
| **retro frame — collector-exclusive** (no base twin) | 21 | `rvr` 446–466 | `regular` | **KEPT (default) — pending owner review.** Retro-only reprints (Rest in Peace, Enter the Infinite, Pack Rat 455, Supreme Verdict, Karn's Bastion, Maze's End, Thespian's Stage, Pithing Needle, Wilderness Reclamation, …) — 0/21 have a base-frame twin, so this is the ONLY print of these cards in the family. Only on the Collector Booster retro sheets (61 C/U + 74 R/M vs Draft's 50 + 64). Tombstone on Darkblast 454, Shambling Shell 460 |
| borderless (`inverted`, some `+legendary`) | 28 | `rvr` 416–443 | `b` | **KEPT (default) — pending owner review.** Distinct art (0/28 share an illustration with any other `rvr` print); the family's chase tier (Cyclonic Rift 419, Bruvac 418, Utvara Hellkite 431, Guardian Project 433, Spark Double 421, Hellkite Tyrant 428, Aurelia 436, Savra 440, …). Pack Rat 426 has no base twin (its other print is retro 455) |
| borderless planeswalkers (no `inverted`) | 2 | `rvr` 444–445 | `b` | **KEPT (default) — pending owner review.** Domri Rade 444, Ral Zarek 445 (mythic) |
| serialized double-rainbow foil | 64 | `rvr` `302z`–`415z` | `ff` (foil-only) | **dropped globally** — `serialized` is in `selectors.UNOBTAINABLE_PROMO_TYPES` (1-of-500 chase). Retro-frame art, rares/mythics of the 302–415 band (59 plain + 5 tombstone/reordered-token variants) |
| release promo | 1 | `rvr` 467 | `regular` (foil-only) | kept — Niv-Mizzet, the Firemind; the only print of that card in the family (no twin) |
| showcase / extended-art / etched / fancy-foil sheet | 0 | — | — | none in this family |

**Borderless subtotal:** 40 prints (292–301 + 416–445), ~$564 nonfoil — the
PREFERRED PREVIEW buckets are `b inverted borderless` 26 + `b inverted+legendary
borderless` 12 (+ the 2 non-inverted planeswalkers).

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `regular` (retro) / `b` (borderless) | n/a (umbrella) | tags the retro and borderless bands |
| `serialized` + `doublerainbow` | `ff` | same art as the retro twin, but 1-of-N | already removed by the global serialized filter — no family rule needed |
| `release` | `regular` | no — unique card | `rvr` 467 Niv-Mizzet, the Firemind, foil-only |

**No fancy-foil sheet** besides the serialized double-rainbow (handled globally) —
so the dupe-foil list should be **empty** (`rvr = []`), which only unblocks
`treatment=preferred` (proposal pending).

**Full-art convention:** `full_art` is FALSE on every `rvr`/`trvr` print.
**Security stamp:** 131 oval-stamped prints (rares/mythics); rest none.

---

## 3. Chase variants

**None.** `set:rvr+related chase` and `chase:5` both return 0 rows; `missing
rarity=uncommon treatment=regular chase` returns 0. Many rares/mythics appear 3×
(base + retro + borderless, e.g. Cyclonic Rift 40 / 313 / 419, the shocks
base / retro 397–415 / borderless 292–301) but that is the normal
base/retro/borderless trio, not a multi-art booster chase.

---

## 4. Scenes / posters / panoramas

**None.** The borderless bands (292–301 shocks, 416–445) are individual
borderless reprints by many artists, not a single-artist contiguous scene; no
`poster` promo_type. Not encoded in `[[scenes.rvr]]`.

---

## 5. Unobtainable rules

**No rule is active.** Tiers that need a
keep/exclude decision:

| Tier | Disposition | Rationale |
|---|---|---|
| retro frame twins (`boosterfun` + `border_color: black`, CN 302–415) | kept (default) — pending owner review | Same art as base; only the frame differs. Computes to `regular`, so `missing-set`'s rare/mythic sub-selectors would list each retro rare/mythic beside its base twin. Excluding all retro with the DMR-style rule `{promo_types_any_of = ["boosterfun"], border_color = "black"}` would ALSO drop the 21 collector-exclusive retro cards (446–466) — which are the only print of those cards here — so a twin-only exclusion needs a `collector_numbers` range rule instead |
| retro frame collector-exclusive (CN 446–466) | kept (default) — pending owner review | Only print of 21 cards in the family (Rest in Peace, Supreme Verdict, Pack Rat, Maze's End, …). Recommend keep |
| borderless shocklands (CN 292–301) | kept (default) — pending owner review | Distinct art, 10 prints ~$177 nonfoil. Recommend keep |
| borderless (`inverted`, CN 416–445) | kept (default) — pending owner review | Distinct art, the family's chase tier (30 prints, ~$386 nonfoil). Recommend keep |

Retro rares/mythics total 74 prints (58 R + 16 M), ~$505 nonfoil.

**Scarcity check:** `scripts/set_status.py rvr` printed no ⚠ concentration note
(missing-set is not available until `[dupe_foil]` is configured; nothing owned
yet). The only true scarcity tier — 64 serialized double-rainbow foils
(`Nz`, up to ~$2,000 each) — is already dropped by the global `serialized`
filter. Remaining top values are a flat curve of borderless/retro staples
(Cyclonic Rift 419 ~$47, Bruvac 418 ~$44, Retro shocks ~$12–22).

---

## 6. PRM destinations

**None.** Ravnica Remastered had no prerelease / promo-pack channel — there is
no `prvr` set and no `Ns`/`Np` stamped promos. The only promo is `rvr` 467
Niv-Mizzet, the Firemind (`release`, foil-only), which lives in the parent
itself. A "PRM"-stamped Ravnica card belongs to an original Ravnica-plane set
(RNA/GRN/WAR/MKM/…) or a WPN/Secret Lair channel, not this family.

---

## 7. Edge cases & gotchas

- **Parent `set_type` is `masters`** — not in `DEFAULT_INVENTORY_SET_TYPES`, but
  the anchor is always included by `filtered_codes()`; `trvr` (token) is
  excluded by default.
- **Retro frame is invisible to the code.** The `cards` table doesn't store
  Scryfall's `frame` (1997 vs 2015), so retro prints look identical to base
  prints to `compute_treatment` (`regular`). Distinguishing fields:
  `promo_types: boosterfun` + `border_color: black` (and the CN band).
- **Two retro bands, not one** (unlike DMR): 302–415 are twins of base cards
  (Draft + Collector); 446–466 are collector-exclusive retro-only reprints with
  NO base print. Any retro exclusion must decide about these separately (§5).
- **Serialized `Nz` CNs** (`302z`–`415z`, 64 prints) mirror the retro CN with a
  `z` suffix; double-rainbow foil, dropped globally. Some have no Scryfall price.
- **Pack Rat** exists only as retro 455 + borderless 426 — no base-frame print.
- **No basic lands** in `rvr` at all; the mana slot is guildgates + shocks
  (MTGJSON `manaSlot` sheet, 31 cards).
- **Ravnica: Clue Edition (`clu`)** is a separate MKM-rooted product released
  six weeks later — not part of this family despite the Ravnica name.
- **No arena leak** — `set:rvr+related missing | grep -i arena` returns nothing.
- **Domri Rade Emblem** is `trvr` 20 (pairs with borderless Domri Rade 444 / base).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] rvr = []` — configured 2026-11-08 (enables `mm query missing-set rvr`).
- `config/families.toml` `[[unobtainable.rvr.rules]]` — None configured yet (proposals pending owner review).
- `[[scenes.rvr]]` — not configured (no scene; see §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Draft Booster (pack / box / case) | booster | MTGJSON `sealedProduct` subtype `draft` |
| Collector Booster (pack / box / case) | booster | MTGJSON subtype `collector`; only source of retro 446–466 and the serialized `Nz` sheet |
| — (no Commander / Bundle / precon / Art Series) | — | `mm mtgjson decks --set rvr` → no decks |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py rvr --list-boosters`:

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `draft` | EV ~$9.88, coverage 99.1%, 4 layouts. Sheets: common, uncommon, rareMythicWithShowcase, manaSlot, retroCommonUncommon (50), retroRareMythic (64), foilWithShowcase |
| `collector` | EV ~$51.23, coverage 99.0%, 2 layouts. Sheets incl. borderlessRareMythic (40), retro C/U (61) + R/M (74), foilShowcaseRareMythic, serialized (64) — serialized EV counts the 1-of-N prints at market |
