# Scryfall printing treatments — keyword space and derivation rules

Reference for the `treatment` column added to inventory intake docs in V1.5. Captures the full audit data, which Scryfall fields are reliable, the user-facing keyword space, and worked examples for every category.

Cross-references:
- [`docs/scryfall-set-families-and-bonus-sheets.md`](scryfall-set-families-and-bonus-sheets.md) — release-family structure (parent/sibling sets, UB-specific patterns).
- [`docs/spg-source-attribution.md`](spg-source-attribution.md) — Special Guests release-window mapping.

---

## 1. The user-facing keyword space (V1.5)

Six codes, `|`-delimited, ordered by visual prominence. Maximum cell width on a worst-case print: `b|shw|ext|sm|ff` = 14 chars. Empty cell = standard printing.

| Code | Source rule | Meaning |
|---|---|---|
| **b** | `'inverted' in frame_effects` | modern overlay/bleed treatment — text/UI rendered on bleeding art (FCA reskins, modern booster-fun premiums, art series). Takes precedence over `fa`. |
| **fa** | `full_art=True` AND `'inverted' not in frame_effects` AND `'showcase' not in frame_effects` | "art-extended" treatment — art panel reaches the card edges, but text box is still standard (FDN starter-collection, Zendikar-style basic lands). |
| **shw** | `'showcase' in frame_effects` | themed UI elements (Mystical Archive scroll frames, BLB storybook, Spider-Man comic title bars). Orthogonal to `b` — both can fire. |
| **ext** | `'extendedart' in frame_effects` | art panel extends past normal text-box edges; standard frame otherwise. |
| **sm** | `'sourcematerial' in promo_types` | UB reskin sheet card (FCA / MAR / PZA) — kept as a primary signal even though it always coincides with `b`, because the conceptual category isn't recoverable from frame fields alone. |
| **ff** | `'etched' in frame_effects` OR `promo_types` has any of: `surgefoil`, `rainbowfoil`, `firstplacefoil`, `raisedfoil`, `doublerainbow`, `confettifoil`, `fracturefoil`, `ripplefoil`, `galaxyfoil`, `oilslick`, `texturedfoil`, `halofoil`, `dazzlefoil`, `dragonscalefoil`, `cosmicfoil`, `silverfoil`, `chocobotrackfoil`, `gilded`, `neonink`, `embossed`, `manafoil`, `textured` | "fancy foil" — any non-standard foil finish. Single keyword collapses ~22 specific finishes since they don't co-occur. |

The pure derivation lives in `src/magic_manager/treatments.py:compute_treatment()`. That function is the single source of truth — XLSX writer, MD writer, intake REPL, and `mm scryfall` all call it.

## 2. Worked examples

| (SET) CN | Card | Cell |
|---|---|---|
| (FIC) 2 | [Cloud, Ex-SOLDIER (FIC) 2](https://scryfall.com/card/fic/2/cloud-ex-soldier) | (empty) |
| (FIC) 168 | [Cloud, Ex-SOLDIER (FIC) 168](https://scryfall.com/card/fic/168/cloud-ex-soldier) | `ext` |
| (FIC) 202 | [Cloud, Ex-SOLDIER (FIC) 202](https://scryfall.com/card/fic/202/cloud-ex-soldier) | `b` |
| (FIC) 210 | [Cloud, Ex-SOLDIER (FIC) 210](https://scryfall.com/card/fic/210/cloud-ex-soldier) | `b\|ff` |
| (FIC) 221 | [Cloud, Ex-SOLDIER (FIC) 221](https://scryfall.com/card/fic/221/cloud-ex-soldier) | `ff` |
| (AFIN) 50 | [Cloud, Ex-SOLDIER (AFIN) 50](https://scryfall.com/card/afin/50/cloud-ex-soldier) | `b` |
| (FCA) 4 | [Counterspell (FCA) 4](https://scryfall.com/card/fca/4/counterspell) | `b\|sm` |
| (FCA) 16 | [Nyxbloom Ancient (FCA) 16](https://scryfall.com/card/fca/16/nyxbloom-ancient) | `b\|sm` |
| (MAR) 7 | [Wedding Ring (MAR) 7](https://scryfall.com/card/mar/7/wedding-ring) | `b\|sm` |
| (MAR) 22 | [Skithiryx, the Blight Dragon (MAR) 22](https://scryfall.com/card/mar/22/skithiryx-the-blight-dragon) | `b\|sm` |
| (FIN) 306 | [Forest (FIN) 306](https://scryfall.com/card/fin/306/forest) | `fa` |
| (FDN) 357 | [Ajani, Caller of the Pride (FDN) 357](https://scryfall.com/card/fdn/357/ajani-caller-of-the-pride) | `fa` |
| (FDN) 718 | [Gigantosaurus (FDN) 718](https://scryfall.com/card/fdn/718/gigantosaurus) | `fa` |
| (STA) 42 | [Lightning Bolt (STA) 42](https://scryfall.com/card/sta/42/lightning-bolt) | `shw` |
| (FIN) 344 | [A Realm Reborn (FIN) 344](https://scryfall.com/card/fin/344/a-realm-reborn) | `b` |
| (FIN) 374 | [Aerith Gainsborough (FIN) 374](https://scryfall.com/card/fin/374/aerith-gainsborough) | `b` |
| (SPG) 136 | [Goblin Sharpshooter (SPG) 136](https://scryfall.com/card/spg/136/goblin-sharpshooter) | `b` |
| (SPM) 213 | [Araña, Heart of the Spider (SPM) 213](https://scryfall.com/card/spm/213/ara%C3%B1a-heart-of-the-spider) | `b\|shw` |
| (TMT) 282 | [April O'Neil, Hacktivist (TMT) 282](https://scryfall.com/card/tmt/282/april-oneil-hacktivist) | filtered out (japanshowcase) |
| (TMT) 292 | [April O'Neil, Hacktivist (TMT) 292](https://scryfall.com/card/tmt/292/april-oneil-hacktivist) | filtered out (japanshowcase + white border) |

## 3. Master-list filtering (V1.5)

Default master-list output excludes printings the user explicitly doesn't catalog. Both the XLSX/MD output AND the seeded `set:<anchor>` list rows are filtered, so completion-math (`mm export … 'set:fin missing'`) doesn't count them.

Filters (any one excludes the row):
- `border_color in ('white', 'yellow')`
- `promo_types` contains any of: `prerelease`, `datestamped`, `stamped`, `promopack`, `japanshowcase`, `serialized`

`mm set master-list <name> --include-variants` opts back in.

## 4. Audit data — what's reliable, what isn't

### `frame_effects` — full inventory (~6,200 prints sampled across UB + non-UB sets)

| Value | Approx count | User-facing? | Rationale |
|---|---|---|---|
| `legendary` | 1578 | no | type indicator, not a treatment |
| `inverted` | 792 | yes (`b`) | modern overlay/bleed style |
| `extendedart` | 562 | yes (`ext`) | stretched art panel |
| `enchantment` | 430 | no | type indicator |
| `showcase` | 425 | yes (`shw`) | themed UI elements |
| `lesson` | 95 | no | mechanic |
| `fullart` | 14 | no | redundant with top-level `full_art=True` |
| `etched` | 31 | yes (rolled into `ff`) | etched-foil finish |
| `tombstone`, `companion`, `colorshifted`, `miracle`, `snow`, `*dfc`, `devoid`, `spree` | 1–28 each | no | mechanic / oracle-level, not printing-treatment |

### `promo_types` — full inventory (~80 distinct values)

User-facing:
- `sourcematerial` → `sm`
- ~22 fancy-foil tags → `ff` (full list in §1)

Filtered out (master-list exclusion):
- `prerelease`, `datestamped`, `stamped`, `promopack`, `japanshowcase`, `serialized`

Dropped (informational, not treatment-defining):
- `universesbeyond` — every UB card has it, useless as discriminator
- `boosterfun` — modern marketing umbrella, subsumed by visual flags (only ~3% of boosterfun cards have no other visual signal)
- Per-game tags: `ffvii`, `ffxiv`, `ffix`, `godzillaseries`, etc. — metadata, not visual difference
- Product-source: `boxtopper`, `bundle`, `buyabox`, `gameday`, `themepack`, `starterdeck`, `brawldeck`, `setextension`, `sldbonus`, `vault`, `dossier`, `playpromo`, `wizardsplaynetwork`, `tourney`, `playtest`, `concept`, `headliner`, `storechampionship`, `planeswalkerdeck`, `portrait`, `startercollection`
- Digital-only: `rebalanced`, `alchemy`

### `border_color` — values and semantics

- `black` (most common) — standard
- `borderless` — no white margin (often coincides with `inverted` or `showcase`)
- `white` — used inconsistently. Some cards genuinely have a white-bordered look (older Magic 30th promos), but Scryfall ALSO tags `japanshowcase` fracturefoil prints as `border_color=white` despite having no visible white border (e.g. [TMT 292](https://scryfall.com/card/tmt/292/april-oneil-hacktivist)). **Treat `white` as a filter signal, not a visual one.**
- `yellow` — un-set / Mystery Booster yellow border
- `silver` — older un-set fully-nonfunctional cards (5 in our sample)

### `full_art` — known unreliability

Scryfall's `full_art` boolean is **inconsistent across sets**. Our audit found:

- **Older sets (TLA, SPM, TMT, ECL, SOS)** mostly tag modern overlay-style cards as `full_art=True + inverted=True` ("both").
- **Newer sets (FIN, EOE)** flipped convention and tag those same visually-identical cards as `full_art=False + inverted=True` ("inv only").

This drift was confirmed by side-by-side image comparison ([Aerith FIN 374](https://scryfall.com/card/fin/374/aerith-gainsborough) is `full_art=True`, [A Realm Reborn FIN 344](https://scryfall.com/card/fin/344/a-realm-reborn) is `full_art=False`, but they look indistinguishable visually). Our `compute_treatment` uses `inverted` as the canonical signal precisely to be drift-resistant.

`full_art=True` is reliable ONLY when `inverted` is absent — that's the genuine Zendikar-style "art-with-floating-text" treatment. FDN starter-collection cards are the canonical non-basic-land case.

### Interesting outliers

- **MAR has mixed `full_art`** — about 100 of 53 MAR cards are `full_art=True`, others are `full_art=False`. Same reskin sheet, same visual treatment, inconsistent tagging.
- **MAR has both `oval` and `circle` security stamps** — mixed within the set.
- **PZA is uniformly `full_art=True`** — consistent.
- **FCA security stamp is `triangle`** — unique to FCA among the modern reskin sheets.

## 5. Why some signals are kept user-facing despite redundancy

- **`sm` (sourcematerial)** is technically redundant with `b` because every sourcematerial card we audited also has `inverted`. Kept user-facing because the conceptual category ("UB-themed reskin sheet") doesn't recover from the visual flags alone — a user wants to see at-a-glance which printings are part of the FCA/MAR/PZA premium tier.
- **`ext` (extendedart)** is technically redundant with the standard frame (no other visual flag fires when only `extendedart` is present). Kept because the user wants the distinction from a standard reprint.
- **`fa`** is rarely seen on non-basic-lands but matters when it does fire (FDN starter collection). Kept as separate from `b` because the visual style is genuinely different (Zendikar-era convention vs. modern overlay).

## 5b. Scope decisions: things we deliberately don't track

### Scene-box and scene-panorama cards

Some MTG products group cards into "scenes" — either:
- **Scene boxes** (e.g. FIC 460–475, the FFXV / FFX / FFVII / FFVI / FFI scene boxes) where a small set of borderless reskin cards is sold together as a non-booster product, AND
- **Scene panoramas in the main set** (e.g. LTR 174–180, where four common-rarity cards' art tiles into one continuous illustration when laid side-by-side).

**Scryfall does not model scene membership.** Verified May 2026 by inspecting [Chocobo Camp (FIC) 462](https://scryfall.com/card/fic/462/chocobo-camp), [Many Partings (LTR) 176](https://scryfall.com/card/ltr/176/many-partings), and [Many Partings (LTR) 445](https://scryfall.com/card/ltr/445/many-partings):

- No `scene_id`, `scene_name`, `panorama_*`, `subgroup`, or comparable field exists.
- Scene-box FF cards (FIC 460–475) have **byte-for-byte identical** Scryfall fingerprints to the FFI commander-deck reskin cards (FIC 442–445): same `border_color: borderless`, same `frame_effects: ['inverted']` (or `['legendary','inverted']`), same `full_art: True`, same `promo_types: ['ff*', 'universesbeyond']`. The only thing distinguishing them is the **collector number range**, which is product-organizing convention not Scryfall metadata.
- `booster: false` is **not** a scene-box discriminator — it's also `false` for all 4 FIC commander decks, all art-series cards, all bundle promos, etc.
- LTR 176 (the in-set print of Many Partings, which is part of the Grey Havens scene panorama) has `frame_effects: null`, `border_color: black`, `booster: true` — visually indistinguishable from any other common.

**Decision:** We don't try to track scene membership. To track it, we'd need an external mapping table (`scryfall_id → scene_id`) seeded from community/marketing sources. That's a manual data-entry chore with low payoff for set-completion math, and the user explicitly opted out (2026-05-27).

If a future use case requires it, the right shape is:
- Add a `scenes` table: `(scene_id, scene_name, parent_set_code, notes)`.
- Add a `card_scene_membership` table: `(scryfall_id, scene_id, position)`.
- Seed manually from external sources per release.

## 6. Scryfall query tips

When researching new sets or unknown frames, use `mm scryfall '<query>'` from the project root. It's a thin wrapper over our rate-limited Scryfall search; results print as a tight table including the computed treatment string.

```bash
# Show every printing of a card across the FF family
uv run mm scryfall '!"Cloud, Ex-SOLDIER" g:fin' --first 20

# Filter by frame_effects directly
uv run mm scryfall 'set:tmt frame:inverted' --fields set,collector_number,name,treatment --first 10

# Raw JSON when you need the full record
uv run mm scryfall 'set:fca cn:4' --json
```

The `mm scryfall` CLI exists specifically to avoid the shell-quoting trap of writing `python -c "..."` with embedded apostrophes. See `.claude/skills/scryfall-search/SKILL.md` for the full pattern.
