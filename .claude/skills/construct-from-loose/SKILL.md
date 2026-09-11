---
name: construct-from-loose
description: Inline workflow for registering a Magic precon as a tracked BUILT deck by pledging cards the user ALREADY OWNS loose — WITHOUT adding those cards to inventory (no double-count). Routes to `mm deck construct-from-loose <fileName>`. Use whenever the user says "I built the <precon> from singles I already had", "register the FF/FIN Starter Kit decks without re-adding the cards", "I assembled <precon> out of my loose cards, track it as a deck", "convert my loose <precon> cards into a constructed deck", or "make <precon> a tracked deck but don't double-count my inventory". Creates the recipe if absent, previews coverage vs free inventory, and (with --allow-shortfall) pledges what's covered.
---

# Construct From Loose

The user assembled a precon out of singles they **already owned** (not a fresh
purchase). The cards are already in `inventory`; what's missing is the *deck* —
a tracked `built` unit with its cards pledged. This skill closes exactly that
gap in one command, and it **never adds inventory** (that would double-count the
cards the user already has).

Under the V5 model a deck has a **recipe** (`deck_cards`) and a **physical
pledge** (`deck_assignments`). `construct-from-loose` composes two existing
primitives in one shot: `import_precon(add_inventory=False, precon_state="built")`
to create the recipe, then the compose engine to pledge free inventory to it.
It pledges only the **net-remaining** need (recipe minus what this deck already
holds), so re-runs are incremental and safe.

## When to use

- "I built the FIN Starter Kit decks from cards I already had — track them."
- "Register BlueBlack_FIN / RedWhite_FIN without re-adding the cards."
- "I assembled <precon> out of my loose singles; make it a tracked deck."
- "Convert my loose <precon> cards into a constructed deck (don't double-count)."

**Don't** use for:
- A precon the user just **bought** (cards NOT yet in inventory) → [[import-precon]]
  / [[add-precon]] (those ADD inventory). This skill is the opposite: cards are
  already owned.
- A custom pasted decklist → `mm deck import` (recipe) then [[compose-deck]].
  This skill is precon-specific (MTGJSON fileName).
- Buying the cards you're missing → [[bulk-add]] / wishlist workflows.
- Recording a torn-down copy (cards stay loose, no pledge) → `mm deck add-precon
  --deconstructed` / `import-precon --state deconstructed`.

## The canonical recipe

### 1. Resolve the fileName
If the user named a set/product rather than an MTGJSON fileName, find it:
```bash
uv run mm mtgjson decks --set <code>        # e.g. --set fin → BlueBlack_FIN, RedWhite_FIN
```

### 2. Dry-run: preview coverage
**Always** dry-run first — it shows how much of the recipe your loose inventory
covers and lists the shortfalls, writing nothing:
```bash
uv run mm deck construct-from-loose <fileName> --dry-run
```
Interpret: `Coverage: X/Y rows fully covered, N short`. Each `short:` line is a
recipe card you don't own enough loose copies of.

### 3. Snapshot (cheap insurance)
```bash
uv run mm db snapshot --label pre-construct-<fileName>
```

### 4. Construct
- **Fully covered** → run plain:
  ```bash
  uv run mm deck construct-from-loose <fileName>
  ```
- **Partial coverage** (the common case for a kit whose commons aren't
  inventoried yet) → surface the shortfall list to the user first, then, only
  if they accept pledging what's owned and leaving the rest:
  ```bash
  uv run mm deck construct-from-loose <fileName> --allow-shortfall
  ```
  Without `--allow-shortfall`, the command **refuses** (exit 3) if any card is
  short — the same refuse-unless-explicit contract as `mm deck compose`.

### 5. Verify
```bash
uv run mm query show "assigned:<slug>"       # what got pledged
uv run mm deck compose <slug> --dry-run       # remaining shortfalls, if partial
```
Inventory value must be **unchanged** before/after (this command adds no
inventory): `uv run mm inventory value`.

## Flags

- `--allow-shortfall` — pledge what's covered, leave the rest as shortfalls.
- `--foil-first` — resolve `either`-finish recipe slots to foil first.
- `--new-copy` — force a second tracked deck row for the same fileName (you
  genuinely own/assembled a second physical copy). Default REUSES the existing
  built deck (no `-2` clone) and pledges only the net-remaining delta.
- `--slug` / `--name` — overrides used only when creating a new recipe.
- `--json` — emit the result dict.

## Guardrails

- **Never adds inventory.** The whole point is no double-count — it pledges
  cards you already own. Contrast with `import-precon`/`add-precon`.
- **Idempotent + incremental re-runs.** Re-running reuses the deck and pledges
  only newly-available cards (net-remaining). Running twice never double-pledges.
- **Refuses partial without `--allow-shortfall`** (exit 3), mirroring compose.
- Writes `deck_assignments` only; `inventory.quantity` and the recipe are
  preserved. Exit 2 on bad fileName / slug conflict; exit 3 on uncovered
  shortfall without the flag.

## Cross-references

- `src/magic_manager/decks.py:construct_precon_from_loose` — the function this
  skill drives (composes `import_precon` + the compose engine).
- [[import-precon]] / [[add-precon]] — the ADD-inventory siblings (fresh purchase).
- [[compose-deck]] — pledge loose inventory to an EXISTING recipe (custom decks).
- [[decompose-deck]] — the inverse (unpledge).
- [[set-status]] — verify the Precons count after (derived from deck rows).
