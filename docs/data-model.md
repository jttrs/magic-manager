# Data model — how magic-manager conforms to data-engineering standards

How the SQLite store is structured, and how it deliberately borrows the
disciplines of modern analytics engineering (the "dbt philosophy") **without**
running dbt-the-software. This is the durable reference for *why the schema is
shaped the way it is* — read it when adding a table, a migration, or a derived
value, and update it when the shape changes.

**See also:** [`CLAUDE.md`](../CLAUDE.md) (the architecture overview + core
engineering rules), [`src/magic_manager/db.py`](../src/magic_manager/db.py) (the
schema + migration list this doc describes).

---

## 1. Why the dbt *philosophy* and not dbt *the tool*

The user asked whether we should adopt dbt. The honest answer, after research:
**adopt the philosophy as documentation + discipline; don't install the software.**

dbt is an **ELT transformation engine**: it takes *immutable raw source data*
already loaded into a warehouse and builds *derived analytical models* (views /
tables) from it via `SELECT` statements, tracking lineage through `ref()` /
`source()`. It does **not** manage transactional writes — the `INSERT` / `UPDATE`
/ `DELETE` of application state ("add a card to inventory", "pledge a card to a
deck", "finalize a deck version"). That transactional mutation is *100% of what
this repo does*: `magic-manager` is a local-first OLTP application over a single
SQLite file, not an analytics warehouse.

Two further facts seal it:
- **No maintained SQLite adapter for modern dbt.** dbt's supported local engine
  is DuckDB (`dbt-duckdb`); `dbt-sqlite` is unmaintained. Running dbt here would
  mean exporting snapshots to DuckDB and running analytics *alongside* — not
  *replacing* — the Python/CLI transactional core. Pure friction, no payoff for a
  single-user tool.
- **The parts of dbt that DO port are free.** Its naming conventions,
  constraints-as-tests, layered mental model, lineage documentation, and — most
  importantly — its **Slowly Changing Dimension Type 2** pattern (which is exactly
  how deck versioning is modeled, §3) are *disciplines*, not dependencies. We get
  them by writing them down and enforcing them with the existing pytest suite.

So: this doc is our `schema.yml` + "how we structure our project" guide, in prose.
The pytest suite (`tests/`) is our test layer. Git + PR review is our CI.

**Sources:** dbt "How we structure our dbt projects" and style guide
(`docs.getdbt.com/best-practices/how-we-structure/*`, `.../how-we-style/*`), dbt
data tests (`docs.getdbt.com/docs/build/data-tests`), dbt snapshots / SCD-2
(`docs.getdbt.com/docs/build/snapshots`), Kimball SCD techniques
(`kimballgroup.com/2008/08/slowly-changing-dimensions/`).

---

## 2. Source → staging → mart layering (the dbt mental model, mapped)

dbt layers data **source → staging → intermediate → marts**. Our tables map onto
that lens even though nothing physically materializes a "staging view":

| dbt layer | Meaning | In this repo |
| --- | --- | --- |
| **Source** | External, authoritative, re-fetchable raw data | Scryfall (`scryfall.py`), MTGJSON (`mtgjson.py`), Mana Pool / TCG / eBay market wrappers, Commander Spellbook (`commander_spellbook.py`). None of it lives in the DB in raw form. |
| **Staging transform** | 1:1 rename/recast/light-clean of a source row | `db._card_row()` — projects a raw Scryfall card JSON into our `cards` row shape (renames `id`→`scryfall_id`, JSON-encodes list fields, derives `is_token`/`is_reskin`). This is the one staging transform; it does no joins/aggregation. |
| **Mart (dimension)** | A described business entity | `cards` (the printing catalog — re-derivable), `decks` (the durable deck identity), `set_targets` (tracked families). |
| **Mart (fact)** | Measurements at a declared grain | `inventory` (owned copies per printing×finish), `deck_cards` (composition per **version**×printing×board×finish, §3), `deck_assignments` (physical pledges per deck×printing×finish), `wishlist_entries`. |
| **Derived / "analytical" models** | Computed on read, never stored | `deck_value`, `precon_unit_counts`, `missing.missing_printings`, the `legality`/`brackets` reports. These are our "models" — Python functions that `SELECT`-and-compute rather than persisted views. See §7. |

**What we deliberately DON'T adopt** (warehouse-only overkill): physical
staging/intermediate/marts *materialization tiers*, view/incremental
materializations, hashed surrogate keys (SQLite `INTEGER PRIMARY KEY` rowids are
simpler and faster), and `fct_`/`dim_` table-name prefixing (conceptual value
only — our names are plain English).

**Precious vs re-derivable** (this repo's own long-standing split, and the
practical version of "source vs mart"): re-derivable tables (`cards`,
`front_cards`, `schema_version`, `settings`) can be rebuilt by re-running a sync;
precious tables (`inventory`, `decks`/`deck_versions`/`deck_cards`,
`deck_assignments`, `ingest_log`, `set_targets`, `earmarked_products`) hold data
the user typed in and can't be reconstructed. Migrations treat the two
differently — see [`db.py`](../src/magic_manager/db.py) "migration-authoring
convention".

---

## 3. Deck versioning is Slowly Changing Dimension Type 2

The versioning feature is a textbook **SCD Type 2** — the Kimball/dbt-snapshots
pattern for "keep every historical version of an entity's composition and diff
them." This is the single most direct answer to the user's dbt question: the
right *standard* for versioning a changing entity already existed, and we adopted
it by name.

### The three tables and how composition is version-scoped

```
decks  (durable dimension — one row per logical deck, stable slug forever)
  │  deck_id (PK), slug (UNIQUE natural key), name, format, precon_state,
  │  current_version_id ─────────────┐   ← fast pointer to the live version
  │                                   │
  └─< deck_versions  (SCD-2 history — one row per version of a deck)
        │  deck_version_id (PK, per-version surrogate key)
        │  deck_id (FK), version_number, status ('brew'|'tuned'),
        │  is_current (0/1), effective_from, effective_to (NULL = current),
        │  change_reason, legality_report, suggested_bracket, bracket_detail
        │                                   ▲
        └─< deck_cards  (fact — composition of ONE version)
              deck_version_id (FK) ─────────┘
              scryfall_id, board, finish, count
              PK (deck_version_id, scryfall_id, board, finish)
```

- **Durable key vs surrogate key.** `decks.slug` is the durable/natural key (the
  deck's identity across all its versions); `deck_versions.deck_version_id` is the
  per-version surrogate key. This dual-key shape is exactly what SCD-2 requires.
- **Effective-dating.** Each version carries `effective_from` / `effective_to`.
  Cutting a new version stamps the prior version's `effective_to` (contiguous, no
  gaps) and clears its `is_current`. Exactly one version per deck has
  `is_current = 1` and `effective_to IS NULL` — the invariant maintained in one
  place (`decks._insert_version`) and checked by `mm audit deck-inventory`.
- **Current-version resolution.** Every read of "the deck's cards" resolves
  through the `decks.current_version_id` pointer (an indexed PK equality), not a
  `WHERE is_current = 1` filter — cheaper on every read path. The helpers
  `decks._current_version_id[_for_slug]` DRY that hop; consumers (`deck_show`, the
  `deck:` selector, `deck_assign_batch`'s recipe cap, `deck find`, `audit`) never
  hand-write the join.
- **Immutable snapshots.** Because `deck_cards` hangs off `deck_version_id`,
  editing a new version never mutates a prior one — `deck_show(slug,
  version_id=…)` renders any historical snapshot, and `version_diff` compares two.
- **dbt-snapshot column parallel.** Our `effective_from`/`effective_to`/
  `is_current`/`version_number` are the hand-rolled equivalents of dbt's
  `dbt_valid_from`/`dbt_valid_to`/`dbt_scd_id` snapshot meta-columns.

### Reconciliation decision: physical pledging stays deck-level

Composition is version-scoped, but **physical fulfillment is not.** `deck_assignments`
(the "pledge loose inventory to this deck" table) and `decks.precon_state`
(built/deconstructed) stay attached to the **deck**, and reconcile implicitly
against the deck's *current* version's recipe. There is deliberately **no
per-copy-per-version pledge table** — a single-user collector doesn't build
"version 2 specifically"; they build the deck as it currently is. This keeps the
V5 recipe/fulfillment split intact and the change surface small.

---

## 4. The three orthogonal deck axes

The feature added three independent dimensions to a deck. Keeping them orthogonal
(rather than one overloaded status enum) is what makes each cheap to reason about:

| Axis | Values | Lives on | Meaning |
| --- | --- | --- | --- |
| **Composition lifecycle** | `brew` → `tuned` | `deck_versions.status` (per **version**) | Confidence the list is complete. `brew` = in progress; `tuned` = finalized (legality/bracket recorded). |
| **Physical state** | `built` / `deconstructed` | `decks.precon_state` (per **deck**) | Are the actual cards sleeved up, or loose? (Generalized from the precon-only V11 column to all decks.) |
| **Versioning** | v1, v2, … | `deck_versions` rows (SCD-2) | Immutable history of the composition over time. |

Terminology dodges MTG collisions on purpose: `brew`/`tuned` avoids "draft" (the
booster-draft *format*) and "constructed" (the *format category*); `built`/
`deconstructed` is the repo's existing precon vocabulary, collision-free.

---

## 5. Naming conventions adopted (dbt style guide)

Applied to all new schema (and the target for future tables):

- **`snake_case`** everywhere; plain business words, no abbreviations.
- **Surrogate primary keys** are `<entity>_id` (`deck_id`, `deck_version_id`);
  foreign keys reuse the referenced PK's name.
- **Booleans** are `is_`/`has_` prefixed and stored as SQLite `INTEGER` 0/1
  (`is_token`, `is_promo`, `is_reskin`).
- **Timestamps** are `<event>_at`, ISO-8601 UTC `TEXT` (`created_at`,
  `updated_at`, `effective_from`, `effective_to`, `assigned_at`,
  `prices_updated_at`).
- **JSON-typed columns** are `TEXT` holding a JSON document (`colors`,
  `color_identity`, `legalities`, `keywords`, `legality_report`, `bracket_detail`).
  Callers decode at the boundary (e.g. `decks._materialize_for_checks`).

**Documented exception:** `cards.game_changer` is a bare boolean-ish name (not
`is_game_changer`). This is deliberate — it mirrors Scryfall's own field name 1:1
so `db._card_row`'s projection stays a dumb copy (`c.get("game_changer")`), and so
a reader cross-referencing Scryfall docs finds the same identifier. Convention
violations are allowed when they buy source-fidelity; they're recorded here rather
than hidden.

---

## 6. Constraints as data contracts (dbt's four tests, enforced at write time)

dbt's generic tests (`unique`, `not_null`, `accepted_values`, `relationships`) are
*read-time assertions on a warehouse*. Our SQLite equivalents are **write-time
constraints** — stronger, because a violating row can't even be inserted (with
`PRAGMA foreign_keys = ON`, which `db.connect()` always sets). Each is guarded by a
pytest that would fail if the constraint were dropped:

| dbt test | Our mechanism | Example | Guarding test(s) |
| --- | --- | --- | --- |
| `unique` | `PRIMARY KEY` / `UNIQUE` | `decks.slug UNIQUE`; `deck_versions UNIQUE(deck_id, version_number)`; `deck_cards` PK `(deck_version_id, scryfall_id, board, finish)` | `test_deck_versions.py` |
| `not_null` | `NOT NULL` | `deck_versions.status`, `.effective_from`, `.is_current` | `test_deck_versions.py` |
| `accepted_values` | `CHECK (col IN (…))` | `deck_versions.status IN ('brew','tuned')`; `deck_cards.board IN (…,'token')`; `finish IN ('nonfoil','foil','either')` | `test_deck_versions.py`, `test_tokens.py` |
| `relationships` | `FOREIGN KEY … REFERENCES` | `deck_versions.deck_id → decks`; `deck_cards.deck_version_id → deck_versions`; `…scryfall_id → cards` | `test_migration_v16_18.py` (`PRAGMA foreign_key_check`) |

Cross-table invariants a single `CHECK` can't express (SQLite `CHECK` can't span
tables) are enforced in Python inside the transaction and, where relevant, checked
by `mm audit deck-inventory`:
- **Exactly one current version per deck** (`is_current = 1`, `effective_to IS
  NULL`) — audit's version-integrity check.
- **Pledges ≤ inventory** and **pledges ≤ recipe** — `deck_assign_batch` raises
  `AssignmentOverflow`; audit reports over-assignment.
- **Orphan decks** (current version has zero `deck_cards`) — audit reports/`--fix`.

---

## 7. Legality & brackets are derived, warn-only metadata

`legality.py` and `brackets.py` are "analytical models" in the dbt sense —
computed from source-conformed card data, never authoritative app state:

- **Legality** (`legality.validate`) is a pure function of a materialized card
  list + a format. It reuses fields synced onto `cards` (V16: `legalities`,
  `keywords`; plus existing `type_line`, `color_identity`, `oracle_id`) — no new
  source. Finalizing a version records the report on `deck_versions.legality_report`
  but **never blocks** (warn-only): the user is the authority.
- **Brackets** (`brackets.suggest`) computes a *suggested floor* for Commander
  decks from `cards.game_changer` (deterministic), curated mass-land-denial /
  extra-turn name sets, and — when reachable — the Commander Spellbook API
  (`commander_spellbook.py`, behind the wrapper+guard hook, monkeypatched offline
  in tests) for two-card combos. It is explicitly a *suggestion + the gating
  cards*, never an authoritative label — matching WotC's own player-declared
  bracket model.
- **Freshness / lineage honesty.** Cards synced before V16 read `legalities =
  NULL` / `game_changer = 0`. Both modules emit a `stale_data` note rather than
  silently under-reporting — the read equivalent of dbt's source-freshness check.
  Recovery is `mm set sync`.

DRY lineage, stated once so it can't drift: `deck_value` ← `deck_show` (current
version, tokens excluded) ← `deck_cards` × `cards`. `precon_unit_counts` ←
`decks.precon_state` GROUP BY. Legality/bracket ← `_materialize_for_checks`
(current version) ← `deck_cards` × `cards`. `missing_printings` ← `set_targets` ∪
`cards` − `inventory` (tokens excluded).

---

## 8. Migration authoring + snapshot-before-migrate

Schema evolves via the imperative `MIGRATIONS` list + `CURRENT_VERSION` in
[`db.py`](../src/magic_manager/db.py) — this is our alternative to dbt's
model-diffing (dbt doesn't manage OLTP schema migrations at all). The full
convention lives in the `db.py` comment block; the essentials:

- **Always-safe ops** (`CREATE TABLE`, `ALTER TABLE ADD COLUMN`, `CREATE INDEX`,
  seed `INSERT`) go straight in a `SCHEMA_VN` string.
- **PK / CHECK / column-drop changes** need the **copy-rebuild dance** (create
  `table__new`, `INSERT … SELECT`, `DROP`, `RENAME`, recreate indexes). V14 used
  it to widen the `board` CHECK; **V18** used it to re-home `deck_cards` from
  `deck_id` to `deck_version_id`.
- **Python post-migration hooks** (`_run_vN_python_migration`) handle what SQL
  can't — e.g. **V17**'s hook back-creates a v1 `tuned` version for every existing
  deck and points `current_version_id` at it, so **V17 must run before V18**
  (V18's `INSERT … SELECT` joins those v1 versions). List order + the
  `UNIQUE(deck_id, version_number)` constraint guarantee that ordering.
- **Snapshot-before-migrate.** `_ensure_schema` auto-writes a `pre-vN` snapshot to
  `db/bak/` before applying anything. Don't bypass it; it's the recovery path.

The deck-versioning feature spanned **V16** (cards legality/bracket columns),
**V17** (`deck_versions` + `current_version_id` + backfill hook), and **V18**
(version-scope `deck_cards`). Note: DB *schema* versions (V16–V18) are unrelated
to *deck* versions (SCD-2 `deck_versions` rows) — orthogonal uses of the word.
