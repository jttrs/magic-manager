---
name: generate-jumpstart-checklist
description: Build the pack-level checklist (XLSX or markdown) for one Jumpstart set — one row per sealed Jumpstart pack variant (e.g. ~51 for MSH, ~121 for J25) with a single acquired_qty column the user fills in per pack (copies opened; ingest splits built vs deconstructed). Use whenever the user wants to catalog Jumpstart packs they opened, by set code. Mechanical workflow: invoke `mm set jumpstart-list <code>` and relay the result. Triggers: "jumpstart checklist for j25", "generate a jumpstart checklist for msh", "catalog my jumpstart packs", "checklist of all <set> jumpstart packs", "I opened some Foundations Jumpstart packs".
---

# Generate Jumpstart Checklist

The mechanical wrapper around `mm set jumpstart-list <code>`. It writes a
**per-set, per-pack** checklist — one row per sealed Jumpstart pack variant the set
publishes in MTGJSON — to `checklists/<code>-jumpstart-checklist.xlsx`. Use this when
the user has opened Jumpstart product and wants to ingest whole packs at once.

This is the Jumpstart sibling of [[generate-set-checklist]] (per-card inventory) and
[[generate-precon-checklist]] (precon products). Jumpstart packs are tracked as
**packs**, not individual cards: filling a row builds/records a whole pack.

> **Set code, not name.** The argument is a Jumpstart set code — `j25` (Foundations
> Jumpstart 2025), `msh` (Marvel Super Heroes), `tle` (Avatar Eternal), `jmp`, `j22`,
> etc. The set must publish `type: Jumpstart` decks in MTGJSON — confirm with
> `mm mtgjson decks --set <code>` if unsure.

## Steps

1. Run `uv run mm set jumpstart-list <code>` (add `--format md` or `--force` as the
   request warrants). That's the whole happy path. It syncs the family first (pack
   contents can span the parent set), then writes the checklist.
2. React to the exit code per the shared **[Exit-code contract](../../../docs/checklist-lifecycle.md#exit-code-contract)**
   (0 success / 2 bad-args or no Jumpstart variants / 3 an active checklist already
   exists — use the collision prompt there; don't blindly `--force`).
3. On success, tell the user the file path and that ingest is the next step — via
   `mm set ingest --path <file>` or the [[ingest-new-inventory-list]] flow.

See [checklist-lifecycle.md](../../../docs/checklist-lifecycle.md) for the full
generate → fill → ingest → archive lifecycle and the transient-artifact principle.

## Fill column (Jumpstart-specific)

One row per pack. Columns: `file_name`, `theme`, `color`, `top_card`, `top_card_usd`,
`card_count`, `usd_total`, and a **single** fill column:

| Column | Meaning |
|---|---|
| **`acquired_qty`** | How many copies of that pack you opened. That's all you enter. |

Ingest SPLITS `acquired_qty` deterministically — you never pre-declare states, so you
don't need to know your existing collection:

- **net-new pack** → 1st copy kept *constructed* (creates a `pack:<theme>-<code>`
  recipe + auto-composes one physical copy), any remaining copies *deconstructed*
  (tracked deck rows, cards loose);
- **you already own a built copy** → every acquired copy *deconstructed*.

Every copy becomes a tracked deck row, so built vs deconstructed counts stay derivable
from `mm deck ls`. Markdown form uses an `[A:n]` bracket per line.

**No `--mode`, no `--rarity`/`--only` slicing** — Jumpstart is always additive (opening
packs only ever adds). `usd_total` includes the pack's front/title card price
(value-only; see [[jumpstart-missing]] for the front-card mechanics).

## Flags (rarely needed)

- `--format md` — markdown instead of XLSX; edit the `[A:n]` bracket per row.
- `--out <path>` — redirect output (skips collision detection).
- `--force` — overwrite an existing active checklist (only after the user chooses
  "discard" at the exit-3 prompt).

## Not to be confused with

- [[jumpstart-missing]] — the *shopping list* for Jumpstart packs you DON'T own
  (`mm query missing-jumpstart <code>`). Read-only buy list, not an ingestible checklist.
- [[jumpstart-buildable]] — buy list for the *cards* to make every theme buildable (not whole
  packs); [[jumpstart-reference]] — read-only XLSX identifying pack versions + contents.
- [[generate-set-checklist]] / [[generate-precon-checklist]] — the per-card and
  precon-product checklists. Different artifacts.
- [[ingest-new-inventory-list]] — ingests the filled Jumpstart checklist back into the DB.

## Examples

User: *"generate a jumpstart checklist for j25"* → `uv run mm set jumpstart-list j25`
→ tell them `checklists/j25-jumpstart-checklist.xlsx` (121 pack rows) is ready.

User: *"I opened some Marvel jumpstart packs, let me log them"* →
`uv run mm set jumpstart-list msh` → they fill `acquired_qty` per pack (ingest splits
built vs deconstructed automatically).

User: *"give me the avatar jumpstart list as markdown"* →
`uv run mm set jumpstart-list tle --format md`.
