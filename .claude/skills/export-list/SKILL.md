---
name: export-list
description: Generate a copy/paste-ready block of cards for an external service (TCGplayer Mass Entry, ManaPool bulk, Moxfield, Archidekt, plain TSV, or Scryfall identifier JSON). Inputs are V2 selectors like `inventory`, `wishlist:edh-staples`, `deck:atraxa-superfriends`, `set:fin missing`, or `set:fca+related missing:foil`. Use whenever the user wants to buy, share, import elsewhere, or analyze a slice of their collection.
---

# Export List

Wraps `mm export` to materialize a card selection and format it for any of six targets. Output is a fenced code block ready to paste, plus a header noting the selector and row count for verification.

## Workflow

1. **Figure out the selector.** Ask if it's not stated. The V2 grammar:
   - **TERMs (one per selector, picks the universe of cards):**
     - `inventory` — every printing I own (qty>0).
     - `wishlist` — every wishlist entry across all categories.
     - `wishlist:<category>` — one wishlist category (e.g. `wishlist:edh-staples`).
     - `deck:<slug>` — every card in a named deck.
     - `set:<code>` — every printing in one set, qty=1 placeholder per finish.
     - `set:<code>+related` — same, but expands to the parent + every sibling/child.
     - `cards:<scryfall query>` — Scryfall query, intersected with the local cards table (only returns cards the user has synced).
     - `scryfall:<scryfall query>` — live Scryfall API query. Upserts each result into the cards table as a side effect.
   - **MODIFIERs (zero or more, AND-composed, order doesn't matter):**
     - `missing` / `missing:nonfoil` / `missing:foil` / `missing:either` — set difference vs the inventory table by `(scryfall_id, finish)`. Invalid on `inventory` and `wishlist` terms.
     - `owned` — set intersection with inventory; replaces placeholder qty with actual owned qty. Invalid on `inventory` and `wishlist` terms.
     - `qty>=N` / `qty<=N` / `qty=N` — filter by quantity.
     - `finish=foil` / `finish=nonfoil` — keep only that finish.
     - `rarity=common|uncommon|rare|mythic|special|bonus` — filter by rarity.
     - `cn>=N` / `cn<=N` — filter by collector-number numeric prefix.
     - `value>=N` / `value<=N` — filter by current Scryfall USD price for the row's finish.
     - `scryfall:<query>` — POST-FILTER, intersect by scryfall_id with a live Scryfall query.
2. **Pick the target.** Ask if not specified. Targets:
   - `tcgplayer` — Mass Entry: `1 Card Name [SETCODE] CN` (e.g. `1 Lightning Bolt [SLD] 84`). Foil is set per-batch via the cart UI toggle, not per-line — for mixed carts, run twice with `finish=nonfoil` and `finish=foil`.
   - `manapool` — emits Moxfield format (ManaPool consumes it directly via their import-from-Moxfield path).
   - `moxfield` — `1 Card Name (SET) CN[ *F*]` (Moxfield's documented import marker for foil; ManaPool also parses it).
   - `archidekt` — `1x Card Name (set) cn`.
   - `plain` (or `plain-text`) — TSV with prices.
   - `scryfall-json` — `{"identifiers":[...]}` for round-tripping back through `scryfall.sh collection`.
3. **Run `mm export <target> '<selector>'`.** Output goes to stdout by default; pass `--out path.txt` to save to a file (useful for very long lists). Quote the selector — modifiers are space-separated and the shell will split otherwise.
4. **Show the user the block, the row count, the URL of the target service, and the paste instructions.** For TCGplayer, also nudge them to verify the first paste.

## Common patterns

```bash
# Everything I own, plain TSV
uv run mm export plain 'inventory'

# Cards I'm missing from FCA, formatted for Moxfield (paste into a new deck for browsing)
uv run mm export moxfield 'set:fca missing'

# Same for TCGplayer Mass Entry
uv run mm export tcgplayer 'set:fin+related missing'

# Same for ManaPool's cart-optimizer (Moxfield-format under the hood)
uv run mm export manapool 'set:fin+related missing'

# My EDH staples wishlist as a Moxfield block
uv run mm export moxfield 'wishlist:edh-staples'

# My Atraxa decklist (whether owned or not)
uv run mm export moxfield 'deck:atraxa-superfriends'

# The buy-list for that deck — cards in the deck I don't own
uv run mm export plain 'deck:atraxa-superfriends missing'

# FCA mythics I'm missing under $20
uv run mm export tcgplayer 'set:fca missing rarity=mythic value<=20'

# Every borderless variant in FF I don't have, as a JSON identifier list
uv run mm export scryfall-json 'set:fin+related missing'

# Anything that matches a Scryfall query — useful for one-off browses
uv run mm export tcgplayer 'scryfall:t:dragon c:r f:modern usd<5 order:edhrec'

# Save to a file (long lists)
uv run mm export tcgplayer 'set:fin+related missing' --out /tmp/ff-buy.txt
```

## Where to paste each target

- **TCGplayer**: <https://www.tcgplayer.com/massentry> — paste into the textarea, "Add to Cart".
- **ManaPool**: <https://manapool.com/mass-entry-info> → mass entry form. Their cart optimizer will minimize price across multiple sellers, which is the main reason to export here over TCGplayer.
- **Moxfield**: New Deck → Bulk Edit → paste → Import.
- **Archidekt**: New Deck → "Add Cards" → "Multi-line Add" → paste.

## Examples

User: *"I want to buy everything I'm missing from Final Fantasy, plus the commander cards."*
1. The recommended selector is `set:fin+related missing` — `+related` pulls FIC and the rest of the family into the same materialization, then `missing` subtracts what's in inventory.
2. Recommend ManaPool for a multi-card order — its cart optimizer minimizes price across sellers. `mm export manapool 'set:fin+related missing'`.
3. Print the block. For an upfront price, run `mm query value 'set:fin+related missing'` (the query app exposes selector-driven totals).

User: *"export my Modern wishlist for Moxfield."*
1. `mm wishlist categories` first if you don't know the category name.
2. `mm export moxfield 'wishlist:modern'`.
3. Direct them to Moxfield → New Deck → Bulk Edit.

User: *"give me a Scryfall identifier JSON for the FCA cards I own."*
1. `mm export scryfall-json 'set:fca owned'`.
2. They can pipe it back through `scryfall.sh collection` for full card data — useful for analytics scripts.

## Caveats

- **TCGplayer Mass Entry format**: `<qty> <Card Name> [SETCODE] CN` (e.g. `1 Lightning Bolt [SLD] 84`), per the help.tcgplayer.com "Getting Started With Mass Entry" article. Set code is uppercased, in brackets; collector number follows the bracket. Foil is NOT marked per-line — the cart UI has a foil toggle that applies to the whole pasted batch. For mixed-finish carts, export twice (once each with `finish=nonfoil` and `finish=foil`) and toggle the UI between pastes; the [[missing-from-set]] orchestrator already does this split automatically.
- **`set:<code> missing` requires the set to have been synced and registered.** `set:` reads from the local cards table, so the set's printings must have been pulled via `mm set sync` or `mm set master-list`. If the selector returns 0 rows but the user expects results, run [[generate-set-list]] for that set first.
- **`missing` and `owned` reject `inventory`/`wishlist` terms.** Both are tautologies (the term IS inventory, so subtracting inventory is empty). Use them with `set:`, `cards:`, `scryfall:`, or `deck:`.
- **Foil exports.** `moxfield` (and `manapool`, which aliases moxfield) appends ` *F*` per line — Moxfield's documented import token, which ManaPool's bulk-add parses natively. `archidekt` doesn't carry foil syntax in V1 (their format also supports `*F*` but our exporter doesn't yet — log a TODO if a user asks). `tcgplayer` doesn't differentiate foil in the line either; the user picks foil at the cart stage.
- **Long pastes.** TCGplayer Mass Entry has historically choked on >500-line pastes; if the export is huge, suggest splitting into chunks via `--out` + manual file split.
