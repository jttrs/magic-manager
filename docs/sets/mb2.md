# `mb2` — `Mystery Booster 2`

> Per-family memory doc. Read this before answering set-specific questions about
> `mb2` or working on `mb2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `mb2`
**Family root type:** `masters`
**Family released:** 2024-08-02
**Last audit:** 2026-11-02 via `/characterize-set mb2` (batch run, non-interactive — keep/exclude decisions pending owner review).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mb2` | masters | 385 | 2024-08-02 | parent — standalone (`parent_set_code: null`, no children: no token / promo / art-series sibling) |

**The `mb2` code holds only the product's special sheets (385).** Most of a Mystery Booster 2 pack is reprints that Scryfall files in **`plst`** (The List). Verified against MTGJSON `MB2.json` `booster.draft.sheets` uuids (2026-11-02):

| Booster sheet (per pack) | Sheet size | Where the printings live |
|---|---:|---|
| `white`/`blue`/`black`/`red`/`green` (2 each) | 242 each | **`plst`** — 1,355 `plst` prints dated 2024-08-02, CNs `<SET>-<CN>` (e.g. `PCY-1` Abolish) |
| `landmulticolorless` (1) | 121 | **`plst`** |
| `rareMythic` (1) | 121 | **`plst`** |
| `whiteBorder` (1) | 121 | **`mb2` 1–121** (weighted 140/153) |
| `futureSight` (1, 94.7% of packs) | 121 | **`mb2` 122–242** (weighted 140/153) |
| `futureSightFoil` (replaces it, 4.5%) | 114 | **`mb2` 144–257** (foil; 243–257 exist ONLY on this sheet) |
| `alchemyAcorn` (replaces it, 0.8%) | 7 | **`mb2` 258–264** |
| `playtest` (1) | 120 | **`mb2` 501–621** |

So `set:mb2+related` / `mm query missing-set mb2` covers the 385 MB2-exclusive prints, **not** the `plst` reprints opened from the product (`plst` is an unbounded reprint pool, out of scope). No `--only` needed.

Related-but-separate Mystery Booster codes (NOT in this family): `mb1`/`fmb1` (Mystery Booster 1, 2019), `cmb1`/`cmb2` (playtest cards 2019/2021), `mbc` (Mystery Booster Commander Edition, 2026 — see [`mbc.md`](mbc.md); its `playtest` and most `futureSight` slots pull from **this** set's 501–621 / 122–257 prints).

**Local DB note:** local `plst` is stale (1 row dated 2024-08-02 vs 1,355 on Scryfall); `sealed_value.py mb2 --list-boosters` still reports 98.3% coverage, but sync `plst` before trusting EV.

---

## 2. Treatments

No showcase, no borderless, no extended-art, no etched, no fancy-foil `promo_types`. Differentiation is by **frame + border + stamp + sheet**, not treatment (survey 2026-11-02: computed `regular` for 381, `fa` for 4):

| Class | Count | CN band | Frame / border / stamp / finishes | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|---|
| white-bordered reprints | 121 | 1–121 | `frame: 2015`, **white** border, rares/mythics carry **oval** stamp, nonfoil-only; 37 R / 14 M / 36 U / 34 C | `regular` (121 Snow-Covered Wastes = `fa`) | KEPT — rares/mythics via rare-/mythic-regular |
| future-frame reprints | 121 | 122–242 | `frame: future`, black border, 116 nonfoil+foil / 5 nonfoil-only (122–143 are NOT on MB2's `futureSightFoil` sheet, yet 17 of them list a foil finish — likely the `mbc` future-foil sheet); 61 R / 9 M / 32 U / 19 C | `regular` (194 Kobolds of Kher Keep, 206 Forest Bear, 228 Memnite = `fa`) | KEPT — rares/mythics via rare-/mythic-regular |
| future-frame foil-only sheet | 15 | 243–257 | `frame: future`, black border, **foil-only** (254 Arcane Signet, 256 Command Tower also nonfoil); 6 M / 5 R / 4 C | `regular` | KEPT — **scarcity tier, pending owner review (§5)** |
| acorn "alchemy" foils | 7 | 258–264 | `frame: 2015`, **acorn** stamp, `promo_types: alchemy`, **paper** foil-only, all uncommon | `regular` | dropped globally (`alchemy` ∈ `promo_types.toml` `unobtainable`) — see §7 |
| playtest cards | 121 | 501–621 | `frame: 2015`, black border, `promo_types: playtest`, nonfoil-only, all rare, not tournament-legal | `regular` | KEPT — **pending owner review (§5)** |
| full-art (`fa`) | 4 | 121, 194, 206, 228 | listed above; commons/uncommons | `fa` | shows in the PREFERRED PREVIEW (collectible-alt fallback) but C/U, so no missing-set sub-selector lists them |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `playtest` (121) | — | no — unique cards | not globally filtered; kept |
| `alchemy` (7) | — | no | paper acorn foils mis-caught by the digital filter (§7) |
| (no surgefoil / textured / serialized / datestamped) | — | — | nothing for `[dupe_foil]` to collapse → proposed `mb2 = []` |

**Full-art convention:** `full_art` TRUE only on the 4 `fa` prints above (art-dependent, not a sheet treatment).

**Alt-treatment tiers (kept-by-default):** no showcase/borderless tier exists. Kept tiers flagged for review: the foil-only future sheet (243–257) and the playtest cards (501–621) — kept (default) — pending owner review.

---

## 3. Chase variants

None (`set:mb2+related chase` → 0 rows). No card name repeats within `mb2`.

---

## 4. Scenes / posters / panoramas

n/a — no borderless prints.

---

## 5. Unobtainable rules

None configured. Tiers flagged for owner review (all kept (default) — pending owner review):

- **Missing-set baseline (2026-11-02, nothing owned, no exclusions; local prices synced 2026-11-02):** rare-regular = **224 prints / ~$450**, mythic-regular = **29 prints / ~$746** → ~$1,196 total.
- **Concentration (manual — `set_status.py mb2` can't compute missing until `[dupe_foil] mb2` exists, so no ⚠ note emitted):** top 5 = Urza, Lord High Artificer 244 ($286.55 foil), Titania, Protector of Argoth 249 ($190.83), Gix, Yawgmoth Praetor 245 ($96.88), Karn, Legacy Reforged 255 ($47.78), Reflecting Pool 257 ($42.41) ≈ $664 = **56%** — all on the **foil-only future sheet 243–257** (rare+mythic $809 of the ~$1,196). Excluding it would drop missing to ~$387. Proposed (not applied) rule: `collector_numbers` 243–257 (see return value / below).
- **Playtest cards 501–621:** 121 rares, $27.90 total (max $1.04 Mox Poison) — would make up over half of the rare-regular **row count** while being near-worthless and not tournament-legal. Recommendation: keep (cheap), but owner may prefer `promo_types_any_of = ["playtest"]`.
- **Acorn foils 258–264** (0.8% of packs, $348; Oracle of the Alpha $159.97) — already out of missing-set (uncommon + globally filtered); no rule needed.

---

## 6. PRM destinations

n/a — no promo channel (no `pmb2` set, no prerelease / WPN stamped prints).

---

## 7. Edge cases & gotchas

- **Reprints live in `plst`, not `mb2`** — see §1. "Add my MB2 pulls" mostly needs `plst` `<SET>-<CN>` printings (resolve by name via [[bulk-add]] / `mm inventory add-card`); only white-border, future-frame, acorn and playtest cards are `mb2` CNs.
- **Acorn foils 258–264 are PAPER but filtered as digital.** Scryfall: `games: [paper]`, `digital: false`, `finishes: [foil]`, acorn stamp — yet `promo_types: [alchemy]` (they reprint Alchemy-designed cards). `selectors._is_digital_only` drops anything with `alchemy`, so these 7 vanish from Collection / `family_cards` unless owned. A global-filter question (`alchemy` as a digital signal is wrong for acorn paper prints), not a family rule. Contrast `mbc` 62/64/66, which Scryfall marks arena-only.
- **Sheet weighting:** `whiteBorder` and `futureSight` sheets are weighted 140 vs 153 (51 vs 70 cards) — not uniform; MTGJSON carries it.
- No `arena`-stamp leak (`grep -i arena` hits only the card named *Arena*, 239).
- White-bordered rares/mythics carry the **oval** stamp (tournament-legal reprints); playtest cards carry no stamp.
- Playtest double-faced cards (537, 548, 577, 582, 621) appear per-face in MTGJSON; sheet count 120 vs Scryfall 121.

---

## 8. Code refs

None configured yet (proposals pending owner review).

- Proposed: `[dupe_foil]` `mb2 = []` in `config/families.toml` (no fancy-foil sheet; the empty list unblocks `treatment=preferred` / `mm query missing-set mb2`).
- Proposed (owner decision): `[[unobtainable.mb2.rules]]` for the foil-only future sheet 243–257 and/or playtest cards.

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md). MB2 is a Mystery-Booster-style product (randomized reprint sheets from `plst` + exclusive `mb2` sheets); no precons, no Collector booster.

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Mystery Booster 2 Booster Pack | booster pack (`draft` subtype) | 15 cards: 2 per colour (10, `plst`), 1 land/multicolor/colorless (`plst`), 1 rare/mythic (`plst`), 1 white-border (`mb2` 1–121), 1 future-frame (`mb2` 122–242; foil 4.5% from 144–257; acorn foil 0.8% from 258–264), 1 playtest (`mb2` 501–621) |
| … Booster Box / Booster Box Case | booster box / case | MTGJSON `sealedProduct` entries; contents = packs |

**Booster types (for `sealed-value` EV):**

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `draft` | Only type. EV $14.90 at 98.3% coverage (3 layouts) — the colour/rareMythic sheets point at `plst`, which is stale locally; `uv run mm set sync plst` before trusting EV |
