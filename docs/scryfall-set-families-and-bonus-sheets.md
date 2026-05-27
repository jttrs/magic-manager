# Scryfall set families, bonus sheets, and Universes Beyond product layouts

How Scryfall models the multiple set codes that ship with a single Magic the Gathering release, with a focus on Universes Beyond (UB) families that bundle a parent expansion with multiple sibling sub-sets — masterpiece reskin sheets, Commander decks, Welcome Decks, Jumpstart, Team-Up, promos, art series, tokens.

This document is the consolidated record of what we've learned by inspecting Scryfall metadata for the FIN (Final Fantasy), SPM (Spider-Man), TLA (Avatar), and TMT (TMNT) releases. It includes the rules we trust, the assumptions we're making, and the pitfalls to watch out for.

---

## 1. The release-family pattern

A modern UB Magic release is not a single set on Scryfall. It's a **parent set plus a fan of sibling sub-sets**, each with its own three-letter code, linked by `parent_set_code`.

For the **modern UB releases we examined (FIN/SPM/TLA/TMT)** the parent is `set_type: "expansion"`. **This is not universal across all UB releases** — older or commander-only UB releases use other set types for the parent:

- LTR (LotR: Tales of Middle-earth): parent `set_type: "draft_innovation"`.
- Doctor Who (`who`), Fallout (`pip`), Warhammer 40,000 Commander (`40k`): parent `set_type: "commander"` (no separate "main expansion" — these were standalone preconstructed-deck releases).
- LTR's family also includes `mltr` (`set_type: "minigame"`), a type the modern releases don't use.

Don't hard-code "parent must be expansion." Walk `parent_set_code` regardless of the parent's type. (See §5b for how our `mm` CLI handles this.)

Siblings can be any of:

| `set_type` | Typical purpose |
|---|---|
| `commander` | Commander preconstructed decks |
| `masterpiece` | Premium reskin reprint sheet (borderless full-art with `flavor_name`) |
| `eternal` | Catch-all bucket — see §3 |
| `promo` | Promo cards (set promos, store promos, etc.) |
| `memorabilia` | Art series, front cards, beginner box inserts |
| `token` | Tokens that come with the set |
| `draft_innovation` | Older parent expansions (LTR) |
| `minigame` | Standalone minigame sets (LTR) |

### Observed families (as of 2026-05)

```
FIN (Final Fantasy)
  fin   expansion       Final Fantasy
  fic   commander       Final Fantasy Commander
  fca   masterpiece     Final Fantasy: Through the Ages
  pfin  promo           Final Fantasy Promos
  rfin  promo           Final Fantasy Regional Promos
  pss5  promo           FIN Standard Showdown
  afin  memorabilia     Final Fantasy Art Series
  tfin  token           Final Fantasy Tokens
  wfin  token           FIN Asia WPN Promo Tokens

SPM (Spider-Man)
  spm   expansion       Marvel's Spider-Man
  spe   eternal         Marvel's Spider-Man Eternal       (Welcome Decks)
  pspm  promo           Marvel's Spider-Man Promos
  aspm  memorabilia     Marvel's Spider-Man Art Series
  tspm  token           Marvel's Spider-Man Tokens
  om1   expansion       Through the Omenpaths            (parent_set_code: spm — IS in the SPM family)

  (Note: `mar` "Marvel Universe" is NOT a child of `spm`. It's its own
   family root with its own children: `lmar` promo and `omb` masterpiece.)

TLA (Avatar: The Last Airbender)
  tla   expansion       Avatar: The Last Airbender
  tle   eternal         Avatar: The Last Airbender Eternal (Jumpstart product)
    ttle  token         Avatar: The Last Airbender Eternal Tokens   (child of tle)
    atle  memorabilia   Avatar: the Last Airbender Eternal Art Series (child of tle)
  ptla  promo           Avatar Promos
  jtla  memorabilia     Jumpstart Front Cards
  ftla  memorabilia     Beginner Box Front Cards
  atla  memorabilia     Art Series
  ttla  token           Tokens

TMT (Teenage Mutant Ninja Turtles)
  tmt   expansion       Teenage Mutant Ninja Turtles
  pza   masterpiece     TMNT Source Material
  tmc   eternal         TMNT Eternal                     (actually the Commander deck — see §3)
  atmt  memorabilia     TMNT Art Series
  ftmc  memorabilia     TMNT Eternal Front Cards
  ttmt  token           TMNT Tokens
  ttmc  token           TMNT Eternal Tokens
```

### How to enumerate a family programmatically

- The `g:` (group) Scryfall search operator pulls every card in the release family.
- The `parent_set_code` field on the *set* object (from `/sets`) lets you walk the tree explicitly.
- Children-of-children exist: e.g. `ttmc` (TMNT Eternal Tokens) is parented to `tmc`, not directly to `tmt`.

---

## 2. Set-code naming heuristics

These are *soft* — informative but never authoritative. Always cross-check with `set_type`.

| Suffix / prefix | Often means | Caveat |
|---|---|---|
| `*c` | Commander deck | `tmc` is `set_type: eternal` despite being a commander deck |
| `*a` | Masterpiece / art-related (`fca`, `pza`) | Inconsistent — `mar` and `tle` break the pattern |
| `t*` | Tokens (`tfin`, `ttla`, `ttmt`) | Reliable in observed cases |
| `p*` | Promos (`pfin`, `pspm`, `ptla`) | Reliable in observed cases |
| `a*` | Art series (`afin`, `aspm`, `atla`, `atmt`) | Reliable in observed cases |
| `f*` | Front cards / beginner box (`ftla`, `jtla`, `ftmc`) | New convention, only seen on recent sets |

**Pitfall:** Don't pattern-match on the set code alone. The `tmc` example is the canonical gotcha: it ends in `c` and contains a Commander deck (Heroes in a Half Shell only appears here), but Scryfall classified it as `set_type: eternal`. Use the suffix as a hint, then verify by inspecting `set_type` and the cards inside.

---

## 3. The `set_type: "eternal"` catch-all

This is the most inconsistently used set type we've seen. Scryfall applies `eternal` to multiple distinct WotC product concepts, and the visual/mechanical treatment varies accordingly.

| Sub-set | Code | Actual product |
|---|---|---|
| Spider-Man Eternal | `spe` | Welcome Decks (all original designs, `reprint: false`) |
| Avatar Eternal | `tle` | Jumpstart (mostly reprints, many reskinned with `flavor_name`) |
| TMNT Eternal | `tmc` | **Commander deck** (new legendary creatures + format staples + reskinned reprints) |

So when you see `set_type: "eternal"`, you cannot tell from that field alone whether the product is a Welcome Deck, Jumpstart pack, or Commander deck. You have to look at:

- The set code suffix (`*c` strongly hints at commander)
- The composition of the cards (lots of new legendaries + format staples = commander)
- Adjacent sibling sub-sets (e.g. a `j*` "Jumpstart Front Cards" sibling implies the parent product is Jumpstart)
- Naming clues in `set_name` (rare; usually just "X Eternal")

**Assumption:** We assume Scryfall will eventually correct these `set_type` classifications, but for now any tooling that relies on `set_type` alone to classify products will misclassify TMC. **Risk:** If we hard-code "TMC = Team-Up" or any other guess, we'll be wrong. We initially guessed TMC was Team-Up before learning Heroes in a Half Shell exists only in TMC, which contradicted that guess.

---

## 4. Identifying bonus-sheet cards

The phrase "bonus sheet" gets used loosely. We've found it actually covers two distinct concepts:

### 4a. Reskin / masterpiece sheets

`set_type: "masterpiece"` plus `promo_types` containing **`"sourcematerial"`**. The `sourcematerial` promo type is **the discriminator** — it's present on every reskin printing across FCA, MAR, and PZA, including the ones that kept their oracle name.

Properties (verified across FCA / MAR / PZA, May 2026):
- `reprint: true` on every card.
- `border_color: "borderless"` consistently across all three sheets.
- `frame: "2015"` with `frame_effects` typically `["inverted"]` (or `["legendary", "inverted"]` / `["enchantment", "inverted"]` for the relevant types).
- `full_art`: **mixed in MAR** — some Marvel Universe cards are `full_art: true`, others are `false`. FCA and PZA are uniformly `full_art: true`.
- `security_stamp`: **mixed in MAR** — values `"oval"` AND `"circle"` both appear. PZA uses `"oval"` only. FCA uses `"triangle"`.
- `booster: false` (separate-product slot, not in main-set boosters).
- `promo_types`: every print includes `"sourcematerial"` and `"universesbeyond"`. FCA and MAR also include `"boosterfun"`; PZA does not. FCA additionally tags the originating Final Fantasy game (`"ffi"` through `"ffvii"`), unique to that set.
- `flavor_name`: **NOT a reliable reskin signal.** Cards that got a themed rename have a populated `flavor_name`; cards that kept their oracle name (because it already fit the theme) do not. Both kinds are still part of the reskin sheet — the discriminator is `sourcematerial` in `promo_types`, not `flavor_name`. About 5–13% of cards in each sheet have a `flavor_name`; the rest don't.

Examples confirmed:
- **FCA #4** — `name: "Counterspell"`, `flavor_name: "Wild Rose Rebellion"`, stamp `triangle`
- **FCA #16** — `name: "Nyxbloom Ancient"`, `flavor_name: "The Cloudsea Djinn"`, stamp `triangle`
- **MAR #7** — `name: "Wedding Ring"`, **no** `flavor_name` (kept original name; theme already fit). `is_reskin` still true.
- **PZA #6** — `name: "Ashcoat of the Shadow Swarm"`, `flavor_name: "Splinter of the Shadows"`
- **PZA #15** — `name: "Conqueror's Flail"`, `flavor_name: "Ronin's Arsenal"`
- **PZA #4** — `name: "Brainstorm"`, no `flavor_name`

**Code rule of thumb:** `is_reskin = "sourcematerial" in promo_types`. The `mm` CLI computes this once at upsert time (`magic_manager.db._card_row`) and stores it on the cards table.

### 4b. Format-specific supplemental sets

`set_type ∈ {"commander", "eternal"}`. Mechanically distinct cards designed for a non-Standard format. Treatment is much more varied:

- May contain originals (`reprint: false`) or reprints, often both
- May or may not have `flavor_name` reskins
- Often `border_color: "black"` rather than borderless
- Different `promo_types`: TMC uses `"surgefoil"`, SPE uses just `"universesbeyond"`, TLE uses `"sourcematerial"` even though it's a Jumpstart product

The cleanest universal signal that a card belongs to a UB supplemental product is **the structural one**: its `set` is a sibling of (or descendant of) a UB parent expansion, and its `set_type` is anything other than `"expansion"`.

---

## 5. Per-card identification rules (cheat sheet)

Given a Scryfall card object, these fields answer specific questions:

| Question | Field(s) to check | Notes |
|---|---|---|
| Is this a reprint? | `reprint: true` | Authoritative oracle-level flag |
| Has it been reskinned with a themed name? | `flavor_name` populated | `name` is still the oracle name |
| Is it part of the premium reskin treatment? | `promo_types` contains `"sourcematerial"` | Sufficient but not necessary — TMC uses `surgefoil` instead |
| Is it borderless? | `border_color: "borderless"` | Or `frame_effects` contains `"borderless"` (older sets) |
| Is it full-art? | `full_art: true` | |
| Does it appear in the parent set's boosters? | `booster: true` | False for separate-product masterpiece sheets and most commander/eternal cards |
| Is it Universes Beyond? | `promo_types` contains `"universesbeyond"` | Present on every UB card we've seen, including main-set ones |
| What product is it from? | `set` + `set_type` + family inspection | `set_type` alone is unreliable for `eternal` (see §3) |

### Useful Scryfall search idioms

```
set:fca                              # all of Final Fantasy: Through the Ages
set:mar has:flavor                   # Marvel masterpiece reskinned reprints
set:mar -has:flavor                  # Marvel masterpiece reprints that kept their oracle name
set:pza                              # all 20 TMNT Source Material cards
set:tmc -is:reprint                  # TMNT Eternal originals (commander legends, etc.)
set:tmc is:reprint                   # TMNT Eternal reprints (commander staples)
g:tmt is:reprint -set:tmt            # all reprints in the TMNT family except the main expansion
g:spm is:reprint -set:spm            # all reprints in the Spider-Man family except the main expansion
```

---

## 5b. How our `mm` CLI handles older UB families

`magic_manager.sets.resolve()` walks `parent_set_code` to build the family tree, regardless of the parent's `set_type`. `filtered_codes()` then keeps only codes whose `set_type` is in the inventory bundle (`expansion`, `commander`, `masterpiece`, `promo`) — **except** the anchor itself, which is always included regardless of its `set_type`.

This means `mm set master-list ltr` works even though `ltr` is `set_type: "draft_innovation"` (not in the default filter): the anchor exemption keeps `ltr` in the family. Same logic for `mm set master-list who` (parent is `set_type: "commander"`).

If you want a non-anchor sibling whose `set_type` is outside the default bundle (tokens, memorabilia, minigame, etc.), pass `--include token,memorabilia` or restrict to specific codes via `--only`.

---

## 6. Assumptions and risks

### Assumption: `promo_types: "sourcematerial"` is stable
We treat the presence of `"sourcematerial"` in `promo_types` as a reliable signal of the masterpiece reskin treatment. **Risk:** This is a Scryfall convention, not a WotC-defined field. If Scryfall renames or splits this tag in a future schema revision, downstream code will silently break. **Mitigation:** Treat the visual-treatment fields (`border_color`, `full_art`, `frame_effects`) as a redundant cross-check.

### Assumption: The `g:` group operator returns the full release family
We use `g:<parent>` to enumerate everything in a family. **Risk:** Scryfall's grouping logic is opaque and can include or exclude edge cases (e.g. it's unclear whether `om1`-style supplemental expansions count as part of the SPM "group"). **Mitigation:** When completeness matters, walk `parent_set_code` from `/sets` directly rather than trusting the search operator.

### Assumption: `set_type` will eventually be normalized
We're assuming that Scryfall's classification of `tmc` as `eternal` (rather than `commander`) is a data-quality issue that may be corrected. **Risk:** If we write code that special-cases `tmc → commander`, that special case will silently rot if Scryfall fixes the upstream data. **Mitigation:** Don't hard-code set codes; instead, derive the "is this a commander deck?" classification from card composition (presence of new legendary creatures, format staples, deck-builder cards like Sol Ring/Arcane Signet).

### Older UB releases use different family shapes (verified)
Our four primary subjects (FIN/SPM/TLA/TMT) follow "expansion parent + siblings." Other UB releases verified May 2026:
- **LTR** (Tales of Middle-earth): parent is `set_type: "draft_innovation"`. Family includes a `minigame` sub-set (`mltr`).
- **Doctor Who, Fallout, Warhammer 40,000 Commander**: parent is `set_type: "commander"`. No "main expansion" — they were standalone preconstructed-deck releases. Family is just the commander deck plus its tokens.
Don't assume "expansion parent." Walk `parent_set_code` from any anchor.

### Fact: `flavor_name` is NOT a reliable reskin signal
We previously assumed `flavor_name` was populated on every reskinned printing. **It isn't.** MAR contains 46 (out of 53) cards that have the full reskin treatment (borderless, full-art for some, `sourcematerial` promo type, themed Marvel art) but kept their oracle name because the original name already fit the theme — Wedding Ring stays "Wedding Ring," Beast Within stays "Beast Within." The discriminator is `promo_types contains "sourcematerial"`, never `flavor_name`. Code that uses `flavor_name` as a reskin discriminator will under-report on MAR.

---

## 7. Pitfalls we've actually hit

These are mistakes we made in this exact investigation that future readers should not repeat.

1. **Conflated `set_type: "eternal"` with "all original designs."** We saw SPE first (where every card is `reprint: false`) and generalized "eternal sets contain originals." Then TLE turned out to be reprint-heavy, and TMC contained both. The lesson: per-card flags (`reprint`, `flavor_name`, `promo_types`) are authoritative; per-set classifications are not.

2. **Assumed `tmc` was Team-Up format based on its `set_type: eternal` and `surgefoil` treatment.** It's actually the TMNT Commander deck. The clue we missed: `Heroes in a Half Shell` is a commander card and lives only in `tmc`. The presence of new legendary creatures + format staples (Arcane Signet, Ash Barrens, Assassin's Trophy) was the structural giveaway.

3. **Assumed every family ships a Commander deck.** Only FIN of {FIN, SPM, TLA, TMT} has a clean `*c`/`commander`-typed sub-set (`fic`). For the others, commander-relevant cards either live in the main expansion or get bundled into a misclassified `eternal` sub-set (TMC).

4. **Read too much into the `*c` set-code suffix.** It's a real signal, but it's overridden by the actual `set_type` field — and conversely, the absence of a `*c` code doesn't mean there's no commander product (it could be hiding in `eternal`).

5. **Treated `promo_types: ["universesbeyond"]` as a bonus-sheet signal.** It's not — every UB card carries it, including main-set originals like SPM proper. The discriminator is `"sourcematerial"`, not `"universesbeyond"`.

6. **Forgot that bonus-sheet sub-sets can themselves have child sub-sets.** `ttmc` (TMNT Eternal Tokens) is parented to `tmc`, not `tmt`. Walking `parent_set_code` only one level deep misses these.

---

## 8. Summary: durable rules

In order of confidence, highest first:

1. **`reprint` and `promo_types` on the card object are authoritative per-card.** Trust them.
2. **`parent_set_code` on the set object is authoritative for family structure.** Trust it. Walk it recursively — bonus-sheet sub-sets can have their own children (`ttmc` is a child of `tmc`, not `tmt`).
3. **`promo_types` containing `"sourcematerial"`** reliably identifies the premium reskin treatment. This is the canonical reskin discriminator.
4. **`flavor_name` is NOT a reskin discriminator.** Cards in a reskin sheet may keep their oracle name; rely on `promo_types`.
5. **`set_type`** is mostly reliable EXCEPT for `"eternal"`, which is a catch-all bucket and may misclassify Commander decks. The parent set's `set_type` also varies (expansion in modern UB, draft_innovation/commander in older ones).
6. **Set-code suffixes** are useful hints but never sole authorities. `*c` correlates weakly (29 commander, 30 token, 12 promo); TMC is the canonical counterexample.
