---
name: add-precon
description: One-liner wrapper around `mm deck add-precon` — adds preconstructed decks (Commander decks, Box Set decks, Planeswalker decks, etc.) as TRACKED UNITS in one shot, writing the precon_ledger AND building the deck AND adding its cards to inventory. Unlike `mm deck import-precon`, this makes the precon show up as a tracked unit under /set-status. Selection is by set code (+ optional --all / fuzzy name query) or an exact MTGJSON fileName. Triggers: "add each BLC commander deck constructed", "I built the Family Matters precon", "add the Otter Limits starter kit", "add 2 copies of X deconstructed", "I opened another copy of the Y precon".
---

# Add Precon

The mechanical wrapper around `mm deck add-precon`. The user names a precon or a whole set's worth of precons; the CLI resolves the MTGJSON deck(s), then runs the SAME ledger+deck+inventory transaction the precon checklist ingest uses — but as a single command, with no XLSX round-trip.

**The key distinction from `mm deck import-precon` ([[import-precon]]):** `import-precon` builds a deck + adds inventory but does NOT touch the `precon_ledger` — those decks don't show up as tracked units under `/set-status`. `add-precon` writes the ledger too, so the Precons count/format breakdown in a set-status report reflects what this command adds. If the user wants their precon purchases counted as tracked units (the normal case for "I bought/built a precon"), use this skill, not `import-precon`.

## When to use

- "Add each BLC commander deck constructed" / "add all the Family Matters-era commander decks"
- "I built the Family Matters precon" / "I opened another copy of X"
- "Add the Otter Limits starter kit"
- "Add 2 copies of Y deconstructed"

**Don't** use for:
- Many precons across many sets at once, or signed corrections to existing ledger counts → the precon checklist flow ([[ingest-new-inventory-list]] + `mm set precon-list`).
- Just want the cards as loose inventory with no deck row and no ledger unit → `mm deck import-precon --deconstruct` or [[bulk-add]].
- Verifying results afterward → [[set-status]] (the Precons row / overview count reflects the ledger).

## The command

```
mm deck add-precon <TARGET> [NAME_QUERY]
    [--constructed/-c N]   (default 1)
    [--deconstructed/-d M] (default 0)
    [--all]
    [--type "Commander Deck"]
    [--include-collector]
    [--json]
```

`TARGET` is EITHER an exact MTGJSON fileName (e.g. `FamilyMatters_BLC`) OR a set code (e.g. `blc`). Find fileNames/types via `uv run mm mtgjson decks --set <code>`.

## Selection forms — map the NL request to the right form

| User says | Command form |
|---|---|
| "each BLC commander deck" / "all the ... decks" | set code + `--all` (add `--type` if they name a product type) |
| a specific named deck ("the Family Matters precon") | set code + fuzzy name query |
| an exact fileName the user already has | that fileName, no name query |
| "keep constructed" / "built" | `--constructed` (default is already 1, so often no flag needed) |
| "deconstructed" / "tore down for parts" / "loose" | `--deconstructed` |

Examples:

```bash
uv run mm deck add-precon blc --all                     # every physical precon in BLC (4 Commander decks)
uv run mm deck add-precon blc "Family Matters"           # one, by fuzzy (case-insensitive substring, then difflib) name match
uv run mm deck add-precon FamilyMatters_BLC              # one, by exact fileName
uv run mm deck add-precon blc --all --type "Commander Deck"   # narrow set-code resolution to one product type
```

`--include-collector` opts in Collector's Edition variants (excluded by default).

## Ambiguity is fatal — never guess

A name query that matches 0 or more than 1 deck exits 2 and prints the candidate list on stderr. **Never guess which deck the user meant.** Surface the candidate list verbatim and ask the user to pick, or offer `--all` as the explicit "all of them" opt-in if that's plausibly what they wanted.

## Additive semantics — re-running adds ANOTHER copy

Re-running `add-precon` on the same deck is additive: constructed 1→2, not a reset. This is correct for "I opened/built another copy." It is NOT the tool for signed ledger CORRECTIONS (lowering a count because you miscounted or sold a deck) — that correction stays in the precon-checklist `--mode modify` flow: `mm set precon-list --mode modify` → edit the XLSX → `mm set ingest`. `add-precon`'s `--constructed`/`--deconstructed` values have a minimum of 0; there is no negative/correction form here.

## Output

The command prints, per deck, a `constructed X→Y, deconstructed X→Y` line plus a headline summarizing rows changed, decks built, decks torn down, and cards added. Relay these to the user. `--json` emits the summary dict: `rows_acted`, `constructed`, `deconstructed`, `inv_qty_total`, `per_row[]` (each with `label`, `file_name`, `ledger_before`, `ledger_after`, and optional `warning`/`error`).

## Guardrails

- **This is a mutation, not a read-only command.** It writes to `decks`, `deck_cards`, `inventory`, and `precon_ledger` in one transaction per deck.
- **Additive by default.** Re-running adds more, it never resets or corrects downward.
- **Never guess on ambiguous names.** Show the candidate list and ask, or use `--all`.

## Cross-references

- [[import-precon]] — the ledger-blind sibling (`mm deck import-precon`); use when you want the deck + inventory but NOT a tracked ledger unit.
- [[ingest-new-inventory-list]] — the precon-checklist flow (`mm set precon-list` + ingest), for bulk multi-set adds or signed corrections.
- [[bulk-add]] — for loose cards with no deck concept at all.
- [[set-status]] — verify the Precons count after running this.
