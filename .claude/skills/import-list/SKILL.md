---
name: import-list
description: Save a pasted decklist or filled-in inventory checklist into the local DB. Use whenever the user has copied a deck/wishlist/cube/etc. block from Moxfield, Archidekt, MTGA, MTGO, deckstats, or any platform that uses the common "<qty> <name> (SET) CN" text format — OR when they've finished filling in the quantity columns of a set inventory checklist (XLSX or markdown) from generate-set-list. Each import routes to one of three tables: `inventory` (cards I own), `wishlist_entries` (cards I want, by category), or `deck_cards` (a named deck's contents).
---

# Import List

Wraps the V2 `mm inventory import` / `mm wishlist import` / `mm deck import` commands to take pasted text or a filled-in XLSX and save it into the right fact table. The V1 single-command + label-prefix routing is gone — the user (or this skill) picks the destination table up front.

## Workflow

1. **Get the paste (or path) and decide what the list MEANS.** Three destinations:
   - **"I own these cards"** → `mm inventory import` (no other arguments).
   - **"I want these cards"** → `mm wishlist import <category>`. Category is positional and free-text; pick something the user already uses (`mm wishlist categories`) or invent a slug like `edh-staples` / `cube-targets`.
   - **"This is the contents of a named deck"** → `mm deck import <slug>`. The deck must already exist; create it first with `mm deck create <slug> --name "..." [--format commander]`.
   - For pasted text, write it to `/tmp/import-<n>.txt` first to avoid quoting issues with apostrophes (`Atraxa, Praetors' Voice`), unicode (`★`), and multi-line content. Then pass the path or pipe via stdin.
2. **Pick the right command.**
   - **For filled-in inventory checklists in `checklists/`** (XLSX or `.md` — both produced by [[generate-set-list]]): tell the user to run **`/ingest-new-inventory-list`**. That slash command walks them through every active checklist, asks replace vs additive per file, archives each on success, and uses content hashing to detect duplicates. Don't run `mm set ingest` directly unless the user is explicitly bypassing the slash command.
   - **For pasted text or an XLSX from outside `checklists/`**: pick one of the three V2 import commands. Pipe via stdin (`cat /tmp/x.txt | uv run mm inventory import`) or pass a path positional arg (`uv run mm inventory import /tmp/x.txt`).
   - **Note:** if the user has been entering data via `mm intake` (the scan-loop REPL), there is no file to ingest — the REPL writes directly to inventory. Skip ingest entirely.
3. **Surface warnings and not-founds.** The CLI prints them to stderr — pass them on. The most important one is `name/printing mismatch` — that means the user typed `Atraxa, Praetors' Voice (CMR) 248` but `(CMR) 248` is actually Reclamation Sage. The user has a typo; show them the line and the resolved name.
4. **Show the result.** After import, run the matching `show`/`value` command — `mm inventory show` / `mm inventory value`, `mm wishlist show --category <cat>` / `mm wishlist value --category <cat>`, or `mm deck show <slug>` / `mm deck value <slug>`.

## Behavior differences by destination

- **`mm inventory import`**: insert-or-sum on `(scryfall_id, finish)`. Re-importing the same block doubles quantities. Use `mm inventory remove` or `mm inventory add --replace` to undo.
- **`mm wishlist import <category>`**: insert-or-sum on `(scryfall_id, finish, category)`. Default finish for unmarked lines is `either`; override per-import with `--finish nonfoil|foil|either`. A line with `*F*` always lands as foil regardless of `--finish`.
- **`mm deck import <slug>`**: insert-or-sum on `(deck_id, scryfall_id, board, finish)`. Default board is `main`; override per-import with `--board main|side|commander|companion|maybe`. To split a deck into main + sideboard, run two imports — one per board.
- **Filled-in set inventory checklist (`mm set ingest` via `/ingest-new-inventory-list`)**: writes the qty cells directly to the `inventory` table, honoring the file's partition (set codes + rarity from `_meta`).

## Format auto-detection

- `.xlsx` (or `.xlsm`) → master-list XLSX parser (reads `qty_normal` and `qty_foil` columns).
- `.md` → master-list markdown parser (reads `[N:k F:k]` brackets).
- Anything else → Moxfield-style text parser, which handles Moxfield, Archidekt, MTGA, MTGO, and deckstats blocks.

## Subcommand cheat sheet

```bash
# Save a Moxfield paste from stdin as a wishlist
cat /tmp/edh-wishlist.txt | uv run mm wishlist import edh-staples

# Equivalent with a file path
uv run mm wishlist import edh-staples /tmp/edh-wishlist.txt

# Wishlist a foil-only buy list
uv run mm wishlist import promo-foils /tmp/x.txt --finish foil

# Add a Moxfield deck export to a deck (must create first)
uv run mm deck create atraxa-superfriends --name "Atraxa Superfriends" --format commander
uv run mm deck import atraxa-superfriends /tmp/atraxa-main.txt
uv run mm deck import atraxa-superfriends /tmp/atraxa-side.txt --board side

# Add a Moxfield paste straight to inventory
cat /tmp/just-opened.txt | uv run mm inventory import

# Show what landed
uv run mm inventory show
uv run mm wishlist show --category edh-staples
uv run mm deck show atraxa-superfriends

# Inventory + wishlist totals
uv run mm inventory value
uv run mm wishlist value --category edh-staples
uv run mm deck value atraxa-superfriends
```

## Examples

User pastes a Moxfield block in chat:
```
1 Sol Ring (CMM) 410
1 Arcane Signet (CMM) 411
1 Counterspell
1 Force of Will
```
> "Save this as my edh-staples wishlist."

Steps:
1. `printf '%s' "$PASTE" > /tmp/import-1.txt`
2. `uv run mm wishlist import edh-staples /tmp/import-1.txt`
3. Tell the user: "4 cards saved under wishlist category `edh-staples`. Total value: $X.XX. To export: `mm export tcgplayer 'wishlist:edh-staples'`."

User finishes filling in `checklists/final-fantasy-through-the-ages-checklist.xlsx`:
> "I'm done filling in the FCA inventory checklist."

Steps:
1. Tell them to run `/ingest-new-inventory-list` (the slash command handles archiving + duplicate detection). Direct invocation is `uv run mm set ingest "Final Fantasy: Through the Ages"`.
2. Surface any warnings (typically zero for a clean XLSX round-trip).
3. Report: "Ingested N rows into inventory. Run `mm export moxfield 'set:fca missing'` to see what's still missing."

User says "this is my Atraxa decklist":
1. `uv run mm deck create atraxa-superfriends --name "Atraxa Superfriends" --format commander` (only the first time).
2. `cat /tmp/atraxa.txt | uv run mm deck import atraxa-superfriends`.
3. Show with `mm deck show atraxa-superfriends`. Buy-list comes from `mm export plain 'deck:atraxa-superfriends missing'`.

## Caveats

- The XLSX parser reads ONLY columns `set`, `collector_number`, `qty_normal`, `qty_foil`. The user can add notes columns to the right and they'll be ignored.
- Foil import: a foil-line in a set inventory checklist (qty_foil > 0) lands as `finish='foil'` in the `inventory` table. Foil pricing flows through (`mm inventory value` uses `prices_usd_foil` for those rows).
- A blank or 0 qty in the XLSX deletes the corresponding inventory row inside that file's partition. If the user wants to "zero out" a card they no longer have, they edit the cell to 0 (or blank) and re-ingest in `replace` mode.
- Section headers (`SIDEBOARD:`, `COMMANDER:`) in pasted text are parsed and stored on the entry as metadata, but the importer doesn't auto-route to the matching board. To preserve a sideboard, run `mm deck import <slug> --board side` against a separate paste.
