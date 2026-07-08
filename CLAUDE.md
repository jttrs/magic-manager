# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`magic-manager` (`mm`) is a local-first MTG collection / set / wishlist / deck manager. Python 3.12, dependencies managed by `uv`, single-file SQLite store. No web service, no cloud — every command operates on `db/magic_manager.db`.

## Running the CLI

The `mm` CLI is a `uv` project script (`pyproject.toml` → `mm = "magic_manager.cli:app"`); it is **not** on `PATH`. **Always invoke it as `uv run mm …`** — bare `mm …` will fail with `mm not found`. Skip the `which mm` / bare-`mm --help` probe; go straight to `uv run mm --help` or the specific subcommand.

Top-level subcommand groups (each `--help` lists its own subcommands):

```
uv run mm set …          # sync sets, build/ingest inventory checklists, jumpstart-list
uv run mm inventory …    # show / value / add / remove / import (V2 fact table)
uv run mm wishlist …     # categories of cards I want
uv run mm deck …         # decks (composition independent of ownership), import-precon
uv run mm query …        # selector queries: show, value, top, total, multiples, stats, url, xlsx, missing-set
uv run mm checklists …   # inspect files in checklists/ (alias: `mm input …`)
uv run mm mtgjson …      # MTGJSON precon/set lookups (cached)
uv run mm db …           # snapshot, snapshots, restore, integrity
uv run mm intake <set>   # scan-loop REPL for fast bulk entry
uv run mm export …       # paste-ready blocks for moxfield/manapool/tcgplayer/archidekt/plain/scryfall-json
uv run mm scryfall <q>   # ad-hoc Scryfall search via the rate-limited wrapper
```

There is no test suite, no linter config, and no build step. `uv sync` installs deps.

## Architecture (the parts that need cross-file reading)

### Selector grammar — the central abstraction

`src/magic_manager/selectors.py` defines a small DSL that nearly every read-side command (`query show/value/url/xlsx/missing-set`, `export`) parses and materializes into `(printing, finish, qty)` rows:

```
SELECTOR ::= TERM (' ' MODIFIER)*
TERM     ::= inventory | wishlist[:CATEGORY] | deck:SLUG
           | set:CODE[+related] | cards:SCRYFALL_QUERY | scryfall:SCRYFALL_QUERY
MODIFIER ::= missing[:nonfoil|foil|either] | owned | available
           | qty{>=,<=,=}N | finish={foil,nonfoil} | rarity=…
           | cn{>=,<=}N | value{>=,<=}N | scryfall:Q | treatment=…
```

When adding a query-shaped feature, prefer a new modifier/term over a one-off command — the rest of the read pipeline (sorting, exports, URL chunking, missing-set unions) gets it for free.

### Set families and the "missing from <set>" pipeline

A Magic "set" is rarely one Scryfall code. `sets_mod.resolve(name_or_code)` returns the parent + every set whose `parent_set_code` traces back to it (e.g. `fin` resolves to `fin` plus 8 siblings). The `set:CODE+related` term and `mm query missing-set <CODE>` build on this.

`mm query missing-set` is a flagship workflow (also exposed as the `missing-from-set` skill). It unions three printing-level sub-selectors (rare-regular, mythic-regular, treatment-class) and emits four artifacts: Scryfall URL chunks (chat output), an XLSX checklist + ManaPool bulk-add `.txt` + TCGplayer Mass Entry `.txt` (under `queries/`). Per-family configuration lives in `selectors.py` near `FAMILY_DUPE_FOIL_PROMO_TYPES` / `FAMILY_UNOBTAINABLE_RULES` — when supporting a new family, look there first.

### Inventory checklists — generate → fill → ingest → archive

`checklists/` (formerly `input/`, both names work — `INPUT_DIR` is an alias) holds active XLSX/MD checklists awaiting ingest. The lifecycle is:

1. `mm set master-list <set>` writes `checklists/<slug>[-slice]-<mode>-checklist.xlsx`. Mode is `add` (blank, additive ingest) or `modify` (prefilled, replace ingest); the mode token is in the filename and in a hidden `_meta` sheet.
2. User edits qty cells in Excel/Numbers (or any text editor for `--format md`).
3. `mm set ingest <set>` (or `--path <file>`) reads `_meta.mode` to pick replace vs additive semantics, writes to the `inventory` table, archives the file under `checklists/processed/<…>-<timestamp>.xlsx`, and appends a row to `ingest_log`. Files are SHA-256-fingerprinted; re-ingesting the same file is refused without `--force`.

There can be only one active checklist per slug+slice+format at a time (collision exits with `EXIT_UNPROCESSED_INTAKE = 3`). Jumpstart checklists are a separate `kind` with their own ingest path (`_ingest_jumpstart`).

### Database

SQLite at `db/magic_manager.db`, with `-wal`/`-shm` siblings colocated. Snapshots go to `db/bak/`, files displaced by `db restore` go to `db/replaced/`. Schema is created on first connect; subsequent versions add to the `MIGRATIONS` list and bump `CURRENT_VERSION` in `db.py`.

Set the `MAGIC_MANAGER_DB` env var to a file path to redirect the entire DB (used by `scripts/rehearse_migration.py` and any future tests).

V2 fact tables: `cards`, `inventory`, `wishlist_entries`, `decks`, `deck_cards`, `ingest_log`, `set_targets`. Pre-V2 used a single conflated `list_rows` table; see `docs/pre-v2-inventory-snapshot.md` for the migration baseline.

### Module map

Inside `src/magic_manager/`:

- `cli.py` — every `typer` command. Long but flat; new commands go here.
- `db.py` — schema, migrations, `connect()` context manager, snapshot/restore.
- `sets.py` — set family resolution, sync from Scryfall, master-list/jumpstart-list writers, ingest readers.
- `selectors.py` — the selector DSL parser + materializer.
- `inventory.py`, `wishlist.py`, `decks.py` — V2 fact-table CRUD + value rollups.
- `intake.py` — scan-loop REPL.
- `parsers.py` — Moxfield-style block parser (used by `import` commands).
- `treatments.py` — derives a treatment string (e.g. `b|ff`, `ext`) from Scryfall card fields. Centralized so missing-set, master-list, and ad-hoc queries all agree on what counts as a "distinct printing".
- `scryfall.py`, `mtgjson.py` — thin clients; the bash wrappers in `.claude/skills/{scryfall,mtgjson}-search/` are the canonical access path (see hooks below).
- `exports/` — one module per target (moxfield, manapool, tcgplayer, archidekt, plain, scryfall_json), all with `build(rows) -> str`.

`scripts/` holds one-off utilities: `rehearse_migration.py` (replays migrations on a copy of the DB), `survey_treatment_signature.py` (audits a family's prints when adding `FAMILY_*` rules), `cleanup_queries.py` (prunes `queries/`).

## External-API hooks (will block you)

`PreToolUse` hooks in `.claude/settings.json` block direct `curl`/`wget` to `api.scryfall.com` and `mtgjson.com`. Use:

- `.claude/skills/scryfall-search/scryfall.sh` (rate-limited, 24h cache, 429 backoff) — or `uv run mm scryfall <query>`
- `.claude/skills/mtgjson-search/mtgjson.sh` (cached under `$TMPDIR/mtgjson-cache` with `.sha256` sidecars) — or `uv run mm mtgjson …`

The Python clients (`scryfall.py`, `mtgjson.py`) ultimately call these wrappers, so the CLI is always safe.

## Conventions

- The user is the only consumer of this codebase; back-compat shims (`INPUT_DIR` alias, `mm input …` typer alias) exist only as long as the user's muscle memory needs them. No need to add new ones for hypothetical future callers.
- Filename conventions encode intent for Finder/cmux (no `_meta` visible there): `<slug>-<slice>-<mode>-checklist.xlsx`, `missing-<code>-checklist-<ts>.xlsx`, `missing-<code>-{manapool,tcgplayer}-<ts>.txt`. Keep them stable — skills and slash commands grep for them.
- `queries/` is for ephemeral artifacts (missing-set XLSX/TXT, `query xlsx` outputs); the `cleanup-queries` skill prunes it. Don't put anything durable there.
- `docs/` is reference, not always implemented — file headers say "Documented but not implemented as of V<N>" when the schema/design exists but the importer doesn't yet.

### Per-set knowledge (`docs/sets/`)

`docs/sets/<anchor>.md` is the durable memory doc for each set-family (LTR, FIN, SPM, TLA, TMT, …). Each follows the shape defined in `docs/sets/_TEMPLATE.md`: family map, treatments, chase variants, scenes/posters, unobtainable rules, PRM destinations, edge cases, code refs.

**Read before answering.** When the user asks a set-specific question or you're working on a set-specific command, `Read` `docs/sets/<anchor>.md` **before** answering. It captures peculiarities Scryfall metadata doesn't (chase variants, scene groupings, family-topology gotchas like MAR being a separately-rooted SPM bonus sheet). If no doc exists yet for the family, suggest running the `characterize-set` skill to bootstrap one.

**Update when you learn something new.** If a session surfaces a new per-set fact — a chase variant we hadn't catalogued, a scene grouping, an unusual `promo_types` behavior, a new PRM destination, a family-topology gotcha — add it to the appropriate section of `docs/sets/<anchor>.md` before ending the session. Keep entries dense and factual (every row of every table should be verifiable via `mm scryfall` or the survey script).

**Code + doc stay in sync.** `docs/sets/<anchor>.md` §8 "Code refs" points at `FAMILY_DUPE_FOIL_PROMO_TYPES` / `FAMILY_UNOBTAINABLE_RULES` entries in `src/magic_manager/selectors.py`. If you add/remove those constants, update the doc's §8 in the same commit.
