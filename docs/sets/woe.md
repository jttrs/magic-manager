# `woe` — Wilds of Eldraine

> Per-family memory doc. Read this before answering set-specific questions about
> `woe` or working on `woe`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `woe`
**Family root type:** `expansion`
**Family released:** `2023-09-08`
**Last audit:** `2026-09-15` via `/characterize-set woe`.

---

## 1. Family map

9 Scryfall codes, all linked via `parent_set_code` (clean graph — no separately-
rooted bonus sheets). A standard 2023-era expansion + Commander product, notable
for the **`wot` "Enchanting Tales" masterpiece bonus sheet** (see §2/§5) that
ships in WOE boosters — the family's headline collectible feature.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `woe` | expansion | 381 | 2023-09-08 | parent |
| `woc` | commander | 173 | 2023-09-08 | Wilds of Eldraine Commander decks |
| `wot` | masterpiece | 103 | 2023-09-08 | **Enchanting Tales** bonus sheet (enchantment reprints) — booster-inserted |
| `pwoe` | promo | 160 | 2023-09-08 | promos — 80 cards × (`p` promopack+stamped / `s` prerelease+datestamped) |
| `awoe` | memorabilia | 81 | 2023-09-08 | Art Series |
| `twoe` | token | 18 | 2023-09-08 | tokens |
| `twoc` | token | 10 | 2023-09-08 | Commander tokens |
| `wwoe` | token | 6 | 2023-09-08 | WOE Japanese Promo Tokens |
| `ywoe` | alchemy | 31 | 2023-09-08 | Alchemy: Wilds of Eldraine (digital-only) |

`mm set master-list woe` / `set:woe+related` resolve the whole family from the
parent (no `--only` needed). 554 prints in the family total; the default-scoped
value-bearing sets are `woe` (expansion) + `woc` (commander) + `wot` (bonus sheet).

---

## 2. Treatments

The family's treatment story is almost entirely **`boosterfun`** (structural
showcase/borderless — the preferred collectible print) plus the **`confettifoil`**
premium-foil dupe tier on the Enchanting Tales sheet.

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b` / `shw` / `ext` (frame-dependent) | n/a (structural) | showcase/borderless frames on `woe`/`woc`; KEPT — the preferred collectible print |
| `confettifoil` (+`boosterfun`, on `wot`) | `b\|ff` | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | **wot 84-103** — 20 foil-only premium versions of the Enchanting Tales borderless art at **wot 64-83**. Each shares its `illustration_id` with its 64-83 sibling (Greater Auramancy 84↔64 `d0e5aea0`, Smothering Tithe 87↔67 `20da3bd5`, Rhystic Study 91↔71 `450c8b78`) — same art, confetti-foil sheet. Foil-only, huge premiums ($1,633 Smothering Tithe, $1,423 Rhystic Study, $416 Necropotence). Computes to `ff`, so the DUPE_FOIL gate catches it: drops the confettifoil, keeps the 64-83 borderless. Total ~$5,495 |
| `promopack`+`stamped` (on `pwoe`) | `''` (regular) | dupe (stamp) — but auto-deduped, no rule needed | pwoe `Np` prints — promo-pack stamped copies of base cards. Compute to empty treatment and dedupe against the plain base card in the preferred path; verified NOT to leak into missing-set even with no unobtainable rule (§5) |
| `prerelease`+`datestamped` (on `pwoe`) | `''` (regular) | dupe (stamp) — auto-deduped, no rule needed | pwoe `Ns` prints — prerelease datestamped copies. Same auto-dedup as the `Np` twins; no leak (§5) |
| `thick` (on `woc`) | `''` (regular) | dupe — auto-deduped, no rule needed | woc 57 Ellivere / 58 Tegwyll — oversized commander display cards (foil-only, no price). Dedupe against the boosterfun commander art; no leak |
| `buyabox` | `''` | promo | woe 381 Expel the Interlopers — buy-a-box promo, singleton. KEPT — a distinct promo the user may want |
| `bundle` | `''` | promo | woe 380 Lich-Knights' Conquest — bundle promo, singleton. KEPT |
| `promopack` (on woe 377) | `''` | promo | woe 377 Faerie Dreamthief — promo-pack singleton (~$0.55), plain base sibling at 89. KEPT (cheap, distinct promo) |

**Full-art convention:** standard (borderless/showcase carry `border_color:
borderless` or `frame_effects: showcase`/`inverted`; `full_art` only on basics).

---

## 3. Chase variants

**None** by the `chase` modifier (0 rows across the family, at threshold 3 and 5) —
no card name has ≥3 distinct-art printings at the same `(name, treatment)`. The
variety is base/showcase tiers of the *same* art, plus the Enchanting Tales sheet's
two-batch structure (§7), not multi-art of one card.

---

## 4. Scenes / posters / panoramas

**None.** WOE has no panorama/poster/scene set. The `woe` borderless-inverted
block (297-307: the six planeswalkers + five Restless lands) is entirely
single-artist-per-card (Serena Malyon, Andreas Zafiratos, Zach Alexander, …) —
no artist-run of ≥3 consecutive CNs. Not encoded in `FAMILY_SCENES`.

**Detection recipe** (re-run to confirm):

```
.claude/skills/scryfall-search/scryfall.sh search 'set:woe border:borderless' unique=prints
# Filter to inverted frame, exclude scroll/silverfoil/poster/serialized,
# group by (artist, contiguous-CN-run), keep runs ≥3. → no runs found.
```

---

## 5. Unobtainable rules

**None configured** — `FAMILY_UNOBTAINABLE_RULES["woe"]` is intentionally absent.

The confettifoil scarcity tier (~$5,495, the 20 wot 84-103 premium foils) is
handled by `FAMILY_DUPE_FOIL_PROMO_TYPES` (§2/§8), NOT an unobtainable rule,
because each confettifoil print has a same-art borderless sibling (wot 64-83) that
IS the preferred print — the dupe-foil dedup drops it cleanly. The pwoe
`stamped`/`datestamped` promo twins and the woc `thick` display cards compute to
empty treatment and auto-dedupe against their base cards, so they never leak and
need no rule (verified: 0 leaks with empty rules).

**Missing-set impact (recorded 2026-09-15):** with the `{confettifoil}` DUPE_FOIL
config and no unobtainable rules, `set:woe+related missing treatment=preferred`
resolves to **124 prints / ~$1,458** (down from **144 prints / ~$6,953** with an
empty dupe-foil set). The 20 confettifoil foils (~$5,495) drop out. The remaining
124 are legitimately wanted: 83 `wot` Enchanting Tales borderless reprints (both
the 1-63 showcase-frame batch and the 64-83 inverted-frame batch, all
nonfoil-available) + 41 `woe` main-set showcase/borderless. The top of the list is
the KEPT nonfoil Enchanting Tales chase (Smothering Tithe 67 $202, Rhystic Study 71
$161, 25 $85) — reprints a collector wants, not scarcity junk. `set_status.py`'s
concentration warning fires (the Enchanting Tales tier dominates), but this is a
wanted-chase tier → keep, per the skill's "concentration ≠ exclude" guidance.

---

## 6. PRM destinations

Standard 2023-era promo channels; `pwoe` holds them all (160 prints = 80 cards ×
two stamp variants):

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` (e.g. `102p`) | `pwoe` | Promo Pack (promopack + stamped) | Rankle's Prank 102p |
| `Ns` (e.g. `102s`) | `pwoe` | Prerelease (prerelease + datestamped) | Rankle's Prank 102s |

The `N` mirrors the main-set card. Resolve a presented PRM by name + stamp-type and
read the `pwoe` CN off the match. (`bulk-add` SKILL.md has no woe-specific PRM note
as of this audit.)

---

## 7. Edge cases & gotchas

- **`wot` (Enchanting Tales) two-batch structure.** wot has 103 cards in three
  strata: **1-63** = borderless Enchanting Tales showcase (frame `showcase,inverted`,
  one illustration per card); **64-83** = a *second* borderless art for 20 marquee
  enchantments (frame `inverted` only, a DIFFERENT `illustration_id` from the 1-63
  batch — e.g. Greater Auramancy 4 `87b73cec` vs 64 `d0e5aea0`); **84-103** =
  `confettifoil` premium-foil versions of the 64-83 art (same illustration_id). So a
  marquee enchantment can appear at up to 3 CNs. The chase modifier misses this
  (different treatments/frames, not same-`(name,treatment)` multi-art).
- **`ywoe` (alchemy)** is digital-only (Alchemy: Wilds of Eldraine, 31 cards) —
  globally filtered by the Arena/Alchemy `_is_digital_only` path. Verified no arena
  leak: `set:woe+related missing | grep -i arena` returns nothing.
- **`woc` `thick` display cards** (57 Ellivere, 58 Tegwyll) — oversized foil-only
  commander cards, no market price; auto-deduped, don't leak.
- **`wwoe`** is a 6-card Japanese Promo Tokens set — token, excluded from value scope.
- Three token sets (`twoe` main, `twoc` commander, `wwoe` JP promo) — all excluded
  from the default value scope.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["woe"]` — **configured**: `frozenset({"confettifoil"})` (20 wot 84-103 premium foils dupe their wot 64-83 borderless siblings).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["woe"]` — **not configured** (no rule needed; §5 — stamped/thick auto-dedupe, confettifoil handled by DUPE_FOIL).
- `FAMILY_SCENES["woe"]` — not configured (no narrative scenes; §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Wilds of Eldraine Commander decks | Commander deck | `woc` (173 cards); 2 preconstructed decks |
| Wilds of Eldraine: Enchanting Tales | masterpiece sheet | `wot` (103 cards) — booster-inserted enchantment reprints; 1-63 showcase, 64-83 second borderless art, 84-103 confettifoil dupes (§2/§7) |
| Wilds of Eldraine Art Series | Art Series | `awoe` (81 cards) |
| Buy-a-Box / Bundle promos | Buy-a-Box / Bundle | Expel the Interlopers (`woe` 381, buyabox), Lich-Knights' Conquest (`woe` 380, bundle) |

**Booster types (for `sealed-value` EV).** MTGJSON carries per-card WotC booster
weights for `woe`. Enumerate with `uv run python scripts/sealed_value.py woe --list-boosters`.

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `set` | EV ~$12.34; coverage 86.4% (4 layouts — Set Boosters carry the Enchanting Tales slot) |
| `draft` | EV ~$10.38; coverage 86.1% |
| `collector` | EV ~$36.83; coverage 85.2% (2 layouts — includes the confettifoil Enchanting Tales) |
| `collector-sample` | EV ~$12.05; coverage 93.5% |
| `arena` | EV ~$9.15; coverage 85.1% (digital-only distribution) |
| `prerelease` | EV ~$2.49; coverage 76.4% (points at the pwoe prerelease sheet — lower coverage until pwoe fully synced) |
