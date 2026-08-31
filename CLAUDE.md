# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`magic-manager` (`mm`) is a local-first MTG collection / set / wishlist / deck manager. Python 3.12, dependencies managed by `uv`, single-file SQLite store. No web service, no cloud — every command operates on `db/magic_manager.db`.

## Running the CLI

The `mm` CLI is a `uv` project script (`pyproject.toml` → `mm = "magic_manager.cli:app"`); it is **not** on `PATH`. **Always invoke it as `uv run mm …`** — bare `mm …` will fail with `mm not found`. Skip the `which mm` / bare-`mm --help` probe; go straight to `uv run mm --help` or the specific subcommand.

Top-level subcommand groups (each `--help` lists its own subcommands):

```
uv run mm set …          # sync sets, is-synced, build/ingest inventory checklists, jumpstart-list, precon-list
uv run mm inventory …    # show / value / add / remove / import (V2 fact table)
uv run mm wishlist …     # categories of cards I want
uv run mm deck …         # decks (composition independent of ownership), import-precon
uv run mm query …        # selector queries: show, value, top, total, multiples, stats, url, xlsx, missing-set
uv run mm checklists …   # inspect files in checklists/ (alias: `mm input …`)
uv run mm mtgjson …      # MTGJSON precon/set lookups (cached)
uv run mm db …           # snapshot, snapshots, restore, integrity, unlock (clear stale -wal/-shm)
uv run mm audit …        # deck-inventory consistency checks (--fix deletes orphan decks)
uv run mm intake <set>   # scan-loop REPL for fast bulk entry
uv run mm export …       # paste-ready blocks for moxfield/manapool/tcgplayer/archidekt/plain/scryfall-json
uv run mm scryfall <q>   # ad-hoc Scryfall search via the rate-limited wrapper
```

There is a pytest suite under `tests/` (`uv run pytest`); fixtures use the
`MAGIC_MANAGER_DB` env override for a throwaway DB and monkeypatch the
`scryfall`/`mtgjson` wrappers so the suite is fully offline.

There is a pytest suite (`uv run pytest`, dev-dep in `pyproject.toml`); no linter config and no build step beyond `uv_build`. `uv sync` installs deps.

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

1. `mm set master-list <set>` writes `checklists/<slug>[-slice]-<mode>-checklist.xlsx`. Mode is `add` (blank cells, additive ingest) or `modify` (cells prefilled from current inventory, replace ingest); the mode token is in the filename, in a hidden `_meta` sheet, and restated in a visible **README banner sheet** (green for add, red for modify) — see `_add_mode_banner_sheet`.
2. User edits qty cells in Excel/Numbers (or any text editor for `--format md`).
3. `mm set ingest <set>` (or `--path <file>`) reads `_meta.mode` to pick semantics. **`modify` is non-destructive by default:** it SETS each in-partition row to its cell value (a signed change vs current — editing 3→5 nets +2, 3→1 nets −2, 0 zeroes that row), but does NOT auto-zero in-partition rows absent from the file. Zeroing absent rows (the old full-audit behavior) is opt-in: `ingest_inventory_from_xlsx(zero_untouched=…)`, surfaced as an interactive prompt (default No) or the `--zero-untouched/--no-zero-untouched` flag (`--json`/non-interactive callers default to No). Then it writes to `inventory`, archives under `checklists/processed/<…>-<timestamp>.xlsx`, and appends to `ingest_log`. Files are SHA-256-fingerprinted; re-ingesting the same file is refused without `--force`.

There can be only one active checklist per slug+slice+format at a time (collision exits with `EXIT_UNPROCESSED_INTAKE = 3`).

**Deck checklists (precon + jumpstart).** A *precon* (preconstructed product) is the base concept; a *Jumpstart pack* is one species of it. `mm set precon-list` writes a **global, all-sets catalog** — one row per physical product (Commander Deck, Box Set, Planeswalker Deck, …) across every set, because there are only a handful of precons per set (a per-set file would be pointless). `mm set jumpstart-list <set>` is the Jumpstart-specific, per-set sibling. Both declare `kind` (`precon`|`jumpstart`) in a hidden `_meta` sheet, and `mm set ingest` dispatches on it (dispatch is hoisted to the top of `set_ingest` because the global precon catalog carries no `anchor_code` for the inventory anchor-resolution path). The CLI consumer is `_ingest_deck_checklist`, parameterized by kind.

*Jumpstart* carries `keep_qty` (0/1) + `deconstructed_qty` and runs through `_apply_deck_checklist` (`sets.ingest_deck_checklist_from_path(kind="jumpstart")`): `keep_qty=1` creates one `pack:*` recipe (`format=jumpstart`) + auto-composes a copy; `keep_qty=0` with `deconstructed_qty>0` adds loose cards. Unchanged by the precon rework — the shared parser accepts both the `keep_qty` column / `[K:…]` bracket and precon's `constructed_qty` / `[C:…]`.

*Precon* tracks decks AS UNITS, with **the `decks` table as the single source of truth** — there is no separate ledger. Two V10 columns make counts *derivable* so they can't drift: `decks.source_precon_file_name` (the MTGJSON fileName join key) and `decks.is_deconstructed` (0=built, 1=torn-down-for-parts — recipe kept, cards loose/unpledged). Then `constructed_qty(X) = COUNT(decks WHERE source_precon_file_name=X AND is_deconstructed=0)` and `deconstructed_qty(X) = COUNT(… AND is_deconstructed=1)`, exposed as `decks.precon_unit_counts[_for]()`. `import_precon` stamps the fileName on every deck row it creates and, with `record_deconstructed_deck=True` (used by the precon path + `import-precon --deconstruct`), creates an `is_deconstructed=1` row for a torn-down copy. (The V7 `precon_ledger` was dropped in the V10 migration, which also back-derives the fileName for pre-existing decks by reverse-mapping `_slug(name)`+`source_set_code` → fileName across `precon_variants`/`jumpstart_variants`.) The checklist has two flavors via `--mode`/`_meta.mode`: `add` (blank cells; ingest ADDS entered counts as new deck rows) and `modify` (cells prefilled from the live deck counts via `_build_precon_rows(prepopulate_from_counts=True)`; ingest applies the SIGNED DELTA). Ingest runs through `_apply_precon_checklist` (NOT the jumpstart engine): +constructed → `import_precon` once per copy (distinct slugs `<slug>`, `<slug>-2`, … via `_count_precon_deck_copies`) building decks + adding cards; +deconstructed → `import_precon(deconstruct=True, record_deconstructed_deck=True)` once per copy; **any negative delta is NOT applied** — removing a copy is an explicit `mm deck delete <slug>` (the derived count updates automatically), so the checklist emits a per-row warning rather than deleting decks from a spreadsheet edit. Files are `precons-<mode>-checklist.xlsx`, MD uses the `[C:c D:d]` bracket, and both carry the same README banner (`_add_precon_banner_sheet`). `mm deck ls` shows a `decon` marker for torn-down copies. **Scope + value:** `precon-list` defaults to the constructed-deck product a collector tracks — `mtgjson.PRECON_MODERN_TYPES` (~680 rows: Commander/Box/Duel/Planeswalker/Starter/Welcome/Intro/Challenger/Guild/Brawl/Clash/Game Night/Archenemy/Planechase). That frozenset is the single knob for "what counts as a precon"; when a product line is reported missing, add its exact MTGJSON `type` string there. `--type X` narrows to one, `--all-physical` opens to every physical product (~1500 rows, incl. Deck Builder's Toolkit / Sample Deck / Welcome Booster / Shandalar / World Championship). Generation does NOT sync by default (an all-sets catalog can't sync all of Magic), so `usd_total` is best-effort — blank for sets not yet in the local `cards` table; ingest self-syncs each filled precon's sets (via `import_precon`'s sync-before-use), which also covers cross-set cards (e.g. a FIC deck's FIN reprints). Pass `--sync-all` to sync every referenced set (~180 for the default scope) up front so all totals populate in one run — `_build_precon_rows(sync_all=True)` does a pre-pass collecting each deck's `setCode`s, then `sets.unsynced_set_codes()` filters to the not-yet-local ones and `sync()` batches them (≤60 codes/query to stay under Scryfall's URL limit). **Collector's Edition** variants are a premium product the collection doesn't track — excluded via `mtgjson._is_collector_edition` (catches both the modern `… Collector's Edition` twins and the 1993 `Collectors' Edition` box sets) unless `--include-collector`. Digital (`MTGO …`), Jumpstart (its own command), and Secret Lair Drop (the `bulk-add` skill) types are never listed by `precon-list`.

### Database

SQLite at `db/magic_manager.db`, with `-wal`/`-shm` siblings colocated. Snapshots go to `db/bak/`, files displaced by `db restore` go to `db/replaced/`. Schema is created on first connect; subsequent versions add to the `MIGRATIONS` list and bump `CURRENT_VERSION` in `db.py`.

Set the `MAGIC_MANAGER_DB` env var to a file path to redirect the entire DB (used by `scripts/rehearse_migration.py` and any future tests).

V2 fact tables: `cards`, `inventory`, `wishlist_entries`, `decks` (with V10 `source_precon_file_name` + `is_deconstructed` — precon unit counts derive from these), `deck_cards`, `ingest_log`, `set_targets`. (The V7 `precon_ledger` was replaced by those derived counts and dropped in V10.) Pre-V2 used a single conflated `list_rows` table; see `docs/pre-v2-inventory-snapshot.md` for the migration baseline.

### Module map

Inside `src/magic_manager/`:

- `cli.py` — every `typer` command. Long but flat; new commands go here.
- `db.py` — schema, migrations, `connect()` context manager, `transaction(conn=None)` borrow-or-open helper (lets a caller run multiple CRUD writes in one atomic transaction — e.g. `import_precon`), snapshot/restore.
- `sets.py` — set family resolution, sync from Scryfall, master-list/jumpstart-list/precon-list writers, ingest readers + the shared deck-checklist ingest engine (`_apply_deck_checklist`).
- `selectors.py` — the selector DSL parser + materializer.
- `inventory.py`, `wishlist.py`, `decks.py` — V2 fact-table CRUD + value rollups. `decks.py` also holds `import_precon` and the derived `precon_unit_counts[_for]` (built/torn-down copies counted from the `decks` table).
- `intake.py` — scan-loop REPL.
- `parsers.py` — Moxfield-style block parser (used by `import` commands).
- `treatments.py` — derives a treatment string (e.g. `b|ff`, `ext`) from Scryfall card fields. Centralized so missing-set, master-list, and ad-hoc queries all agree on what counts as a "distinct printing".
- `util.py` — dependency-free shared helpers: `cn_sort_key` (canonical collector-number sort, aliased by `selectors._cn_sort_key`) and `fmt_usd`.
- `scryfall.py`, `mtgjson.py` — thin clients; the bash wrappers in `.claude/skills/{scryfall,mtgjson}-search/` are the canonical access path (see hooks below). **Product contents** (which decks/cards ship in a Beginner Box, Bundle, Scene Box, …) come from `sealedProduct[].contents` in the set file — `mtgjson.sealed_products(code)` / `sealed_product_decks(code, name)` — NOT the DeckList `type` field (a deck's `type` is format flavor, orthogonal to which SKU it shipped in; e.g. FDN's Beginner Box decks are typed `Jumpstart`, TLA's `Box Set`). See the `mtgjson-search` skill before answering "what's in product X".
- `exports/` — one module per target (moxfield, manapool, tcgplayer, archidekt, plain, scryfall_json), all with `build(rows) -> str`.

`scripts/` holds one-off utilities: `rehearse_migration.py` (replays migrations on a copy of the DB), `survey_treatment_signature.py` (audits a family's prints when adding `FAMILY_*` rules), `cleanup_queries.py` (prunes `queries/`), `foil_price_diff.py` (ranks a card list by foil-vs-nonfoil price gap via live `/cards/collection` prices), `scene_table.py` (standardized per-scene ownership + live-price completion table, driven by `selectors.FAMILY_SCENES`), `manapool_cart.py` (fetches the live Mana Pool cart — headless login, else bookmarklet paste), `manapool_common.py` (shared cart plumbing: load + mtgjson-uuid→product mapping + overpay buckets — the DRY core imported by both cart tools), `manapool_price_check.py` (grades a cart vs Scryfall/TCG market — thin consumer of `manapool_common`) + `manapool_cart_check.py` (full cart audit: four atomic checks — `dupes` (cart lines that duplicate a printing you're already buying — ×N same finish, or foil+nonfoil of the same art collated, grouped by `scryfall_id`), `owned` (cart lines you already own), `missing` (family gaps missing from the cart), and `overpay`; reuses `magic_manager.missing` for the gaps. Runs `dupes`+`overpay` with **no `--set`** and imputes the family via `sets.resolve` (stderr); `--set` adds the anchor-scoped `owned`+`missing`). See the `price-check` skill, `manapool` mode, and the `cart-check` skill.

## External-API hooks (will block you)

`PreToolUse` hooks in `.claude/settings.json` block direct `curl`/`wget` to `api.scryfall.com` and `mtgjson.com`. Use:

- `.claude/skills/scryfall-search/scryfall.sh` (rate-limited, 24h cache, 429 backoff) — or `uv run mm scryfall <query>`
- `.claude/skills/mtgjson-search/mtgjson.sh` (cached under `$TMPDIR/mtgjson-cache` with `.sha256` sidecars) — or `uv run mm mtgjson …`
- `.claude/skills/manapool-search/manapool.sh` (Mana Pool sanctioned API — catalog/prices; rate-limited, 24h cache, 429 backoff; reads `MANAPOOL_*` from `.env`). The `manapool-guard.sh` hook blocks ad-hoc curl to `manapool.com/api` and `sb-api.manapool.com`; the cart tiers in `scripts/manapool_cart.py` are allowlisted (they handle the short-lived Supabase session JWT correctly — that JWT is held in memory only, never persisted).

The Python clients (`scryfall.py`, `mtgjson.py`) ultimately call these wrappers, so the CLI is always safe.

Secrets live only in the gitignored `.env` at repo root (`MANAPOOL_EMAIL`, `MANAPOOL_ACCESS_TOKEN`, optional `MANAPOOL_PASSWORD` for the tier-3 headless cart fetch). Never commit or log them.

## Conventions

- The user is the only consumer of this codebase; back-compat shims (`INPUT_DIR` alias, `mm input …` typer alias) exist only as long as the user's muscle memory needs them. No need to add new ones for hypothetical future callers.
- Filename conventions encode intent for Finder/cmux (no `_meta` visible there): `<slug>-<slice>-<mode>-checklist.xlsx`, `<code>-jumpstart-checklist.xlsx`, `precons-checklist.xlsx` (global, all-sets), `missing-<code>-checklist-<ts>.xlsx`, `missing-<code>-{manapool,tcgplayer}-<ts>.txt`. Keep them stable — skills and slash commands grep for them.
- `queries/` is for ephemeral artifacts (missing-set XLSX/TXT, `query xlsx` outputs); the `cleanup-queries` skill prunes it. Don't put anything durable there.
- `docs/` is reference, not always implemented — file headers say "Documented but not implemented as of V<N>" when the schema/design exists but the importer doesn't yet.

### Per-set knowledge (`docs/sets/`)

`docs/sets/<anchor>.md` is the durable memory doc for each set-family (LTR, FIN, SPM, TLA, TMT, …). Each follows the shape defined in `docs/sets/_TEMPLATE.md`: family map, treatments, chase variants, scenes/posters, unobtainable rules, PRM destinations, edge cases, code refs, product types. For **cross-family product-type archetypes** (Scene Box, Beginner Box, Jumpstart, Commander/Welcome deck, masterpiece sheet, Bundle, Secret Lair, Collector's Edition) — sourcing, MTGJSON mapping, handling — see `docs/product-types.md`; a per-family doc records only that family's product *specifics* and links there for the definitions. (`docs/product-types.md` explains the archetypes behind `mtgjson.PRECON_MODERN_TYPES`, the constant that drives `precon-list`.)

**Read before answering.** When the user asks a set-specific question or you're working on a set-specific command, `Read` `docs/sets/<anchor>.md` **before** answering. It captures peculiarities Scryfall metadata doesn't (chase variants, scene groupings, family-topology gotchas like MAR being a separately-rooted SPM bonus sheet). If no doc exists yet for the family, suggest running the `characterize-set` skill to bootstrap one.

**Update when you learn something new.** If a session surfaces a new per-set fact — a chase variant we hadn't catalogued, a scene grouping, an unusual `promo_types` behavior, a new PRM destination, a family-topology gotcha — add it to the appropriate section of `docs/sets/<anchor>.md` before ending the session. Keep entries dense and factual (every row of every table should be verifiable via `mm scryfall` or the survey script).

**Code + doc stay in sync.** `docs/sets/<anchor>.md` §8 "Code refs" points at `FAMILY_DUPE_FOIL_PROMO_TYPES` / `FAMILY_UNOBTAINABLE_RULES` entries in `src/magic_manager/selectors.py`. If you add/remove those constants, update the doc's §8 in the same commit.
