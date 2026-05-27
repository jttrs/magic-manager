---
name: import-list
description: Save a pasted decklist or filled-in inventory checklist under a labeled list in the local DB. Use whenever the user has copied a deck/wishlist/cube/etc. block from Moxfield, Archidekt, MTGA, MTGO, deckstats, or any platform that uses the common "<qty> <name> (SET) CN" text format — OR when they've finished filling in the quantity columns of a set inventory checklist (XLSX or markdown) from generate-set-list. Each import targets a label like `wishlist:edh-staples`, `deck:atraxa-superfriends`, or `set:fin`.
---

# Import List

Wraps `mm list import` to take pasted text or a filled-in XLSX and save it under a labeled list. The same skill handles wishlists, deck lists, idea lists, set inventory checklists — they're all just labels on the same `list_rows` table.

## Workflow

1. **Get the paste (or path) and the label.**
   - If the user pasted text in chat, write it to `/tmp/import-<n>.txt` first to avoid quoting issues with apostrophes (`Atraxa, Praetors' Voice`), unicode (`★`), and multi-line content.
   - If they're re-importing an inventory checklist, the label MUST be `set:<code>` — the same one `generate-set-list` seeded.
   - For new free-form lists, suggest a label following these conventions: `wishlist:<name>`, `deck:<name>`, `idea:<name>`, `buy:<name>`. Anything works; the prefix is a tag, not a constraint.
2. **Pick the right command.**
   - **For filled-in inventory checklists in `input/`** (XLSX or `.md` — both produced by [[generate-set-list]]): tell the user to run **`/ingest-new-inventory-list`**. That slash command walks them through every active checklist, asks replace vs additive per file, archives each on success, and uses content hashing to detect duplicates. Don't run `mm set ingest` directly unless the user is explicitly bypassing the slash command.
   - **For everything else** (pasted text, an XLSX from outside `input/`, a wishlist/deck/idea label): use `uv run mm list import <label> <path>` or pipe via stdin: `cat /tmp/x.txt | uv run mm list import <label>`.
   - **Note:** if the user has been entering data via `mm intake` (the scan-loop REPL), there is no file to ingest — the REPL writes directly to the DB. Skip ingest entirely.
3. **Surface warnings and not-founds.** The CLI prints them to stderr — pass them on. The most important one is `name/printing mismatch` — that means the user typed `Atraxa, Praetors' Voice (CMR) 248` but `(CMR) 248` is actually Reclamation Sage. The user has a typo; show them the line and the resolved name.
4. **Show the result.** After import, run `mm list show <label>` and `mm list value <label>` to confirm what landed.

## Behavior differences by label kind

The CLI's behavior depends on the label prefix:

- **`set:<code>` labels** are *seeded* by `generate-set-list` with every printing at qty=0. Importing into a `set:*` label only updates existing rows; pasted cards that aren't in the seeded universe go to a `(not in seeded set list)` warning. **Always sync the set first via [[generate-set-list]] before importing into a `set:*` label.**
- **All other labels** are free-form. New cards get inserted; cards already in the list have their quantity *summed* with the new line. Useful for "add 4 more Lightning Bolts to my wishlist".

## Format auto-detection

- `.xlsx` (or `.xlsm`) → master-list XLSX parser (reads `qty_normal` and `qty_foil` columns).
- Anything else → Moxfield-style text parser, which handles Moxfield, Archidekt, MTGA, MTGO, and deckstats blocks.

## Subcommand cheat sheet

```bash
# Re-import a filled-in inventory checklist
uv run mm list import set:fca input/final-fantasy-through-the-ages-master.xlsx

# Save a Moxfield paste from stdin as a wishlist
cat /tmp/edh-wishlist.txt | uv run mm list import wishlist:edh-staples

# Equivalent with a file path
uv run mm list import wishlist:edh-staples /tmp/edh-wishlist.txt

# Show what landed
uv run mm list show wishlist:edh-staples
uv run mm list value wishlist:edh-staples

# See every saved list
uv run mm list ls
```

## Examples

User pastes a Moxfield block in chat:
```
1 Sol Ring (CMM) 410
1 Arcane Signet (CMM) 411
1 Counterspell
1 Force of Will
```
> "Save this as `wishlist:edh-staples`."

Steps:
1. `printf '%s' "$PASTE" > /tmp/import-1.txt`
2. `uv run mm list import wishlist:edh-staples /tmp/import-1.txt`
3. Tell the user: "4 cards saved under `wishlist:edh-staples`. Total value: $X.XX. To export: `mm export tcgplayer label:wishlist:edh-staples`."

User finishes filling in `input/final-fantasy-through-the-ages-master.xlsx`:
> "I'm done filling in the FCA inventory checklist."

Steps:
1. `uv run mm list import set:fca input/final-fantasy-through-the-ages-master.xlsx`
2. Surface any warnings (typically zero for a clean XLSX round-trip).
3. Report: "Updated N rows in `set:fca`. Current owned value: $Y.YY. Run `mm export moxfield 'set:fca missing'` to see what's still missing."

## Caveats

- The XLSX parser reads ONLY columns `set`, `collector_number`, `qty_normal`, `qty_foil`. The user can add notes columns to the right and they'll be ignored.
- Foil import: a foil-line in a set inventory checklist (qty_foil > 0) lands as `finish='foil'` in the DB. Make sure foil pricing flows through (`mm list value` uses `prices_usd_foil` for those rows).
- A blank or 0 qty in the XLSX deletes the corresponding row. If the user wants to "zero out" a card they no longer have, they edit the cell to 0 (or blank) and re-import.
- Section headers (`SIDEBOARD:`, `COMMANDER:`) in pasted text are parsed and stored on the entry as metadata, but V1 doesn't differentiate sections at the list-level — every imported card lands in the labeled list flat. If the user wants a "sideboard" preserved separately, suggest a separate label like `deck:atraxa-sideboard`.
