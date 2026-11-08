# `who` — Doctor Who

> Per-family memory doc. Read this before answering set-specific questions about
> `who` or working on `who`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `who`
**Family root type:** `commander` (Universes Beyond — a 4-deck preconstructed Commander *product* + Collector Boosters, NOT a draftable expansion; same shape as [`pip`](pip.md) / [`40k`](40k.md))
**Family released:** 2023-10-13
**Last audit:** 2026-11-01 via `/characterize-set who` (survey_treatment_signature + local DB + Scryfall wrapper; non-interactive batch run — tier decisions pending owner review).

---

## 1. Family map

Tiny, clean topology — parent commander product + its token set. No promo/prerelease set, no masterpiece sheet.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `who` | commander | 1178 | 2023-10-13 | parent — 4 Commander decks + Collector Booster sheets (see CN map below) |
| `twho` | token | 64 | 2023-10-13 | Doctor Who Tokens — CN 1–32 regular, 33–64 surgefoil twins |

**Separately-rooted bonus sheets:** none. Release-window `/sets` scan (2023-09-15 → 2023-11-15) shows only `who`, `twho` (plus unrelated `altc`, `ywoe`). No `pwho`.

**`who` CN map** (verified from local DB):

| CN band | Content | Finishes / treatment |
|---|---|---|
| 1–8 | The 8 face commanders (Davros, 4th/10th/13th Doctor, Rose Tyler, Sarah Jane Smith, Yasmin Khan, Missy) | foil-only, `regular` — the deck's foil commander printings |
| 9–191, 196–331 | Deck contents (new cards + reprints + basics) | nonfoil+foil, `regular` |
| 192–195 | Davros / 4th / 10th / 13th Doctor — oversized display commanders | `etched`, `thick`, inverted → `b\|ff` |
| 332–534 | Extended-art collector versions | nonfoil+foil, `ext` |
| 535–564 | Borderless showcase (17 characters 535–551 + the 13 Doctors 552–564) | nonfoil+foil, `b\|shw` |
| 552z–564z | Serialized doublerainbow Doctors (13) | foil, globally filtered |
| 565 | Past in Flames — `release` promo | foil |
| 566–605 | 40 Planechase planes / phenomena (decks include planar decks) | nonfoil-only, common |
| 606–1125 | Surgefoil twins of the regular (606–922) and extended-art (923–1125) prints | foil, `ff` / `ext\|ff` |
| 1126–1155 | Surgefoil twins of the borderless showcase 535–564 | foil, `b\|shw\|ff` |
| 1156–1165 | Surgefoil basics/misc | foil, `ff` |

**`mm` invocations:** default `set:who+related` resolution works. No `--only` needed.

---

## 2. Treatments

`promo_types` frequency (1242 prints incl. tokens): `universesbeyond` 1242, `boosterfun` 806, `surgefoil` 592, `serialized` 13, `doublerainbow` 13, `thick` 4, `release` 1.

**Frame/finish treatment classes present** (computed treatment × finish):

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 391 nonfoil / 360 foil | 1–331, 566–605 (+ twho 1–32) | `regular` | handled by rarity/base sub-selectors |
| surgefoil twin | 359 | 606–922, 1156–1165, twho 33–64 | `ff` | auto-dropped (pure `ff`) |
| extended-art | 203 nf / 203 foil | 332–534 | `ext` | auto-dropped by `preferred` (ext class) |
| extended-art surgefoil | 203 | 923–1125 | `ext\|ff` | auto-dropped (ext class) |
| showcase (borderless) | 30 nf / 30 foil | 535–564 | `b\|shw` | KEPT by default — **kept (default) — pending owner review** (see §5) |
| showcase (borderless) surgefoil | 30 | 1126–1155 | `b\|shw\|ff` | collapses onto 535–564 via proposed `surgefoil` dupe-foil |
| showcase (borderless) serialized | 13 | 552z–564z | `b\|shw\|ff` | globally filtered (`serialized`) |
| etched (oversized/thick) | 4 | 192–195 | `b\|ff` [etched] | auto-dropped (ff-dupe collapse); display cards, not shopped |

No **black-bordered** showcase exists in this family — every showcase is borderless (`fe=[showcase, inverted]`, `border=borderless`). The showcase art is **distinct** from the base/ext art (different `illustration_id` for every 535–564 vs its base; e.g. Davros 540 ≠ Davros 1/407).

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `universesbeyond` | (none) | n/a | UB marker on every print. |
| `boosterfun` | (none) | n/a | Umbrella tag on ext / showcase / surgefoil collector prints. |
| `surgefoil` | `ff` | **yes → propose `[dupe_foil] who = ["surgefoil"]`** | 560 `who` + 32 `twho` prints; 559/560 `who` surgefoils share an `illustration_id` with a non-surgefoil sibling (exception: Osgood 796, see §7). Same shape as `pip`. |
| `serialized` + `doublerainbow` | `b\|shw\|ff` | n/a — globally filtered | 13 serialized Doctors 552z–564z (unpriced locally). |
| `thick` | (etched) | n/a | 4 oversized display commanders 192–195. |
| `release` | n/a | n/a | 1 print — Past in Flames 565 (foil). |

**Full-art convention:** `full_art` not used for the showcase; the borderless treatment rides on `frame_effects: [showcase, inverted]`.

---

## 3. Chase variants

Only low-value multi-art staples (no rare/mythic chase):

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Sonic Screwdriver | 3 | `who` 184–186 (surgefoil 789–791) | uncommon | regular |
| Command Tower | 4 | `who` 263–266 (surgefoil 854–857) | common | regular |
| Clue / Food / Treasure tokens | 3–4 each | `twho` 21–31 (surgefoil 53–63) | common | regular (tokens — excluded from missing-set) |

`mm query show 'set:who+related chase'` = 51 rows, all of the above.

---

## 4. Scenes / posters / panoramas

**None.** The borderless showcase run (535–564) is a character-portrait frame, not a panorama; no `poster` promo_type. n/a — no `[[scenes.who]]` warranted.

---

## 5. Unobtainable rules

**None proposed.** Scarcity sanity (simulated with the proposed `surgefoil` dupe-foil, in memory — config not edited):

| View | Rows | Missing $ |
|---|---:|---:|
| `set:who+related missing treatment=collectible-alt` | 73 | $1,380.98 |
| `set:who+related missing treatment=preferred` | 30 | $61.39 |
| full `missing_printings('who')` (all sub-selectors) | 260 | $400.88 |

No ⚠ concentration note from `set_status.py` (simulated). Top missing items are a smooth gradient (Cybermen Squadron $22, Danny Pink $21, Heroic Intervention $16, Everybody Lives! $16, Cyberman Patrol showcase $15).

**Tier pending owner review:** borderless showcase (535–564, 30 prints, ~$61 missing nonfoil) — **kept (default) — pending owner review.** Recommendation: keep (distinct-art character/Doctor portraits, cheap, the family's only alt-art chase). If excluded, the rule would be `frame_effects_all_of = ["showcase"]`, `border_color = "borderless"`.

Globally filtered (not per-family): `serialized`, `rebalanced`, `alchemy`.

---

## 6. PRM destinations

**No promo set exists** (no `pwho`, no prerelease — direct-to-retail Commander product). The single `release` promo (Past in Flames, `who` 565) lives in the parent set. The 14th/15th Doctor cards are **Secret Lair** (`sld` 1583–1584), not part of this family.

---

## 7. Edge cases & gotchas

- **Commander PRODUCT, not an expansion** — no draft/set/play boosters; `missing-set` still works via rare/mythic/treatment sub-selectors.
- **Planechase cards in-set** — 40 planes/phenomena at 566–605, nonfoil-only commons (each deck shipped a 10-card planar deck). They are ordinary `regular` commons in missing-set terms.
- **Face commanders 1–8 are foil-only** (`regular` treatment, ~$0.30 each) — the deck's foil commander. They share `illustration_id` with their extended-art (e.g. Davros 1 = 407), etched oversized (192) and surgefoil (606, 998) prints; only the borderless showcase (540/1131) is a different art.
- **Osgood, Operation Double 796** (surgefoil) carries a different Scryfall `illustration_id` than 191/367/958 (same artist, Justyna Dura). Likely Scryfall data quirk; harmless — pure `ff` is auto-dropped from preferred anyway.
- **Serialized Doctors 552z–564z** — `z`-suffix CNs, unpriced locally; globally filtered.
- **No arena/digital leak** — `mm query show 'set:who+related missing' | grep -ic arena` → 0.
- **`twho` surgefoil token twins** (33–64) — tokens are excluded from missing-set at the `is_token` chokepoint.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] who = ["surgefoil"]` — configured 2026-11-08 (enables `mm query missing-set who`).
- `config/families.toml` `[[unobtainable.who.rules]]` — None configured yet (none proposed).
- `config/families.toml` `[[scenes.who]]` — none (no scenes).
- Related test data: none.

---

## 9. Product types

Archetypes live in [`../product-types.md`](../product-types.md). Doctor Who = four 100-card UB Commander decks + a Collector Booster SKU.

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Blast from the Past | Commander Deck | fileName `BlastFromThePast_WHO` |
| Masters of Evil | Commander Deck | fileName `MastersOfEvil_WHO` |
| Paradox Power | Commander Deck | fileName `ParadoxPower_WHO` |
| Timey-Wimey | Commander Deck | fileName `TimeyWimey_WHO` |
| Doctor Who Collector Booster | Collector Booster | ext (332–534), showcase (535–564), surgefoil (606–1165), serialized Doctors (552z–564z) |

Each deck includes a planar deck (CN 566–605). All four are `Commander Deck` ∈ `PRECON_MODERN_TYPES` → picked up by `mm set precon-list` / `mm deck add-precon who --all`.

**Booster types (for `sealed-value` EV):**

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `collector` | EV ~$46.94, coverage 99.6%, 1 layout. |
| `collector-sample` | EV ~$5.03, coverage 100%, 3 layouts. |
