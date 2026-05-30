---
name: mtgjson-search
description: Read MTGJSON.com data — preconstructed deck contents, per-set files, build metadata. MTGJSON publishes structured JSON for every WotC precon ever shipped, including a `identifiers.scryfallId` cross-reference that bridges back to our local cards table. Use whenever the user asks "what's in this precon?", "which cards from FIC came in Counter Blitz vs Limit Break?", or anything else where Scryfall's data model (which has no precon-membership signal) falls short.
---

# MTGJSON Search

Read-only access to [mtgjson.com](https://mtgjson.com) — a free, MIT-licensed third-party MTG data project that publishes structured JSON for every set, every printing, and (critically) every preconstructed deck WotC has ever shipped.

## When to use

- "What cards are in the Counter Blitz precon?" → `mm mtgjson deck CounterBlitzFinalFantasyX_FIC`
- "List all FIC commander decks" → `mm mtgjson decks --set fic`
- "Which precon has [card]?" → fetch `DeckList.json` + every relevant deck file, search.
- Set-completion math that needs to subtract "owned via precon X" from "still need."
- Any future "is this card a precon-only card or did it have a booster print?" question.

**Don't** use this skill for things Scryfall already covers (per-card pricing, frame data, treatments, search-syntax queries). Use [[scryfall-search]] for those.

## Workflow

1. **Prefer the CLI**: `mm mtgjson <subcommand>`. Six subcommands cover every common case.
2. **Drop to the wrapper** (`mtgjson.sh`) for low-level scripting.
3. **Drop to the Python module** (`magic_manager.mtgjson`) for analysis loops or anything that needs the `identifiers.scryfallId` bridge.

## CLI: `mm mtgjson`

```bash
mm mtgjson meta                                # build date + version
mm mtgjson set fic                             # per-set summary
mm mtgjson decks --set fic                     # list decks for a set
mm mtgjson decks                               # list all decks
mm mtgjson deck CounterBlitzFinalFantasyX_FIC  # one deck (commander, main, side)
mm mtgjson refresh FIC.json                    # delete cached file → next fetch re-downloads
mm mtgjson check-stale FIC.json                # compare cached SHA-256 to published .sha256
```

Useful flags:
- `--json` on every "show" command → emit raw JSON instead of the table/summary.
- `--first N` on `decks` → show at most N rows.
- `--show N` on `deck` → show at most N cards per board (default 10).

## Wrapper: `.claude/skills/mtgjson-search/mtgjson.sh`

Subcommands:
- `meta` — Meta.json (build date + version).
- `set <SETCODE>` — `<SETCODE>.json` (case-insensitive).
- `deck <FILENAME>` — `decks/<FILENAME>.json`. Pass the bare fileName from `DeckList.json` (e.g. `CounterBlitzFinalFantasyX_FIC`); the `.json` suffix is optional.
- `decklist` — `DeckList.json` (every deck's metadata: code, fileName, name, releaseDate, type).
- `setlist` — `SetList.json` (every set's metadata).
- `sha256 <RESOURCE_PATH>` — fetches the published `.sha256` sidecar (always re-fetched, 64 bytes).
- `raw '/api/v5/<path>'` — escape hatch for arbitrary paths.
- `check-stale <RESOURCE_PATH>` — prints `fresh`, `stale`, or `absent`.
- `refresh <RESOURCE_PATH>` — deletes the cached file.

**Always go through the wrapper.** A PreToolUse hook blocks any direct `curl https://mtgjson.com/...` and tells you to use this script instead.

## Python module: `magic_manager.mtgjson`

```python
from magic_manager import mtgjson as mj

mj.meta()                                  # → {'date': '2026-05-29', 'version': '5.3.0+...'}
mj.set_list()                              # → list of every set's metadata
mj.set_file('FIC')                         # → full set object (cards, tokens, decks)
mj.deck_list(set_code='FIC')               # → list of FIC's deck metadata entries
mj.deck('CounterBlitzFinalFantasyX_FIC')   # → full deck object (mainBoard, sideBoard, commander)
mj.is_stale('FIC.json')                    # → True if published .sha256 differs from cached
mj.refresh('FIC.json')                     # → delete cached file
mj.deck_card_scryfall_ids(deck_obj)        # → list of scryfallIds across mainBoard+sideBoard+commander
```

`MtgJsonError` is raised on wrapper failure or non-JSON responses.

## Caching model — read this once, internalize it

The wrapper caches every fetched resource at `${TMPDIR}/mtgjson-cache/<resource_path>` (e.g. `mtgjson-cache/FIC.json`, `mtgjson-cache/decks/CounterBlitzFinalFantasyX_FIC.json`). Cache **never expires automatically**.

Why? Two facts about MTGJSON's data:

1. **Per-deck files are immutable.** Once a precon ships, its decklist is a historical record. Cache forever with confidence.
2. **Per-set files change rarely.** They only update when WotC drops post-release printings (e.g. the FIC `chocobotrackfoil` cards a few weeks after FIC's main release). Daily auto-refresh would waste bandwidth on multi-MB files for a near-zero change rate.

To detect staleness when you actually need to: `mm mtgjson check-stale FIC.json` — fetches the 64-byte `.sha256` sidecar and compares to the cached file's actual hash. Cheap, opt-in.

To force a re-fetch: `mm mtgjson refresh FIC.json` then re-run whatever fetch command needs the fresh data.

## The `identifiers.scryfallId` bridge

Every Card (Deck) entry in an MTGJSON deck file carries:

```json
{
  "name": "Yuna, Grand Summoner",
  "setCode": "FIC",
  "number": "8",
  "count": 1,
  "isFoil": true,
  "finishes": ["foil"],
  "uuid": "<MTGJSON's own UUID>",
  "identifiers": {
    "scryfallId": "930da933-4263-40ff-96af-4bd9e797249e"
  }
}
```

The `scryfallId` matches `cards.scryfall_id` in our local DB exactly — verified 100/100 on Counter Blitz against a freshly-synced FIC. So every precon card resolves to a local cards row without name-matching, set-disambiguation, or fuzzy logic.

`mtgjson.deck_card_scryfall_ids(deck_obj)` extracts those IDs across mainBoard + sideBoard + commander; pass `boards=("tokens",)` if you want tokens too.

For the V2 implementation sketch (precons + precon_cards tables, `precon:` selector grammar), see [`docs/mtgjson-precon-attribution.md`](../../../docs/mtgjson-precon-attribution.md).

## Data model snippets we actually use

### Deck file (`decks/<FILENAME>.json`)

```
{
  "data": {
    "code":        "FIC",
    "name":        "Counter Blitz (FINAL FANTASY X)",
    "type":        "Commander Deck",
    "releaseDate": "2025-06-13",
    "commander":   [Card(Deck), ...],   // 1 entry for commander decks
    "mainBoard":   [Card(Deck), ...],   // 99 for commander decks
    "sideBoard":   [Card(Deck), ...],   // often empty
    "tokens":      [Card(Token), ...]   // optional
  }
}
```

### Card (Deck) entry — the fields we read

| Field | Use |
|---|---|
| `name` | Display |
| `count` | How many copies in the deck |
| `isFoil` / `finishes` | Whether this slot is foil/etched/whatever |
| `setCode` | Cross-check vs. our family resolver |
| `number` | Collector number for display |
| `uuid` | MTGJSON's internal ID (we don't store) |
| `identifiers.scryfallId` | **The bridge** to `cards.scryfall_id` |

### DeckList entry

`{code, fileName, name, releaseDate, type}` — five fields. `code` is the parent set's code (uppercase). `fileName` is what you pass to `deck()`.

## Examples

User: *"what cards are in Counter Blitz?"*

```bash
uv run mm mtgjson decks --set fic              # find the fileName
uv run mm mtgjson deck CounterBlitzFinalFantasyX_FIC
```

User: *"how many cards from FIC are exclusive to commander precons (no booster print)?"*

That's the kind of cross-reference question this skill enables. Sketch:

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, 'src')
from magic_manager import mtgjson as mj, db

precon_ids = set()
for d in mj.deck_list(set_code='FIC'):
    deck = mj.deck(d['fileName'])
    precon_ids |= set(mj.deck_card_scryfall_ids(deck))

with db.connect() as conn:
    rows = conn.execute(
        "SELECT scryfall_id, name FROM cards WHERE set_code = 'fic'"
    ).fetchall()
    booster_only = [r for r in rows if r['scryfall_id'] not in precon_ids]
    print(f"FIC cards not in any precon: {len(booster_only)}")
PY
```

User: *"is the cached FIC.json still current?"*

```bash
uv run mm mtgjson check-stale FIC.json   # → "fresh" or "stale"
```

If `stale`, run `mm mtgjson refresh FIC.json` then re-fetch.

## Etiquette

- MTGJSON is a static-file CDN serving multi-GB-per-day. Don't hammer it.
- The wrapper enforces a polite 100ms gap between requests and a `User-Agent` header identifying the project.
- Build cadence: 1AM EST nightly, live by 9AM EST. There's no benefit to fetching the same `Meta.json` twice in one minute — the wrapper's cache covers that automatically.
- Per-deck files: cache forever. Per-set files: refresh manually when you have a reason to suspect a change. Don't write loops that re-fetch on every iteration.

## Cross-references

- [[scryfall-search]] — for per-card data, search syntax, treatments. MTGJSON is **not** a Scryfall replacement.
- [`docs/mtgjson-precon-attribution.md`](../../../docs/mtgjson-precon-attribution.md) — V2 implementation sketch for precon-membership tables.
- [`docs/spg-source-attribution.md`](../../../docs/spg-source-attribution.md) — parallel "deferred attribution" pattern for SPG/PMEI.
