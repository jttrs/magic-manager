---
name: add-precon
description: One-liner wrapper around `mm deck add-precon` — adds preconstructed decks (Commander decks, Box Set decks, Planeswalker decks, etc.) as TRACKED UNITS in one shot, building the deck AND adding its cards to inventory. Each copy is recorded in one of three states — built / deconstructed / pool (card pools like the Starter Collection or a Scene Box) — auto-detected when no count flag is given. Precon unit counts derive from the decks table, so the added copies show up under /set-status and prefill the precon checklist's modify flavor. Selection is by set code (+ optional --all / fuzzy name query) or an exact MTGJSON fileName. Triggers: "add each BLC commander deck constructed", "I built the Family Matters precon", "add the Foundations Starter Collection", "add a (Foundations) Beginner Box", "I opened a Bundle / sealed box", "add 2 copies of X deconstructed", "I opened another copy of the Y precon". For a sealed box/bundle (Beginner Box, Bundle) — a multi-deck product with no decklist — resolve its component decks from `sealedProduct` first (see the "Sealed boxes" section); never conclude the product doesn't exist from a DeckList scan.
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
    [--constructed/-c N]     built copies (assembled decks)
    [--deconstructed/-d M]   torn-down copies (loose cards, marker row)
    [--pool/-p P]            card-pool copies (Starter Collection / Scene Box)
    [--all]
    [--type "Commander Deck"]
    [--include-collector]
    [--json]
```

`TARGET` is EITHER an exact MTGJSON fileName (e.g. `FamilyMatters_BLC`) OR a set code (e.g. `blc`). Find fileNames/types via `uv run mm mtgjson decks --set <code>`.

**Pass NO count flag and the state auto-detects per deck:** pool-like products (Starter Collection, Scene Box — via `mtgjson.default_precon_state`) default to one `pool` copy, everything else to one `built` copy. The command prints an `ℹ auto-detected a card pool` note when it does. Only pass `-c/-d/-p` to override or to add more than one.

## Selection forms — map the NL request to the right form

| User says | Command form |
|---|---|
| "each BLC commander deck" / "all the ... decks" | set code + `--all` (add `--type` if they name a product type) |
| a specific named deck ("the Family Matters precon") | set code + fuzzy name query |
| an exact fileName the user already has | that fileName, no name query |
| "I built it" / "keep constructed" | `--constructed` (or nothing — a normal deck auto-defaults to built 1) |
| "deconstructed" / "tore down for parts" / "loose" | `--deconstructed` |
| "the Starter Collection" / "a Scene Box" / any card pool | nothing (auto → pool), or explicit `--pool` |
| a **sealed box / bundle** ("a Beginner Box", "the Foundations Beginner Box") | set code + the box name — the CLI expands it to its component decks |

### Sealed boxes (Beginner Box, Bundle, …) — one command

A sealed **box/bundle is NOT a single deck** and usually has **NO decklist**, so it never appears in `mm mtgjson decks`. Its membership lives in the set's `sealedProduct[].contents.deck` (see [[mtgjson-search]]). **`add-precon` resolves this for you** — pass the set code + the box name and it expands to the box's component decks:

```bash
uv run mm deck add-precon fdn "Foundations Beginner Box" -c 1   # → builds its 10 component decks
```

Resolution is **deck-first**: a real deck named X still wins; the box expansion is the fallback when no single deck matches. A matched product with no component decks (a pack-only Bundle) errors clearly. Don't hand-loop fileNames or use `<code> --all` (that sweeps in other products) — just name the box.

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

Re-running `add-precon` on the same deck is additive: built 1→2, not a reset (it creates another deck row — distinct slug `<slug>-2`). This is correct for "I opened/built another copy." It has no downward/correction form: `--constructed`/`--deconstructed`/`--pool` are ≥ 0. To REMOVE a copy (sold/miscounted), delete its deck row with `mm deck delete <slug>` — the derived count drops automatically.

## Output

The command prints, per deck, a `built X→Y, deconstructed X→Y, pool X→Y` line plus a headline summarizing rows changed and totals built / torn down / pooled. Relay these to the user. `--json` emits the summary dict: `rows_acted`, `built`, `deconstructed`, `pool`, `inv_qty_total`, `per_row[]` (each with `label`, `file_name`, `count_before`/`count_after` as 3-tuples `(built, deconstructed, pool)`, and optional `warning`/`error`). Counts are derived live from the decks table.

## Guardrails

- **This is a mutation, not a read-only command.** It writes to `decks`, `deck_cards`, and `inventory` in one transaction per deck. Unit counts are derived from those deck rows — there's no separate ledger to keep in sync.
- **Additive by default.** Re-running adds more, it never resets or corrects downward — removal is `mm deck delete <slug>`.
- **Never guess on ambiguous names.** Show the candidate list and ask, or use `--all`.

## Cross-references

- [[import-precon]] — the lower-level sibling (`mm deck import-precon`), takes one exact fileName; same deck+inventory effect, counts derive the same way.
- [[generate-precon-checklist]] / [[ingest-new-inventory-list]] — the precon-checklist flow (`mm set precon-list` + ingest), for reviewing current counts or bulk multi-set adds.
- [[bulk-add]] — for loose cards with no deck concept at all.
- [[set-status]] — verify the Precons count after running this.
