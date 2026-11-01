---
name: census-reconcile
description: >-
  Census reconciliation — the user physically counts ALL their loose cards for a
  set family into an add-mode master-list checklist; products kept off the sheet
  (built decks, set-aside decks, scene boxes) are named by fileName. The tool
  diffs census + product recipes against OWNED inventory and writes the
  difference (adds and over-count removals), never an overwrite, never below
  copies pledged to built decks. Dry run by default. Triggers: "census", "I
  counted my loose cards", "reconcile my box against the DB", "my checklist is
  all my loose cards", "fix double-counted cards".
---

# census-reconcile

Thin relay over the deterministic `scripts/census_reconcile.py` (engine:
`magic_manager.census`). The script does ALL logic and arithmetic; this skill
gathers inputs and relays its output.

## What it answers

"I counted everything I physically have for this set — make the DB match."
Target = census (the filled sheet) + the recipes of products kept OFF the sheet.
The tool shows what must be added and what is over-counted in inventory, over the
sheet's printings only.

## Workflow

1. **Sheet.** If the user has no sheet yet, generate an add-mode one:
   `uv run mm set master-list <set>`. They fill in EVERY loose card (qty_normal /
   qty_foil) and save it in `checklists/`.
2. **Off-sheet products.** Ask which products are kept OFF the sheet and how many
   copies of each (built decks, set-aside / deconstructed decks, scene boxes).
   Name EVERY such product, built or not: an unnamed built deck contributes only
   what is pledged to it, so a partly pledged built precon must still be named
   (it then counts its full recipe). Resolve fileNames per family code, with a
   higher cap, for each code in the family:
   `uv run mm mtgjson decks --set <code> --first 500`.
   List a fileName once per copy. Products whose cards ARE on the sheet (e.g. a
   loose deck mixed into the count) are NOT passed. Copies pledged to other
   built decks (custom / imported / unnamed precon) are counted off-sheet
   automatically — no flag needed. If the user wants the products tracked as
   decks, register them with `uv run mm deck add-precon …` BEFORE the dry run —
   never after `--apply`.
3. **Dry run** (read-only; re-run it right before `--apply`):
   `uv run python scripts/census_reconcile.py <sheet.xlsx> --product <fileName> [--product <fileName> …]`
   Relay the summary block and the adds / removals tables (the `in decks` and
   `pledged` columns show built-deck copies). Exit 1 means some removal would
   drop below pledged copies — relay those lines; nothing can be written. The
   way out: fix the census, or break the deck down
   (`uv run mm deck decompose <slug>`), then re-run. Exit 2 = bad input (relay
   the message, e.g. `uv run mm set sync <code>` for an unsynced set, or
   "needs an add-mode inventory checklist" → generate a fresh sheet with
   `uv run mm set master-list <set>`). Add `--json` for machine-readable output:
   its `status` is `ok` | `refused` | `applied`, and an applied run also carries
   `applied` (event ids, copy counts) and `snapshot`.
4. **Apply** only on the user's explicit OK: rerun the same command with
   `--apply`. It snapshots the DB first, writes one `import-block` event (adds)
   and one `adhoc` event (removals), and archives the sheet to
   `checklists/processed/<stem>-census-<date>.xlsx` (`--no-archive` to keep it).
   Relay the event ids and the snapshot path. `uv run mm ingest revert <id>`
   undoes either event. A refused `--apply` (exit 1) writes nothing and takes no
   snapshot.
5. **Built decks.** To pledge built decks against the corrected inventory, suggest
   `uv run mm audit deck-inventory` and `uv run mm deck compose <slug>`.

## Cross-references

- `scripts/census_reconcile.py` / `src/magic_manager/census.py` — the engine.
- `decks.precon_recipe_needs` — product recipes; `ingest.revert_event` — undo.
- [[trueup-pools]] — the sibling that attributes loose cards to products.
