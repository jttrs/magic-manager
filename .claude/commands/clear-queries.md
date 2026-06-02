---
description: Clear ALL classified artifacts in queries/ (missing checklists, ManaPool MDs, ad-hoc XLSXs). Aggressive sibling of /cleanup-queries — keeps nothing by default.
allowed-tools:
  - Bash
  - AskUserQuestion
---

# Clear queries/

Aggressive sibling of [[cleanup-queries]]. Where `/cleanup-queries` keeps the newest of each `(set, kind)` group and leaves ad-hoc XLSXs alone, this command clears **all classified files** in `queries/` (missing-* checklists, missing-* ManaPool MDs, AND ad-hoc query XLSXs). Unclassified files (hand-written notes that don't match any pattern) are still skipped silently — that safety net is enforced by the script itself.

Use this when the user wants a clean slate — e.g. starting a new investigation, or after archiving the artifacts they cared about elsewhere.

## Steps (do these in order, deterministically)

### 1. Dry-run first

```bash
uv run python -m scripts.cleanup_queries --keep 0 --include-adhoc --dry-run
```

Surface the output verbatim. The header line tells the user how many files will be deleted; the bulleted list shows each one with its size.

If "Will delete: 0" — tell the user "queries/ is already empty (or contains only unclassified files); nothing to do" and stop.

### 2. Confirm

Use `AskUserQuestion`:

- **Header**: `Clear scope`
- **Question**: `Delete all J files (size)?`
- **Options**:
  - **Yes, clear everything (Recommended)** — runs the dry-run command above without `--dry-run`. Matches the listing above exactly.
  - **Keep ad-hoc XLSXs** — fall back to `/cleanup-queries` semantics (`--keep 0` only, no `--include-adhoc`). Drops missing-* files but preserves any user-named XLSXs from `mm query xlsx`.
  - **Cancel** — don't delete anything. Tell the user the queries/ directory is untouched.

If the user picks "Keep ad-hoc XLSXs", re-run the dry-run with just `--keep 0` and confirm the (smaller) selection before applying.

### 3. Apply

Run the chosen command without `--dry-run`:

```bash
uv run python -m scripts.cleanup_queries --keep 0 --include-adhoc
```

(or `--keep 0` alone if the user picked "Keep ad-hoc XLSXs")

Surface the final summary line ("Deleted N files, freed X.X KB"). If any failures (exit code 1), surface the per-file errors verbatim — typical cause is Excel having a file open; ask the user to close it and re-run.

### 4. Optional: post-clear inventory

```bash
uv run python -m scripts.cleanup_queries --dry-run
```

Should report "queries/ inventory: 0 files across 0 groups" (or only unclassified files remaining).

## Hard rules

- **Always dry-run first.** Even though this is the aggressive variant, the user should see the file list before deletion.
- **Don't reach outside `queries/`.** Same as `/cleanup-queries` — never pass `--queries-dir` overrides unless the user explicitly asks.
- **Surface errors verbatim.** Permission/open-file errors should be reported with the exact filename.
- **The unclassified-skip safety net still applies.** Hand-written notes files (anything not matching the missing-* / `<...>-<ts>.xlsx` patterns) are NEVER deleted, even with `--include-adhoc`. The script enforces this; you don't need to.

## Cross-references

- [[cleanup-queries]] — the conservative sibling. Use that one when the user wants to keep recent history or preserve ad-hoc XLSXs. This command exists for the "wipe and start fresh" case.
- `scripts/cleanup_queries.py` — the underlying script. `--keep 0 --include-adhoc` is the flag combo this command always uses (or `--keep 0` alone if the user opts to preserve ad-hoc files).
