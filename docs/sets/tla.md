# `tla` — Avatar: The Last Airbender

> Per-family memory doc. Read this before answering set-specific questions about
> `tla` or working on `tla`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `tla`
**Family root type:** `expansion`
**Family released:** 2025-11-21
**Last audit:** 2026-07-08 via `survey_treatment_signature.py` + session context

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `tla` | expansion | 394 | 2025-11-21 | parent |
| `tle` | eternal | 317 | 2025-11-21 | Avatar: The Last Airbender Eternal — the Jumpstart-analog product for this family |
| `ptla` | promo | 80 | 2025-11-21 | Prerelease datestamped promos (`Ns` CNs) |
| `atla` | memorabilia | 54 | 2025-11-21 | Art Series |
| `atle` | memorabilia | 12 | 2025-11-21 | Eternal Art Series |
| `jtla` | memorabilia | 46 | 2025-11-21 | Jumpstart Front Cards |
| `ftla` | memorabilia | 10 | 2025-11-21 | Beginner Box Front Cards |
| `ttla` | token | 22 | 2025-11-21 |  |
| `ttle` | token | 2 | 2025-11-21 | Eternal tokens |

**Separately-rooted bonus sheets:** none — TLA has no equivalent to SPM's mar-not-a-child-of-spm gotcha. The `sourcematerial` reskin prints (61 total) live inside `tla` itself (CN range 297-350ish, `boosterfun+sourcematerial+universesbeyond` promo_types) rather than a separate `atla` or `xtla`-style set code.

**`mm` invocations:** default `set:tla+related` resolution works correctly.

---

## 2. Treatments

`selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["tla"] = frozenset()` — TLA's audit reveals no surgefoil / doublerainbow / silverfoil *dupe* signals, so the empty set satisfies the `treatment=preferred` config requirement without filtering anything. TLA's fancy-foil signals are all unique-art (neonink 4-card themed chase, raisedfoil singleton) — those are handled by the §5 unobtainable rule, not the dupe-foil filter.

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `neonink` | `ff` | **no — unique art** | 4 prints (TLA 359, 360, 361, 362 — Aang, Zuko, Katara, Toph), all by Flavio Girón. This is a 4-card themed premium chase set with distinct art (different from the base-set versions of these characters). Kept. |
| `raisedfoil` | `ff` | **unknown / singleton** | 1 print: TLA 363 Avatar Aang (Bryan Konietzko), co-occurs with `headliner`. Probably a chase card with unique art; needs visual audit if the user encounters it. |
| `sourcematerial` | `sm` | n/a (part of embedded reskin sheet) | 61 prints inside `tla` itself with `boosterfun+sourcematerial+universesbeyond`. TLA's UB reskin equivalent of FIN's `fca` sheet, but not a separate set code. |
| `prerelease` + `datestamped` | (base treatment) | **yes** → global `preferred` filter drops these | 80 ptla `Ns` prints. Handled by the `preferred`-mode datestamped-sibling filter. |
| `headliner` | (attached to raisedfoil) | n/a | Singleton on TLA 363. |
| `buyabox` | (special promo) | n/a | Singleton, standard buyabox promo. |
| `bundle` | (special promo) | n/a | Singleton, standard bundle promo. |

**Full-art convention:** TLA follows the newer UB convention — borderless-inverted cards have `full_art: true` (like SPM). See `docs/scryfall-printing-treatments.md` §6.5.

---

## 3. Chase variants

Detected by `selectors._modifier_chase` (default threshold 3).

**No uncommon multi-variant chase** in TLA analogous to LTR Nazgûl or FIN Cid. `mm query missing-set tla rarity=uncommon treatment=regular chase` returns zero rows.

The chase filter surfaces:
- **Momo, Friendly Flier** — 3 prints (ptla 29s + tla 29 + tla 394), spans 3 treatments (base, prerelease, buyabox variant). Not a single-treatment chase like Cid.
- **Flavio Girón neonink 4-set** (§2 above) — Aang/Zuko/Katara/Toph at TLA 359-362. Each has a same-name base-set sibling (TLA 4/220/N/N), so `chase` counts these together as a 2-print chase per name, below threshold 3.
- **Basic-land common CNs** (Plains, Mountain, etc.) hit chase threshold naturally since sets always ship multiple basic-land arts. Not a shopping target — sealed product provides these.

---

## 4. Scenes / posters / panoramas

### 4a. Scene Boxes — TLA instances (audited 2026-08-26)

**Scene Box** is a cross-family archetype — product-exclusive scene cards that were
never a playable deck, so they ingest as state **pool** (cards loose, marker deck row);
see [`../product-types.md`](../product-types.md#scene-box) for the definition, MTGJSON
modelling, and handling. TLA ships **two**:

| Scene Box | MTGJSON `fileName` | `tle` CNs | Cards |
|---|---|---|---|
| **The Black Sun Invasion** | `TheBlackSunInvasion_TLA` | 62–67 | Appa, the Vigilant · Katara's Reversal · Fire Nation Turret · Swampbenders · Sokka's Charge · Earthshape |
| **Tea Time at the Jasmine Dragon** | `TeaTimeAtTheJasmineDragon_TLA` | 68–73 | Mai and Zuko · Aang and Katara · Toph, Greatest Earthbender · Sokka and Suki · Momo's Heist · Uncle's Musings |

A contiguous **`tle` 62–73** block: all `rare`, all `boosterfun+universesbeyond`,
all `[foil, nonfoil]`, all `booster: null`. Verified product-exclusive: CN ≤61 and
≥74 flip to Jumpstart-deck membership; **62–73 are the exclusive island**. Import
each as a **pool** — `default_precon_state` auto-classifies both (their "Scene Box"
sealedProduct name), so `mm deck add-precon tla "Black Sun"` / `import-precon
<fileName>` route to pool with no flag.

### 4b. Not yet audited (main-set scenes)

TLA is a large family (394 in parent, 317 in tle) so full scene detection on the *parent* set is still worth running. Apply the LTR scene-detection recipe (`docs/sets/ltr.md` §4a) if a parent-set scene-completion question comes up.

Candidate signal areas:
- **`sourcematerial` reskin prints** (61 in `tla`, around CN 297-350) may include thematic groupings analogous to LTR 399-451.
- **`atla` Art Series** (54 cards) is a memorabilia set — not spatial "scenes" but a themed art collection.

Update this section when a parent-set scene audit runs.

---

## 5. Unobtainable rules

`selectors.FAMILY_UNOBTAINABLE_RULES["tla"]` = `[{"promo_types_any_of": {"neonink", "headliner", "raisedfoil"}}]` (added 2026-07-21).

Excludes the 5 chase-tier premiums the user does not shop for. All foil-only, extreme-rarity Play Booster pulls with **unique art** — so the dupe-foil filter would *keep* them; this rule is what removes them from `mm query missing-set tla`:

| CN | Card | Treatment | ~USD foil |
|---|---|---|---:|
| `tla` 359 | Aang, Swift Savior // Aang and La | neonink | $536 |
| `tla` 360 | Fire Lord Zuko | neonink | $465 |
| `tla` 361 | Katara, the Fearless | neonink | $472 |
| `tla` 362 | Toph, the First Metalbender | neonink | $886 |
| `tla` 363 | Avatar Aang // Aang, Master of Elements (Bryan Konietzko, set headline ultra-rare) | headliner + raisedfoil | $3,908 |

`any_of` because neonink and headliner/raisedfoil never co-occur; matching any one catches exactly these 5 and nothing else in the family (verified 2026-07-21). Effect on missing-set: total drops from ~$7,343 (141 prints) to **~$1,075 (136 prints)** — the realistic completion target.

Globally filtered (not via this rule):
- `serialized` promo_type.
- `rebalanced` / `alchemy` promo_types (TLA has A-prefixed Arena rebalances).

---

## 6. PRM destinations

TLA's PRM-stamped physical promo cards can land in these Scryfall set codes:

| Physical stamp | Scryfall set | Channel | Example |
|---|---|---|---|
| Prerelease datestamped, CN `Ns` | `ptla` | Set prerelease | Aang `ptla` 203s, Aang's Iceberg `ptla` 5s |
| Play Promo, small CN | `pw25` (if within release window) or `pw26` | WPN Play Promo | e.g. pw25 14 Gran-Gran (Mizutametori) |
| Bundle promo | inside `tla` (CN 393 Firebending Student, `buyabox` promo_type) | In-set bundle | Not a `p*` set. |

For any PRM-stamped TLA card, resolve by name+artist per `.claude/skills/bulk-add/SKILL.md`.

---

## 7. Edge cases & gotchas

- **`tle` (Avatar: The Last Airbender Eternal) is `set_type: eternal`, not `set_type: commander`.** Similar to TMT's `tmc`. Contains a Jumpstart-analog product with 317 cards. As of the 2026-08 protocol change, `eternal` is in `DEFAULT_INVENTORY_SET_TYPES` (`sets.py:33`), so `tle` is now pulled into the default `master-list` family — previously it was silently dropped, and its Collector-Booster cards (e.g. foil 118/158/217, ext-art 206, sourcematerial 5) had to be added by hand via `mm inventory add`.
- **`tle` CN boundary at 265 — Jumpstart cards vs Beginner Box.** `tle` has a hard collector-number split: **CN ≤ 264** cards ship `[foil, nonfoil]` and populate the 66 fixed **Jumpstart** half-decks (126 cards across mainBoard/sideBoard); **CN ≥ 265** cards are **nonfoil-only** (191 cards) and are largely **Beginner Box** fixed-deck content, e.g. **Aang Tutorial = tle 265–276 + Plains 297–304**. So a ≥265 nonfoil card is typically obtained via the Beginner Box, not by cracking Jumpstart packs. (Beginner Box archetype + the cross-set-sourcing gotcha: [`../product-types.md`](../product-types.md#beginner-box).)
- **TLA is the reference Beginner-Box cross-set instance.** The Avatar Beginner Box (`sealedProduct` `Avatar The Last Airbender Beginner Box`, `box_set`/`starter_deck`; 10 `Box Set`-type decks in `TLA.json`) is composed of `tle` 265+ printings — resolving its deck `{count, uuid}` entries against only `TLA`'s `cards` yields **20/20 unresolved**; index `TLA`+`TLE`. (The worked example behind the [product-types.md](../product-types.md#beginner-box) gotcha. TLE's own `decks` are all 66 Jumpstart; the Beginner Box is not among them.)
- **Dual "Aang, Air Nomad" printing in `tle`.** Two prints: **TLE 210** (foil-only, ~$1.22) and **TLE 265** (nonfoil-only, ~$0.33). Same art/frame (`legendary`, `universesbeyond`, black border, non-full-art); they differ only in finish + CN. **TLE 265 is card #1 of the Beginner Box "Aang Tutorial" deck** (so it's a guaranteed fixed-deck card, not a pull); TLE 210 is the foil booster version. A third same-name print exists in `pmei` (magazine insert, CN `2025-25`). The `tle` 210-nonfoil / 265-foil counterparts do NOT exist — 210 is foil-only, 265 nonfoil-only.
- **`jtla` "Jumpstart Front Cards"** (46 memorabilia) — a separate memorabilia set for Jumpstart product front cards. Different from the actual Jumpstart cards in tle.
- **`ftla` "Beginner Box Front Cards"** (10 memorabilia) — similar; front cards from the beginner box product.
- **Digital-only Arena prints** — TLA has A-prefixed Alchemy rebalanced variants (globally filtered).
- **Full-art convention flip** — TLA borderless-inverted has `full_art: true` (see §2); this differs from LTR/FIN.
- **Embedded reskin sheet** — 61 `sourcematerial` prints inside `tla` (not a separate set code like FIN's `fca` or SPM's `mar`). Discriminator is the promo_type, not a set code check.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["tla"]` = `frozenset()` (audit shows no dupe-foil signals; empty set unblocks `missing-set` queries).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["tla"]` = `[{"promo_types_any_of": {"neonink", "headliner", "raisedfoil"}}]` — excludes the 5 chase premiums (359-363). See §5.
- `selectors.py:_modifier_chase` — chase variants surface via `mm query missing-set tla`.
- Related docs: [`../scryfall-printing-treatments.md`](../scryfall-printing-treatments.md) §6.5 (full_art convention).
