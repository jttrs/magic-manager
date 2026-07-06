---
name: decompose-deck
description: Inline workflow for physically disassembling an owned deck — unpledging the cards so they return to the free-inventory pool, WITHOUT destroying the deck's composition. Routes to `mm deck decompose <slug>`. Use whenever the user says "decompose <deck>", "break down <deck>", "unpledge <deck>", "I'm taking apart the <name> precon to use the cards elsewhere", "return the cards from <deck> to my collection", or "the cards are loose again". Also handles the "I opened a second copy of a precon I already have" flow — those cards go straight to inventory as loose, without needing to decompose anything.
---

# Decompose Deck

Under V5 the DB separates a deck's **recipe** (`deck_cards` — never destroyed by decompose) from its **physical assignment** (`deck_assignments` — what inventory copies are currently pledged to fulfill the recipe). Decomposing a deck means "release the pledges" — the recipe survives, the pledged copies rejoin the free pool, and inventory `quantity` is unchanged throughout.

## When to use

- "I'm taking apart <deck> to use the cards elsewhere"
- "Decompose <deck>" / "break down <deck>" / "unpledge <deck>"
- "The cards from <deck> are free again"
- "I opened a second copy of <precon> and I want to use those cards for other decks" — cards land loose in inventory; if the second copy is being decomposed straight out of the sealed box, use [[import-precon]] with `--merge-inventory` (see step 1a below).

**Don't** use for:
- Deleting the deck composition entirely — that's `mm deck delete <slug>` (this skill *preserves* the composition; delete is a separate destructive op).
- First-time precon imports — that's [[import-precon]].
- Adding loose cards to inventory from a paste/list — that's [[bulk-add]] or [[import-list]].

## Mental model (read this once)

Three tables under V5:

- **`inventory`** — physical cards owned. `quantity` is the only truth about "do I have this card?".
- **`deck_cards`** (the recipe) — what a deck *wants*. Immutable under compose/decompose.
- **`deck_assignments`** (the pledge) — what inventory copies are *currently* pledged to fulfill the recipe. Grows on compose, shrinks on decompose.

Selector vocabulary:

| Selector | Meaning |
|---|---|
| `inventory` | Every physical copy owned. |
| `free` | `inventory` minus everything currently pledged to any deck. |
| `inventory assigned` | Inventory rows that have ≥1 copy pledged to some deck. |
| `assigned:<slug>` | The copies currently pledged to one deck. |
| `deck:<slug>` | The deck's *recipe*. Unaffected by compose/decompose. |

Two invariants held by every write path (composition/assignment):

1. `SUM(deck_assignments.count) ≤ inventory.quantity` per `(scryfall_id, finish)` — you can't pledge cards you don't own.
2. `SUM(deck_assignments.count for a printing on one deck) ≤ SUM(deck_cards.count for that printing)` — you can't pledge more than the recipe wants.

## Workflow

### 1. Resolve the slug

The user says "the Terra precon" or "revival trance"; convert to a slug via `mm deck ls`:

```bash
uv run mm deck ls | grep -i <keyword>
```

If nothing matches, abort with the mismatch surfaced to the user. If multiple match, ask which one.

### 1a. Special case — second copy of a precon just opened

If the user is decomposing a **second physical copy of a precon they already have as a deck**, and the cards haven't been added to inventory yet, use `import-precon --merge-inventory` instead of this skill's step 3 onward:

```bash
uv run mm deck import-precon <FileName> --merge-inventory
```

This adds a copy's worth of inventory without touching the (already-existing) deck composition. Then no further decompose is needed — the extra cards are already loose in inventory.

Only fall through to step 2 when the user is decomposing an already-composed deck (assignments exist) — i.e., they physically took the deck apart and the cards need to be returned to the free pool.

### 2. Preview + snapshot

Show the user what will be released, then snapshot:

```bash
uv run mm query show "assigned:<slug>"
uv run mm db snapshot --label pre-decompose-<slug>
```

If `assigned:<slug>` returns 0 rows, the deck has no current pledges — there's nothing to decompose. Surface that and stop (the user probably meant a different deck or already ran this).

### 3. Decompose

```bash
uv run mm deck decompose <slug>
```

Expected output: `Deck '<slug>' decomposed: N rows (M card-qty) unpledged. Recipe preserved.`

### 4. Verify

```bash
uv run mm query show "assigned:<slug>"
```

Must return 0 rows.

Optionally confirm the recipe survived (it always does — this is a sanity check):

```bash
uv run mm deck show <slug>
```

Row count should be unchanged from before the decompose.

### 5. Report to the user

Summarize:
- N rows unpledged, M card-qty released.
- Recipe (`deck:<slug>`) preserved — the deck can be re-composed later with `mm deck compose <slug>` when the user rebuilds it (assuming the cards are still in inventory).
- Snapshot path so they can undo with `mm db restore <path>` if desired.

## Caveats

- **This does not touch inventory.** Inventory `quantity` is invariant across compose/decompose — only the *slice* that's `free` vs. `assigned` changes.
- **Deleting the composition is a separate op.** Users who *also* want the recipe gone should run `mm deck delete <slug>` afterwards. This skill deliberately does NOT chain into delete; the deck record is memory of what the physical stack used to be, and might be wanted later for a re-build.
- **Idempotence:** running `mm deck decompose <slug>` twice is safe. The second run reports "had no assignments to unpledge" and does nothing.
- **Ingest log:** every decompose writes a `deck-unassigned:<slug>` row to `ingest_log`. Audit later via `SELECT * FROM ingest_log WHERE label LIKE 'deck-%';`.

## See also

- [[compose-deck]] — the inverse (pledge inventory to a deck).
- [[import-precon]] — first-time precon import; `--merge-inventory` for extra physical copies of an already-composed precon.
