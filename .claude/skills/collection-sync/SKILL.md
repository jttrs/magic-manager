---
name: collection-sync
description: Import or export your whole COLLECTION (inventory) to/from an external service via CSV, with a mandatory diff-review-and-approve step. Import reads a service's exported collection CSV into local inventory under one of three modes (add / modify / overwrite); export renders your inventory back out as that service's CSV. Always relays to `mm collection import|export|diff`, which writes a review artifact (XLSX + JSON) and is DRY-RUN by default — nothing hits the DB until you approve with --apply. Supported services: manabox, moxfield, archidekt, mtggoldfish (each a declarative config block; manabox/archidekt/mtggoldfish carry a Scryfall ID for exact matching, moxfield resolves by set+collector-number, mtggoldfish is low-confidence for id-less promos). Scryfall has no collection. Triggers: "import my manabox/moxfield/archidekt/mtggoldfish collection", "sync my collection from <service> CSV", "load my collection export into inventory", "export my collection to <service>", "diff my collection CSV against what I own", "bulk-add my whole collection from a CSV".
---

# collection-sync

Bridges an external **collection** (not a deck) and the local `inventory` table.
Decks have their own skill ([[import-deck]]); this one moves the whole owned
collection in or out, as a CSV, with a review gate because a collection is large
and a bad apply is expensive to undo.

Thin relay per the repo rule: ALL logic lives in `scripts/collection_sync.py` →
`magic_manager.collection_sync`. This skill only picks the command + flags and
relays the output.

## When to use

- "Import my ManaBox collection" / "load my collection export into inventory"
- "Sync my collection from a `<service>` CSV"
- "Export my collection to `<service>`" / "render my inventory as a `<service>` CSV"
- "Diff my collection CSV against what I own" (read-only, no write)

**Don't** use for:
- A single DECK from a URL → [[import-deck]] (`mm deck import-deck`).
- A short explicit list of specific cards → [[add-cards]] / [[bulk-add]].
- A filled-in inventory CHECKLIST (XLSX/MD from a `master-list`) → [[import-list]] /
  `mm set ingest`. (Collection-sync is for a *service's own* CSV export, not our
  generated checklists.)

## The canonical recipe

```bash
# 1. DRY-RUN (default): review the diff, write the XLSX/JSON artifact, no DB write.
uv run mm collection import manabox <path-to-collection.csv> --mode add

# 2. Review the printed diff (added / changed / removed) + the "not resolved" list.

# 3. APPLY once it looks right:
uv run mm collection import manabox <path-to-collection.csv> --mode add --apply
```

The command reads the CSV, resolves each row against Scryfall (ManaBox rows carry
a Scryfall ID → exact), diffs it against the current inventory, and writes a
review artifact under `output/collection-sync/diffs/`. `--apply` recomputes the
diff and writes to inventory through the V19 provenance ledger (method
`collection-import`), so `inventory.quantity == SUM(delta)` always holds.

## Modes (import) — map 1:1 onto the inventory-checklist semantics

| `--mode` | Semantic | Use when |
|---|---|---|
| `add` (default) | **Additive** — each incoming qty is SUMMED onto any existing row. | Adding newly-acquired cards; the CSV is a batch of new stuff. |
| `modify` | **Replace** — each incoming row is SET to its CSV qty; rows ABSENT from the CSV are left untouched. | Correcting counts for the cards in the file, without touching the rest. |
| `overwrite` | **Full audit** — `modify` PLUS every inventory row absent from the CSV is zeroed. | The CSV is the authoritative full snapshot of the collection. |

> ⚠️ `overwrite` deletes inventory rows not present in the CSV. Always review the
> dry-run **removed** list first.

## Export

```bash
uv run mm collection export manabox            # dry-run diff vs empty (or --against)
uv run mm collection export manabox --against <service-export.csv>   # diff vs real state
uv run mm collection export manabox --apply    # emit full reconciled CSV to output/collection-sync/exports/
uv run mm collection export manabox --against <csv> --mode delta --apply   # emit ONLY what the service is missing/wrong
```

Export **never writes the DB** — it renders your inventory as the service's CSV
(finish mapped back, condition defaulted). `--against <csv>` supplies the service's
current state so the diff shows the true delta; without it, the whole inventory
reads as "added".

**`--mode` shapes the emitted CSV:**
- `full` (default): the entire inventory, rendered in the service's format.
- `delta`: only the rows the service is **missing or has at the wrong count**
  (the diff's added + changed) — the "just what to add/fix" CSV. **Requires
  `--against`.** `removed` rows (cards the service has but you don't) are shown in
  the review but NOT emitted — a CSV can't express a deletion; that's a manual
  service-side action.

## Flags

| Flag | Effect |
|---|---|
| `--mode add\|modify\|overwrite` | (import) semantic (see table). Default `add`. |
| `--mode full\|delta` | (export) full inventory, or only added+changed vs `--against`. Default `full`; `delta` requires `--against`. |
| `--apply` | Write (import) / emit the CSV (export). Default is a dry-run review. |
| `--force` | Re-import an identical file (bypasses the sha256 dedup that refuses a repeat import). |
| `--against <csv>` | (export) The landing-state CSV to diff against. |
| `--direction import\|export` | (`diff` subcommand) Which way to diff. |
| `--json` | Emit JSON instead of the markdown review. |

## Notes

- **Services + fidelity** (verified against real exports):
  | Service | Identity | Confidence | Notes |
  |---|---|---|---|
  | `manabox` | Scryfall ID | high | mobile app; CSV-only |
  | `archidekt` | Scryfall ID | high | both export variants (default / all-fields) work |
  | `moxfield` | set + collector number | high | id-less; see binder gotcha below |
  | `mtggoldfish` | Scryfall ID, else (set,cn) | **low** | some promos (`PRM-*` pseudo-sets) have no id AND a non-Scryfall set code → reported not_found |
  Scryfall has no collection feature (excluded).
- **Moxfield binder gotcha:** Moxfield won't let you move an existing collection card
  into a binder — you re-add it net-new, and it then exports as a card in BOTH the main
  collection and the binder (two byte-identical rows). collection-sync SUMS same-printing
  rows, so such a card shows as qty 2 in the diff. **Review the diff before --apply** and
  correct if it's really one physical copy.
- **MTGGoldfish set remap:** `config/collection_formats.toml` has an (initially empty)
  `[mtggoldfish.set_remap]` for service→Scryfall set-code fixes. Only code-level
  mismatches are fixable; `PRM-*` promos with MTGGoldfish-internal collector numbers
  can't be remapped and stay not_found.
- **Condition / language / purchase price** are passthrough-only: carried in the CSV
  adapter but NOT stored in the DB (a future dimension). Export defaults condition to
  `near_mint`.
- **Dedup:** importing the identical file twice is refused (exit 3) unless `--force`.
- A row that can't be resolved against Scryfall is REPORTED (never silently dropped)
  and skipped from the apply.
- Format config is declarative in `config/collection_formats.toml` — adding a service
  is config, not code.
