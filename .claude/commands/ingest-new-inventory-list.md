---
description: Walk the user through ingesting every active inventory checklist (XLSX or markdown) in checklists/, asking replace vs additive per file.
allowed-tools:
  - Bash
  - AskUserQuestion
---

# Ingest new inventory lists

Walk the user through ingesting every active inventory checklist currently in `checklists/`. Both `.xlsx` and `.md` files are picked up — the CLI auto-dispatches to the right parser. The work is mechanical: there is one decision per file (replace vs additive) and the rest is reading structured CLI output and surfacing it.

## Steps (do these in order, deterministically)

### 1. List files

Run this exact command (one line, captures the JSON):

```bash
uv run mm input list --json
```

Parse the JSON. The shape is `{ "input_dir": "...", "files": [...] }` where each `files[i]` has:

- `path`, `name`, `sha256`, `size_bytes`
- `summary`: `{anchor_code, set_codes[], rarity_filter[], rows_total, rows_with_qty, total_qty, estimated_value, top_value[], warnings[]}`
- `duplicate_of_log_id`: integer or `null`. **Non-null means this file's content matches a prior successful ingest** (almost certainly a failed cleanup from a previous run — the file should already have been archived but ended up back in `checklists/`).
- `prior_success`: the matching log row if duplicate, else `null`.
- `prior_failed`: a prior FAILED ingest with the same hash, if any.

If `files` is empty: tell the user "no inventory checklists in `checklists/` to ingest. Generate one with `mm set master-list <name>` (or `--format md`) first, or use `mm intake <name>` for the scan-loop REPL instead." and stop.

### 2. Show a one-shot summary of what was found

Print a compact bulleted list, one line per file:

> 1. `final-fantasy-through-the-ages-rare.xlsx` — fca / rare-only / **42 cells filled / $312.40 estimated**
> 2. `final-fantasy-through-the-ages-uncommon.xlsx` — fca / uncommon-only / **8 cells filled / $4.20 estimated**

If any file has `duplicate_of_log_id != null`, surface that VERY prominently before walking the user into per-file ingest:

> ⚠ `<name>` is a content-match for a prior successful ingest (log id N at <timestamp>). This usually means a failed cleanup left the archived file in `checklists/`. Recommended: skip it. If you really want to re-apply, you'll need to confirm `--force` for that one.

### 3. Per file, ask mode + ingest

For each file (in the order returned by `mm input list`):

a. **Decide whether to skip duplicates.** If `duplicate_of_log_id` is set, ask via `AskUserQuestion`:

- Header: `Duplicate file`
- Question: `<filename> matches a prior successful ingest. What do you want to do?`
- Options:
  - **Skip (Recommended)** — likely a failed cleanup; just remove the file with `rm "<path>"`.
  - **Re-ingest with --force** — apply again as a fresh ingest with a new log entry. You'll still pick the mode in the next question.

If the user picks Skip, run `rm <path>` and continue to the next file.

b. **Ask the mode.** Always ask via `AskUserQuestion`:

- Header: `Ingest mode`
- Question: `How should <filename> be applied to set:<anchor_code>?`
- Options (always exactly these two):
  - **Replace (recommended for whole-set master lists)** — XLSX cells inside the file's partition (`set_codes` × `rarity_filter`) become the new DB qty. In-partition cards missing from the XLSX go to 0. Out-of-partition cards untouched.
  - **Additive (recommended for new acquisitions like a booster)** — Only XLSX cells with qty>0 add to the existing DB qty. Blanks/0s do nothing.

Tip: if the file's `rarity_filter` is empty AND `rows_with_qty` is close to `rows_total`, default-recommend **Replace**. If `rarity_filter` is set OR `rows_with_qty` is small (<10% of `rows_total`), default-recommend **Additive**.

c. **Run the ingest.** Build and run:

```bash
uv run mm set ingest --path "<file.path>" --mode <replace|additive> --json
```

Add `--force` IFF the user explicitly chose "Re-ingest with --force" in step 3a.

Parse the JSON output. The shape is documented in `mm set ingest --help`. Surface to the user, in this order:

1. The headline: `<filename>: N updated, M added, Z zeroed (mode=<mode>) → archived to <archived_path>`.
2. **All warnings** (especially `name/printing mismatch` — that means the user typed the wrong set/CN; show the line verbatim).
3. **All `not_found`** entries.
4. **All `extras`** entries (cards not in the seeded set list — the user needs to run `mm set master-list` for the relevant set first).
5. The new label_summary: `set:<anchor> now: X distinct rows, qty Y, value $Z`.

### 4. Final aggregate report

After all files are processed (skipped or ingested), print a single combined summary:

> Ingested N files. Combined: A added, U updated, Z zeroed across labels [list of labels touched]. K files skipped.

If any file failed (status=`failed` in the JSON), call that out explicitly and tell the user the error from the JSON's `error` field.

## Hard rules

- **One file at a time.** Do not batch ingest commands together. Each file gets its own `mm set ingest --path X --mode Y --json` call so the user can inspect output between files.
- **Never silently choose mode.** Always ask. Even when the recommendation is obvious, the user gets the final say.
- **Never overwrite without confirmation.** The CLI itself refuses with exit 4 on duplicate hash; trust the CLI to do the right thing rather than computing it yourself.
- **Surface all warnings.** Especially `name/printing mismatch` — they almost always mean the user has a typo, not that the data is fine.
- **Do not delete `checklists/processed/` files** under any circumstances. The archived copy is the audit trail.
- **All shell paths are quoted** because XLSX filenames contain hyphens and the user's set names sometimes contain colons that survive into the slug.
