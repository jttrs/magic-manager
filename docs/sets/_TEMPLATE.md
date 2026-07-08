# `<ANCHOR>` — `<Human-Readable Family Name>`

> Per-family memory doc. Read this before answering set-specific questions about
> `<ANCHOR>` or working on `<ANCHOR>`-related commands. When new peculiarities
> emerge in chat, update the appropriate section here so the knowledge outlives
> the session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `<anchor>`
**Family root type:** `<expansion | commander | draft_innovation | masterpiece | promo>`
**Family released:** `<YYYY-MM-DD or range>`
**Last audit:** `<YYYY-MM-DD>` via `/characterize-set <anchor>` (or "manual").

---

## 1. Family map

Every Scryfall set code that belongs to this family (including separately-rooted bonus sheets that logically belong to the family but have `parent_set_code: null`).

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `<anchor>` | expansion | N | YYYY-MM-DD | parent |
| `<siblingA>` | commander | N | YYYY-MM-DD |  |
| `<siblingB>` | promo | N | YYYY-MM-DD |  |
| … | … | … | … | … |

**Separately-rooted bonus sheets** (Scryfall's `parent_set_code` doesn't link these; they must be added explicitly via `mm set master-list <anchor> --only <anchor>,<sibling>,<bonus>`):

- `<code>` — `<name>` (why it belongs here despite null parent).

**`mm` invocations that need `--only`:**

```
mm set master-list <anchor> --only <anchor>,<sibling1>,<sibling2>,<bonus>
```

---

## 2. Treatments

Which `promo_types` appear in this family, and how they map through `treatments.compute_treatment()` (`src/magic_manager/treatments.py`).

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `surgefoil` | `ff` | yes → `FAMILY_DUPE_FOIL_PROMO_TYPES` | same art as base, fancy foil |
| `chocobotrackfoil` | `ff` | **no — unique art** | kept even though it's a fancy foil |
| … | … | … | … |

**Full-art convention:** `<full_art field is TRUE on which category | FALSE everywhere>`.
Some UB families flip this convention — record what's true here.

---

## 3. Chase variants

Card names with ≥3 distinct-art printings at the same `(name, treatment)` in this family. Detected by `selectors._modifier_chase` (default threshold 3).

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| `<Card Name>` | N | `<anchor>` CN A–B | uncommon | regular |
| `<Other Name>` | N | `<sibling>` CN A–B | rare | ext |

Chase variants surface in `mm query missing-set <anchor>` via the `uncommon-chase` sub-selector (added `751e627`, see `cli.py:2200-2210`).

---

## 4. Scenes / posters / panoramas

Scryfall-UI-only groupings that don't appear in card metadata. Detection is heuristic (typically contiguous-CN by same artist).

| Scene / poster | CN range | Cards | Detection |
|---|---|---:|---|
| `<name>` | `<anchor>` 399–451 | 53 | borderless-inverted + artist-run |

If a detailed one-off analysis exists, link it (e.g. `docs/ltr-borderless-scenes.md`).

**Detection recipe** (if this family has scenes worth cataloguing):

```
.claude/skills/scryfall-search/scryfall.sh search 'set:<anchor> border:borderless' unique=prints
# Filter to inverted frame, exclude scroll/silverfoil/poster/serialized,
# group by (artist, contiguous-CN-run), keep runs ≥3.
```

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["<anchor>"]` in `src/magic_manager/selectors.py` with rationale. These are prints the user has personally ruled out of missing-set output despite them being distinct art.

| Rule | Rationale |
|---|---|
| `promo_types_all_of: {silverfoil, scroll}` | LTR-style: scroll-frame showcase prints, bundle-only, rarely surface |
| … | … |

---

## 6. PRM destinations

For the "I have a PRM-stamped card" flow ([[bulk-add]] skill). PRM is the printed set-code stamp; the actual Scryfall set code depends on which promo channel the card came from.

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` (e.g. `114s`) | `p<anchor>` | Prerelease datestamped | Spider-Ham 114s → `pspm` 114s |
| `N` (small, 1-16) | `pw25` / `pw26` | WPN Play Promo | Spider-Ham 10 → `pw25` 10 |
| `N` (small, 1-N) | `<L>mar` etc. | Special insert (Marvel Legends, etc.) | Anti-Venom 1 → `lmar` 1 |

The physical CN often DOESN'T match Scryfall's CN — resolve by artist+name and read the Scryfall CN off the match.

---

## 7. Edge cases & gotchas

Anything else that doesn't fit above. Free-form.

- Meld-back faces (if any): CNs that only exist as the back face of a meld pair — not sold as products.
- Digital-only prints (Arena/Alchemy rebalanced) — filtered globally by `selectors.UNOBTAINABLE_PROMO_TYPES`.
- Name collisions between siblings (e.g. same card name at different CNs in `<anchor>` vs `<sibling>`).
- Serialized 1-of-N chase prints — filtered globally.
- Sets in the family with `set_type` mismatched from their content (e.g. TMT's `tmc` is `set_type: eternal` but is actually a Commander deck).

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["<anchor>"]` — <status: configured / not configured>
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["<anchor>"]` — <status: configured / not configured>
- Related test data: `<path>` if any
