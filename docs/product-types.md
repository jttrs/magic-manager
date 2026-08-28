# MTG product types — cross-family archetype definitions

How a Magic release's physical **products** (SKUs) map to MTGJSON/Scryfall data,
how each is *sourced*, and how the collection *handles* it. This is the
cross-family companion to the per-family memory docs: [`docs/sets/<anchor>.md`](sets/)
records what's true of *one* family; **this file defines the product archetypes
those docs refer to**, so a Scene Box or Beginner Box is explained once here
instead of re-derived in every family doc.

**Read this** when a product-type question comes up ("what does this card come
from?", "is this booster-pullable?", "constructed or deconstructed?"), or when a
per-family doc cross-links here. **Update this** when a session surfaces a new
archetype or a new sourcing/handling rule — then have the family doc reference it.

**See also:**
- [`docs/scryfall-set-families-and-bonus-sheets.md`](scryfall-set-families-and-bonus-sheets.md) — set-*code* / family topology (the sibling-set axis; see below).
- [`docs/sets/_TEMPLATE.md`](sets/_TEMPLATE.md) §9 — where per-family product specifics go.
- `CLAUDE.md` § "Per-set knowledge".

---

## Two axes — don't conflate them

Product classification runs on **two orthogonal axes**. Confusing them is the
single most common mistake here.

| Axis | Question it answers | Authority | Values |
|---|---|---|---|
| **set_type** | Which Scryfall *set codes* in a family are collectable? | `sets.DEFAULT_INVENTORY_SET_TYPES` (`src/magic_manager/sets.py:30-38`) | `expansion`, `commander`, `masterpiece`, `promo`, `eternal` (tokens + memorabilia off by default) |
| **product-type** | Which physical *SKU* did a card ship in? | `mtgjson.PRECON_MODERN_TYPES` etc. (`src/magic_manager/mtgjson.py:114-157`) — see §3 | MTGJSON `deck.type` / `sealedProduct.category`+`subtype` strings |

**The canonical trap: `set_type: "eternal"` is not a product.** Scryfall applies
`eternal` to three *different* products (per families-doc §3):

| Set code | set_type | Actual product |
|---|---|---|
| `spe` (Spider-Man Eternal) | eternal | **Welcome Deck** |
| `tle` (Avatar Eternal) | eternal | **Jumpstart** |
| `tmc` (TMNT Eternal) | eternal | **Commander Deck** |

You cannot infer the product from `set_type` alone — you must look at the MTGJSON
`deck.type` / composition. This doc is about the **product-type** axis.

---

## §1 Archetype index

| Archetype | MTGJSON signal | Sourcing | Default handling |
|---|---|---|---|
| **Commander Deck** | `deck.type = "Commander Deck"` | Fixed 100-card constructed deck (sealed product) | `import-precon` **constructed** (deck row + inventory) |
| **Box Set** | `deck.type = "Box Set"` | Umbrella `type` covering several distinct SKUs (Beginner Box, Scene Box, curated box sets) — disambiguate by `sealedProduct` + composition | depends on the SKU (see Beginner Box / Scene Box below) |
| **Beginner Box** | `sealedProduct` `… Beginner Box`, category `box_set`/subtype `starter_deck`; N themed `Box Set`-type decks | Fixed multi-deck intro product; **cross-set sourced** (see below) | `import-precon` **constructed** (or `--deconstruct` for loose) |
| **Scene Box** | `Box Set`-type deck of "scene" cards; `sealedProduct` category `box_set` | Fixed set of scene cards; **product-EXCLUSIVE** (`booster: null`, not pack-pullable) | `import-precon --deconstruct` — **always deconstructed** |
| **Jumpstart** | `deck.type = "Jumpstart"` | Modular fixed-list half-deck packs (a set ships 50+ variants) | **Own workflow** — `mm set jumpstart-list`; excluded from precon catalog |
| **Welcome Deck** | `deck.type = "Welcome Deck"` | Fixed intro constructed deck (often all-original designs) | `import-precon` constructed |
| **Duel/Planeswalker/Starter/Challenger/Guild/Brawl/Clash/Game Night/Archenemy/Planechase/Intro/Spellslinger** | matching `deck.type` string | Fixed constructed decks | `import-precon` constructed — all in `PRECON_MODERN_TYPES` (§3) |
| **Art Series** | `set_type: memorabilia`, code `a<anchor>` | Oversized art cards | Excluded from default checklists (memorabilia) |
| **Front cards** (Jumpstart / Beginner Box) | `set_type: memorabilia`, code `f<anchor>`/`j<anchor>` | Product front/divider cards | Excluded from default checklists (memorabilia) |
| **Masterpiece / reskin sheet** | `set_type: masterpiece` + `promo_types` ⊇ `{sourcematerial}` | Premium bonus sheet (may be embedded in parent or a sibling code) | In default checklists (masterpiece set_type) — see families-doc §4a |
| **Bundle / Buy-a-Box** | a **`promo_type`** (`bundle`/`buyabox`), NOT a deck type | In-set promo slot (sits at a main-set CN) | Normal in-set print; TCGplayer export suffixes it (`exports/tcgplayer.py:179-186`) |
| **Secret Lair Drop** | `deck.type = "Secret Lair Drop"` | Direct-sale drop | **Own workflow** — the [[bulk-add]] skill; excluded from precon catalog |
| **Collector's Edition** | deck *name* contains "collector's edition" / "collectors' edition" | Premium variant twin (own scryfall_ids) | **Not tracked** — excluded by `_is_collector_edition` unless `--include-collector` |

---

## §2 Per-archetype detail

### Scene Box
A **fixed-contents SKU** of "scene" cards (paired-character / event cards in the
scene visual style), sold as a standalone display product. **Product-exclusive:**
the cards are `booster: null` and appear in no deck — obtainable ONLY by buying the
box (or the singles), never by cracking packs. MTGJSON models each Scene Box as a
`Box Set`-`type` **deck** filed under the *parent* set, with `sourceSetCodes`
pointing at the eternal child that actually holds the printings.

- **Handling: always deconstructed.** A Scene Box is loose collectible cards, never
  a playable deck — `mm deck import-precon <fileName> --deconstruct` (inventory
  only, no deck row).
- **Terminology caveat:** the *Scene Box* (the display SKU) is distinct from the
  `a<anchor>` **memorabilia set code** that Scryfall sometimes labels similarly,
  and from the borderless-inverted **scene cards** inside the main set (§4 of a
  family doc). Three different things — a family doc should say which it means.
- **Instances:** TLA — `TheBlackSunInvasion_TLA`, `TeaTimeAtTheJasmineDragon_TLA`
  (see [`sets/tla.md`](sets/tla.md) §4a for the CN 62–73 card list). LTR `altc`,
  FIN `afic` are family-specific instances (see those docs).

### Beginner Box
A **fixed multi-deck intro product** — N themed tutorial decks in one box
(e.g. Avatar's 10: Aang Tutorial, Zuko Tutorial, Allies, …).

- **Cross-set sourcing gotcha:** MTGJSON files the Beginner Box's decks under the
  **parent** set (e.g. `TLA.json`, `deck.type = "Box Set"`), but the decks are
  *composed of the eternal-child's printings* (e.g. `tle` cards). So resolving a
  deck's `{count, uuid}` entries against only the parent set's `cards` list yields
  **all-unresolved** — you must index the whole family (parent + child). *A
  fully-unresolved deck means "wrong index," not "empty deck."*
- **Handling:** `import-precon` **constructed** by default (one deck row per tutorial
  deck + inventory); `--deconstruct` adds the cards as loose inventory with no deck
  rows. (A box opened both ways: run once normal, once `--deconstruct`.)
- **Instance:** TLA — see [`sets/tla.md`](sets/tla.md) §7 (the CN-265 boundary +
  the worked "20/20 unresolved" example).

### Jumpstart
Modular **fixed-list half-deck packs** — a set publishes many variants (TLE ships
66; MSH 51). Has its **own workflow** (`mm set jumpstart-list <set>` →
fill `keep_qty`/`deconstructed_qty` → `mm set ingest`), so it is deliberately in
`PRECON_EXCLUDED_TYPES` and never appears in the precon catalog.

### Commander Deck / Welcome Deck / other constructed lines
Standard sealed constructed decks. `import-precon` constructed is the default (deck
recipe + inventory; `--deconstruct` to break down for parts). All the constructed
`deck.type` strings live in `PRECON_MODERN_TYPES` (§3).

### Art Series / Front cards / tokens
`set_type: memorabilia` (art series `a<anchor>`, front cards `f<anchor>`/`j<anchor>`)
or `token`. **Off by default** — not in `DEFAULT_INVENTORY_SET_TYPES`, so the
default checklists exclude them; opt in explicitly per family.

### Masterpiece / reskin sheet
`set_type: masterpiece`, discriminated by `promo_types ⊇ {sourcematerial}` (the
reliable signal — not `flavor_name`). May be a separate sibling code (FIN `fca`,
SPM `mar`) or embedded in the parent (TLA's 61 `sourcematerial` prints). See
families-doc §4a.

### Bundle / Buy-a-Box
**A `promo_type`, not a deck type.** The card sits at a normal main-set collector
number with `promo_types` containing `bundle`/`buyabox`; it's a regular in-set
print for inventory purposes. Only special handling is on export — TCGplayer
appends a `(<SET> Bundle)` product suffix (`exports/tcgplayer.py:179-186`,
`:440-454`).

### Secret Lair Drop / Collector's Edition
Both **excluded** from the precon catalog: Secret Lair via `PRECON_EXCLUDED_TYPES`
(own workflow — [[bulk-add]]); Collector's Edition via `_is_collector_edition`
(name match — a premium variant the collection doesn't track, unless
`--include-collector`).

---

## §3 Code authority + sync

The **exact product-type strings** are owned by code, not this doc — this doc
explains the archetypes, sourcing, and handling; the frozensets decide what string
"counts." Single sources of truth in `src/magic_manager/mtgjson.py`:

- **`PRECON_MODERN_TYPES`** (`:127-145`) — the constructed-precon allow-set (17 types:
  Commander Deck, Box Set, Duel Deck, Planeswalker Deck, Starter Kit/Deck,
  Spellslinger Starter Kit, Welcome Deck, Intro Pack, Challenger Deck, Pioneer
  Challenger Deck, Guild Kit, Brawl Deck, Clash Pack, Game Night Deck, Archenemy
  Deck, Planechase Deck). **See the constant for the authoritative full list** —
  the archetype index (§1) is explanatory, this frozenset is normative.
- **`PRECON_EXCLUDED_TYPES`** (`:114`) — `{Jumpstart, Secret Lair Drop}` (own workflows). `MTGO *` types are filtered separately in `precon_variants` (`:189`).
- **`_is_collector_edition`** (`:148`) — the Collector's Edition name-match exclusion.
- **`sets.DEFAULT_INVENTORY_SET_TYPES`** (`sets.py:30-38`) — the orthogonal set_type axis.

**Keep in sync (bidirectional), mirroring the `docs/sets/*.md` §8 convention:**
- If you add/remove a `type` string in `PRECON_MODERN_TYPES` / `PRECON_EXCLUDED_TYPES`, update §1 here in the same commit.
- If you add an archetype here that corresponds to a constructed precon `type`, ensure its exact string is in `PRECON_MODERN_TYPES` (the "when a product line is reported missing, add its exact MTGJSON `type` string here" note on the constant).

---

## §4 Related docs

- [`docs/scryfall-set-families-and-bonus-sheets.md`](scryfall-set-families-and-bonus-sheets.md) — the set-*code*/family-topology axis, and §3 (the `eternal` catch-all) which is the canonical product-type-vs-set_type illustration.
- [`docs/sets/_TEMPLATE.md`](sets/_TEMPLATE.md) §9 — per-family product specifics slot.
- [`docs/sets/tla.md`](sets/tla.md) — the reference *instances* for Scene Box (§4a) and Beginner Box (§7).
- `CLAUDE.md` § "Per-set knowledge" and § "Inventory checklists" (precon-list/jumpstart-list machinery).
