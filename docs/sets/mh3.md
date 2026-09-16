# `mh3` — Modern Horizons 3

> Per-family memory doc. Read this before answering set-specific questions about
> `mh3` or working on `mh3`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mh3`
**Family root type:** `draft_innovation` (Modern Horizons sets are `draft_innovation`, NOT `expansion`)
**Family released:** `2024-06-14` (Commander/tokens/art same day; `pmh3` promos same day)
**Last audit:** `2026-09-15` via `/characterize-set mh3`.

---

## 1. Family map

8 Scryfall codes, all linked via `parent_set_code` → `mh3` (clean graph — no
separately-rooted bonus sheets; the nearby `acr`/`yotj` records are unrelated
2024 releases). A Modern Horizons draft product + Commander product + the
Modern Horizons 2 retro-timeshift bonus sheet.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mh3` | draft_innovation | 528 | 2024-06-14 | parent — the main set + its own boosterfun/borderless/concept/textured/serialized alt sheets (CN 300+) |
| `m3c` | commander | 398 | 2024-06-14 | Modern Horizons 3 Commander — 4 decks; carries the `ripplefoil` collector sheet + `portrait`/`thick` display commanders |
| `pmh3` | promo | 92 | 2024-06-14 | promos — prerelease (`Ns` prerelease+datestamped) + promo-pack (`Np` promopack+stamped) |
| `h2r` | draft_innovation | 16 | 2024-06-14 | **Modern Horizons 2 Timeshifts** — the retro-frame MH2 reprint bonus sheet seeded into MH3 boosters (all `boosterfun`). Distinct desirable reprints, NOT a scarcity tier |
| `amh3` | memorabilia | 54 | 2024-06-14 | Art Series |
| `tmh3` | token | 43 | 2024-06-14 | tokens |
| `tm3c` | token | 28 | 2024-06-14 | Commander tokens |
| `smh3` | token | 1 | 2024-06-14 | Substitute card |

`mm set master-list mh3` / `set:mh3+related` resolve the whole family from the
parent. 942 prints in the family total; the default value-bearing scope is
`mh3` (draft_innovation) + `m3c` (commander).

**Topology note (the MH3 "retro/special bonus structure"):** the notable bonus
sheet is `h2r` (MH2 Timeshifts), NOT a masterpiece set. There is **no `mps`-style
Modern Horizons masterpiece / retro-frame masterpiece set for MH3** — the retro
`h2r` sheet is `parent_set_code: mh3` (cleanly rooted, no `--only` needed). The
special "retro / special guest" flavor lives inside `mh3` itself as the `concept`
Eldrazi borderless (§3) + the `textured` foils (§2), not as a separate code.

---

## 2. Treatments

The family is heavy on booster-fun structural variety of the *same* art (borderless
/ showcase / etched) rather than multi-art. Two fancy-foil tiers dupe an already-kept
sibling and are dropped; `concept` is unique art and kept.

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b` / `shw` / `ext` (frame-dependent) | n/a (structural) | showcase/borderless/etched frames; KEPT — the collectible-alt prints |
| `ripplefoil` (alone, m3c) | `ff` | **naturally excluded** — it's the ONLY print of the m3c reprint | m3c CN 218+ (273 prints): the Commander-set reprint foil sheet. Each is a *distinct* printing with no plain sibling (e.g. Acidic Slime exists ONLY as m3c 218 ripplefoil, `finishes: [nonfoil, foil]`). Computes to `{ff}` alone → Step 1 of `_filter_treatment_preferred` excludes pure-`{ff}` before the dupe step, so it never enters `preferred` regardless. A DUPE_FOIL entry is a **safe no-op on these** (the sibling drop can't fire without a non-ff twin) |
| `ripplefoil` (+`boosterfun` / +`portrait`+`boosterfun`, m3c) | `b\|ff` | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | m3c CN 45-143: the ripplefoil version of a booster-fun/portrait card that ALSO has a non-ripplefoil twin (same art). E.g. Aether Refinery 54 ripplefoil+boosterfun ↔ 106 plain; Azlask 136 ripplefoil+portrait+boosterfun ↔ 9 portrait. DUPE_FOIL drops the ripplefoil, keeps the plain/portrait/showcase sibling |
| `textured` (+`boosterfun`, mh3 468-472) | `b\|ff` | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | The 5 textured-foil DFC planeswalkers — Ajani 468 ($55.85f), Tamiyo 469 ($71.80f), Sorin 470 ($45.57f), Ral 471 ($87.78f), Grist 472 ($18.62f). Foil-only, borderless-inverted; SAME borderless art as the `bundle`+boosterfun twin (Ral 445 bundle ↔ 471 textured; Tamiyo 443 ↔ 469) but on the textured sheet at 2-3× the price. codes-minus-ff = `{b}` matches the bundle sibling's `{b}` → DUPE_FOIL drops textured, keeps the `bundle` borderless |
| `portrait` (m3c) | `b` | n/a (structural) | m3c display/borderless commanders (CN 9-16); KEPT — the borderless collectible print |
| `thick` (m3c 144-151) | `b\|ff` | scarcity display | The 4 face-commander "thick display" cards (Disa/Omo/Satya/Ulalek) + ripplefoil twins — oversized display cards. Mostly unpriced. Not separately excluded (low signal; harmless) |
| `concept` (mh3 381/382/383) | `b` | **NO — unique art** | The 3 Eldrazi "concept art" borderless — Emrakul 381 ($23.72nf/$66f), Kozilek 382 ($11.33nf/$38f), Ulamog 383 ($45.30nf/$109f). Genuinely distinct art from base (6/10/15) and boosterfun (384/386/389). The family's flagship KEPT chase |
| `serialized`+`concept`+`doublerainbow` (mh3 381z/382z/383z) | `b\|ff` | scarcity → GLOBAL filter | The serialized Eldrazi (`z`-suffix, e.g. Ulamog 383z ~$2,335). `serialized` is in GLOBAL `UNOBTAINABLE_PROMO_TYPES` → filtered before any family rule. §5 lists a documented no-op for parity |
| `bundle` (mh3 442-445 + basic lands 318/319) | `b` / `''` | promo | bundle-exclusive borderless planeswalkers (KEPT — the twin the textured foil dupes to) + bundle basic Forests |
| `buyabox` | `''` | promo | 1 buy-a-box promo, KEPT |

**Full-art convention:** borderless carries `border_color: borderless` + `frame_effects:
inverted`; `full_art` is TRUE on borderless-inverted prints (fetchlands/Ocelot Pride
322/343 have `full_art=1`). Treatment relies on `border_color`/`frame_effects`, not
`full_art`.

---

## 3. Chase variants

The `chase` modifier (default threshold 3) returns **4 rows** — the m3c face
commanders that have ≥3 distinct-treatment printings at the same name:

| Card name | Count | CN range | Rarity | Treatments spanned |
|---|---:|---|---|---|
| Disa the Restless | 7 | m3c 1 / 12 / 20 / 28 / 139 / 144 / 148 | mythic | plain, portrait, showcase-etched, ext, ripplefoil+portrait, thick, ripplefoil+thick |
| Omo, Queen of Vesuva | 7 | m3c 2 / 14 / 22 / 30 / 141 / 145 / 149 | mythic | (same shape as Disa) |
| Satya, Aetherflux Genius | 7 | m3c 3 / 15 / 23 / 31 / 142 / 146 / 150 | mythic | (same shape) |
| Ulalek, Fused Atrocity | 6 | m3c 4 / 16 / 24 / 143 / 147 / 151 | mythic | (same shape; Ulalek 143 ripplefoil+portrait = $36 top) |

These are the 4 named-commander "display" legends; the multi-print count is
frame variety of the SAME art, not multi-art. `chase:5` returns 0. The genuinely
distinct-art chase is the `concept` Eldrazi (§2), which the `chase` modifier does
NOT surface (only one distinct-art borderless each, plus the base/boosterfun art).

---

## 4. Scenes / posters / panoramas

**None.** The borderless-inverted block (mh3 320-379+) has one card per distinct
artist — no run of ≥3 consecutive same-artist cards, no narrative scene or
panorama. Not encoded in `FAMILY_SCENES`. (MH3's borderless treatment is
individual showcase art, unlike LTR/FIN scene panoramas.)

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["mh3"]` in `src/magic_manager/selectors.py`.

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {serialized, doublerainbow}` | The 3 serialized Eldrazi (mh3 381z/382z/383z, up to ~$2,335). **Documented no-op:** `serialized` is already in GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so they're filtered before this rule applies. Kept for parity/discoverability with the TDM/INR headliner families. |

**No `stamped`/`datestamped`/prerelease rule is needed.** Verified 2026-09-15: the
`pmh3` promo-pack (`Np`, promopack+stamped) and prerelease (`Ns`, prerelease+
datestamped) prints do NOT leak into the `collectible-alt`/`preferred` class (0 pmh3
prints in `preferred`) — they compute to `regular` and are handled by the rare/mythic
sub-selectors, or have non-stamped siblings the datestamped step drops. Recheck if
`pmh3` prints ever surface in a `preferred` run.

**No `ripplefoil`-scarcity rule is needed.** The pure-`ripplefoil` m3c reprints are
naturally excluded from `preferred` (they compute to `{ff}` alone; §2). The DUPE_FOIL
entry is what handles the `ripplefoil`+boosterfun/portrait twins.

**Missing-set impact (recorded 2026-09-15):**

| Config | `missing treatment=preferred` |
|---|---|
| `collectible-alt` baseline (pre-config) | **99 prints, $3,537.14** |
| `DUPE_FOIL = {ripplefoil}` only | 96 prints, $1,202.15 |
| `DUPE_FOIL = {ripplefoil, textured}` (**proposed**) | **91 prints, $922.53** |

The ripplefoil+boosterfun/portrait dupes and the 5 textured foils (~$280) drop out;
the serialized Eldrazi (~$2,335) were already global-filtered (that's the bulk of the
$3,537→$922 drop). **Verified the `concept` Eldrazi are KEPT** (Ulamog 383 $45.30,
Emrakul 381 $23.72, Kozilek 382 $11.33) — they are the wanted flagship chase, distinct
art, correctly retained. Top of the remaining list is the KEPT borderless staples
(Ocelot Pride 322 $83, borderless fetchlands ~$28-42, medallions) + the bundle
borderless planeswalkers — no scarcity-tier bloat. `set_status.py`'s concentration ⚠
does not indicate an exclude here (the remaining tier is wanted borderless singles).

---

## 6. PRM destinations

`pmh3` (92 prints) holds all standard promo channels for MH3:

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` (e.g. `15s`) | `pmh3` | Prerelease (prerelease + datestamped) | Ulamog, the Defiler 15s |
| `Np` (e.g. `110p`) | `pmh3` | Promo Pack (promopack + stamped) | Warren Soultrader 110p |

The `N` mirrors the main-set card CN. Resolve a presented PRM by name + stamp-type
and read the `pmh3` CN off the match. Not every card has both variants — the
promo-pack (`Np`) set is a subset (~11 seen); prerelease (`Ns`) is the larger set.

---

## 7. Edge cases & gotchas

- **`h2r` (Modern Horizons 2 Timeshifts, 16 cards)** is a `draft_innovation`
  bonus sheet cleanly rooted at `mh3` (no `--only` needed). All 16 are `boosterfun`
  retro-frame reprints of MH2 staples (Ragavan, Esper Sentinel, Solitude, Fury, …).
  They are DISTINCT desirable reprints (surface in the rare/mythic sub-selectors),
  NOT a scarcity tier — do NOT exclude.
- **Family root is `draft_innovation`, not `expansion`** — like all Modern Horizons
  sets. `set:mh3+related` still resolves the whole graph.
- **`ripplefoil` semantics** (m3c): alone = the reprint's own foil sheet (distinct,
  no plain twin → naturally excluded from `preferred`); with `boosterfun`/`portrait`
  = the ripplefoil twin of a card that also has a non-ripplefoil version (dupe →
  DUPE_FOIL). One promo_type, two roles — the `{ff}`-alone exclusion + DUPE_FOIL
  cover both.
- **Serialized Eldrazi** (mh3 381z/382z/383z) — global-filtered by `serialized`.
- **"Arena" is a false grep hit** — the card *Arena of Glory* (mh3 215/351, pmh3
  215s) is a real paper card, not a digital-only leak. No Arena/Alchemy
  security-stamp leak in the family (`ymh3`-style Alchemy set does not exist here;
  the 4 `rebalanced`/`alchemy` promo_types in the survey are on cards from adjacent
  Alchemy releases, not mh3-family prints).
- **`thick` display commanders** (m3c 144-151) — oversized non-tournament display
  cards, mostly unpriced; not separately excluded (harmless, low value).

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["mh3"]` — **PROPOSED (not yet applied)**: `frozenset({"ripplefoil", "textured"})`. ripplefoil catches the m3c ripplefoil+boosterfun/portrait dupes (pure-ripplefoil reprints are naturally excluded); textured catches the 5 mh3 textured-foil planeswalkers (dupe of their bundle borderless twin).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["mh3"]` — **PROPOSED (not yet applied)**: `[{"promo_types_any_of": frozenset({"serialized", "doublerainbow"})}]` (documented no-op — serialized already global-filtered; parity with TDM).
- `FAMILY_SCENES["mh3"]` — not configured (no narrative scenes; §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Modern Horizons 3 Commander decks | Commander deck | `m3c` (398 cards); 4 decks. Carries the `ripplefoil` collector foil sheet (CN 218+) + `portrait`/`thick` display commanders |
| Modern Horizons 3 Art Series | Art Series | `amh3` (54 cards) |
| Modern Horizons 2 Timeshifts | bonus sheet (retro-frame reprints) | `h2r` (16 cards), seeded into MH3 boosters; all `boosterfun` |
| Bundle | Bundle | mh3 442-445 borderless planeswalkers + 318/319 Forests are bundle-exclusive |

**Booster types (for `sealed-value` EV).** MTGJSON carries per-card WotC booster
weights for `mh3`. Enumerate with `uv run python scripts/sealed_value.py mh3 --list-boosters`.

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `collector` | EV ~$49.28; coverage 94.9% (2 layouts). The high-EV product |
| `collector-sample` | EV ~$9.72; coverage 98.8% |
| `play` | EV ~$11.86; coverage 94.0% (6 layouts) |
| `play-arena` | EV ~$9.65; coverage 94.1% (the code-redemption Play Booster variant) |
| `prerelease` | EV ~$8.40; coverage 96.4% (points at `pmh3` prerelease sheet) |

MH3 has NO `draft` booster type in MTGJSON — it shipped Play Boosters (the
post-2024 replacement for draft/set boosters).
