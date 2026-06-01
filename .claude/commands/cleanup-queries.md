---
description: Prune accumulated artifacts in queries/ (missing checklists + ManaPool MDs from `mm query missing-set`). Default keeps the newest of each set+kind group.
allowed-tools:
  - Bash
  - AskUserQuestion
---

# Cleanup queries/

Walk the user through pruning the `queries/` directory. Each `mm query missing-set <CODE>` invocation writes a new timestamped pair (`missing-<code>-checklist-<ts>.xlsx` + `missing-<code>-manapool-<ts>.md`); these accumulate without bound. This command runs `scripts/cleanup_queries.py` which keeps the newest of each `(set, kind)` group by default.

## Steps (do these in order, deterministically)

### 1. Show the user what's there

Always start with a dry run so the user sees the impact before anything is deleted:

```bash
uv run python -m scripts.cleanup_queries --dry-run
```

Surface the output verbatim. Three signals to watch for:

- **"queries/ inventory: N files across M groups"** — header line. Tells the user how many distinct artifact groups are present. M of 1–3 is normal; >3 means multiple sets have been queried this session.
- **"Will keep: K"** — files that will survive the default rule (newest of each missing-* group + all ad-hoc XLSXs).
- **"Will delete: J (size)"** — total candidate count. If J=0, tell the user "queries/ is already at minimum; nothing to do" and stop.

### 2. Confirm what they want pruned

Use `AskUserQuestion`:

- **Header**: `Cleanup scope`
- **Question**: `Apply the cleanup above (J files / size)?`
- **Options**:
  - **Yes, default cleanup (Recommended)** — keep newest of each missing-* group, leave ad-hoc XLSXs alone. Matches the dry-run output.
  - **Keep more history** — re-run with `--keep N`. Ask the user for N (default 3 if they don't say). Useful when the user wants to compare a few recent runs.
  - **Also prune ad-hoc query XLSXs** — re-run with `--include-adhoc`. Drops the `--name`-named files from `mm query xlsx`. Use only if the user explicitly says so; ad-hoc files are often hand-named for specific reports they want to keep.
  - **Time-based purge** — re-run with `--older-than 7d` (or whatever the user specifies). Composes with `--keep`: a file must be both older than the cutoff AND past the keep threshold to be deleted.

If the user picks anything other than "default cleanup", re-run the dry-run with the requested flags and confirm the new selection before applying.

### 3. Apply

Run the same command without `--dry-run`. Surface the final summary line ("Deleted N files, freed X.X KB"). If any failures (exit code 1), surface the per-file errors verbatim so the user can investigate.

```bash
uv run python -m scripts.cleanup_queries [--keep N] [--include-adhoc] [--older-than SPEC]
```

### 4. Optional: post-cleanup inventory

If the user wants to verify, run:

```bash
ls -la queries/
```

…or, equivalently, `uv run python -m scripts.cleanup_queries --dry-run` again — should now show 0 files to delete.

## What the script keeps and drops

The script classifies every file in `queries/` into one of three "kinds" based on filename:

| Filename pattern | Kind | Default behavior |
|---|---|---|
| `missing-<code>-checklist-<ts>.xlsx` | `missing-checklist` | Keep newest 1 per `<code>`; delete the rest |
| `missing-<code>-manapool-<ts>.md`    | `missing-manapool`  | Keep newest 1 per `<code>`; delete the rest |
| `<anything-else>-<ts>.xlsx`          | `adhoc`             | Keep all (unless `--include-adhoc`) |
| Files that don't match any pattern   | (unclassified)      | Skipped silently — never touched |

The unclassified-skip rule is the safety net: if you put a hand-written notes file in `queries/`, the script won't delete it.

## Hard rules

- **Always dry-run first.** Don't apply without showing the user what will be deleted.
- **Never run with `--include-adhoc` by default.** Ad-hoc query XLSXs are user-named one-off reports; deleting them silently is a foot-gun.
- **Don't reach outside `queries/`.** The script enforces this internally; don't pass `--queries-dir` overrides unless the user explicitly asks.
- **Surface errors verbatim.** Permission errors or open-file errors (Excel having the file open) should be reported to the user with the exact filename so they can resolve.

## Cross-references

- `scripts/cleanup_queries.py` — the script itself. Has its own `--help`; run `uv run python -m scripts.cleanup_queries --help` for the canonical reference.
- `[[missing-from-set]]` — the source of most artifacts in `queries/`. Each `mm query missing-set <CODE>` invocation produces 2 files; running it 10 times leaves 20 stale files this command can clean up.
- `[[feedback-checklist-artifacts]]` (memory) — the artifact-type definitions this script uses to classify filenames.
