---
name: export-list
description: Generate a copy/paste-ready block of cards for an external service (TCGplayer Mass Entry, ManaPool bulk, Moxfield, Archidekt, plain TSV, or Scryfall identifier JSON). Inputs are either a saved labeled list (wishlist, set master, deck) OR a selector expression like `set:fin missing` or `set:fca+related missing:both`. Use whenever the user wants to buy, share, import elsewhere, or analyze a slice of their collection.
---

# Export List

Wraps `mm export` to materialize a card selection and format it for any of six targets. Output is a fenced code block ready to paste, plus a header noting the selector and row count for verification.

## Workflow

1. **Figure out the selector.** Ask if it's not stated. The grammar:
   - `label:<label>` — any saved labeled list (e.g. `label:wishlist:edh-staples`, `label:set:fca`).
   - `set:<code>` — every printing in one set, qty=1, nonfoil.
   - `set:<code>+related` — same, but expands to the parent + every sibling/child.
   - `set:<code> missing` — every printing whose nonfoil qty is < 1 in the seeded `set:<code>` list. This is the "what I'm missing from this set" expression and is the bridge to TCGplayer/ManaPool buy lists.
   - `set:<code> missing:foil` — same but foil-only.
   - `set:<code> missing:both` — both finishes missing.
   - `set:<code>+related missing` — combine.
   - `scryfall:<query>` — wrap any Scryfall search query.
2. **Pick the target.** Ask if not specified. Targets:
   - `tcgplayer` — Mass Entry: `1 Card Name [Set Name]`. **First-paste verification required** (see Caveats below).
   - `manapool` — emits Moxfield format (ManaPool consumes it directly via their import-from-Moxfield path).
   - `moxfield` — `1 Card Name (SET) CN[★]`.
   - `archidekt` — `1x Card Name (set) cn`.
   - `plain` (or `plain-text`) — TSV with prices.
   - `scryfall-json` — `{"identifiers":[...]}` for round-tripping back through `scryfall.sh collection`.
3. **Run `mm export <target> '<selector>'`.** Output goes to stdout by default; pass `--out path.txt` to save to a file (useful for very long lists).
4. **Show the user the block, the row count, the URL of the target service, and the paste instructions.** For TCGplayer, also nudge them to verify the first paste.

## Subcommand cheat sheet

```bash
# Cards I'm missing from FF, formatted for TCGplayer Mass Entry
uv run mm export tcgplayer 'set:fin+related missing'

# Same for ManaPool (Moxfield-format under the hood)
uv run mm export manapool 'set:fin+related missing'

# My EDH staples wishlist as a Moxfield block (paste into a new deck on Moxfield)
uv run mm export moxfield 'label:wishlist:edh-staples'

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
1. Confirm the selector: `set:fin+related missing` if they want everything in the family, or `set:fin missing or set:fic missing` if they specifically want just the parent + commander deck (currently unsupported as a single selector — emit two exports and concatenate).
2. Recommend ManaPool for a multi-card order — its cart optimizer minimizes price across sellers. `mm export manapool 'set:fin+related missing'`.
3. Print the block. Tell them how many cards and roughly the total (run `mm list value` against the materialized rows isn't directly supported as a selector value; offer to run a quick `plain` export and sum the line_usd column if they want the price upfront).

User: *"export my Modern wishlist for Moxfield."*
1. `mm list ls` first if you don't know the label.
2. `mm export moxfield 'label:wishlist:modern'`.
3. Direct them to Moxfield → New Deck → Bulk Edit.

User: *"give me a Scryfall identifier JSON for my entire FCA collection."*
1. `mm export scryfall-json 'label:set:fca'`.
2. They can pipe it back through `scryfall.sh collection` for full card data — useful for analytics scripts.

## Caveats

- **TCGplayer first-paste verification.** The Mass Entry tool's exact spec wasn't documented during this skill's development; we ship with `1 Card Name [Set Name]`, the most widely-attested form. On the FIRST paste, take 5 lines and verify they all match. If TCGplayer rejects the format or matches the wrong printing:
  1. Open `src/magic_manager/exports/tcgplayer.py`.
  2. Adjust the line builder (likely candidates: `1x` prefix, set code instead of name, `Foil` keyword).
  3. Re-export and re-paste.
  4. Update this skill once the canonical format is confirmed.
- **`set:<code> missing` requires the set to have been synced first.** If the selector returns 0 rows but the user expects results, run [[generate-set-list]] for that set first (or `mm set master-list <code>` directly).
- **Foil exports.** `moxfield` appends ` ★`. `archidekt` doesn't carry foil syntax in V1 (their format supports `*F*` but our exporter doesn't yet — log a TODO if a user asks). `tcgplayer` doesn't differentiate foil in the line either; the user picks foil at the cart stage.
- **Long pastes.** TCGplayer Mass Entry has historically choked on >500-line pastes; if the export is huge, suggest splitting into chunks via `--out` + manual file split.
