# `unk` — `Unknown Event` (MagicCon playtest cards)

> Per-family memory doc. Read this before answering set-specific questions about
> `unk` or working on `unk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `unk`
**Family root type:** `funny` (a **special product**, not a booster set: text-only playtest cards handed out at MagicCon "Unknown Event" play areas, wave by wave)
**Family released:** 2023-02-15 (Scryfall set date; first cards 2023-02-17) → ongoing (latest local wave 2026-07-30)
**Last audit:** 2026-11-01 via `/characterize-set unk` (non-interactive batch run).

**Read this first:** every one of the 579 prints carries `promo_types: [playtest]`,
has **no illustration** (`illustration_id` NULL, no artist, playtest frame), is
`not_legal` in every format, and is distributed only at in-person events. It is
the same "playtest card" genre as `cmb1`/`cmb2` (Mystery Booster Playtest
Cards), but those are separately-rooted sets, not part of this family.

---

## 1. Family map

Resolved via `mm set list-related unk`. Both codes are synced locally.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `unk` | funny | 527 | 2023-02-15 | parent; event-wave playtest cards, CN = `<rarity><colour><NN>[suffix]` (see §7) |
| `punk` | funny | 52 | 2024-02-24 | "Black Lotus Unknown Planechase" — oversized-style Plane/Phenomenon playtest cards, CN `PLA001`–`PLA046` (+`a` gold-border reprints) |

Topology is **cleanly rooted** (`punk.parent_set_code = unk`). No separately-rooted
bonus sheet. `cmb1` (2019) / `cmb2` (2021) are unrelated playtest sets with
`parent_set_code: null` — do NOT fold them in.

**`mm` invocations:**

```
mm set master-list unk          # whole family via normal resolve
mm query missing-set unk        # only after a [dupe_foil] entry exists (see §8)
```

**Release waves** (`cards.released_at` per print — each is one event's batch):
2023-02-17 (62), 2023-05-06/07 (62), 2023-07-29/30 (62), 2023-08-05 (1),
2023-09-23 (34), 2024-02-24 (51 + `punk` 10), 2024-06-29 (29), 2024-08-03 (3),
2024-10-25 (49), 2025-02-21 (45), 2025-06-20 (44), 2025-08-02 (12),
2025-09-26 (18), 2026-05-01 (40), 2026-07-17 (14), 2026-07-30 (1).
New waves keep landing — re-sync (`mm set sync unk`) after each MagicCon.

---

## 2. Treatments

There is effectively **one treatment**: plain playtest-frame, nonfoil, no art.
`promo_types` is uniformly `playtest` (579/579), so axis 1 carries no signal.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (playtest, black border) | 536 | all `unk` CNs except `RU01a` + `punk` `PLA001`–`PLA010` | `regular` | handled by rarity/base sub-selectors |
| gold border (`punk`) | 42 | `punk` `PLA001a`/`003a`/`005a`/… + `PLA011`–`PLA046` | `regular` | no alt class — gold border is not a treatment keyword; see below |
| white border | 1 | `unk` `RU01a` The Whiteboarder (a joke card about white borders) | `regular` | n/a — single card, the border is the joke |
| enchantment frame | 5 | `UB05a`, `UU04c`, `CR02`, `RC06b`, `CG04` ("Fear of …") | `regular` | n/a — `frame_effects: enchantment`, normal card frame flag |
| legendary frame + foil | 1 | `unk` `RW90e` The Keeper of Favorite Cards (only print with `foil` finish) | `regular` | n/a — only foil in the family; no dupe-foil sheet |
| showcase / borderless / extended-art / etched | 0 | — | — | **none present** |

No showcase, borderless, extended-art, etched or fancy-foil tier exists, so there is
**no kept-by-default alt-treatment tier to review**. PREFERRED PREVIEW (fallback
`collectible-alt`): *no rows*.

**Gold-bordered `punk` Planes.** `PLA001`/`002`/`003`/`004`/`005`/`009` (2024-02-24,
black) each have an `…a` gold-border reprint (2024-06-28 or 2025-02-21) — same
name/text, different border (art-less, so "same art" is moot). `PLA011`–`PLA046`
exist only in gold. They compute `regular` (all common), so they never reach the
rare/mythic missing sub-selectors.

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `playtest` | none | no | on every print; generic umbrella, not a dupe signal |

**Full-art convention:** `full_art` FALSE everywhere (579/579).

---

## 3. Chase variants

`chase` here is **not art-based** (nothing has art) — it fires on repeated
printings of the same card name across waves:

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| The Keeper of Favorite Cards | 5 | `unk` RW90a–RW90e (one per wave 2024-02 → 2026-05; `e` is foil+nonfoil) | rare | regular |
| Artist Alley | 3 | `punk` PLA001 + PLA001a (common), `unk` UL01 (uncommon, 2026-05-01) | common/uncommon | regular |

Other repeat names (2 prints each) are the `punk` black/gold Plane pairs: The Bean,
Black Lotus Lounge, City Hall, Pin Collector's Booth, The Windy City; plus `unk`
pairs The Asker of More Mana, The Sprinkler of Stardust.

---

## 4. Scenes / posters / panoramas

n/a — no art, no borderless prints, so no scene/poster runs exist.

---

## 5. Unobtainable rules

No rule is active. **Owner decision pending:** the whole family is a scarcity tier
— event-attendance-only cards (MagicCon play areas), 579 prints, only 173 priced
locally ($6,920.53 total; top: Snapsail Rider RR05 $499.99, The Snapstone Wielder
RZ06h $427.99, Your Favorite Character RC05c $267.49, Monet, Sensei of the Sewers
RZ06g $174.00, Seventh Stage of Magic Design RZ06d $139.95). Rare+mythic alone = 340 prints
($5,715.35 priced across 119). If configured as-is, `missing-set unk` would list
all 340 rare/mythic prints, most unpriced. Options: keep (family is wanted) —
`[dupe_foil] unk = []` only; or exclude everything via a
`promo_types_any_of = ["playtest"]` unobtainable rule (the family is then
effectively tracked-but-never-missing). Status: **kept (default) — pending owner review**.

Concentration check (`scripts/set_status.py unk`) could not run the missing
figure: family not configured (owns 0 of 579).

---

## 6. PRM destinations

n/a — no promo channels. Cards come only from event play areas; CNs printed on the
card match Scryfall's (`unk` `RW90b`, `punk` `PLA012`, …).

---

## 7. Edge cases & gotchas

- **CN scheme** `<R><C><NN>[x]`: R = rarity (`C`ommon/`U`ncommon/`R`are/`M`ythic,
  plus `WW02` The Pleasant Taxer, rarity `special`); C = colour (`W U B R G`,
  `Z` multicolour, `A` artifact, `C` colourless, `L` land). The letter suffix does
  NOT mean a variant — `RZ06` + `RZ06a`…`RZ06k` are twelve different cards sharing a slot
  (362 of 527 `unk` CNs carry a suffix). Only RW90a–e are true same-card reprints.
- **No art anywhere** — `illustration_id`/artist NULL, so art-tag, art-swap and
  "same art" reasoning don't apply; gallery tiles are text-only scans.
- **Not legal in any format** (all `legalities` = not_legal). 34 prints carry `security_stamp: oval`; none `arena` (no
  digital-only leak; no tokens).
- Hyper-long name: `punk` PLA025 "Asmoranomardicadaistinaculdacar's Kitchen".
- `unk` card_count on Scryfall (527) grows with each wave — the family is not closed.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] unk = []` — configured 2026-11-08 (enables `mm query missing-set unk`).
- `config/families.toml` `[[unobtainable.unk.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.unk]]` — n/a (no scenes).

---

## 9. Product types

| Product | Archetype (→ [product-types.md](../product-types.md)) | Family-specific detail |
|---|---|---|
| Unknown Event playtest cards | none (event giveaway) | not sold sealed; obtained at MagicCon Unknown Event play areas, one wave per event |
| Black Lotus Unknown Planechase (`punk`) | none (event giveaway) | Plane/Phenomenon cards; 2024-02 black-border wave, later gold-border waves |

**Booster types:** none — `sealed_value.py unk --list-boosters` → "no booster data in MTGJSON".
