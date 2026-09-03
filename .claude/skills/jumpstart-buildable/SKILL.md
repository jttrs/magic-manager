---
name: jumpstart-buildable
description: Deterministic buy list for the cards needed to make EVERY theme of a Jumpstart set buildable — hold one built copy of each theme at once, plus each theme's other-version unique cards so any version is assemblable on demand, with no unnecessary cards. Reports what's still MISSING (target minus what you own) as ManaPool + TCGplayer + XLSX artifacts under queries/. Script-driven via `scripts/jumpstart_buildable.py <set_code>`. Triggers: "/jumpstart-buildable", "what cards do I need to build every jumpstart theme", "finish out my j25 jumpstart", "buildable set for <set>", "cards missing to construct every jumpstart theme", "efficient jumpstart catalog", "minimum cards for all <set> jumpstart themes".
---

# jumpstart-buildable

Deterministic, script-driven "buildable set" buy list. Claude invokes
`scripts/jumpstart_buildable.py <set_code>`, relays the stdout summary, and hands the user the
`queries/` artifact paths. No inline computation — the script is the single source of truth.

## When to use

- "What do I still need to build every theme of <Jumpstart set>?" / "finish out my j25 jumpstart"
  / "the efficient set of cards so I can construct any version of any theme."

**Don't** use for:
- A shopping list of whole packs you don't own — that's [[jumpstart-missing]] (per-pack), whereas
  this is per-*card* deduped across a theme's versions.
- Cataloging packs you OPENED — that's [[generate-jumpstart-checklist]] (ingestible).
- Identifying which version a pack is / what's in it — that's [[jumpstart-reference]].

## The canonical recipe

```bash
uv run python scripts/jumpstart_buildable.py <set_code>          # all 3 artifacts (default)
uv run python scripts/jumpstart_buildable.py <set_code> --format manapool|tcgplayer|xlsx
uv run python scripts/jumpstart_buildable.py <set_code> --out-dir <path>
```

`set_code` is required (e.g. `j25`). Relay the stdout summary (theme count, target, owned, missing
distinct/copies, `$` to buy) and the written file paths.

## What it computes

Target per card = **Σ over themes of max over that theme's versions of the card's count**. Within
a theme, the union of its versions at max multiplicity means any single version is buildable
(reusing shared cards); across themes it SUMS, because all themes are built at once (a card used by
K themes needs K copies). **Owned = total inventory** (including copies pledged to already-built
packs — you can deconstruct to reuse them). `missing = max(0, target − owned)`. **Basics are
included**; finish is not tracked (a foil you own satisfies the need; the buy list is nonfoil).

## Output shape

Three artifacts in `queries/` (ephemeral; pruned by [[cleanup-queries]]):
- `buildable-<code>-manapool-<ts>.txt` — ManaPool bulk-add (flat, paste-ready)
- `buildable-<code>-tcgplayer-<ts>.txt` — TCGplayer Mass Entry
- `buildable-<code>-checklist-<ts>.xlsx` — set / cn / name / rarity / finish / qty / unit_usd / line_value

Stdout: `<CODE> buildable set — N themes across M variants` + target / owned / missing / `$` lines
and the file paths. Cards not in the local `cards` table are reported by name to stderr and omitted.

## Determinism guarantees

- Themes group by name minus the `(N)` version suffix; rows sort by `(set, collector-number)`.
- Integer target math (max-within, sum-across); no `Date.now()`/random in the card list.
- The only moving part is synced prices (they affect the XLSX `$` columns, not which cards appear).
  The script syncs the set's family first so names/prices resolve locally.

## Guardrails

- Read-only against inventory; writes only ephemeral `queries/` artifacts.
- Exit 0 on success (even if nothing missing); exit 2 on bad set code / no Jumpstart variants.

## Not to be confused with

- [[jumpstart-missing]] — buy list for whole packs you DON'T own. This one is a *per-card* list to
  make every theme buildable (deduped by union-at-max-then-sum), not whole packs.
- [[generate-jumpstart-checklist]] — catalog packs you OPENED (ingestible checklist). This is a
  read-only shopping list, not ingestible.
- [[jumpstart-reference]] — read-only reference identifying pack versions + contents. Not a buy list.

## Cross-references

- `scripts/jumpstart_buildable.py` — the script this skill drives.
- `src/magic_manager/mtgjson.py` (`jumpstart_variants`, `deck`), `sets.py` (`resolve`/`sync`),
  `selectors.py` (`MaterializedRow`, `_card_dict`), `exports/` (`build`), `util.py`.
- [[foil-diff]] / [[secret-lair-value]] / [[set-status]] — sibling deterministic script-driven skills.
