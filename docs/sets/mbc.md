# `mbc` — `Mystery Booster Commander Edition`

> Per-family memory doc. Read this before answering set-specific questions about
> `mbc` or working on `mbc`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `mbc`
**Family root type:** `draft_innovation`
**Family released:** 2026-10-19
**Last audit:** 2026-11-01 (re-verified 2026-11-02) via `/characterize-set mbc` (batch run, non-interactive — keep/exclude decisions pending owner review).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mbc` | draft_innovation | 80 | 2026-10-19 | parent — standalone (`parent_set_code: null`, no children: no token / promo / art-series / alchemy sibling) |

**The `mbc` code holds only the product's NEW / exclusive prints (80).** Most of a Mystery Booster Commander pack is reprints that Scryfall files ELSEWHERE (verified against MTGJSON `MBC.json` `booster.draft.sheets` uuids, 2026-11-01):

| Booster sheet | Cards | Where the printings live |
|---|---:|---|
| `white`/`blue`/`black`/`red`/`green` (3 each per pack) | 358 each | **`plst`** (The List) — Scryfall's 483 `plst` prints dated 2026-10-19, CNs `<SET>-<CN>` (e.g. `CLB-662` Aboleth Spawn, `MID-1` Adeline) |
| `commander` (1/pack) | 121 | **`plst`** |
| `wildcard` (1/pack) | 111 | **`plst`** |
| `newCommander` / `newCommanderFoil` (1/pack) | 60 | **`mbc` 1–60** |
| `playtest` (1/pack) | 120 | **`mb2`** (Mystery Booster 2's playtest cards) |
| `futureSight` / `futureSightFoil` (1/pack) | 119 / 134 | **`mb2`** future-frame sheet (109 / 124) + **`mbc` 71–80** (10) |
| `alchemyAcorn` (rare slot replacement) | 10 | **`mbc` 61–70** |

So `set:mbc+related` / `mm query missing-set mbc` covers only the 80 exclusive prints — **not** the reprints opened from the product. The `plst` / `mb2` reprints are deliberately out of scope (`plst` is an unbounded reprint pool; `mb2` is its own family, no doc yet). No `--only` needed.

Related-but-separate Mystery Booster codes (NOT in this family): `mb2` (Mystery Booster 2, masters, 2024-08-02), `cmb1`/`cmb2` (playtest cards 2019/2021, funny).

**Local DB note:** the local `plst` rows are stale (newest 2024-08-02) — the 2026-10-19 MBC reprints aren't synced; `sealed_value.py mbc --list-boosters` coverage is 78.5% until `uv run mm set sync plst` runs.

---

## 2. Treatments

Flat family: **no showcase, no borderless, no extended-art, no etched, no fancy-foil `promo_types`.** Survey (2026-11-01): computed treatment = `regular` for all 80 (77 have a foil finish, 70 nonfoil). The only `promo_types` token is `alchemy` (3 prints, digital — see §7). Differentiation is by **frame + security stamp**, not treatment:

| Class | Count | CN band | Frame / stamp / finishes | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|---|
| new commanders (playtest-style legends) | 60 | 1–60 | `frame: 2015`, `legendary` frame_effect (51; the 9 planeswalkers have none), **oval** security stamp, nonfoil+foil, all `rare`, all **not Commander-legal** | `regular` | KEPT — base rares; surface via the rare-regular sub-selector |
| acorn foils | 7 | 61, 63, 65, 67–70 | `frame: 2015`, **acorn** stamp, **foil-only**, uncommon (67 Overcooked + 70 Euru carry `enchantment`/`legendary` frame_effects) | `regular` | uncommon + regular → not listed by `missing-set` (no chase); visible in Collection |
| acorn "alchemy" prints | 3 | 62, 64, 66 | acorn stamp, `promo_types: alchemy`, `games: arena`, `finishes: []` | `regular` | dropped globally by `_is_digital_only` (alchemy ∈ `UNOBTAINABLE_PROMO_TYPES`) |
| future-frame reprints | 10 | 71–80 | `frame: future`, no stamp, nonfoil+foil, Commander staples (Chaos Warp, Chromatic Lantern, Exotic Orchard, Path of Ancestry, …), Commander-legal | `regular` | KEPT — rares (72, 73, 79) surface via rare-regular; uncommons/common don't |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `alchemy` (3) | — | n/a | digital-only per Scryfall + MTGJSON; globally filtered |
| (no surgefoil / textured / serialized / datestamped) | — | — | nothing for `[dupe_foil]` to collapse → proposed `mbc = []` |

**Full-art convention:** `full_art` FALSE everywhere.

**Alt-treatment tiers (kept-by-default) for owner review:** none present — the PREFERRED PREVIEW returned no rows (no showcase/borderless/ext class exists). Not a keep/exclude question for this family.

---

## 3. Chase variants

None (`set:mbc+related chase` → 0 rows, owned or missing). Every name appears once.

---

## 4. Scenes / posters / panoramas

n/a — no borderless prints at all.

---

## 5. Unobtainable rules

None configured, none proposed. No `[[unobtainable.mbc.rules]]` needed:

- **Missing-set baseline (2026-11-01, nothing owned, no exclusions):** rare-regular sub-selector = **63 prints / $831.50** (60 new commanders + Chaos Warp, Chromatic Lantern, Exotic Orchard). Top line $44.31 (Ekthi, Contaminator Priest 1); top 5 ≈ $183 (22%) — **not concentrated**, no $100+ nonfoil print. `scripts/set_status.py mbc` emitted no ⚠ concentration note (family not yet configured, so it could not compute missing; the manual check above stands in).
- **Scarcity tier that does NOT reach missing-set:** the 10-card `alchemyAcorn` foil sheet appears in only ~0.3% of packs (booster weights 1143 + 57 of 400000) — Overcooked 67 ($75 foil), Euru, Acorn Scrounger 70 ($101.48 foil), the five Collectors unpriced. All are `uncommon` + `regular`, so neither the rare/mythic nor the uncommon-chase sub-selector lists them; no rule needed. They do appear in the web Collection view (owner may want to know they're the scarce tier).
- New-commander **foils** (`newCommanderFoil`, ~4.75% of packs; $45–$245) are a finish, not a printing — missing-set lists the printing once.

---

## 6. PRM destinations

n/a — no promo channel for this product (no `pmbc` set, no prerelease / WPN stamped prints found).

---

## 7. Edge cases & gotchas

- **Reprints live in `plst` / `mb2`, not `mbc`** — see §1. A user who opened MBC packs and asks "add these" will mostly need `plst` CNs (`<SET>-<CN>`) or `mb2`, resolved by name + set code via [[bulk-add]] / `mm inventory add-card`.
- **CN 62/64/66 (Case of the Lost Witness, Oracle of the Alpha, Perforator Crocodile) — data conflict.** Scryfall and MTGJSON both mark them `arena`-only, `digital`, no finishes, `promo_types: alchemy`, yet MTGJSON's booster data puts all 10 CNs 61–70 on the paper `alchemyAcorn` foil sheet — which suggests physical acorn-foil copies of these three Alchemy cards exist. Unverified. Today they are dropped by `_is_digital_only`. If Scryfall later relabels them as paper `foil` while keeping `promo_types: alchemy`, they'd still be filtered as digital — a `selectors._is_digital_only` question (not a family rule) to revisit then.
- Plain `mm query show 'set:mbc+related missing'` (no treatment filter) DOES list 62/64/66 as nonfoil rows with no price; the missing-set pipeline's preferred gate drops them. No `arena`-stamp leak (`grep -i arena` → 0).
- CN 1–60 are **not legal in Commander** (playtest-style new legends, oval stamp) despite being "commanders"; 71–80 are tournament-legal reprints in the Future Sight frame.
- Card count is 80 with no token set.

---

## 8. Code refs

None configured yet (proposals pending owner review).

- Proposed: `[dupe_foil]` `mbc = []` in `config/families.toml` (no fancy-foil sheet; the empty list just unblocks `treatment=preferred` / `mm query missing-set mbc`).
- `[[unobtainable.mbc.rules]]` — none proposed.

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md). MBC is a Mystery-Booster-style draft-innovation product (randomized reprint sheets + exclusive sheets); no precons, no Scene Box, no Collector booster.

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Mystery Booster Commander Edition Booster Pack | booster pack (`draft_set` subtype) | 20 cards: 3 per colour (15, `plst`), 1 commander (`plst`), 1 wildcard (`plst`), 1 new commander (`mbc` 1–60; foil ~4.75%), 1 playtest (`mb2`), 1 future-frame (`mb2` + `mbc` 71–80; foil ~4.4%) — the future-frame slot is replaced by an `alchemyAcorn` foil (`mbc` 61–70) in ~0.3% of packs |
| … Booster Box / Booster Box Case | booster box / case | contents = packs; MTGJSON `sealedProduct` entries |

**Booster types (for `sealed-value` EV):**

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `draft` | Only type. EV $28.77 at **78.5% coverage** (6 layouts) — the gap is the 2026-10-19 `plst` reprints not being synced locally; `uv run mm set sync plst` (and `mb2` if needed) before trusting EV |
