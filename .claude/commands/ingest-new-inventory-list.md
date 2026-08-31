---
description: Walk the user through ingesting every active checklist (XLSX or markdown) in checklists/ — inventory checklists AND precon/jumpstart deck checklists. Mode/kind is auto-detected from the file's _meta (no per-file prompt for tagged files).
allowed-tools:
  - Bash
  - AskUserQuestion
---

# Ingest new checklists

Walk the user through ingesting every active checklist currently in `checklists/`. Both `.xlsx` and `.md` files are picked up — the CLI auto-dispatches to the right parser.

**There are two families of checklist, distinguished by each file's `summary.kind`:**

- **Inventory checklists** (`kind: "inventory"`, or absent for legacy files) — from `mm set master-list`. These carry `qty_normal`/`qty_foil` and ingest into the `inventory` table.
- **Jumpstart checklists** (`kind: "jumpstart"`) — from `mm set jumpstart-list`. Carry `keep_qty` (0/1) + `deconstructed_qty`; ingest via `import_precon` (creating `pack:*` decks + adding inventory). Always additive.
- **Precon checklists** (`kind: "precon"`) — from `mm set precon-list`. Carry `constructed_qty` + `deconstructed_qty` and track precon decks AS UNITS. Counts are DERIVED from the `decks` table (each built or torn-down copy is a deck row), so there's no separate ledger to drift. Two flavors via `_meta.mode`: `add` (blank; ingest ADDS the entered counts as new deck rows) and `modify` (prefilled from the live deck counts; ingest applies the SIGNED DELTA). Raising a count builds copies / records torn-down copies; **lowering a count in `modify` is NOT applied** — removing a copy is an explicit `mm deck delete <slug>` (the derived count then updates itself), so ingest just warns.

**Mode/kind is declared by the file, not the user.** For inventory checklists, `_meta.mode` says how to apply: `modify` → `replace` (signed per-row; untouched/absent rows left alone unless you opt into zeroing), `add` → `additive`. Jumpstart is always additive. Precon reads its own `_meta.mode` (add/modify) internally. This command does NOT ask replace-vs-additive per file. Legacy inventory files (no `_meta.mode`) need an explicit `--mode` — see step 3b. In all cases the ingest command is the same: `mm set ingest --path "<file>" --json`.

## Steps (do these in order, deterministically)

### 1. List files

Run this exact command (one line, captures the JSON):

```bash
uv run mm input list --json
```

Parse the JSON. The shape is `{ "input_dir": "...", "files": [...] }` where each `files[i]` has:

- `path`, `name`, `sha256`, `size_bytes`
- `summary`: always has `kind` (`"inventory"`, `"precon"`, or `"jumpstart"`), `rows_total`, `rows_with_qty`, `total_qty`, `estimated_value`, `warnings[]`. **Branch on `summary.kind`:**
  - `kind == "inventory"` → also has `{anchor_code, set_codes[], rarity_filter[], top_value[]}`.
  - `kind in ("precon","jumpstart")` → also has `{mode, decks_to_construct, loose_copies, filled[]}` where each `filled[i]` is `{file_name, label, constructed_qty, deconstructed_qty, delta, set, usd_total}`. `rows_with_qty` = rows that will act; for a precon `modify` file (`mode: "modify"`) the entered numbers are absolute targets prefilled from the live deck counts, so a row acts only when it differs (`delta` = the `(Δconstructed, Δdeconstructed)` this ingest applies), and `decks_to_construct`/`loose_copies` are the positive deltas. `estimated_value` = summed `usd_total` over rows that build a new copy.
- `duplicate_of_log_id`: integer or `null`. **Non-null means this file's content matches a prior successful ingest** (almost certainly a failed cleanup from a previous run — the file should already have been archived but ended up back in `checklists/`).
- `prior_success`: the matching log row if duplicate, else `null`.
- `prior_failed`: a prior FAILED ingest with the same hash, if any.

If `files` is empty: tell the user "no checklists in `checklists/` to ingest. Generate an inventory checklist with `mm set master-list <name>` (or `--format md`), a precon catalog with `mm set precon-list`, or use `mm intake <name>` for the scan-loop REPL." and stop.

### 2. Show a one-shot summary of what was found

Print a compact bulleted list, one line per file. **Format the line by `summary.kind`:**

- Inventory:
  > 1. `final-fantasy-through-the-ages-rare.xlsx` — inventory / fca / rare-only / **42 cells filled / $312.40 estimated**
- Precon / jumpstart (use `summary.mode` if present; for a precon `modify` file the counts are net changes vs the current deck collection):
  > 2. `precons-modify-checklist.xlsx` — precon (modify) / **3 precons changed → 2 to build, 1 loose / $214.60 estimated**

If any file has `duplicate_of_log_id != null`, surface that VERY prominently before walking the user into per-file ingest:

> ⚠ `<name>` is a content-match for a prior successful ingest (log id N at <timestamp>). This usually means a failed cleanup left the archived file in `checklists/`. Recommended: skip it. If you really want to re-apply, you'll need to confirm `--force` for that one.

### 3. Per file, handle duplicates + ingest (mode auto-detected)

For each file (in the order returned by `mm input list`):

a. **Decide whether to skip duplicates.** If `duplicate_of_log_id` is set, ask via `AskUserQuestion`:

- Header: `Duplicate file`
- Question: `<filename> matches a prior successful ingest. What do you want to do?`
- Options:
  - **Skip (Recommended)** — likely a failed cleanup; just remove the file with `rm "<path>"`.
  - **Re-ingest with --force** — apply again as a fresh ingest with a new log entry. Mode is still auto-detected from the file.

If the user picks Skip, run `rm <path>` and continue to the next file.

b. **Run the ingest.** Build and run:

```bash
uv run mm set ingest --path "<file.path>" --json
```

Add `--force` IFF the user explicitly chose "Re-ingest with --force" in step 3a. Do NOT pass `--mode` — the CLI reads the file's `_meta` and applies the right semantics automatically (inventory: `modify`→replace / `add`→additive; deck checklists: always additive). The command is identical for both families.

**Legacy file edge case (inventory only)** — if `mm set ingest` exits with code 2 and the error mentions `_meta.mode`, the file is a pre-tagging inventory checklist. Deck checklists (`kind` precon/jumpstart) never hit this. In that one case, fall back to the per-file prompt:

- Ask via `AskUserQuestion` with header `Legacy file mode`, question `<filename> has no _meta.mode (legacy file). How to apply?`, options:
  - **Replace (recommended if the file is a full set audit / current-inventory snapshot)** — pass `--mode replace`.
  - **Additive (recommended if the file is a new-acquisitions delta)** — pass `--mode additive`.
- Then re-run `mm set ingest --path "<file.path>" --mode <chosen> --json`.

Parse the JSON output and surface it to the user. **The `kind` field (also in the JSON) selects the report shape:**

**Inventory** (`kind: "inventory"`), in this order:

1. The headline: `<filename>: N updated, M added, Z zeroed (mode=<mode>) → archived to <archived_path>`.
2. **All warnings** (especially `name/printing mismatch` — that means the user typed the wrong set/CN; show the line verbatim).
3. **All `not_found`** entries.
4. **All `extras`** entries (cards not in the seeded set list — the user needs to run `mm set master-list` for the relevant set first).
5. The label_summary: `set:<anchor> now: X distinct rows, qty Y, value $Z`.

**Jumpstart** (`kind: "jumpstart"`) — the JSON `summary` has `rows_acted`, `rows_total`, `constructed`, `loose_copies`, `inv_qty_total`, `per_row[]`, `warnings[]`. Surface:

1. Headline: `<filename>: <rows_acted>/<rows_total> packs acted — <constructed> constructed, <loose_copies> loose copies, <inv_qty_total> cards added → archived to <archived_path>`.
2. Per acted row: `<file_name> (<label>) → <slug>` when constructed, or `deconstructed <n> → loose inventory`.
3. Any `per_row[i].error` verbatim; any `per_row[i].missing_sids` count; all `summary.warnings`.

**Precon** (`kind: "precon"`) — the JSON `summary` has `rows_acted`, `rows_total`, `constructed` (decks built this ingest), `deconstructed` (torn-down copies recorded this ingest), `inv_qty_total`, `per_row[]`, `warnings[]`. Each `per_row[i]` has `count_before` `[c,d]`, `count_after` `[c,d]`, `delta` `[Δc,Δd]`, `built`, `torn_down`, `warning`, `error`, `missing_sids`. Surface:

1. Headline: `<filename>: <rows_acted>/<rows_total> precons changed — <constructed> built, <deconstructed> torn down, <inv_qty_total> cards added → archived to <archived_path>`.
2. Per acted row: `<file_name> (<label>): constructed <before_c>→<after_c>, deconstructed <before_d>→<after_d>`.
3. **Any `per_row[i].warning`** verbatim — this is where "lowered a count; not applied — run `mm deck delete <slug>`" appears. Show it; it's expected, not an error.
4. Any `per_row[i].error` verbatim; any `per_row[i].missing_sids` count; all `summary.warnings`.

### 4. Final aggregate report

After all files are processed (skipped or ingested), print a single combined summary. Report inventory and deck-checklist tallies separately (they don't share units):

> Ingested N files. Inventory: A added, U updated, Z zeroed across labels [list]. Precon/jumpstart: C built, L torn down, Q cards added. K files skipped.

Omit whichever family had no files.

If any file failed (status=`failed` in the JSON), call that out explicitly and tell the user the error from the JSON's `error` field.

## Hard rules

- **One file at a time.** Do not batch ingest commands together. Each file gets its own `mm set ingest --path X --json` call so the user can inspect output between files.
- **Trust the file's declared mode.** `_meta.mode` is the source of truth — don't ask the user to confirm mode for tagged files (that defeats the whole point of the tagging system). The only exception is the legacy-file fallback in step 3b.
- **Never overwrite without confirmation.** The CLI itself refuses with exit 4 on duplicate hash; trust the CLI to do the right thing rather than computing it yourself.
- **Surface all warnings.** Especially `name/printing mismatch` — they almost always mean the user has a typo, not that the data is fine. Also surface the stderr override warning if `--mode` was passed and disagreed with `_meta.mode`.
- **Do not delete `checklists/processed/` files** under any circumstances. The archived copy is the audit trail.
- **All shell paths are quoted** because XLSX filenames contain hyphens and the user's set names sometimes contain colons that survive into the slug.
