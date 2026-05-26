---
name: generate-set-list
description: Build a fillable Excel master list for a Magic the Gathering set. Resolve a plain-language set name (e.g. "Final Fantasy", "Outlaws of Thunder Junction") into Scryfall set codes, sync every printing locally, and emit an XLSX the user can fill in by going through their physically-sorted boxes (qty_normal and qty_foil columns). Use this whenever the user wants to start cataloging a set, or wants a printable per-set checklist with current prices.
---

# Generate Set List

Wraps `mm set master-list` to give the user a fillable Excel spreadsheet for an entire MTG set (or set family — parent + commander + promos + masterpiece etc.). The XLSX is the primary cataloging UX: the user fills in `qty_normal` and `qty_foil` while flipping through their boxes, then re-imports it via `import-list`.

## Workflow

1. **Get the set name.** If the user just says "generate a set list" without naming one, ask. Accept either a plain-language name ("Final Fantasy") or a 3–5 letter Scryfall code (`fin`).
2. **Show related sets and confirm scope.** Run `mm set list-related <name>` and show the user the family tree. Most parent expansions have 5–10 sibling sets (commander deck, masterpiece, promos, art series, tokens). Ask which to include — sensible defaults are *parent + commander + promos + masterpiece*; tokens, art series, and scene boxes are usually skipped unless the user collects them.
3. **Generate.** Run `mm set master-list <code> [--include-related] [--only code1,code2,...] [--out path]`. The default output path is `inventory/<slug>-master-<YYYY-MM-DD>.xlsx`. Defaults to NOT including tokens; pass `--include-tokens` if the user wants them.
4. **Hand off.** Tell the user the path, that columns 8 and 9 (`qty_normal`, `qty_foil`) are tinted yellow and validated as non-negative integers, and that re-import is `mm list import set:<code> <path>` — point them at the [[import-list]] skill for that step.

## Subcommand cheat sheet

```bash
# 1. Show what's in the family
uv run mm set list-related "Final Fantasy"

# 2. Generate parent set only
uv run mm set master-list fin --out inventory/fin-master.xlsx

# 3. Generate parent + commander + promos + masterpiece (skipping tokens, art, scene)
uv run mm set master-list fin --include-related --only fin,fic,pfin,fca

# 4. Generate the full family
uv run mm set master-list fin --include-related --include-tokens
```

## What the XLSX looks like

| Column | Notes |
|---|---|
| `set` | lowercase Scryfall code (e.g. `fca`) |
| `collector_number` | the printed CN within the set (`5`, `123-456`, etc.) |
| `name` | exact Scryfall name; double-faced cards use `Front // Back` |
| `rarity` | `mythic`, `rare`, `uncommon`, `common`, `bonus`, `special` |
| `mana_value` | numeric CMC |
| `usd` | current normal price from Scryfall (may be blank if not for sale) |
| `usd_foil` | current foil price from Scryfall (blank for nonfoil-only printings) |
| `qty_normal` | **input column** — yellow tint, integer ≥ 0 |
| `qty_foil` | **input column** — yellow tint, integer ≥ 0 |

Rows are sorted by **rarity bucket then collector number** to match how the user has their physical boxes organized. Header row is frozen.

## Re-running for the same set

`mm set master-list` is idempotent: re-run anytime to refresh prices or pick up newly-printed cards. The seeded list `set:<code>` keeps existing quantity entries — running master-list again only adds *new* zero-qty rows for printings that didn't exist before; it never overwrites filled-in numbers.

## Examples

User: *"generate a set list for Final Fantasy."*
- Run `mm set list-related fin`. There are 11 related sets (parent + 10 children/siblings).
- Ask whether to include the regional promos (`rfin`, `pss5`), art series (`afin`), scene box (`afic`), tokens (`tfin`, `tfic`, `wfin`). Recommend `--only fin,fic,pfin,fca` (parent + commander + promos + masterpiece) unless they say otherwise.
- Run `mm set master-list fin --include-related --only fin,fic,pfin,fca`. Tell them where the file landed, what to fill in, and how to re-import.

User: *"give me a master list for OTJ but include the breaking news cards too."*
- The Big Score (`big`) and Breaking News (`otp`) are siblings of `otj`. `mm set list-related otj` confirms.
- Run `mm set master-list otj --include-related --only otj,big,otp`.

## Caveats

- Scryfall sometimes reports a set's `card_count` higher than the search returns. If you see `Wrote N rows` and N is lower than the printed count, a handful of variants are hidden by default — usually art-series-only entries that don't show up in standard search. Not a bug.
- `mm set master-list` calls Scryfall through the project's rate-limited wrapper. A full Final Fantasy family sync is ~1,300 cards, which takes 8–12 seconds (paginated, 175 cards per page, 500ms between calls).
