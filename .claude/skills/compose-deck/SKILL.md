---
name: compose-deck
description: Inline workflow for physically assembling a deck from loose inventory — pledging one copy of each recipe card to the deck so it becomes physically built. Routes to `mm deck compose <slug>`. Use whenever the user says "compose <deck>", "build <deck>", "assemble <deck>", "pledge cards to <deck>", "I'm sleeving up <name>", or "put together <deck>". Handles the "either"-finish resolution automatically and refuses to write anything if the recipe would overflow either inventory or itself.
---

# Compose Deck

Under V5 the DB separates a deck's **recipe** (`deck_cards`) from its **physical assignment** (`deck_assignments`). Composing a deck means "pledge free inventory copies to fulfill the recipe" — inventory `quantity` is unchanged, but the `free` slice shrinks and `assigned:<slug>` grows to mirror the recipe.

## When to use

- "Compose <deck>" / "build <deck>" / "assemble <deck>"
- "I'm sleeving up <deck>"
- "Pledge the cards for <deck>"
- "Put together the <name> precon" (when the cards are already in inventory)

**Don't** use for:
- First-time precon import — that's [[import-precon]] (which handles the loose→inventory step; then run this skill or `mm deck compose <slug>` to pledge).
- Adding cards to a deck's recipe — that's `mm deck import` or `mm deck import-precon`; recipe edits don't touch assignments.
- Buying cards you don't yet own — that's [[bulk-add]] or wishlist workflows.

## Mental model

See [[decompose-deck]] for the full three-table picture. Short version: `deck:<slug>` is the recipe, `assigned:<slug>` is what's currently pledged. Compose adds to `assigned:<slug>` until it equals the recipe. Two invariants block bad states:

1. **Inventory overflow:** can't pledge more than the free pool holds. Reported per `(scryfall_id, finish)` with `kind='inventory'`.
2. **Recipe overflow:** can't pledge more to a deck than its recipe demands (this catches "compose the same deck twice"). Reported with `kind='recipe'`.

If either fails, `mm deck compose` refuses to write anything (single-transaction rollback) unless `--allow-shortfall` is passed to skip the offending rows.

## Workflow

### 1. Resolve the slug

```bash
uv run mm deck ls | grep -i <keyword>
```

Abort if no match, ask if multiple.

### 2. Dry-run: `mm deck free <slug>`

**Always** dry-run first. This is the shortfall report + `either`-finish resolution preview:

```bash
uv run mm deck free <slug>
```

Interpret the output:

- **`rows: N  shortfalls: 0  either_choices: K`** — clean compose ahead. Proceed to step 3.
- **`shortfalls: M`** — the user is missing cards or has them already pledged elsewhere. Surface the shortfall list to the user before proceeding:
  - `kind='inventory'` shortfalls: the user needs to acquire those cards first. Offer [[bulk-add]] or wishlist workflows.
  - `kind='recipe'` shortfalls: something weird — the deck is already partially composed. Ask the user whether to `mm deck decompose <slug>` first or to compose only the delta.
- **`either_choices: K`** — recipe has K `finish='either'` slots; the plan chose nonfoil where free, foil as fallback. If the user has a strong preference (foil-first), re-run with `mm deck free <slug> --foil-first`.

### 3. Snapshot

```bash
uv run mm db snapshot --label pre-compose-<slug>
```

Composition is an inventory-preserving op (only `deck_assignments` grows), but the snapshot is cheap insurance and makes recovery `mm db restore <path>`.

### 4. Compose

```bash
uv run mm deck compose <slug>
```

If step 2 showed `either_choices > 0` and the user preferred foil, add `--foil-first`. If they explicitly opted into partial coverage after seeing shortfalls, add `--allow-shortfall`.

Expected clean output: `Deck '<slug>' composed: N rows pledged (M total card-qty).`

### 5. Verify

```bash
uv run mm query show "assigned:<slug>"
```

Row count should equal the recipe (`mm deck show <slug>` row count, modulo `either`-slot resolution collapsing rows).

Optional: confirm the `free` pool shrank correctly:

```bash
uv run mm query total "free"
```

The delta from before the compose should equal the total card-qty just pledged.

### 6. Report to the user

Summarize:
- N rows pledged, M card-qty. Recipe fully fulfilled (or partial if `--allow-shortfall` was used — enumerate the shortfalls).
- Any `either`-slot resolutions (finish chosen for each).
- Snapshot path.

## Caveats

- **Inventory qty is invariant.** `mm inventory value` before/after must be identical. If it isn't, something wrote through a non-V5 path — investigate before proceeding.
- **Cross-deck contention:** two decks that both want card X compete for the free pool. First-composer wins; the second gets an `inventory` shortfall until the user decomposes the first or acquires more copies. This is the intended behavior — surface it to the user with the shortfall list so they can decide.
- **`either` resolution is greedy per-card.** For a recipe entry like `4x Sol Ring [either]` with 2 nonfoil + 2 foil free, the current logic will try nonfoil-first and fall back to foil only if nonfoil can't cover the whole 4. It does NOT split 2+2. If a user's recipe uses `either` and they want mixed-finish coverage, they should edit the recipe to be finish-specific.
- **Ingest log:** every compose writes a `deck-assigned:<slug>` row to `ingest_log`.

## See also

- [[decompose-deck]] — the inverse.
- [[import-precon]] — creates the recipe (and adds inventory); run compose *after* to pledge.
