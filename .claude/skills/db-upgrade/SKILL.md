---
name: db-upgrade
description: The required protocol for any DATABASE change in this repo — a new MIGRATIONS entry (schema version), a new column/table, or a one-off data backfill. Covers both halves: (A) on the feature branch, make the change upgrade-safe and PROVE it (tests, migration rehearsal, ownership-unchanged rehearsal through scripts/post_merge_upgrade.py on a pre-migration snapshot), and (B) after the PR merges, upgrade the owner's REAL collection DB on the main checkout (rehearse on a copy → show results → --apply only on the owner's OK → audits). Use whenever you add/alter schema in src/magic_manager/db.py, write a backfill, touch ownership tables (inventory, ingest_events, inventory_events, wishlist_entries, decks, deck_cards, deck_versions, deck_assignments), or the user says "upgrade my db", "apply the migrations", "run the post-merge upgrade", "is my collection safe", "db changes on this branch".
---

# db-upgrade

A thin relay over two deterministic scripts — they hold all the logic and verification:

- `scripts/rehearse_migration.py` — replays migrations on a copy of a DB; precious tables (`ingest_events`, `inventory_events`, …) must stay byte-identical.
- `scripts/post_merge_upgrade.py` — the ONE upgrade runner for a real DB: applies pending migrations, runs every registered one-off backfill, then proves the ownership tables are byte-identical on their pre-upgrade columns and that `inventory == SUM(inventory_events.delta)`. Default = rehearsal on a copy; `--apply` = `db/bak` snapshot, then in place; `--db PATH` = rehearse a specific older snapshot.

Relay the scripts' output verbatim. Never hand-edit a DB, never compute counts yourself, and **never copy a worktree/dev DB over the real one** — a worktree's `db/magic_manager.db` is a disposable snapshot; the real collection only changes by running migrations + backfills in place.

## A. On the feature branch (every DB change)

1. **Migration.** Append to `db.MIGRATIONS` (`CURRENT_VERSION` follows). Additive only: new tables/columns with defaults; never rewrite or drop ownership data. Schema-only — **no network in a migration**.
2. **Backfill as code, not a migration.** Anything that needs Scryfall/MTGJSON or is slow: an idempotent engine function (only fills NULL / `auto` rows, never overwrites user values) + a `uv run mm …` command. If users can override it, keep a provenance column (e.g. `kind_source = auto|user`) so re-runs respect overrides.
3. **Register it in `scripts/post_merge_upgrade.py`** — one `_step(...)` per backfill, guarded to skip when there is nothing to do (e.g. `if decks.unclassified_precon_count()`), and add a row to the docstring table (`V<N> <what> → <function> (<mm command>)`). New ownership table? Add it to `OWNERSHIP` there (and to `PRECIOUS_TABLES` in `rehearse_migration.py` if it is irreplaceable).
4. **Write paths stamp the new data** (sync/upsert/import), and re-syncs must not null it (`COALESCE(excluded.x, table.x)` pattern).
5. **Tests** (offline): migration adds the columns/defaults; backfill fills, is idempotent, respects overrides; write paths stamp it; bump any schema-version assertions.
6. **Prove it** before opening the PR — run both, and paste their verdicts into the PR:
   ```bash
   uv run python -m scripts.rehearse_migration
   uv run python scripts/post_merge_upgrade.py --db db/bak/<the …-pre-v<N> snapshot>
   ```
   (`uv run mm` auto-migrates the worktree DB on connect and leaves `db/bak/…-pre-v<N>` — rehearse against that, so the N-1 → N step is actually exercised.) Exit 0 and every line `✓` is the bar.
7. **PR body** gets an **After merge** section: `uv run python scripts/post_merge_upgrade.py` (rehearsal) then `--apply`, plus expected runtime.

## B. After merge — upgrade the owner's real DB (main checkout)

Touching the main checkout needs the owner's go-ahead for this run.

```bash
cd <main checkout>
git status --short                       # must be clean; stop and ask if not
git pull --ff-only origin main && uv sync
uv run python scripts/post_merge_upgrade.py          # rehearsal on a copy — live DB untouched
```

Show the owner the rehearsal summary (schema version, each backfill's result, the ✓ lines, ledger reconcile). **Only on their explicit OK:**

```bash
uv run python scripts/post_merge_upgrade.py --apply  # snapshots to db/bak/, then upgrades in place
uv run mm audit ingest-ledger                         # must say OK
uv run mm db integrity                                # must say ok
```

Report the snapshot path and its restore command (printed by the script: `uv run mm db restore <snapshot>`). If any step shows `✗` or a non-zero exit, stop, do not retry blindly, and tell the owner — the snapshot restore is the rollback. Web deps after frontend changes: `npm --prefix web install`.

## Don't

- Don't fold network/slow work into a migration (startup would hang on the real DB).
- Don't merge a DB-changing PR without the step-6 proof in its body.
- Don't run `--apply` without a fresh rehearsal on the same commit and the owner's OK.
