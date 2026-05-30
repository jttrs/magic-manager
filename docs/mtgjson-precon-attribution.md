# MTGJSON precon attribution

How to model preconstructed-deck membership for Magic cards. **Documented but not implemented as of V1.7.** The `mtgjson-search` skill (V1.7) ships read-only access to the data; this doc captures the V2 schema and importer design so future work can pick it up.

## The problem

Scryfall's data model has **no signal** indicating which cards in a set came in which preconstructed product:

- `set:fic` returns all 1,241 prints.
- 4 commander decks shipped at FIC release (Counter Blitz, Limit Break, Revival Trance, Scions & Spellcraft) plus 4 collector's-edition variants — together they cover ~800 of those prints.
- Scryfall has no `precon`, `product`, or `deck_membership` field. `set_type: commander` on the FIC sub-set tells us "these are commander cards" but not "these came in deck X."

A user filling out the FIC inventory checklist who already owns Counter Blitz wants `set:fic missing` to subtract the Counter Blitz contents from the missing-cards list. Without precon-membership data, that math is impossible.

## What MTGJSON provides

[mtgjson.com](https://mtgjson.com) publishes a per-deck JSON file for every preconstructed deck WotC has ever shipped — verified back to the early 2000s, ~2,700 decks total as of 2026-05.

### URL structure

- `https://mtgjson.com/api/v5/DeckList.json` — every deck's metadata: `{code, fileName, name, releaseDate, type}`. ~700KB; updated daily.
- `https://mtgjson.com/api/v5/decks/<FILENAME>.json` — one deck file. Each one is ~10KB.
- Sidecar `<resource>.sha256` files for staleness detection (64 bytes each).

### Naming convention

Deck `fileName` is `<DeckCamelCase><SetVariant?>_<SETCODE>` (no `.json`). The FIC family:

```
CounterBlitzFinalFantasyX_FIC
CounterBlitzCollectorSEditionFinalFantasyX_FIC
LimitBreakFinalFantasyVii_FIC
LimitBreakCollectorSEditionFinalFantasyVii_FIC
RevivalTranceFinalFantasyVi_FIC
RevivalTranceCollectorSEditionFinalFantasyVi_FIC
ScionsSpellcraftFinalFantasyXiv_FIC
ScionsSpellcraftCollectorSEditionFinalFantasyXiv_FIC
```

**Pitfall:** the deck name as displayed (`Counter Blitz (FINAL FANTASY X)`) is NOT a sluggable form of the filename. Don't try to derive `fileName` from `name`. Always look up `fileName` via `DeckList.json`.

### Deck file structure

```jsonc
{
  "meta":  { "date": "2026-05-29", "version": "5.3.0+20260529" },
  "data": {
    "code":        "FIC",
    "name":        "Counter Blitz (FINAL FANTASY X)",
    "type":        "Commander Deck",
    "releaseDate": "2025-06-13",
    "commander":   [ <Card(Deck)>, ... ],   // 1 entry for commander decks
    "mainBoard":   [ <Card(Deck)>, ... ],   // 99 for commander decks
    "sideBoard":   [ <Card(Deck)>, ... ],   // often empty
    "tokens":      [ <Card(Token)>, ... ]   // optional
  }
}
```

### Card (Deck) entry — the fields we need

| Field | Notes |
|---|---|
| `name` | Display name (oracle name, not flavor name). |
| `count` | How many copies in the deck. Almost always 1 for commander decks; can be higher in 60-card precons. |
| `isFoil` | Boolean: whether the printed card in the product is foil. |
| `finishes` | List, e.g. `["foil"]` or `["nonfoil"]`. Authoritative when `isFoil` is ambiguous. |
| `setCode` | Cross-check vs. our family resolver. |
| `number` | Collector number for display. |
| `uuid` | MTGJSON's internal UUID. We don't store. |
| **`identifiers.scryfallId`** | **The bridge.** Matches `cards.scryfall_id` exactly. |

## The `identifiers.scryfallId` bridge

This is the load-bearing fact for the entire precon-import workflow.

Every Card (Deck) entry carries `identifiers.scryfallId`, which matches our `cards.scryfall_id` PK byte-for-byte. **No name-matching, no set-code disambiguation, no fuzzy logic** — just look up the row by primary key.

Verified 2026-05-29 against `Counter Blitz (FINAL FANTASY X)`:
- Deck has 100 cards (1 commander + 99 mainBoard).
- 100/100 `identifiers.scryfallId` values resolved cleanly to local `cards` rows after `mm set sync fin`.

The Python helper `magic_manager.mtgjson.deck_card_scryfall_ids(deck_data)` extracts every ID across mainBoard + sideBoard + commander in one call.

## V2 implementation sketch

### Schema

Two new tables (schema v4):

```sql
CREATE TABLE precons (
    precon_code         TEXT PRIMARY KEY,    -- our short code, e.g. 'fic-counter-blitz'
    name                TEXT NOT NULL,        -- 'Counter Blitz (FINAL FANTASY X)'
    set_code            TEXT NOT NULL,        -- 'fic'
    file_name           TEXT NOT NULL,        -- 'CounterBlitzFinalFantasyX_FIC' (MTGJSON's)
    type                TEXT NOT NULL,        -- 'Commander Deck'
    release_date        TEXT,
    commander_scryfall_id  TEXT REFERENCES cards(scryfall_id),
    FOREIGN KEY (set_code) REFERENCES <inferred>
);

CREATE TABLE precon_cards (
    precon_code   TEXT NOT NULL REFERENCES precons(precon_code) ON DELETE CASCADE,
    scryfall_id   TEXT NOT NULL REFERENCES cards(scryfall_id),
    finish        TEXT NOT NULL CHECK (finish IN ('nonfoil','foil')),
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    board         TEXT NOT NULL CHECK (board IN ('main','side','commander','tokens')),
    PRIMARY KEY (precon_code, scryfall_id, finish, board)
);

CREATE INDEX precon_cards_scryfall_idx ON precon_cards (scryfall_id);
```

### Importer

```python
# mm precon import <set_code>
def import_precons(set_code: str) -> int:
    from magic_manager import mtgjson as mj, db
    decklist = mj.deck_list(set_code=set_code)
    n = 0
    with db.connect() as conn:
        for entry in decklist:
            deck = mj.deck(entry['fileName'])
            precon_code = _slug(entry['name'])  # 'counter-blitz-final-fantasy-x'
            commander_ids = mj.deck_card_scryfall_ids(deck, boards=('commander',))
            conn.execute("INSERT OR REPLACE INTO precons VALUES (?, ?, ?, ?, ?, ?, ?)", (
                precon_code, entry['name'], entry['code'].lower(),
                entry['fileName'], entry['type'], entry['releaseDate'],
                commander_ids[0] if commander_ids else None,
            ))
            for board in ('mainBoard', 'sideBoard', 'commander', 'tokens'):
                for card in deck.get(board) or []:
                    sid = (card.get('identifiers') or {}).get('scryfallId')
                    if not sid:
                        continue
                    finish = 'foil' if card.get('isFoil') else 'nonfoil'
                    conn.execute("INSERT OR REPLACE INTO precon_cards VALUES (?, ?, ?, ?, ?)", (
                        precon_code, sid, finish, card.get('count', 1),
                        {'mainBoard': 'main', 'sideBoard': 'side', 'commander': 'commander', 'tokens': 'tokens'}[board],
                    ))
                    n += 1
    return n
```

This runs once per set; idempotent via `INSERT OR REPLACE`. Re-running after MTGJSON publishes a corrected deck file is safe.

### Selector grammar extension

```
precon:fic-counter-blitz                # cards in that one precon
set:fic missing precon:fic-counter-blitz  # FIC cards missing from inventory, EXCLUDING those provided by Counter Blitz
```

Implementation: extend `lists.materialize()` to recognize `precon:` prefix; resolve to the union of `precon_cards.scryfall_id` for the named precon. Compose with existing `set:`, `missing`, etc.

### Master-list integration

`mm set master-list fin` could grow a `--exclude-precon <precon-code>` flag (or several `--exclude-precon` repeats). XLSX rows for cards owned via the named precon would render with `qty_normal` pre-populated to the precon's `count`, so the user only fills in additional copies.

Alternative: keep `mm set master-list` clean; do the math at export-time via the selector grammar. Probably the right call — keeps the checklist generation deterministic and pushes "what do I still need" math into the existing selector flow.

## Refresh strategy

Per the [[mtgjson-search]] skill:
- Per-deck files: cache forever. Decks don't change post-release.
- `DeckList.json`: cache until refreshed. New decks ship with new sets; refresh manually when you sync a new set.
- The importer should call `mj.refresh('DeckList.json')` before re-importing if the user passed a `--refresh` flag.

## Why this is deferred

1. **The skill ships V1.7 read-only access.** That's the unblocker — anyone curious about precon contents can run `mm mtgjson deck <file>` today.
2. **The schema design is straightforward** but adding two new tables + a selector-grammar token wants a real use case driving the design. The user hasn't filled out the FIC checklist yet, so the "subtract precon contents from missing math" feature isn't actually demanded yet.
3. **MTGJSON cross-reference quality is verified.** 100/100 bridge rate on Counter Blitz means future implementation has zero data-cleanup work.

## When to revisit

- User finishes filling out a set with a meaningful precon footprint and wants `missing` math that accounts for owned precons.
- A set ships where precon-vs-booster overlap is significant enough that the user wants to filter the inventory checklist itself.
- The selector grammar gets extended for any other reason — we can fold `precon:` in then.

## Cross-references

- [[mtgjson-search]] — the V1.7 skill that wraps all this.
- [`docs/spg-source-attribution.md`](spg-source-attribution.md) — sister "deferred attribution" pattern for SPG and PMEI.
- [`docs/scryfall-set-families-and-bonus-sheets.md`](scryfall-set-families-and-bonus-sheets.md) — the family-resolver doc that this would compose with.
