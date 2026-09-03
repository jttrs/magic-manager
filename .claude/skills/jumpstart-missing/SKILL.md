---
name: jumpstart-missing
description: Build a buy list for the Jumpstart packs you DON'T own from a set — every pack with no pack:* deck, emitted as combined ManaPool + TCGplayer + XLSX shopping artifacts under queries/, each pack's full singles plus its front/title card. Read-only shopping list, not an ingestible checklist. Mechanical workflow: invoke `mm query missing-jumpstart <code>` and relay the result. Triggers: "what jumpstart packs am I missing", "buy list for the jumpstart packs I don't have", "missing jumpstart packs for msh", "shopping list for j25 jumpstarts", "which jumpstart packs do I still need".
---

# Jumpstart Missing (buy list)

The mechanical wrapper around `mm query missing-jumpstart <code>`. For a Jumpstart set,
it finds every pack the user does **not** own (no `pack:<theme>-<code>` deck) and emits
the combined singles as a shopping list under `queries/`.

This is the Jumpstart analogue of [[missing-from-set]] (`mm query missing-set`), which
does the same for a set family's singles. It is the *shopping* sibling of
[[generate-jumpstart-checklist]] (the *cataloging* checklist for packs you opened).

## What it does

1. Syncs the family + front cards, enumerates the set's MTGJSON Jumpstart variants.
2. Diffs against owned `pack:<theme>-<code>` decks → the packs you're missing.
3. For each missing pack, lists its full contents — gameplay singles **plus the pack's
   front/title card** (from the quarantined `front_cards` table, e.g. FMSC for MSH).
4. Emits three combined artifacts under `queries/` (named `missing-jumpstart-<code>-*`
   so they never collide with `missing-set`'s files):
   - XLSX checklist, ManaPool bulk-add `.txt`, TCGplayer Mass Entry `.txt`.
   - Plus a per-pack summary table + `file://` links to chat.

## Steps

1. Run `uv run mm query missing-jumpstart <code>`.
2. Exit codes: **0** success (or "you own all N packs" — nothing missing); **2** bad
   code / no Jumpstart variants for the set. There's no exit-3 collision — artifacts are
   timestamped and land in ephemeral `queries/`.
3. Relay the per-pack summary and the three `file://` links to the user.

## Important scope notes

- **Read-only shopping list.** These artifacts are NOT ingestible checklists — they're
  for pasting into ManaPool / TCGplayer to buy. (To catalog packs you've opened, use
  [[generate-jumpstart-checklist]].)
- **Full contents, not deduped or owned-subtracted.** It lists each un-owned pack's
  complete singles, with no cross-pack dedup and without subtracting cards you already
  own. A future workflow will shrink the "must buy" list by constructing packs from free
  inventory — that reduction is deliberately NOT part of this command.
- `queries/` is ephemeral (pruned by [[cleanup-queries]] / [[clear-queries]]).

## Not to be confused with

- [[generate-jumpstart-checklist]] — catalog packs you OPENED (ingestible). This is the
  inverse: a buy list for packs you HAVEN'T.
- [[jumpstart-buildable]] — buy list for the *cards* to make every theme buildable (deduped
  across a theme's versions), rather than whole packs. [[jumpstart-reference]] — read-only XLSX
  identifying which pack version is which + its contents.
- [[missing-from-set]] — the singles buy list for a whole set family (`missing-set`).
- [[export-list]] — the general per-pack export (`mm set jumpstart-pack <code> <theme>`)
  for ONE named pack, with an optional `--missing` inventory filter.

## Examples

User: *"what jumpstart packs am I missing from Marvel?"* →
`uv run mm query missing-jumpstart msh` → per-pack summary of the un-owned MSH packs +
combined ManaPool/TCGplayer/XLSX buy lists.

User: *"buy list for the j25 packs I don't have"* →
`uv run mm query missing-jumpstart j25`.
