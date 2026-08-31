---
name: add-cards
description: One-liner wrapper around `mm inventory add-card` — adds a short, explicit list of specific cards to inventory by set code + collector number, no need to look up a scryfall_id first. Resolves via Scryfall's /cards/collection in one batched call and syncs unsynced sets on demand. Additive by default; --replace sets quantity outright. Triggers: "add SPG 60 nonfoil and BLC 123", "add these: FIN 5 foil, TLA 118 foil", "put 2x BLC 123 foil in my collection", "add these specific cards to inventory".
---

# Add Cards

The mechanical wrapper around `mm inventory add-card`. The user names a short, explicit list of specific cards — no CN range, no whole-product cataloging — and this skill maps each named card to one SPEC and calls the command once.

## When to use

- "Add SPG 60 nonfoil and BLC 123" / "add these: FIN 5 foil, TLA 118 foil"
- "Put 2x BLC 123 foil in my collection"
- Any short, explicit list of specific cards the user names by set + collector number.

**Don't** use for:
- A contiguous collector-number RANGE or a whole product with preview/gap-checking → [[bulk-add]] (that skill previews + gap-checks CN ranges; `add-card` is for a short explicit list, no preview).
- A whole set/family checklist → [[generate-set-checklist]] + [[ingest-new-inventory-list]].
- Rapid physical scan-loop entry → `mm intake <set>`.
- A whole precon deck → [[add-precon]].

`add-card` is the fast path for "these N specific cards"; `bulk-add` is the preview-heavy path for ranges/products. Don't conflate them.

## The command

```
mm inventory add-card <SPEC> [<SPEC> ...] [--replace] [--json]
```

Each SPEC is either the space form `"SET CN [finish] [qty]"` or the colon form `"SET:CN[:finish][:qty]"`. `finish` is `nonfoil` or `foil` (default `nonfoil`), `qty` defaults to `1`.

Examples:

```bash
uv run mm inventory add-card "spg 60"
uv run mm inventory add-card "blc 123 foil 2"
uv run mm inventory add-card "blc:123:foil:2"
uv run mm inventory add-card "blc:123::4"        # empty finish field = nonfoil, qty=4
uv run mm inventory add-card "spg 60" "blc 123 foil 2" "fin 5 foil"   # multiple specs, one call
```

Map each named card in the user's request → one SPEC, then call the command **once** with all specs together.

## Behavior

- Resolves every spec via Scryfall's `/cards/collection` in a single batched call — no need to look up a `scryfall_id` first.
- **Sync-on-demand:** a card whose set isn't synced locally yet (e.g. SPG) resolves and is upserted automatically; no pre-sync step needed.
- **Additive by default** — sums into existing inventory quantity. Pass `--replace` to set the quantity outright instead.
- Surfaces name/printing-mismatch warnings and not-found specs on stderr. A not-found result usually means a bad set code or collector number (a typo) — surface it to the user verbatim, don't silently drop it.
- `--json` emits `{added, updated, cards[], warnings, not_found}`.

## Guardrails

- **This is a mutation, not read-only** — it writes to `inventory` (and upserts into `cards` for any newly-synced printing).
- **Additive unless `--replace`.** Re-running the same spec without `--replace` sums quantities again.
- **Surface warnings/not_found verbatim.** Don't paper over a mismatch or a not-found — it's the user's signal that a set/CN was mistyped.

## Cross-references

- [[bulk-add]] — the preview-heavy path for CN ranges or whole products; use that instead when the request is a range, not a short explicit list.
- [[generate-set-checklist]] — for cataloging a whole set/family checklist.
- [[ingest-new-inventory-list]] — the ingest side of the checklist flow.
- [[add-precon]] — for adding a whole precon deck as a tracked unit, not loose individual cards.
