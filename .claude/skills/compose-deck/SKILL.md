---
name: compose-deck
description: Inline workflow for physically assembling a deck from loose inventory — pledging the recipe cards the deck does not already hold so it becomes physically built. Routes to `mm deck compose <slug>`. Use whenever the user says "compose <deck>", "build <deck>", "assemble <deck>", "top up <deck>", "pledge cards to <deck>", "I'm sleeving up <name>", or "put together <deck>". Tops up (recipe minus what is already pledged, safe to re-run), resolves "either"-finish slots with the same rule as the web Build, and refuses to write anything if the top-up would overflow inventory or the recipe.
---

# Compose Deck

Under V5 the DB separates a deck's **recipe** (`deck_cards`) from its **physical assignment** (`deck_assignments`). Composing a deck means "pledge free inventory copies to fulfill the recipe" — inventory `quantity` is unchanged, but the `free` slice shrinks and `assigned:<slug>` grows to mirror the recipe.

**Compose is a top-up.** It pledges only `recipe − already pledged to this deck`, per printing and finish, so it is safe to re-run: a partly-pledged deck is completed, a complete deck is a no-op.

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
2. **Recipe overflow:** a printing's pledges can't exceed what the recipe calls for. Because compose only pledges the top-up, re-running it never trips this; it fires only when the deck holds pledges the recipe doesn't want (for example a pledged finish the recipe no longer lists, or a recipe edited down after the deck was built). Reported with `kind='recipe'`; resolve with `mm deck decompose <slug>` (or edit the recipe back) rather than `--allow-shortfall`.

If either fails, `mm deck compose` refuses to write anything (single-transaction rollback) unless `--allow-shortfall` is passed to skip the offending rows.

## Workflow

### 1. Resolve the slug

```bash
uv run mm deck ls | grep -i <keyword>
```

Abort if no match, ask if multiple.

To find decks that need a top-up (built decks whose pledges no longer cover their recipe), run `uv run mm audit deck-inventory` and read its **"Built decks short of their recipe"** section: each line gives `pledged P of N; free inventory covers C of the S missing` and the exact `mm deck compose <slug>` to run.

### 2. Dry-run: `mm deck free <slug>`

**Always** dry-run first (`mm deck free <slug>` is an alias for `mm deck compose <slug> --dry-run`). This is the top-up + shortfall report and the `either`-finish resolution preview:

```bash
uv run mm deck free <slug>
```

Interpret the output:

- **`# already pledged to this deck: X of Y card-qty`** — X of the Y recipe cards are already pledged; compose will pledge the other `Y - X` (capped by free inventory). `X == Y` means the deck is complete and compose is a no-op.
- **`rows: N  shortfalls: 0  either_choices: K`** — clean top-up ahead. Proceed to step 3 (skip it when `X == Y`).
- **`shortfalls: M`** — free inventory can't cover the top-up. Each line reads `<id>/<finish>: need N (recipe R, pledged P), free F`: `N` is what is still missing, `R` the recipe's need for that printing+finish, `P` what this deck already holds, `F` what is free. Surface the list to the user before proceeding and offer [[bulk-add]] or wishlist workflows for the missing cards. (Free copies pledged to *other* decks are not free; the user decides whether to decompose that deck.)
- **`either_choices: K`** — recipe has K `finish='either'` slots. They resolve with the same rule as the web Build: copies this deck already holds are kept first, then free nonfoil, then free foil, splitting a slot across finishes when needed (`chose` is `nonfoil`, `foil` or `split`). If the user prefers foil, re-run with `mm deck free <slug> --foil-first`.

### 3. Snapshot

```bash
uv run mm db snapshot --label pre-compose-<slug>
```

Composition is an inventory-preserving op (only `deck_assignments` grows), but the snapshot is cheap insurance and makes recovery `mm db restore <path>`. Skip it when the dry-run showed the deck is already complete.

### 4. Compose

```bash
uv run mm deck compose <slug>
```

If step 2 showed `either_choices > 0` and the user preferred foil, add `--foil-first`. If they explicitly opted into partial coverage after seeing shortfalls, add `--allow-shortfall`.

Expected clean output: `Deck '<slug>' composed: N rows pledged (M total card-qty).` — `N`/`M` count only the top-up. **`0 rows pledged (0 total card-qty)` means the deck was already complete: exit 0, nothing written, and no `deck-assigned` event is recorded.** It is a success, not an error.

### 5. Verify

```bash
uv run mm query show "assigned:<slug>"
```

Total pledged should now equal the recipe (`mm deck show <slug>`, modulo `either`-slot resolution collapsing or splitting rows); re-running `mm deck free <slug>` should report `# already pledged to this deck: Y of Y`.

Optional: confirm the `free` pool shrank correctly:

```bash
uv run mm query total "free"
```

The delta from before the compose should equal the total card-qty just pledged (the top-up, not the whole recipe).

### 6. Report to the user

Summarize:
- N rows pledged, M card-qty (the top-up; `0` = already complete). Recipe fully fulfilled (or partial if `--allow-shortfall` was used — enumerate the shortfalls).
- Any `either`-slot resolutions (finish chosen for each, `split` included).
- Snapshot path.

## Caveats

- **Inventory qty is invariant.** `mm inventory value` before/after must be identical. If it isn't, something wrote through a non-V5 path — investigate before proceeding.
- **Cross-deck contention:** two decks that both want card X compete for the free pool. First-composer wins; the second gets a shortfall until the user decomposes the first or acquires more copies. This is the intended behavior — surface it to the user with the shortfall list so they can decide.
- **`either` resolution splits.** A recipe entry like `4x Sol Ring [either]` with 2 nonfoil + 2 foil free pledges 2 nonfoil + 2 foil (nonfoil first, or foil first with `--foil-first`); copies the deck already holds in either finish are kept before any free copy is taken. The same function (`decks.resolve_needs`) backs the web Build, so the two never disagree about what a deck still needs.
- **Ingest log:** a compose that pledges something writes a `deck-assigned:<slug>` event to `ingest_events`; a no-op compose writes none.

## See also

- [[decompose-deck]] — the inverse.
- [[import-precon]] — creates the recipe (and adds inventory); run compose *after* to pledge.
- [[construct-from-loose]] — one-step "register a precon + pledge cards I already own loose" (recipe-create with NO inventory add, then compose) — for a precon assembled from singles you already had.
