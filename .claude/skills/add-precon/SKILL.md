---
name: add-precon
description: One-liner wrapper around `mm deck add-precon` — adds preconstructed decks (Commander decks, Box Set decks, Planeswalker decks, etc.) as TRACKED UNITS in one shot, building the deck AND adding its cards to inventory. Precon unit counts derive from the decks table, so the added copies show up under /set-status and prefill the precon checklist's modify flavor. Selection is by set code (+ optional --all / fuzzy name query) or an exact MTGJSON fileName. Triggers: "add each BLC commander deck constructed", "I built the Family Matters precon", "add the Otter Limits starter kit", "add 2 copies of X deconstructed", "I opened another copy of the Y precon".
---

# Add Precon

The mechanical wrapper around `mm deck add-precon`. The user names a precon or a whole set's worth of precons; the CLI resolves the MTGJSON deck(s), then runs the SAME deck+inventory transaction the precon checklist ingest uses — but as a single command, with no XLSX round-trip.

**Relationship to `mm deck import-precon` ([[import-precon]]):** both create deck rows carrying the MTGJSON fileName + adds inventory, and precon unit counts DERIVE from those deck rows (there is no separate ledger — the reconciliation dropped it). So both feed the same single source of truth and both show up under `/set-status`. `add-precon` is the higher-level convenience: it resolves a set code / fuzzy name to the right MTGJSON fileName(s) and takes `--constructed`/`--deconstructed` counts, whereas `import-precon` takes one exact fileName. Use `add-precon` for "I bought/built the X precon" (or a whole set's worth); reach for `import-precon` when you already have the exact fileName and want the lower-level knobs.

## When to use

- "Add each BLC commander deck constructed" / "add all the Family Matters-era commander decks"
- "I built the Family Matters precon" / "I opened another copy of X"
- "Add the Otter Limits starter kit"
- "Add 2 copies of Y deconstructed"

**Don't** use for:
- Many precons across many sets at once, or reviewing current counts before editing → the precon checklist flow ([[ingest-new-inventory-list]] + `mm set precon-list --mode modify`).
- Just want the cards as loose inventory with no deck row at all → [[bulk-add]].
- Removing a copy (sold/miscounted) → `mm deck delete <slug>`; the derived count updates automatically.
- Verifying results afterward → [[set-status]] (the Precons row / overview count is derived from the deck rows).

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

Re-running `add-precon` on the same deck is additive: constructed 1→2, not a reset (it creates another deck row — distinct slug `<slug>-2`). This is correct for "I opened/built another copy." It has no downward/correction form: `--constructed`/`--deconstructed` are ≥ 0. To REMOVE a copy (sold/miscounted), delete its deck row with `mm deck delete <slug>` — the derived count drops automatically.

## Output

The command prints, per deck, a `constructed X→Y, deconstructed X→Y` line plus a headline summarizing rows changed, decks built, decks torn down, and cards added. Relay these to the user. `--json` emits the summary dict: `rows_acted`, `constructed`, `deconstructed`, `inv_qty_total`, `per_row[]` (each with `label`, `file_name`, `count_before`, `count_after`, and optional `warning`/`error`). The counts are derived live from the decks table.

## Guardrails

- **This is a mutation, not a read-only command.** It writes to `decks`, `deck_cards`, and `inventory` in one transaction per deck. Unit counts are derived from those deck rows — there's no separate ledger to keep in sync.
- **Additive by default.** Re-running adds more, it never resets or corrects downward — removal is `mm deck delete <slug>`.
- **Never guess on ambiguous names.** Show the candidate list and ask, or use `--all`.

## Cross-references

- [[import-precon]] — the lower-level sibling (`mm deck import-precon`), takes one exact fileName; same deck+inventory effect, counts derive the same way.
- [[generate-precon-checklist]] / [[ingest-new-inventory-list]] — the precon-checklist flow (`mm set precon-list` + ingest), for reviewing current counts or bulk multi-set adds.
- [[bulk-add]] — for loose cards with no deck concept at all.
- [[set-status]] — verify the Precons count after running this.
