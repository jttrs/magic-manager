# Checklist lifecycle — shared reference

> Shared reference for the checklist-generating skills: [[generate-set-checklist]]
> (inventory, per-card), [[generate-precon-checklist]] (precon products, global),
> [[generate-jumpstart-checklist]] (Jumpstart packs, per-set). Each of those skills
> wraps one `mm` subcommand and links here for the lifecycle mechanics they all
> share. Command-specific columns, flags, and scope live in the individual skills.

## The lifecycle: generate → fill → ingest → archive

1. **Generate.** A `mm set <cmd>` writes a fillable artifact under `checklists/`
   (XLSX by default, or markdown with `--format md`). The file carries a hidden
   `_meta` sheet recording `kind` (`inventory` / `precon` / `jumpstart`) and, where
   applicable, `mode` — so ingest later knows how to apply it without asking.
2. **Fill.** The user edits the fill columns in Excel/Numbers (XLSX) or any text
   editor / phone (markdown). Each generator documents its own fill columns.
3. **Ingest.** `mm set ingest --path <file>` (or the [[ingest-new-inventory-list]]
   flow, which auto-detects every active checklist's `_meta`) reads the file, writes
   to the DB, and reports what changed. **This is when data actually lands.**
4. **Archive.** Ingest moves the file to `checklists/processed/<name>-<timestamp>.xlsx`
   (immutable) and appends a row to `ingest_log`. Files are SHA-256-fingerprinted;
   re-ingesting the same file is refused without `--force`.

**The checklist is a transient editing artifact, not a source of truth — the DB is.**
Tell the user to ingest when they're done editing; nothing is recorded until then.

There can be only **one active checklist per slug+slice+format at a time** — a
collision exits with code **3** (`EXIT_UNPROCESSED_INTAKE`).

## Exit-code contract

Every checklist generator returns the same three exit codes. Branch on them:

- **0 — success.** Tell the user the file path and the next step (fill the columns,
  then ingest). Done.
- **2 — bad arguments / no match.** Surface the error verbatim and ask for
  clarification (bad `--format`/`--mode`, no Scryfall/MTGJSON match, an empty slice).
- **3 — `EXIT_UNPROCESSED_INTAKE`.** An unprocessed active checklist already exists
  at the target path. Do NOT pass `--force` without asking — un-ingested edits would
  be lost. Surface the CLI's readout, then use `AskUserQuestion` (template below).

### Exit-3 collision prompt (AskUserQuestion)

Always the same two options (swap in the concrete command/name):

> **An unprocessed checklist already exists for `<name>`. What should I do?**
> - **Ingest the existing file first (Recommended)** — run the ingest command to save
>   the filled-in quantities, then regenerate a fresh checklist.
> - **Discard the partial edits and regenerate** — re-run with `--force`. Any
>   quantities filled in but not yet ingested will be lost.

## Modes — `add` vs `modify`

Generators that support `--mode` encode it in both the filename and `_meta.mode`;
ingest auto-detects it. (Jumpstart has no `--mode` — it is always additive.)

| `--mode` | Cells at generation | Ingest semantics | When to use |
|---|---|---|---|
| **`add`** (default) | **Blank** | **Additive** — entered counts sum into the DB; blanks/0s no-op. Only ever increases. | New acquisitions (a pack opened, a precon built, a trade-in). Safe — cannot remove or zero anything. |
| **`modify`** | **Prefilled** from current state | **Replace, signed per-row** — each row is SET to its cell value (a signed change vs current). Rows left untouched are not wiped. | Correcting/reviewing existing records (sold a card, miscounted, re-auditing). |

**Default is `add`** for safety. Recommend `modify` only when the user's phrasing
implies correction/review over augmentation ("I sold some", "re-audit", "what do I
already have"). Each generator's SKILL.md notes any command-specific `modify` nuance
(e.g. precon `modify` won't apply a *lowered* count; it points at `mm deck delete`).

### Deck checklists (precon + jumpstart) — `add` mode is a single `acquired_qty`

For **precon and jumpstart** checklists, `add` mode does NOT ask you to pre-declare
built-vs-deconstructed. It has ONE fill column, **`acquired_qty`** (`[A:n]` in
markdown) = how many copies of that product you acquired. Ingest SPLITS it
deterministically, so you never need to know your prior collection at fill time:

- **card-pool products** (Starter Collection, Scene Box) → all copies → `pool`;
- **buildable, net-new** → 1st copy kept `built` (recipe + auto-composed), the rest
  `deconstructed`;
- **buildable, you already own a built copy** → every acquired copy `deconstructed`.

Every copy — including jumpstart — becomes a tracked `decks` row (distinct `-2`/`-3`
slugs), so built vs deconstructed counts stay derivable from the decks table. There
is no silent "already exists" skip: a redundant copy becomes a tracked deconstructed
row. Precon `modify` mode keeps the explicit three-column layout
(`constructed_qty`/`deconstructed_qty`/`pool_qty`, `[C:c D:d P:p]`) for correcting
absolute per-state counts.

Both flavors carry a colored **README banner sheet** (green `add` / red `modify`) in
the XLSX, and the same as a blockquote under the H1 in markdown.

## Intake surfaces

The same DB is fed by three interchangeable surfaces — exports/queries are
surface-agnostic:

| Surface | When to use | How |
|---|---|---|
| **XLSX** (default) | Sit-down cataloging in a spreadsheet app | `mm set <cmd>` |
| **Markdown** (`--format md`) | Phone / plain-text editor / git-diffable | `mm set <cmd> --format md` |
| **Scan loop (REPL)** | Rapid manual entry with a stack of cards in hand | `mm intake "<name>"` (inventory only) |

## Common caveats

- Re-running a generator is safe **after** the previous checklist has been ingested
  (DB-backed cells re-prefill). If you see exit 3, resolve it via the prompt above —
  don't blindly `--force`.
- `queries/` is for ephemeral shopping-list artifacts (missing checklists); `checklists/`
  is for ingestible inventory/precon/jumpstart checklists. Don't conflate them.
- Stale lock state: if a wrapper died mid-run you may see `lock timeout`. Clear with
  `rm -rf "${TMPDIR}scryfall-state/lock"` and retry.
