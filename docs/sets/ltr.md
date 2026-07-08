# `ltr` — The Lord of the Rings: Tales of Middle-earth

> Per-family memory doc. Read this before answering set-specific questions about
> `ltr` or working on `ltr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ltr`
**Family root type:** `draft_innovation` (NOT `expansion` — LTR was pre-standard-UB-parent-set-type)
**Family released:** 2023-06-23
**Last audit:** 2026-07-08 (backfilled from session context + `docs/ltr-borderless-scenes.md`)

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ltr` | draft_innovation | 856 | 2023-06-23 | parent — includes the poster series 731–750 |
| `ltc` | commander | 591 | 2023-06-23 | Commander decks (Riders of Rohan, Hosts of Mordor, Elven Council, Food and Fellowship) |
| `pltr` | promo | 86 | 2023-06-23 | Prerelease + set promos |
| `pltc` | promo | 4 | 2023-06-23 | Deluxe Commander Kit promos |
| `altc` | memorabilia | 24 | 2023-06-23 | **Scene Box** — physical panels sold as a display product |
| `tltr` | token | 25 | 2023-06-23 |  |
| `tltc` | token | 15 | 2023-06-23 |  |
| `fltr` | memorabilia | 10 | 2023-06-23 | Front cards (beginner box) |
| `altr` | memorabilia | 81 | 2023-06-23 | Art Series |
| `mltr` | minigame | 1 | 2023-06-23 | Minigame — unusual `set_type`, not seen in newer UB families |

**Separately-rooted bonus sheets:** none — LTR's family is fully linked via `parent_set_code`.

**`mm` invocations:** default `set:ltr+related` resolution works correctly for this family.

```
mm set master-list ltr
mm query missing-set ltr
```

---

## 2. Treatments

`selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["ltr"] = frozenset({"surgefoil", "doublerainbow"})` (see `src/magic_manager/selectors.py:89`).

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `surgefoil` | `ff` | **yes** → in DUPE_FOIL | Same-art fancy-foil sheet. Example: LTC 378 Great Henge (surgefoil) matches LTC 348 (borderless inverted). |
| `doublerainbow` | `ff` | **yes** → in DUPE_FOIL | Serialized `z`-suffix prints (e.g. LTC 378z). Also filtered globally by the `serialized` promo_type exclusion. |
| `silverfoil` | `ff` | **no — unique art** | Scroll-frame showcase prints (LTR 452–490, LTC 411–431) have a distinct parchment scroll frame — different art, not a dupe. Kept in DUPE_FOIL exclusion list explicitly. Combined with `scroll` promo_type triggers the unobtainable rule below. |
| `poster` | `ff` (implicitly via serialized twins) | n/a | LTR 731–750 poster series — see §4. Non-serialized twins available in nonfoil and foil; `z`-suffix serialized twins filtered globally. |

**Full-art convention:** LTR's borderless-inverted prints have `full_art: false` and `frame_effects: ["inverted"]`. See `docs/scryfall-printing-treatments.md` §6.5 for the SPM/TLA/TMT convention flip.

---

## 3. Chase variants

Detected by `selectors._modifier_chase` (default threshold 3, added `751e627`). The `mm query missing-set ltr` pipeline includes an `uncommon-chase` sub-selector that surfaces these.

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Nazgûl | 9 | `ltr` 100, 332–339 | uncommon | regular |
| Nazgûl (scroll silverfoil variants) | 9 | `ltr` 551, 723–730 | uncommon | ff | (excluded from missing via §5 unobtainable rule) |
| Ringwraiths | 2 | `ltr` 284, 385 | rare | regular + ext |
| Lord of the Nazgûl | 3 | `ltc` 60, 142, 467 | rare | regular + b + ff |

Nazgûl is the canonical LTR chase: 9 distinct artists across `ltr` 100 + 332–339. The `ltr` 551 + 723–730 silverfoil-scroll variants are the same 9 artworks in scroll-frame treatment — deliberately excluded by the §5 unobtainable rule despite being distinct art (rare distribution, bundle-only, low-availability).

---

## 4. Scenes / posters / panoramas

LTR has **two** distinct scene-like grouping mechanisms, neither tagged by Scryfall in card metadata.

### 4a. Borderless "Scene Cards" (CN 399–451)

Scryfall's web UI groups these as "Scene Cards" via a hand-curated CN range (see `https://scryfall.com/search?order=set&q=e%3Altr+cn%E2%89%A5399+cn%E2%89%A4451&unique=prints`). 53 borderless-inverted prints across 7 artist runs. Full analysis lives in [`docs/ltr-borderless-scenes.md`](../ltr-borderless-scenes.md).

**Detected 7 scenes** (contiguous CN + shared artist):

| Scene # | Artist | CN range | Cards | Theme (informal) |
|---:|---|---|---:|---|
| 1 | Livia Prima | 399–404 | 6 | Shire / Hobbits |
| 2 | Colin Boyer | 405–410 | 6 | Balrog / Moria |
| 3 | David Rapoza | 411–419 | 9 | Isengard / Ents |
| 4 | Tyler Jacobson | 420–437 | 18 | Minas Tirith / Battle of Pelennor **(contains LTR 433 Orcish Bowmasters)** |
| 5 | Martina Fačková | 438–441 | 4 | Scouring of the Shire |
| 6 | Kieran Yanner | 442–447 | 6 | Grey Havens |
| 7 | Marta Nael | 448–451 | 4 | Mount Doom climax |

**Detection recipe:**

```bash
.claude/skills/scryfall-search/scryfall.sh search 'set:ltr border:borderless' unique=prints \
  | jq -r '.data[] | select((.promo_types // []) as $pt | ($pt|index("silverfoil")|not) and ($pt|index("scroll")|not) and ($pt|index("poster")|not) and ($pt|index("serialized")|not)) | select((.frame_effects // []) | index("inverted")) | select(.collector_number | test("^[0-9]+$")) | [(.collector_number|tonumber), .name, .artist] | @tsv' \
  | sort -k1,1n
```

Then group consecutive rows sharing an artist. Runs of ≥3 are scenes. Runs of 1–2 are typically buyabox/prerelease promos or basics (e.g. LTR 340–345 are 6 unique-artist basics, LTR 398 is Alexander Gering's solo buyabox promo).

**Buying-strategy note:** the user assembles scenes in a single finish (all NF or all foil) to avoid mismatched appearance when panels are placed together. Per-scene finish recommendations live in `docs/ltr-borderless-scenes.md` based on current inventory partial-ownership state.

### 4b. Poster series (CN 731–750)

20 mythic-rare panels that tile into 4 posters (5 CNs each = 1 poster). Sealed 5-card inserts distributed in Draft/Set booster boxes.

| Poster block | CN range | Nonfoil total | Foil total |
|---|---|---:|---:|
| A (Fellowship-era) | 731–735 | $368.68 | $811.36 |
| B (Sauron/Ents) | 736–740 | $481.53 | $761.25 |
| C (Aragorn-era) | 741–745 | $876.93 | $1,506.29 |
| D (Objects/Doom, incl. The One Ring 748) | 746–750 | $1,186.33 | $2,160.39 |

Each panel has both nonfoil and foil finishes plus a serialized `z`-suffix version (731z, 732z, …) that's globally filtered.

**Scryfall doesn't tag** which specific poster (Fellowship / Two Towers / Return of the King / etc.) each panel belongs to — the CN grouping (contiguous 5-CN blocks) is the only signal.

---

## 5. Unobtainable rules

`selectors.FAMILY_UNOBTAINABLE_RULES["ltr"]` (see `src/magic_manager/selectors.py:118-128`).

| Rule | Rationale |
|---|---|
| `promo_types_all_of: {silverfoil, scroll}` | Scroll-frame showcase prints (LTR 452–490, LTC 411–431). Distinct parchment-scroll art but bundle-only distribution, priced $50–$130 each, rarely surface on secondary market. User has personally decided not to shop for these. Matches both `silverfoil` AND `scroll` promo_types AND'd; a single-promo-type match would over-shoot into other silverfoil prints that ARE in standard distribution (LTC 517, 525, etc.). |

Also filtered **globally** (not via LTR-specific rules):
- `serialized` promo_type → LTR 731z–750z poster series serialized chase, LTC 378z–407z borderless land serialized. See `selectors.UNOBTAINABLE_PROMO_TYPES` (`selectors.py:202`).
- `rebalanced` / `alchemy` promo_types → digital-only Arena prints.

---

## 6. PRM destinations

LTR's PRM-stamped physical promo cards can land in these Scryfall set codes:

| Physical stamp | Scryfall set | Channel | Example |
|---|---|---|---|
| Prerelease datestamped, CN `Ns` | `pltr` | Set prerelease | `pltr` 1s-86s |
| Play Promo, small CN | `pw25`/`pw26` (LTR-era: check period) | WPN Play Promo | (few LTR-era WPN promos) |
| Deluxe Commander Kit promo | `pltc` | Deluxe Commander product | `pltc` 1-4 |

For any PRM-stamped card the user presents, resolve by name+artist first (see `.claude/skills/bulk-add/SKILL.md` § "Printed `PRM` set code") rather than trying `set:prm` (which is MTGO digital-only, not physical PRM).

---

## 7. Edge cases & gotchas

- **`mltr` minigame set** — 1 card, `set_type: minigame`. Unusual type not seen in newer UB families. Excluded from default `filtered_codes()` in `sets.py:33` (which allows expansion/commander/masterpiece/promo). If the user ever wants it included in checklists, use `--include minigame`.
- **`altc` Scene Box** — 24 memorabilia cards. Not in default checklists (memorabilia excluded). Distinct product from the borderless-inverted "Scene Cards" of §4a — the Scene Box is a physical display, altc is the memorabilia set code.
- **LTC set_type=commander** — this is a genuine Commander-deck set (Riders of Rohan / Hosts of Mordor / Elven Council / Food and Fellowship, 4 decks). Distinct from TMT's `tmc` which has `set_type: eternal` despite being a Commander deck (TMT gotcha).
- **Meld-back faces** — none known; the missing-set pipeline's `_drop_meld_back_faces` filter (`cli.py:2233`) is defensive here.
- **Basic lands (LTR 273–281, 340–345, 751–756)** — three basic-land runs: standard (273–281), borderless-inverted (340–345), and duplicate borderless (751–756). Not part of any scene; treat as ordinary basics.

---

## 8. Code refs

- `selectors.py:78-90` — `FAMILY_DUPE_FOIL_PROMO_TYPES["ltr"] = frozenset({"surgefoil", "doublerainbow"})`
- `selectors.py:118-128` — `FAMILY_UNOBTAINABLE_RULES["ltr"]` with the `silverfoil+scroll` rule
- `selectors.py:_modifier_chase` — surfaces the Nazgûl chase via `mm query missing-set ltr`
- Related docs: [`ltr-borderless-scenes.md`](../ltr-borderless-scenes.md) — one-off scene analysis with per-scene ownership + finish-completion cost.
