---
name: generate-precon-checklist
description: Build the global preconstructed-deck catalog (XLSX or markdown) across ALL Magic sets — one row per precon product (Commander deck, Box Set, Planeswalker deck, Duel deck, Starter Kit, …) with constructed_qty/deconstructed_qty columns the user fills in. Two flavors via --mode: 'add' (default; blank cells; ingest ADDS the counts) and 'modify' (cells prefilled from the user's current deck collection so they see what they already own and don't double-add). Use whenever the user wants to catalog which precon decks they have. Mechanical workflow: invoke `mm set precon-list [--mode add|modify]` and relay the result. Triggers: "generate a precon checklist", "make me a precon catalog", "precon checklist", "which precons do I have", "checklist of all commander decks".
---

# Generate Precon Checklist

The mechanical wrapper around `mm set precon-list`. It writes a **global, all-sets catalog** — one row per preconstructed product across every Magic set — because there are only a handful of precons per set (a per-set file would be pointless). Precon decks are tracked AS UNITS via three fill columns: `constructed_qty` (built copies kept assembled), `deconstructed_qty` (copies torn down for parts), and `pool_qty` (card POOLS — Starter Collection / Scene Box — that were never a playable deck; cards go loose, a marker row is kept). Pool-suggested rows tint their `pool_qty` cell green (XLSX) or show `← pool (fill P)` (md).

This is the precon sibling of [[generate-set-checklist]] (which is the per-card *inventory* checklist). They are different artifacts: this one is precon products as units; that one is individual card printings.

> **Counts are derived from the decks table — there is no ledger.** Each copy is a deck row carrying the MTGJSON fileName + a `precon_state` (built / deconstructed / pool), so `--mode modify` prefills from the user's real deck collection and can never drift. See [[add-precon]] / [[import-precon]] for the one-liner add paths.

## Steps

1. Run `uv run mm set precon-list` (add the flags below as the request warrants). That's the whole happy path.
2. Look at the exit code:
   - **0**: success. Tell the user the file path and the next step (fill the `constructed_qty`/`deconstructed_qty` cells, then `mm set ingest --path <file>` — or use the [[ingest-new-inventory-list]] flow). Done.
   - **2**: bad arguments (e.g. bad `--format`/`--mode`) or "no precon variants found" for a `--type` that matched nothing. Surface the error verbatim.
   - **3** (`EXIT_UNPROCESSED_INTAKE`): a catalog for this mode already exists at `checklists/precons-<mode>-checklist.xlsx`. Tell the user; offer to ingest the existing one first (`mm set ingest --path <file>`) or regenerate with `--force` (warn that un-ingested edits are lost).

## Mode — `add` vs `modify`

The mode is encoded in the filename (`precons-<mode>-checklist.xlsx`) and the file's `_meta.mode`; `mm set ingest` auto-detects it.

| `--mode` | Filename | Cells at generation | Ingest semantics | When to use |
|---|---|---|---|---|
| **`add`** (default) | `precons-add-checklist.xlsx` | **Blank** | ADDS the entered counts — `constructed_qty` builds a deck copy (+cards), `deconstructed_qty` records a torn-down copy, `pool_qty` records a card-pool unit (cards loose). Only ever increases. | Recording precons you acquired. |
| **`modify`** | `precons-modify-checklist.xlsx` | **Prefilled** from your current deck collection (derived counts) | Applies the SIGNED DELTA vs the prefilled value. Raising a count builds/records copies. **Lowering a count is NOT applied** — it warns and points to `mm deck delete <slug>` (the derived count updates when you actually delete). | Seeing what you already own before adding, so you don't double-add. |

**Default is `add`.** Recommend `modify` when the user wants to *review/correct* what they already have ("which precons do I have", "show me my current precons", "I want to see what's already tracked").

Both flavors carry a colored **README banner sheet** (green add / red modify) restating the semantics, and the markdown form carries it as a blockquote under the H1.

## Scope + value flags (rarely needed)

- `--type "Commander Deck"` — narrow to one exact MTGJSON product type. Default is the modern-constructed set (`mtgjson.PRECON_MODERN_TYPES`: Commander/Box/Duel/Planeswalker/Starter/Welcome/Intro/Challenger/Guild/Brawl/Clash/Game Night/Archenemy/Planechase — ~680 rows).
- `--all-physical` — widen to EVERY physical product (~1500 rows, incl. old Theme Decks / Sample Decks / Welcome Boosters). Ignored when `--type` is given.
- `--include-collector` — include the `… Collector's Edition` twins (excluded by default; the collection doesn't track them).
- `--sync-all` — **slow.** Generation is best-effort on `usd_total` (blank for sets not yet in the local `cards` table). `--sync-all` syncs every referenced set (~180) from Scryfall up front so all totals populate in one run. Only use when the user explicitly wants full pricing now; otherwise values fill in over time as precons get ingested (each ingest self-syncs its own sets). Warn it takes several minutes.
- `--format md` — markdown instead of XLSX; edit the `[C:c D:d P:p]` bracket per row (P = pool).
- `--out <path>` / `--force` — override path / overwrite an existing catalog.

Never listed by `precon-list`: digital (`MTGO …`), Jumpstart (its own `mm set jumpstart-list` + [[generate-set-checklist]]-adjacent flow), and Secret Lair Drop ([[bulk-add]] / [[secret-lair-value]]).

## Not to be confused with

- [[generate-set-checklist]] — per-card inventory checklist for one set family (`mm set master-list`). Different artifact.
- [[add-precon]] — the one-liner "I built/bought precon X" path (`mm deck add-precon`), no XLSX. Use that for a specific precon or a whole set's worth; use THIS skill to generate the fillable all-sets catalog.
- [[ingest-new-inventory-list]] — ingests the filled catalog (and inventory checklists) back into the DB.

## Examples

User: *"generate a precon checklist"* → `uv run mm set precon-list` → tell them `checklists/precons-add-checklist.xlsx` is ready.

User: *"give me a checklist showing which precons I already have"* → `uv run mm set precon-list --mode modify` → `checklists/precons-modify-checklist.xlsx`, prefilled from their collection.

User: *"just the commander decks"* → `uv run mm set precon-list --type "Commander Deck"`.

User: *"and price everything"* → add `--sync-all` (warn: several minutes).
