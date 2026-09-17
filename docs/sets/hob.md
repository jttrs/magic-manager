# `hob` — The Hobbit (Tales of Middle-earth: The Hobbit)

> Per-family memory doc. Read this before answering set-specific questions about
> `hob` or working on `hob`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `hob`
**Family root type:** `expansion` (a modern Universes Beyond Tolkien release — every print carries `universesbeyond`)
**Family released:** `2026-08-14`
**Last audit:** `2026-09-16` via `/characterize-set hob`.

---

## 1. Family map

3 Scryfall codes, all linked via `parent_set_code` (clean graph — no separately-
rooted bonus sheets; the "The Hobbit may have a masterpiece/scene sheet" theory
was checked and is **false** — the poster/headliner prints all live inside `hob`
itself, see §4). A standard modern UB expansion + a commander-style eternal
sibling + a token set.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `hob` | expansion | 321 | 2026-08-14 | parent — includes the poster series 239–248, the headliner 249, and all surgefoil dupes 250–284 |
| `hoc` | **eternal** | 158 | 2026-08-14 | The Hobbit Eternal — the commander-style sibling. `set_type: eternal`, NOT `commander` (mirrors TMT's `tmc` / echoes LTR's `ltc` role). Holds The One Ring reprint (hoc 44/84), Orcish Bowmasters (hoc 19/59), and the 2 boxtoppers (hoc 25/28) |
| `thob` | token | 15 | 2026-08-14 | tokens |

`mm set master-list hob` / `set:hob+related` resolve the whole family from the
parent (no `--only` needed). 474 prints in the family total; the default-scoped
value-bearing sets are `hob` (expansion) + `hoc` (eternal).

**`mm` invocations:** default resolution works.

```
mm set master-list hob
mm query missing-set hob
```

---

## 2. Treatments

`selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["hob"] = frozenset({"surgefoil"})` (configured — see §8).

Every print carries `universesbeyond` (474/474) — it's the UB marker, not a
treatment signal. The meaningful tokens:

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `surgefoil` | `shw\|ff` or `b\|ff` (frame-dependent) | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | The `hob` fancy-foil sheet. **60 family prints, 0 lone** (every surgefoil shares its `illustration_id` with a same-art non-surgefoil twin — verified). Two sub-groups: **showcase** surgefoils (hob 250–274, `shw\|ff`) dupe the plain showcase siblings (e.g. Azog 258↔222, art `182adfc5`); **inverted-poster** surgefoils (hob 275–284, `b\|ff`) dupe the **poster** panels of §4 (e.g. Gleaming Splendor 275↔239 art `d7bdeff9`; Bard 280↔244 art `150ac73b`). Both compute to a treatment CONTAINING `ff`, and the `(name, codes-minus-ff)` sibling dedup pairs them cleanly (`shw`↔`shw`, `b`↔`b`), so the DUPE_FOIL gate catches ALL of them — drops the surgefoil, keeps the showcase/poster representative. Verified: preferred keeps poster panels 239–248 as nonfoil, drops 275–284 foil twins |
| `poster` | `b` (borderless + `inverted`; NO `ff`) | **no — unique art, KEPT** | hob 239–248 — 10 borderless-inverted showcase panels of headline cards (Gleaming Splendor 239, The Lord of the Eagles 240, Gollum 241, Gandalf 242, Thorin 243, Bard 244, Smaug 245, Thranduil 246, The Arkenstone 247, The Lonely Mountain 248). Mixed artists (Bousema, Jacobson, …) — NOT a tiling panorama, just the "poster" showcase treatment. Distinct art; the nonfoil poster is the `preferred` representative (its surgefoil foil twin 275–284 drops). Unlike LTR's poster series (§4b there), these compute to `b` not `ff`, and the user gets them via ordinary borderless-inverted collecting — KEPT in missing-set |
| `headliner` (+`poster`+`gleaminggold`) | `''` (EMPTY treatment) | **no — excluded via UNOBTAINABLE rule (§5)** | **hob 249 Smaug the Magnificent** — the family headliner, `black` border, foil-only, **~$22,250** (!). ⚠ Its `gleaminggold`+`headliner` combo computes to an EMPTY treatment string, which behaves as `regular` — so it does NOT self-exclude; it LEAKED into the `mythic-regular` sub-selector (it was 93% of hob's raw missing $, $22,250 of ~$23,840). Removed by `FAMILY_UNOBTAINABLE_RULES["hob"]` `{headliner, gleaminggold}` (§5) — the same handling as the TLA/EOE/ECL/SOS/MSH headline ultra-rares |
| `boxtopper` | `b` (borderless) | no — KEPT | hoc 25 Delighted Halfling, hoc 28 Aragorn and Arwen, Wed — 2 borderless box-topper prints (the [box-topper booster](../product-types.md), see §9). Distinct borderless art, computes to `b`, KEPT as preferred |
| `bundle` | `''` | promo — KEPT | hob 321 The Misty Mountains Cold — bundle promo singleton. KEPT (a distinct promo the user may want) |

**Full-art convention:** standard — borderless prints carry `border_color:
borderless` + `frame_effects: inverted`/`showcase`; `full_art` not relied upon.
The poster panels (239–248) are `border_color: borderless` + `frame_effects:
[legendary/enchantment, inverted]`.

---

## 3. Chase variants

**None** of the character-multi-art kind. The `chase` modifier (`set:hob+related
chase`, threshold 3) surfaces only **basic-land art runs** (Plains 194/313–320,
etc. — multiple foil/nonfoil arts of one basic), which are noise, not a
collectible chase. No named card has ≥3 distinct-art printings at one `(name,
treatment)`: the set's variety is base / showcase / poster / surgefoil tiers of
the *same* art, not multi-art of one card (contrast LTR's 9-artist Nazgûl).

`chase:5` gives the same basic-land-only result. So `mm query missing-set hob`'s
`uncommon-chase` sub-selector contributes nothing meaningful for this family.

---

## 4. Scenes / posters / panoramas

**No tiling scene/panorama.** The `poster`-tagged prints (hob 239–248) were
audited against the LTR borderless-inverted artist-run recipe and are **NOT** a
scene set: they're 10 individually-arted borderless-inverted showcase panels of
headline cards across mixed artists (James Bousema, Tyler Jacobson, …), not a
contiguous single-artist run that tiles into a poster. They are the "poster
treatment" showcase tier — distinct-art collectibles, each with a surgefoil foil
twin (275–284).

No `FAMILY_SCENES["hob"]` entry is warranted. `scripts/scene_table.py hob` is
not applicable.

**Detection recipe** (as run — confirmed no artist-run ≥3):

```bash
.claude/skills/scryfall-search/scryfall.sh search 'set:hob is:poster' unique=prints \
  | jq -r '.data[] | select((.frame_effects//[])|index("inverted")) | [(.collector_number|tonumber),.name,.artist]|@tsv' \
  | sort -k1,1n
# → mixed artists across 239-248; no ≥3 contiguous same-artist run.
```

---

## 5. Unobtainable rules

`selectors.FAMILY_UNOBTAINABLE_RULES["hob"]` (configured 2026-09-16):

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {headliner, gleaminggold}` | **hob 249 Smaug the Magnificent** — the family headline ultra-rare, `black` border, foil-only, ~$22,250. ⚠ It computes to an EMPTY treatment string, which behaves as `regular` — so contrary to first impression it does NOT self-exclude; it leaked into the `mythic-regular` sub-selector (the ONLY $1000+ row, 93% of hob's raw missing $). Both `headliner` and `gleaminggold` are exclusive to this one print in the family (verified 1 each), so `any_of` catches exactly Smaug 249, nothing else. Same handling as the TLA/EOE/ECL/SOS/MSH headline ultra-rares. |

**Missing-set before/after (owns 0; whole set measured, 2026-09-16):** without this rule, `mm query missing-set hob` = **191 prints · $23,839.81** (dominated by the single $22,250 Smaug 249 leak). With it: **190 prints · $1,589.81** — a realistic buy-in. After the `surgefoil` DUPE_FOIL drop + this rule, the `preferred` top is ordinary singles the user wants (The One Ring hoc 44 ~$149, Gleaming Splendor poster 239 ~$78, The Arkenstone 247 ~$66, Orcish Bowmasters hoc 19 ~$61), no scarcity tier remaining.

**Effect of the two curation rules on the full `mm query missing-set` union
(user owns 0; whole-set measure, 2026-09-16):**

| Config | Prints | Missing $ |
|---|---:|---:|
| unconfigured (raw union) | 191 | **$23,839.81** |
| + `surgefoil` DUPE_FOIL + `{headliner,gleaminggold}` UNOBTAINABLE | 190 | **$1,589.81** |

The ~$22,250 drop is dominated by the single Smaug 249 headliner leak; the
surgefoil dupes (e.g. Gleaming Splendor 275 foil $591.79 → dropped, its nonfoil
poster twin 239 $77.89 → kept) account for the rest.

Also filtered **globally** (not via `hob`-specific rules):
- `serialized` promo_type → any serialized twins (none prominent in this family).
- `rebalanced` / `alchemy` → digital-only Arena prints (none; arena-leak check clean, §7).

---

## 6. PRM destinations

**No promo sibling set exists** for this family (no `phob`, no prerelease/promo
code — only `hob`/`hoc`/`thob`). If the user later presents a PRM-stamped Hobbit
promo, it will most likely land in a cross-set WPN/Play code (`pw26`) or a future
`phob` — resolve by name+artist and read the Scryfall CN off the match (see
`.claude/skills/bulk-add/SKILL.md` § "Printed `PRM` set code"). Update this
section when the first such promo surfaces.

| Physical stamp | Scryfall set | Channel | Example |
|---|---|---|---|
| (none observed as of audit) | — | — | — |

---

## 7. Edge cases & gotchas

- **`hoc` is `set_type: eternal`, not `commander`** — the commander-style sibling
  carries the `eternal` type (same quirk as TMT's `tmc`; contrast LTR's `ltc`
  which is genuinely `commander`). It is included in `set:hob+related` because
  `sets.filtered_codes()` allows `eternal`. It holds the family's reprint value:
  The One Ring (hoc 44 nonfoil ~$149 / hoc 84 foil ~$608), Orcish Bowmasters
  (hoc 19/59), Galadriel/Sauron/Tom Bombadil, and the 2 boxtoppers (25/28).
- **hob 249 Smaug the Magnificent headliner (~$22,250)** — `gleaminggold`+
  `headliner`, black border, foil-only, the family's whale. ⚠ Its EMPTY computed
  treatment behaves as `regular`, so it does NOT self-exclude — it leaked into
  the `mythic-regular` sub-selector (93% of hob's raw missing $) until the
  `FAMILY_UNOBTAINABLE_RULES["hob"]` `{headliner, gleaminggold}` rule was added
  (§5). Now correctly out of `missing-set`.
- **Split/adventure `//` names** — several prints are DFC/adventure (Gandalf,
  Goblins' Bane // Flameshape 96/242/278; The Arkenstone // Seek the Heart
  247/270/283). `jq` name-equality matching on these fails (the `//` full name);
  match on `illustration_id` or CN instead when scripting.
- **Basic-land chase noise** — the `chase` modifier surfaces only basic lands
  (Plains 194/313–320 etc.), not a real chase (§3). Ignore.
- **Meld-back faces** — none known.
- **Arena/digital leak** — `mm query show 'set:hob+related missing' | grep -i
  arena` returns 0 rows (clean).

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["hob"]` — **configured** `frozenset({"surgefoil"})` (§2): drops the 60 same-art collector-foil dupes.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["hob"]` — **configured** `{headliner, gleaminggold}` (§5): removes the Smaug 249 headliner ($22,250) that leaked via its empty computed treatment.
- `selectors.py:FAMILY_SCENES["hob"]` — **not applicable** (no tiling scene, §4).
- `selectors.py:_modifier_chase` — no meaningful chase for this family (§3).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md) — this
section records only `hob`-specific detail.

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Box-topper insert | [Box topper](../product-types.md) | hoc 25 (Delighted Halfling), hoc 28 (Aragorn and Arwen, Wed) — 2 borderless box-topper prints. `box-topper` booster type in MTGJSON (EV ~$22.51, 100% coverage) |
| Bundle | Bundle | hob 321 The Misty Mountains Cold — bundle-promo singleton (`bundle` promo_type) |

**Booster types (for `sealed-value` EV).** MTGJSON carries per-card WotC weights;
`sealed-value` reads them at runtime. Enumerated via
`uv run python scripts/sealed_value.py hob --list-boosters`:

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `play` | EV ~$4.34, coverage 91.6%, 2 layouts — the standard Play Booster. |
| `collector` | EV ~$47.20, coverage 89.7%, 2 layouts — Collector Booster (pulls the surgefoil/poster showcase tiers). Coverage <100% (a sheet points at not-fully-priced showcase prints). |
| `box-topper` | EV ~$22.51, coverage 100%, 1 layout — the box-topper insert (hoc 25/28). |
