---
name: generate-set-list
description: Build the inventory intake spreadsheet (XLSX) for a Magic the Gathering release family — every printing across the parent set + commander + masterpiece + promos, with current Scryfall prices and two quantity columns the user fills in by going through their physically-sorted boxes. Use this whenever the user wants to start (or resume) cataloging a set. Mechanical workflow: invoke `mm set master-list <name>` and react only to the structured exit codes; no judgment about which sibling sets to include.
---

# Generate Set List

The mechanical wrapper around `mm set master-list`. The user names a release ("Final Fantasy", "Outlaws of Thunder Junction", `otj`, `fin`); the CLI computes the family from Scryfall's `parent_set_code` graph filtered to `set_type IN (expansion, commander, masterpiece, promo)`, syncs prices, and writes `input/<slug>-master.xlsx` pre-populated from any existing inventory.

**You make zero judgment calls about scope.** The recommended bundle is codified in the CLI; do not list sibling sets and ask which to include. If the user wants tokens or memorabilia, they will say so explicitly — translate that to `--include token,memorabilia`.

## Steps

1. Run `uv run mm set master-list "<name-or-code>"` from the repo root. That's the whole happy path.
2. Look at the exit code:
   - **0**: success. Tell the user the file path and the next step (`mm set ingest "<name>"` when they've filled in quantities). Done.
   - **2**: bad arguments / no Scryfall match. Surface the error verbatim and ask for clarification.
   - **3**: an unprocessed intake XLSX already exists. The CLI prints a readout of the current `set:<anchor>` state (rows owned, total value, top-value cards). Show that readout to the user and ask which path forward they want via `AskUserQuestion`.
3. If they chose "ingest first": run `uv run mm set ingest "<name>"`, surface the result, then re-run `mm set master-list "<name>"` to start a fresh intake doc.
4. If they chose "discard partial work": re-run `uv run mm set master-list "<name>" --force` and warn that any XLSX-only edits (those not yet ingested) are gone.

## Slicing — generating partial intake docs

The user often catalogs piecemeal: "just the rares from FF", "just the `fic` cards", "this booster I just opened". For these cases, slice at generate-time so the resulting XLSX only covers the intended scope. Two flags compose:

- `--rarity <r>` (repeatable, comma-OK): emit only the named rarities. Values: `mythic`, `rare`, `uncommon`, `common`, `bonus`, `special`. Filename gains a rarity suffix (`<slug>-rare.xlsx`, `<slug>-rare+mythic.xlsx`).
- `--only <codes>`: restrict to specific set codes within the family. Filename gains a code suffix (`<slug>-fic.xlsx`).

Both compose: `--only fic --rarity rare` → `<slug>-fic-rare.xlsx`.

When the user says "just the rares", run `mm set master-list "<name>" --rarity rare`. When they say "just the commander deck", run `mm set master-list "<name>" --only fic` (after confirming the family has the code they meant via `mm set list-related`).

Each slice can be in flight independently — collision detection is per-filename, so you can have `<slug>-rare.xlsx` and `<slug>-uncommon.xlsx` both pending at the same time.

The XLSX carries a hidden `_meta` sheet recording the slice, so ingest knows which (set, rarity) pairs are in-partition. The user never sees `_meta`.

## Other flags (rarely needed)

- `--include token,memorabilia` — opt extra `set_type`s into the family. Use only when the user explicitly asks for tokens, art series, or scene boxes.
- `--out <path>` — redirect output to a non-default path (skips collision detection). Almost never the right answer.
- `--force` — overwrite an existing intake XLSX. Only after the user has explicitly chosen "discard partial work" via the exit-3 prompt.

## Exit-3 prompt template

When the CLI exits 3, the stderr already contains the readout. After surfacing it, use `AskUserQuestion` with these two options (always the same two):

> **An unprocessed intake XLSX exists for `<set-name>`. What should I do?**
> - **Ingest the existing XLSX first (Recommended)** — run `mm set ingest "<set-name>"` to save your filled-in quantities, then start a fresh intake doc.
> - **Discard the partial XLSX edits and regenerate** — run `mm set master-list "<set-name>" --force`. Any quantities filled in but not yet ingested will be lost.

## What the user sees

| Path | Filename | Lifecycle |
|---|---|---|
| Active intake doc (one per family at a time) | `input/<slug>-master.xlsx` | Created by `master-list`. User edits in Excel/Numbers. |
| Archived intake docs | `input/processed/<slug>-master-<YYYY-MM-DD-HHMMSS>.xlsx` | Created by `ingest` after the data lands in the DB. Immutable. |

The XLSX columns: `set`, `collector_number`, `name`, `rarity`, `mana_value`, `usd`, `usd_foil`, `qty_normal`, `qty_foil`. The two `qty_*` columns are tinted yellow, validated as non-negative integers, and pre-populated from `set:<anchor>` whenever the user already owns cards from previous ingest cycles. Rows are sorted by rarity bucket (mythic → rare → uncommon → common → bonus → special) then collector number to match the user's physical box order.

For Universes Beyond reskin printings (FCA, MAR, PZA, etc.) the `name` cell renders as `<flavor_name> / <oracle_name>` so the user can find the row by either the printed name (what they see on the card) or the canonical Magic name. Non-reskin rows show just the oracle name.

> **Upgrading from V1.2:** if your DB was populated before V1.3, the `flavor_name`/`is_reskin` columns will be NULL/0 on existing card rows. Run `uv run mm set sync <name>` once before the next `master-list` to backfill — the sync upserts every printing and the next XLSX will display merged names correctly.

## Examples

User: *"generate an inventory excel for the Final Fantasy sets."*

```bash
uv run mm set master-list "Final Fantasy"
```

If exit 0: tell them `input/final-fantasy-master.xlsx` is ready and `mm set ingest "Final Fantasy"` is the next command.
If exit 3: surface the readout, show the AskUserQuestion above.

User: *"give me a master list for OTJ but include the breaking news cards too."*

`pbig`, `big`, `otp` are already in the default family for `otj` (they're `set_type=expansion`/`promo`). The user's request is already covered by the default. Run:

```bash
uv run mm set master-list otj
```

User: *"include the FF tokens this time."*

```bash
uv run mm set master-list "Final Fantasy" --include token
```

## Caveats

- The XLSX is a **transient intake document**, not a source of truth. The DB is the source of truth. Tell the user to run `mm set ingest "<name>"` when they're done editing — that's when the data actually lands.
- Re-running `master-list` is safe (DB-backed cells re-pre-populate), but only after the previous intake has been ingested. If you see exit 3, do NOT pass `--force` without confirming with the user — XLSX-only edits will be silently discarded.
- A full Final Fantasy family sync touches Scryfall ~1,244 cards over 8 paginated calls (~4–6 seconds with the 500ms wrapper rate limit). OTJ is similar.
- Stale lock state: if `scryfall.sh` died mid-run, you may see `lock timeout`. Clear with `rm -rf "${TMPDIR}scryfall-state/lock"` and retry.
