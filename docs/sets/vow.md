# `vow` — Innistrad: Crimson Vow

> Per-family memory doc. Read this before answering set-specific questions about
> `vow` or working on `vow`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `vow`
**Family root type:** `expansion`
**Family released:** `2021-11-19`
**Last audit:** `2026-09-15` via `/characterize-set vow`.

---

## 1. Family map

9 Scryfall codes, all linked via `parent_set_code` (clean graph — no separately-
rooted bonus sheets). A 2021 pre-"Play Booster"/pre-fancy-foil-era Innistrad
expansion + Commander product. `voc`'s children (`ovoc`, `tvoc`) parent to `voc`,
which parents to `vow`, so `set:vow+related` reaches all 9 from the parent.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `vow`  | expansion  | 423 | 2021-11-19 | parent |
| `voc`  | commander  | 188 | 2021-11-19 | Crimson Vow Commander — 2 preconstructed decks |
| `pvow` | promo      | 121 | 2021-11-19 | promos — prerelease (`Ns`) + promo-pack (`Np`) stamps + WPN + 2 resale `★` |
| `avow` | memorabilia|  81 | 2021-11-19 | Art Series |
| `tvow` | token      |  21 | 2021-11-19 | main-set tokens |
| `svow` | token      |   9 | 2021-11-19 | Substitute Cards (DFC helper cards; all named "Double-Faced Substitute Card") |
| `tvoc` | token      |   6 | 2021-11-19 | Commander tokens |
| `mvow` | minigame   |   3 | 2021-11-19 | Minigame inserts |
| `ovoc` | memorabilia|   2 | 2021-11-19 | Commander Display Commanders (oversized) |

854 prints in the family total. Default value-bearing scope is `vow` (expansion)
+ `voc` (commander). `mm set master-list vow` / `set:vow+related` resolve the
whole family from the parent — no `--only` needed.

**No Alchemy sibling.** VOW predates the standalone `y<code>` Alchemy-per-set
convention; its Alchemy rebalances (`A-` prefix, 11 prints, `rebalanced`+
`alchemy`) live INSIDE the `vow` set record itself (Arena-only), not a separate
`yvow`. There is no `yvow` set on Scryfall. See §7.

---

## 2. Treatments

VOW is a **2021 pre-fancy-foil-sheet set** — there is NO halofoil / surgefoil /
gilded / textured / manafoil / rainbowfoil sheet. Every premium is a *frame*
treatment (showcase / extended-art / borderless), not a duplicate-art foil sheet.
Consequently `FAMILY_DUPE_FOIL_PROMO_TYPES["vow"]` is an **empty `frozenset()`**
(like tla/spm/sos/mat/neo/blb): it exists only to unblock the `treatment=preferred`
filter; it drops nothing.

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b` / `shw` / `ext` (frame-dependent) | n/a (structural) | KEPT — the collectible showcase/borderless/ext frame. VOW 279-395: eternal-night borderless (279-287), showcase (288-324), extended-art (346-395) |
| `draculaseries` (+`boosterfun`) | `b` (borderless-inverted) | **no — DISTINCT art** | The **"Eternal Night" / Dracula Series**: 18 prints, VOW 329-345 (17 contiguous) + 403 Voldaren Estate. Universes-Within reimagining as classic Dracula characters (Count Dracula = Sorin 337, Dracula the Voyager = Edgar 341, The Three Weird Sisters = Henrika 335, Sisters of the Undead = Olivia 343, …) — different art from the base card, borderless. **KEPT** (a distinct collectible treatment the user may want). $0.2–$7 each; not a scarcity tier |
| `promopack`+`stamped` (on `pvow`) | `''` (empty) | dupe (stamp) | pvow `Np` prints (35) — promo-pack stamped copies of base cards. Compute to **empty treatment** (NOT `regular` like the ONE/tdm families — the `p`/`s` stamp promos have no frame effects). They already do NOT appear in `missing` output (§5), so no rule is needed |
| `prerelease`+`datestamped` (on `pvow`) | `''` (empty) | dupe (stamp) | pvow `Ns` prints (84) — prerelease datestamped copies. Same as above: empty treatment, absent from `missing` — no rule needed |
| `resale` (on `pvow`) | `''` | promo (`★` variant) | pvow 46★ Welcoming Vampire, 118★ Headless Rider — "resale"/retailer promo copies with `★` collector suffix. Singletons, low value; absent from missing. No rule |
| `moonlitland`+`wizardsplaynetwork` | `b` (inverted full-art land) | promo (unpriced) | VOW 408-412 — the WPN "Eternal Night" full-art basic lands (Plains/Island/Swamp/Mountain/Forest). WPN-distribution promos, no market price. KEPT (harmless; unpriced so no value bloat) |
| `playpromo` | `b` (inverted) | promo | VOW 405-407 Geistlight Snare/Fell Stinger/Dominating Vampire — Play Promo, foil-only, ~$0.26-$0.39. KEPT |
| `bundle` | `''` | promo (basic land) | VOW 399-402 bundle basic lands (Island/Mountain/Forest…) — each has plain base siblings. Low-value dupes, KEPT (basic lands, negligible) |
| `thick` | — | oversized | 2 `ovoc` Display Commanders (oversized stock). Memorabilia, not a tradeable single |
| `rebalanced`+`alchemy` | (digital) | digital-only | 11 `A-` prints inside `vow` — Arena rebalances, globally filtered (§7) |

**Full-art convention:** standard (borderless/showcase carry `border_color:
borderless` or `frame_effects: showcase`/`inverted`; `full_art` is TRUE only on
the moonlitland WPN lands and not relied upon for treatment).

---

## 3. Chase variants

**None** (genuine multi-art). The `chase` modifier (threshold 3) reports 208 rows,
but those are the base/showcase/ext/promo-stamp *tiers of the same art* inflating
the per-name print count — not multiple distinct arts of one card (same as tdm).
`chase:5` narrows to 9 rows, all of which are the `svow` "Double-Faced Substitute
Card" tokens (9 prints sharing one name) — a false positive of the name-count
heuristic, not a real chase. Not encoded.

---

## 4. Scenes / posters / panoramas

**None.** The Dracula Series (VOW 329-345, §2) is a *thematic* group (classic
Dracula-character reimaginings) but NOT a contiguous-art panorama/scene — each is
a standalone borderless card, not a tiled artwork. Not encoded in `FAMILY_SCENES`.
The `moonlitland` WPN lands (408-412) are a 5-land full-art cycle, also not a
panorama scene.

---

## 5. Unobtainable rules

**None needed.** `FAMILY_UNOBTAINABLE_RULES["vow"]` is absent (no entry).

- No fancy-foil scarcity sheet exists (pre-2022 set) — nothing to exclude there.
- No serialized / textured / headliner / neonink chase tier anywhere in the
  family (verified via `survey_treatment_signature.py` — the full promo_types set
  is `boosterfun, prerelease, datestamped, promopack, stamped, draculaseries,
  rebalanced, alchemy, bundle, moonlitland, wizardsplaynetwork, playpromo, thick,
  resale, buyabox`; none is a scarcity signal).
- The `pvow` stamp promos (`Np` promopack+stamped, `Ns` prerelease+datestamped)
  compute to **empty treatment** and do NOT leak into `missing` output — no
  `stamped`/`datestamped` rule required (unlike ONE/tdm, whose stamp promos
  compute to `regular` and needed a `stamped` rule to suppress).

**Missing-set impact (recorded 2026-09-15):** with an empty-`frozenset()`
DUPE_FOIL config and NO unobtainable rules, `set:vow+related missing
treatment=collectible-alt` (which equals `treatment=preferred` here, since the
empty dupe-foil set drops nothing) resolves to **97 prints**. Top of the list is
ordinary chase mythics/rares — Toxrill 321 ($14.76), Olivia 315 ($12.93), Sorin
297 ($10.31), then the Dracula Series borderless (Olivia 343 $8.96, Count Dracula
337 $7.15, Edgar 341 $6.88) and the dual lands (Shattered Sanctum, Sundown Pass,
Deathcap Glade ~$5). Max card $14.76 — **no scarcity tier dominates**, so
`missing.is_concentrated` does not fire meaningfully. Before/after are identical
(97 → 97): there is no rule to apply, so no prints drop out. (Raw `missing` with
no treatment filter = 685 prints, but that includes every treatment tier + tokens
+ art series; the value-bearing preferred slice is the 97.)

---

## 6. PRM destinations

Standard 2021 promo channels; `pvow` holds the singles (121 prints):

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` (e.g. `132s`) | `pvow` | Prerelease (prerelease + datestamped) | Toxrill 132s |
| `Np` (e.g. `132p`) | `pvow` | Promo Pack (promopack + stamped) | Toxrill 132p |
| `N★` (e.g. `46★`) | `pvow` | Resale / retailer promo | Welcoming Vampire 46★, Headless Rider 118★ |
| `N` (408-412) | `vow` | WPN Eternal Night full-art land | Forest 412 (moonlitland + wizardsplaynetwork) |
| `N` (405-407) | `vow` | Play Promo | Geistlight Snare 405 (playpromo) |

The `N` in the `pvow` CN mirrors the main-set card. Resolve a presented PRM by
name+stamp-type and read the `pvow` CN off the match. Not every base card has both
a `p` and an `s` twin — many rares have only the `s` prerelease print (see the
resale listing in §7 code refs; 84 `s` vs 35 `p`).

---

## 7. Edge cases & gotchas

- **Alchemy lives inside `vow`, not a `yvow` set.** The 11 `A-`-prefixed prints
  (`A-48` A-Binding Geist, `A-52` A-Cobbled Lancer, `A-233`, `A-235`, `A-247`,
  `A-248`, `A-58`, `A-62`, `A-66`, `A-69`, `A-81`) carry `rebalanced`+`alchemy`
  and are Arena-only. Globally filtered by `selectors._is_digital_only`. Verified
  no arena/alchemy leak: `set:vow+related missing | grep -i arena` → nothing.
- **`svow` Substitute Cards** — 9 tokens all named "Double-Faced Substitute Card"
  (DFC play-aids), no market price. They trip the `chase:5` name-count heuristic
  (§3) but are not real cards. Excluded from default value scope (token set).
- **Two Commander decks** in `voc` (188 cards): "Vampiric Bloodlust" (Strefan) and
  "Spirit Squadron" (Millicent). `ovoc` holds the 2 oversized Display Commanders.
- **No name collisions of concern** — the `pvow` stamp promos share names with
  their `vow` base but are disambiguated by set+CN-suffix.
- **Pre-Play-Booster era.** VOW used the old Draft/Set/Collector booster split
  (see §9) plus 6 mono-color + vampire theme boosters — relevant for `sealed-value`.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["vow"]` — **PROPOSED (not yet applied)**: `frozenset()` (empty — no fancy-foil sheet; unblocks `treatment=preferred` like tla/spm/sos/mat/neo/blb). See §9 of the characterization report.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["vow"]` — **not configured / none needed** (no scarcity tier; stamp promos compute to empty treatment and don't leak).
- `FAMILY_SCENES["vow"]` — not configured (no narrative panorama; §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Crimson Vow Commander decks | Commander deck | `voc` (188 cards); 2 decks — Vampiric Bloodlust (Strefan), Spirit Squadron (Millicent) |
| Crimson Vow Art Series | Art Series | `avow` (81 cards) |
| Eternal Night / Dracula Series | Showcase (borderless alt-art) | VOW 329-345 + 403; `draculaseries` promo_type; distinct Dracula-character art, KEPT (§2) |
| Bundle | Bundle | VOW 399-402 bundle basic lands + a promo; pre-Play-Booster (Set Boosters) |
| WPN Eternal Night lands | WPN Play Promo | VOW 408-412, `moonlitland`+`wizardsplaynetwork`, unpriced |

**Booster types (for `sealed-value` EV).** MTGJSON carries per-card WotC booster
weights for `vow`. Enumerate with `uv run python scripts/sealed_value.py vow --list-boosters`.

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `draft` | EV ~$4.62, coverage 86% — the classic Draft Booster (VOW is pre-Play-Booster) |
| `set` | EV ~$5.54, coverage 84% — Set Booster (2021 product line) |
| `collector` | EV ~$11.79, coverage 85% — highest-EV booster; 4 layouts |
| `arena` | EV ~$3.95, coverage 86% — the Arena/digital draft weights (physical N/A) |
| `theme-w/u/b/r/g` + `theme-vampires` | 6 mono-color/vampire Theme Boosters; theme-r ~$11.74, theme-vampires ~$10.04 (94% coverage), others ~$6.6-$7.5 |
| `prerelease` | EV ~$2.37 — the prerelease pack |
| `box-topper` | EV ~$0.91, coverage 74% — box-topper sheet (low EV) |
