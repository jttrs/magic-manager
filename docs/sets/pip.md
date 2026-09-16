# `pip` — Fallout

> Per-family memory doc. Read this before answering set-specific questions about
> `pip` or working on `pip`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `pip`
**Family root type:** `commander` (Universes Beyond — a 4-deck preconstructed Commander *product*, NOT a draftable expansion)
**Family released:** 2024-03-08
**Last audit:** 2026-09-15 via `/characterize-set pip` (survey_treatment_signature + Scryfall direct queries + local DB, fully synced).

---

## 1. Family map

Tiny, clean topology — no separately-rooted bonus sheets, no promo/prerelease set, no masterpiece sheet. Just the parent commander product + its token set.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `pip` | commander | 1068 | 2024-03-08 | parent — the 4-deck Fallout Commander product (see §9) |
| `tpip` | token | 22 | 2024-03-08 | Fallout Tokens (not synced locally; tokens aren't shopped) |

**Separately-rooted bonus sheets:** none. Verified via the release-window `/sets` scan (`released_at` 2024-02 → 2024-04) — only `pip` + `tpip` carry the Fallout name. No `ppip` promo code exists.

**`mm` invocations:** default `set:pip+related` resolution works. No `--only` needed.

---

## 2. Treatments

`selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["pip"]` — **not configured yet.** Propose `frozenset({"surgefoil"})`. See §8 / PROPOSED DIFFS.

`promo_types` frequency across the family (1068 prints): `universesbeyond` 1068 (every card — it's a UB set), `surgefoil` 528, `serialized` 7, `doublerainbow` 7, `thick` 4, `release` 1. Only one co-occurrence pair ≥10: `surgefoil + universesbeyond` (528).

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `universesbeyond` | (base, no keyword on its own) | n/a | Present on ALL 1068 prints; it is the UB marker, not a treatment. |
| `surgefoil` | `ff` (verified — `compute_treatment` returns `ff`) | **yes → DUPE_FOIL** | 528 prints, the collector-foil sheet. Each is the SAME art as a `universesbeyond`-only sibling, just on the surgefoil sheet (e.g. PIP 722 Abundant Growth = PIP 194; PIP 617 Agent Frank Horrigan = PIP 89 art). The whole "collector" run (CN ~581–889) is surgefoil twins of the main run. |
| `serialized` + `doublerainbow` | `b\|ff` (base showcase + fancy foil) | n/a — globally filtered | The 7 serialized **SPECIAL-slot bobbleheads** (CN 1057–1068 range, `border=black fe=[inverted]`), foil-only, ~$640–$1,050 each. Globally excluded by `selectors.UNOBTAINABLE_PROMO_TYPES` (`serialized`), so they never reach `treatment=preferred` — no per-family rule needed. Each has a non-serialized base (`universesbeyond`) + surgefoil twin still in scope. |
| `thick` | (thick stock, not an art variant) | n/a | 4 prints — oversized/thick-stock display cards, not shopped as singles. |
| `release` | n/a | n/a | 1 print — a release promo. Incidental. |

**Full-art convention:** `full_art` is **FALSE** on the borderless showcases here (checked PIP 722/194/617 → `full_art=0`). Fallout's borderless treatment rides on `frame_effects: ["inverted"]` (± `showcase`), not the `full_art` flag. Treatment classification keys off `inverted`/`showcase`, so this is fine.

---

## 3. Chase variants

**None.** `mm query show 'set:pip+related chase'` returns **0 rows**. Being a precon product, `pip` has no card with ≥3 distinct arts at the same `(name, treatment)`: the standard shape is base `universesbeyond` + surgefoil twin (2 finishes of ONE art), which the dupe-foil filter collapses. The borderless boosterfun reprints (CN 343–361) are single-art each. `mm query missing-set pip`'s `uncommon-chase` sub-selector will therefore be empty — expected, not a bug.

---

## 4. Scenes / posters / panoramas

**None.** The only contiguous single-artist run is CN 353–361 (9 cards, artist "AKQA" — a studio credit) but it is a mixed-rarity run of unrelated borderless reprints (Farewell, Ravages of War, Vandalblast, Arcane Signet, Crucible of Worlds, Nuka-Cola Vending Machine, Sol Ring, Command Tower, Wasteland), NOT a spatial panorama/scene. These are the "Fallout" full-borderless showcase reprints, handled by the normal missing-set pipeline. No `FAMILY_SCENES["pip"]` entry warranted.

---

## 5. Unobtainable rules

`selectors.FAMILY_UNOBTAINABLE_RULES["pip"]` — **none needed.** The only concentrated scarcity tier (the 7 serialized doublerainbow SPECIAL bobbleheads, ~$4,900 of the raw missing $) is already removed by the GLOBAL `serialized` filter — no per-family rule required.

**Scarcity sanity (before/after missing total):**

| View | Rows | Missing $ |
|---|---:|---:|
| `treatment=collectible-alt` (full bypass — includes serialized) | 88 | **$6,998.10** |
| `treatment=preferred` (proposed dupe-foil `{surgefoil}`, no unobtainable rules) | 36 | **$410.64** |

The drop from $6,998 → $411 is entirely (a) surgefoil dupe-foils collapsing onto their base art and (b) the globally-filtered serialized bobbleheads (~$4,900) dropping out. What remains ($411 across 36 rows) is a smooth gradient of genuinely-shoppable borderless/extendedart reprints — top items Sol Ring ($36), Crucible of Worlds ($33), Nuka-Cola Vending Machine ($30), Wasteland ($27), Walking Ballista ($24). No lingering $100+ concentration. Nothing to exclude.

Globally filtered (not per-family): `serialized`, `rebalanced`, `alchemy` (`selectors.UNOBTAINABLE_PROMO_TYPES`).

---

## 6. PRM destinations

**No dedicated promo/prerelease set exists for Fallout** (no `ppip`, no `pip`-prerelease code). Fallout was a direct-to-retail Commander product with no prerelease events, so there is no `Ns`-stamped datestamp channel. If the user ever presents a "PRM"-marked Fallout card, it is almost certainly the `release` promo (1 print in-set) or a `thick`-stock display card — resolve by name + artist against `set:pip` directly. Nothing to catalog here.

---

## 7. Edge cases & gotchas

- **`pip` is a Commander PRODUCT, not an expansion** — `set_type: commander`, 4 preconstructed decks (see §9), no draft/set/play boosters. `mm query missing-set pip` still works via the standard rare/mythic/treatment sub-selectors; there just are no draftable rarities-at-once and no booster EV interpretation.
- **`pip` DOES have `collector` booster data** despite being precon-only — `sealed_value.py pip --list-boosters` reports a `collector` booster (EV ~$87.70, 99.4% coverage) and a `collector-sample`. Fallout shipped Collector Boosters as a companion SKU to the Commander decks. So §9b is NOT empty for this family (contrary to the usual precon-product assumption). Coverage 99.4% is healthy — no unsynced-sheet gap.
- **No arena/digital leak** — `mm query show 'set:pip+related missing' | grep -i arena` returns nothing. `_is_digital_only` behaves.
- **Two `universesbeyond` arts for a few cards** — e.g. Agent Frank Horrigan has PIP 89 (main) and PIP 405 (a second `universesbeyond` art); the surgefoil PIP 617 is the foil twin of ONE of them, not a third art. Both non-foil arts stay in scope for missing-set (distinct art); the surgefoil collapses via DUPE_FOIL.
- **`tpip` tokens not synced** — 0 prints locally. Tokens aren't shopped; no action needed.
- **The 7 SPECIAL bobbleheads** (Agility/Charisma/Endurance/Intelligence/Luck/Perception/Strength + one extra) exist in three tiers: base `universesbeyond` (CN ~126–132), surgefoil twin (CN ~654–671), and serialized `doublerainbow` (CN 1057–1068). Only the first two are shoppable; the serialized tier is globally filtered.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["pip"]` — **not configured.** Propose `"pip": frozenset({"surgefoil"})` (528 same-art collector-foil twins; verified `surgefoil` → treatment `ff`, so the DUPE_FOIL drop in `_filter_treatment_preferred` catches them).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["pip"]` — **none needed** (the only scarcity tier, serialized bobbleheads, is filtered globally). See §5.
- Related test data: none.

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md) — this section records only Fallout's specifics.

Fallout is a **Universes Beyond Commander product**: four ready-to-play 100-card Commander decks (the `ncc`/Commander-preconstructed shape), sold individually and as a set, with a companion Collector Booster. No draft/set/play boosters, no bundle-with-boosters.

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Scrappy Survivors | Commander Deck | MTGJSON fileName `ScrappySurvivors_PIP`; 93 mainboard + 1 commander. |
| Science! | Commander Deck | fileName `Science!_PIP` (note the `!` in the name); 92 + 1. |
| Mutant Menace | Commander Deck | fileName `MutantMenace_PIP`; 90 + 1. |
| Hail, Caesar | Commander Deck | fileName `HailCaesar_PIP`; 91 + 1. |
| Fallout Collector Booster | Collector Booster | Companion SKU — surgefoil (CN ~581–889) + serialized SPECIAL bobblehead slots. See §9b. |

All four are picked up by `mm set precon-list` (type `Commander Deck` ∈ `PRECON_MODERN_TYPES`). `mm deck add-precon pip --all` / `import-precon` handle them the standard way.

### 9b. Booster types (for `sealed-value` EV)

Unlike most precon-only products, Fallout **does** expose booster data (its Collector Booster SKU):

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `collector` | EV ~$87.70, coverage 99.4%, 1 layout. The Fallout Collector Booster — surgefoil main sheet + a SPECIAL slot (bobbleheads incl. the serialized doublerainbow parallels). Healthy coverage; no unsynced-sheet gap. |
| `collector-sample` | EV ~$6.41, coverage 99.4%, 2 layouts. A sample/promo variant. |

No draft/set/play booster exists — the four Commander decks themselves are fixed lists, valued as decks (not booster EV) by `construct-value`.
