---
name: import-precon
description: Inline workflow for adding the contents of a Magic preconstructed deck (precon) to the local DB. Routes to `mm deck import-precon` which uses MTGJSON's per-deck JSON to populate both inventory AND a named deck row in one shot. Use whenever the user says "I bought N copies of <precon>", "add the contents of <precon>", "I just opened a Commander deck", "import the cards from <precon>". Default behavior keeps the precons assembled (creates named decks); `--deconstruct` is opt-in for "I'm breaking it down for parts."
---

# Import Precon

A precon is a preconstructed deck that ships pre-built. The user buys precons routinely, and the question "what cards am I getting and how do I track them?" answers the same way every time:

- The cards land in **`inventory`** (physical ownership grew).
- The cards ALSO land in a named **`deck`** row, with `deck_cards` rows for each entry, because the cards are physically sleeved together and aren't available for other decks until the user explicitly deconstructs.

This skill walks the assistant through that workflow and produces deterministic, idempotent results.

## When to use

- "I bought 2 copies of Counter Blitz" / "the Cloud precon" / any precon-by-name reference
- "I just opened a Commander deck" / "I have a precon to add"
- "Import the [precon] contents"
- Any phrasing that mentions a precon name + a quantity ("two of", "all four", etc.)

**Don't** use for:
- Cards opened from booster packs ([[bulk-add]] handles ad-hoc CN ranges)
- Custom-built decks ([[import-list]] for pasted Moxfield blocks → `mm deck import` for routing into a deck row)
- Specific singletons or pulls ([[bulk-add]] again)

## Workflow

### 1. Resolve the precon name → MTGJSON `fileName`

The user usually says "the Cloud precon" or "Counter Blitz" — not the MTGJSON internal filename. Map via `mm mtgjson decks --set <CODE>`:

```bash
uv run mm mtgjson decks --set fic
```

For Final Fantasy Commander (FIC), the four regular precons are:

| Common name | Game | MTGJSON fileName |
|---|---|---|
| Counter Blitz / "the Tidus precon" | FFX | `CounterBlitzFinalFantasyX_FIC` |
| Limit Break / "the Cloud precon" | FFVII | `LimitBreakFinalFantasyVii_FIC` |
| Revival Trance / "the Terra precon" | FFVI | `RevivalTranceFinalFantasyVi_FIC` |
| Scions & Spellcraft / "the Y'shtola precon" | FFXIV | `ScionsSpellcraftFinalFantasyXiv_FIC` |

Each has a `<Name>CollectorSEdition<...>_FIC` sibling. **Always confirm the user wants the regular version unless they explicitly say "collector"** — the collector edition has different scryfall_ids (foil-stamped versions) and would inflate inventory if mistakenly imported.

For other sets (Avatar, TMNT when those ship), run `mm mtgjson decks --set <code>` and either confirm the match with the user or report the available filenames.

### 2. Confirm: kept assembled vs deconstructed

Default is **kept assembled** (precons stay sleeved together, cards aren't available for other decks). If the user is opening a precon planning to break it down for parts ("I'm just opening it for the chase rares"), pass `--deconstruct`.

Use `AskUserQuestion` only when the user's intent is genuinely ambiguous. If they say "I bought 4 precons and I'm gonna build commander decks with them," that's clearly kept-assembled. If they say "opened the precon for the foil Cloud," that's deconstructed. When in doubt, ask.

### 3. Run the import

For each distinct precon, **one** `mm deck import-precon` call with `--copies N`:

```bash
uv run mm deck import-precon CounterBlitzFinalFantasyX_FIC --copies 2
uv run mm deck import-precon LimitBreakFinalFantasyVii_FIC --copies 2
uv run mm deck import-precon RevivalTranceFinalFantasyVi_FIC --copies 1
uv run mm deck import-precon ScionsSpellcraftFinalFantasyXiv_FIC --copies 1
```

What this does:

- Creates `N` `decks` rows (slug derived from the precon's MTGJSON name).
- Walks `commander` + `mainBoard` + `sideBoard`, inserts `deck_cards` rows for each Card(Deck) entry × N copies.
- Aggregates by `(scryfall_id, finish)` across boards and copies, then calls `inventory_add` once per aggregated entry. So buying 2 Counter Blitz adds 2 of every shared land/staple, but a card unique to one precon copy increments by 2.

### 4. Slug naming convention

The first copy gets the bare slug; copies 2..N get numeric suffixes:

| File | Copies | Slugs created |
|---|---:|---|
| `CounterBlitzFinalFantasyX_FIC` | 2 | `counter-blitz-final-fantasy-x`, `counter-blitz-final-fantasy-x-2` |
| `RevivalTranceFinalFantasyVi_FIC` | 1 | `revival-trance-final-fantasy-vi` |

The full MTGJSON name is used by default — if the user wants a shorter slug like `counter-blitz`, they pass `--slug`. Slug collisions error out with a clear message; use `--slug` to override or `mm deck delete` first.

### 5. Surface the summary

Each `mm deck import-precon` invocation emits two lines:

```
Imported precon 'Counter Blitz (FINAL FANTASY X)' as 2 deck(s): counter-blitz-final-fantasy-x, counter-blitz-final-fantasy-x-2. Deck rows: 200 added, 0 updated (200 total card-qty).
Inventory: 93 new rows, 7 bumped (200 total card-qty).
```

Relay these to the user verbatim — they tell you (a) the slugs created, (b) deck-write count, (c) inventory delta. After all precons are done, summarize: total decks, total inventory delta, link to `mm deck ls` for the user to verify.

## Flags

| Flag | Effect |
|---|---|
| `--copies N` | Create N independent decks (default 1). |
| `--slug <slug>` | Override the auto-derived slug. With `--copies>1`, the override applies to copy 1; copies 2..N still get numeric suffixes. |
| `--name <name>` | Override the deck's display name (defaults to MTGJSON's `name`). |
| `--add-inventory` / `--no-add-inventory` | Add cards to inventory (default on). Pass `--no-add-inventory` if you're modeling a deck composition without claiming physical ownership. |
| `--deconstruct` | Skip deck creation entirely; only add cards to inventory. Implies the precon is being broken down. Mutually exclusive with `--no-add-inventory` in spirit (no-op together). |

## Verifying after import

```bash
mm deck ls                                      # see all decks created
mm deck show <slug>                             # spot-check a deck's contents
mm inventory value                              # see the new inventory total
mm query show 'inventory available' --first 10  # what's NOT committed to a deck
```

## Caveats

- **Always the regular version, not the collector edition** unless the user explicitly says collector. Collector editions have separate MTGJSON files (`...CollectorSEdition...`) and different scryfall_ids; importing the wrong one is a bug, not a recoverable mistake.
- **FIC precons each ship 2 foil legends per box** — face commander + a second mainboard foil. So a 2× Counter Blitz import yields 4 foils (Tidus + Yuna ×2 each), not 2. This is correct, not a double-count.
- **Card(Deck) entries with no `identifiers.scryfallId`** are skipped with a stderr warning. This is rare and usually means an MTGJSON build glitch; it does not silently corrupt the import.
- **Slug collisions are loud, not silent.** If `counter-blitz-final-fantasy-x` already exists, the import errors out with the existing slug listed. Use `mm deck delete <slug> --yes` to clear, or pass `--slug` to override.
- **Bulk-add semantics for inventory.** `inventory_add` is additive (insert-or-sum), so re-running the same precon import doubles the inventory and creates duplicate decks (different slugs). The slug-collision check protects against the deck side, but there's no "did you already import this?" guardrail on inventory. Recovery: `mm db restore <snapshot>`.
- **Foil/nonfoil follows MTGJSON's `isFoil`.** All FIC precon mainboard/sideboard cards are nonfoil except the foil-stamped legendary creatures. The commander slot is foil-stamped (foil), the secondary face commander is foil, everything else is nonfoil. MTGJSON gets this right; we trust it.

## What changes in inventory vs. decks

After `mm deck import-precon X --copies N` (default flags):

- **Inventory grows** by `sum(count × N for each Card(Deck) entry)`. Cards already in inventory get bumped, not duplicated.
- **N deck rows** are created in `decks`.
- **Per-board deck_cards rows** are inserted for each Card(Deck) entry × N. So a 2× Counter Blitz creates 2 deck_cards rows for Sol Ring (one per deck slug), each at count=1.
- **`inventory available`** drops by exactly the deck commitments. If the user owned Sol Ring at qty=2 before the precon and the precon adds 2 more (via 2× copies), inventory becomes qty=4, deck_cards committed=2, available=2.

## Cross-references

- [[mtgjson-search]] — underlying data source. `mm mtgjson decks --set <CODE>` lists available precons; `mm mtgjson deck <fileName>` inspects one before import.
- [[inventory-query]] — `mm query show 'inventory available'` shows what's free for new decks. `mm deck find <card>` shows which deck contains a specific printing.
- [[bulk-add]] — for cards opened OUTSIDE a precon (booster packs, singles, etc.).
- [[missing-from-set]] — for "what am I missing from <set>?"; honors the printing-level missing convention but does NOT subtract decked cards. If you want the gap report relative to "uncommitted inventory only," that's a different question; ask the user explicitly.
