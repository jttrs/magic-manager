---
name: trueup-pools
description: >-
  True up the deconstructed-precon collection by attributing LOOSE cards to the
  products they actually came from — scene boxes, precon/jumpstart decks, card
  pools, and complete Secret Lair drops — and re-labelling their provenance in
  the V19 ledger (moving copies out of the `unattributed-backfill` bucket into a
  real `precon` event). Only claims a product when its FULL recipe is present in
  free inventory; reports conflicts instead of guessing; dry-run by default.
  Triggers: "true up my precons", "which of my loose cards are actually scene
  boxes / jumpstart packs / drops", "attribute my unknown cards", "reconcile the
  unattributed bucket", "what products are sitting loose in my collection".
---

# trueup-pools

Thin relay over the deterministic `scripts/trueup_pools.py` (invoked as
`mm deck trueup`). The script does ALL logic (enumeration, recipe matching,
conflict detection, ledger re-attribution); this skill just picks the mode and
relays the output.

## When to use

The V19 provenance backfill left some owned copies in the `unattributed-backfill`
bucket (surfaced by `mm audit provenance`). Many are real **products never
registered as tracked deck rows** — a scene box's cards sitting loose, a
jumpstart pack's `tle` half, a Secret Lair drop bought whole. This tool finds
them in the user's FREE (unpledged) inventory and, on `--apply`, registers each
as a `deconstructed` deck row (so precon unit counts become correct — no
inventory double-count) AND moves its copies into a `precon` ledger event.

**Don't** use for:
- Registering a precon you kept ASSEMBLED from loose singles → [[construct-from-loose]] (built + pledged).
- Ingesting a newly-bought precon's cards → [[import-precon]] / [[add-precon]].
- Just checking provenance numbers → `mm audit provenance` (read-only).

## The recipe

```bash
uv run mm deck trueup                      # dry-run, --from-unattributed (default scope)
uv run mm deck trueup tla                  # scope to one set/family or product-name substring
uv run mm deck trueup --all                # every set with loose cards (full sweep)
uv run mm deck trueup --apply              # WRITE the ready products (default is dry-run)
uv run mm deck trueup --pick SceneBox_TLA,Battalion_MSH --apply   # resolve conflicts, then write
uv run mm deck trueup --sld-partial-threshold 0.8   # widen the near-complete SLD flag
uv run mm deck trueup --json               # machine-readable result
```

## Behavior contract (relay these faithfully)

- **Dry-run by default.** Nothing is written unless `--apply` is passed. Always
  show the user the dry-run preview first and let them confirm before `--apply`.
- **Three report sections:**
  - **READY** — products whose FULL recipe is present in uncontested free
    inventory; these get registered on `--apply`.
  - **CONFLICTS** — products contending for the same loose card when copies are
    insufficient for all. NOT written. The user resolves by re-running with
    `--pick <fileName>,...` to choose which product(s) claim the contested cards.
  - **SECRET LAIR** — `complete` drops (every CN owned → registered like any
    product) and `near-complete` partials (≥ threshold, flagged for the user to
    confirm whether they bought the drop or just some singles).
- **Full-coverage only.** A product is never claimed on partial ownership (except
  the SLD near-complete *flag*, which is advisory, not a write).
- **No double-count / no over-attribution.** A loose card backs at most as many
  products as the user owns copies of it; cards already pledged to a built deck
  have `free = 0` and can't be claimed. `--apply` verifies the ledger still
  reconciles (`inventory == SUM(delta)`) before committing.

## Workflow

1. Run the dry-run for the chosen scope; relay the READY / CONFLICTS / SECRET
   LAIR sections + the summary line verbatim (clean them into a short markdown
   list, don't dump raw stdout).
2. If there are CONFLICTS the user cares about, help them choose and re-run with
   `--pick`.
3. On the user's go-ahead, run `--apply` (suggest `mm db snapshot` first for a
   large sweep) and relay the write summary.
4. Confirm with `mm audit provenance` that the `unattributed-backfill` bucket
   shrank by the attributed copies, and `mm audit ingest-ledger` still exits 0.

## Cross-references

- `scripts/trueup_pools.py` — the deterministic engine this skill drives.
- `decks.register_precon_from_loose` (deconstructed sibling of
  `construct_precon_from_loose`) + `decks.precon_recipe_needs` — the write
  primitive + recipe extraction.
- `ingest.reattribute` — moves ledger provenance between events (net-zero).
- `mtgjson.default_precon_state` / `POOL_NAME_PATTERNS` — pool classification.
- `sld.identify_drop` / `collect_drop_ids` — Secret Lair drop CN membership.
- [[import-precon]] / [[add-precon]] / [[construct-from-loose]] — the write-side
  siblings; `mm audit provenance` / `mm audit ingest-ledger` — the guards.
