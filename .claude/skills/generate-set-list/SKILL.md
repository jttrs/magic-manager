---
name: generate-set-list
description: Build the inventory checklist (XLSX or markdown) for a Magic the Gathering release family — every printing across the parent set + commander + masterpiece + promos, with two quantity columns the user fills in. Two flavors via --mode: 'add' (default; blank cells; ingests as additive — safe for new acquisitions) and 'modify' (prefilled cells; ingests as replace — for correcting existing records). Use this whenever the user wants to catalog cards. Mechanical workflow: invoke `mm set master-list <name> [--mode add|modify]` and react only to the structured exit codes.
---

# Generate Set List

The mechanical wrapper around `mm set master-list`. The user names a release ("Final Fantasy", "Outlaws of Thunder Junction", `otj`, `fin`); the CLI computes the family from Scryfall's `parent_set_code` graph filtered to `set_type IN (expansion, commander, masterpiece, promo)`, syncs prices, and writes `checklists/<slug>-<mode>-checklist.xlsx` (mode = `add` by default — blank qty cells; `modify` pre-populates from current inventory).

**You make zero judgment calls about scope.** The recommended bundle is codified in the CLI; do not list sibling sets and ask which to include. If the user wants tokens or memorabilia, they will say so explicitly — translate that to `--include token,memorabilia`.

## Steps

1. Run `uv run mm set master-list "<name-or-code>"` from the repo root. That's the whole happy path.
2. Look at the exit code:
   - **0**: success. Tell the user the file path and the next step (`mm set ingest "<name>"` when they've filled in quantities). Done.
   - **2**: bad arguments / no Scryfall match. Surface the error verbatim and ask for clarification.
   - **3**: an unprocessed intake XLSX already exists. The CLI prints a readout of inventory in this set's family (rows owned, total value, top-value cards). Show that readout to the user and ask which path forward they want via `AskUserQuestion`.
3. If they chose "ingest first": run `uv run mm set ingest "<name>"`, surface the result, then re-run `mm set master-list "<name>"` to start a fresh inventory checklist.
4. If they chose "discard partial work": re-run `uv run mm set master-list "<name>" --force` and warn that any XLSX-only edits (those not yet ingested) are gone.

## Mode — `add` vs `modify` (CRITICAL: pick the right one)

`mm set master-list` produces two flavors of inventory checklist depending on `--mode`. The mode is encoded in both the filename and the file's `_meta.mode`, and `mm set ingest` auto-detects it later.

| `--mode` | Filename | Qty cells at generation | Ingest semantics | When to use |
|---|---|---|---|---|
| **`add`** (default) | `<slug>-add-checklist.xlsx` | **Blank** | **additive** — qty>0 cells sum into existing inventory; blanks/0s no-op | New acquisitions: a booster pack opened, a precon, a trade-in, cards picked up at a tournament. Safe — additive ingest cannot accidentally zero out rows. |
| **`modify`** | `<slug>-modify-checklist.xlsx` | **Prefilled** from current `inventory` | **replace** — in-partition cells overwrite DB qty; rows in-partition but missing from the file are zeroed out | Correcting existing records: you sold a card, miscounted on a previous ingest, or want to do a full audit pass on a set you already cataloged. Powerful — can zero rows. |

**Default is `add` for safety.** Only switch to `--mode modify` when the user explicitly says they want to correct/audit their current inventory (e.g. "I sold some cards and need to update", "let me re-audit FCA"). For everything else (a new pack, a precon, "let me catalog these cards I have"), use the default `add`.

The filename convention means both flavors can coexist — `final-fantasy-add-checklist.xlsx` and `final-fantasy-modify-checklist.xlsx` are independent files in `checklists/`. Each ingests with the right semantics automatically.

When asking the user, default-recommend `add`. Only suggest `modify` if their phrasing implies correction over augmentation.

## Slicing — generating partial inventory checklists

The user often catalogs piecemeal: "just the rares from FF", "just the `fic` cards", "this booster I just opened". For these cases, slice at generate-time so the resulting XLSX only covers the intended scope. Two flags compose:

- `--rarity <r>` (repeatable, comma-OK): emit only the named rarities. Values: `mythic`, `rare`, `uncommon`, `common`, `bonus`, `special`. Filename gains a rarity suffix (`<slug>-rare-add-checklist.xlsx`, `<slug>-rare+mythic-add-checklist.xlsx`).
- `--only <codes>`: restrict to specific set codes within the family. Filename gains a code suffix (`<slug>-fic-add-checklist.xlsx`).

All compose with `--mode`: `--only fic --rarity rare --mode modify` → `<slug>-fic-rare-modify-checklist.xlsx`.

When the user says "just the rares", run `mm set master-list "<name>" --rarity rare`. When they say "just the commander deck", run `mm set master-list "<name>" --only fic` (after confirming the family has the code they meant via `mm set list-related`).

Each slice can be in flight independently — collision detection is per-filename, so you can have `<slug>-rare-add-checklist.xlsx` and `<slug>-uncommon-add-checklist.xlsx` both pending at the same time.

The XLSX carries a hidden `_meta` sheet recording the slice, so ingest knows which (set, rarity) pairs are in-partition. The user never sees `_meta`.

## Other flags (rarely needed)

- `--include token,memorabilia` — opt extra `set_type`s into the family. Use only when the user explicitly asks for tokens, art series, or scene boxes.
- `--include-variants` — opt prerelease, store-stamped, japanshowcase, serialized, and white/yellow-bordered printings back in. **Off by default** — these are filtered out of the master-list output and from set-missing math via the registered `set_targets` row. The user said they don't catalog these and there are too few to keep around.
- `--out <path>` — redirect output to a non-default path (skips collision detection). Almost never the right answer.
- `--force` — overwrite an existing intake XLSX. Only after the user has explicitly chosen "discard partial work" via the exit-3 prompt.
- `--format md` — emit a markdown checklist instead of XLSX. The file lands at `checklists/<slug>-<slice>-checklist.md` with YAML frontmatter, sections per rarity, and lines like `- (FCA) 4 [N:0 F:0] [b|sm] — [Wild Rose Rebellion / Counterspell](https://scryfall.com/card/fca/4) — $4.66 / $5.50`. Edit the `[N:k F:k]` brackets in any text editor (or on a phone). `mm set ingest` and `/ingest-new-inventory-list` both auto-detect the format.

## Treatment column

Each row has a `treatment` cell between `rarity` and `mana_value`. It's a `|`-delimited keyword string identifying what kind of special print this is (modern overlay/bleed, masterpiece reskin, fancy foil, etc.). Empty cell = standard print. Full keyword space and derivation rules in [`docs/scryfall-printing-treatments.md`](../../../docs/scryfall-printing-treatments.md). The XLSX has a hidden `_legend` sheet documenting the codes; the markdown form appends a `## Treatment legend` section at the bottom.

This column lets you tell apart multiple printings of the same card (e.g. the six [Cloud, Ex-SOLDIER (FIC)](https://scryfall.com/card/fic/2/cloud-ex-soldier) variants) without clicking through to Scryfall.

## Three intake surfaces (XLSX, markdown, scan loop)

The user picks the surface that fits the moment. All three converge on the same `inventory` table, so exports/queries are surface-agnostic.

| Surface | When to use | Command |
|---|---|---|
| XLSX (default) | First-pass cataloging of a whole set / sit-down session in a spreadsheet app | `mm set master-list "<name>"` |
| Markdown | Phone-editable, plain-text-editor, or wanting to diff against an old version in git | `mm set master-list "<name>" --format md` |
| Scan loop (REPL) | Rapid manual entry — fastest for "I have a stack of cards in my hand right now" | `mm intake "<name>"` |

The scan loop's grammar:

```
> fca 4         # +1 to FCA #4 nonfoil (default)
> 4 +3          # sticky set: FCA #4 +3 nonfoil
> 4 =1          # FCA #4 nonfoil → exactly 1 (overwrite)
> 4 f           # FCA #4 foil +1
> 4 +2 f        # FCA #4 foil +2
> u             # undo the last entry
> q             # quit + show summary
```

The set code is sticky after first use — typing just `4` after `fca 4` still means FCA. The REPL writes to the DB on every line (Ctrl-C is safe; partial work persists). Run `mm set master-list <name>` once before scanning so the family is seeded.

## Exit-3 prompt template

When the CLI exits 3, the stderr already contains the readout. After surfacing it, use `AskUserQuestion` with these two options (always the same two):

> **An unprocessed intake XLSX exists for `<set-name>`. What should I do?**
> - **Ingest the existing XLSX first (Recommended)** — run `mm set ingest "<set-name>"` to save your filled-in quantities, then start a fresh inventory checklist.
> - **Discard the partial XLSX edits and regenerate** — run `mm set master-list "<set-name>" --force`. Any quantities filled in but not yet ingested will be lost.

## What the user sees

| Path | Filename | Lifecycle |
|---|---|---|
| Active inventory checklist (one per family per mode at a time) | `checklists/<slug>-<mode>-checklist.xlsx` (e.g. `final-fantasy-add-checklist.xlsx`, `final-fantasy-modify-checklist.xlsx`) | Created by `master-list`. User edits in Excel/Numbers. |
| Archived inventory checklists | `checklists/processed/<slug>-<mode>-checklist-<YYYY-MM-DD-HHMMSS>.xlsx` | Created by `ingest` after the data lands in the DB. Immutable. |

The XLSX columns: `set`, `collector_number`, `name`, `rarity`, `mana_value`, `usd`, `usd_foil`, `qty_normal`, `qty_foil`. The two `qty_*` columns are tinted yellow, validated as non-negative integers, and pre-populated from the `inventory` table whenever the user already owns cards from previous ingest cycles. Rows are sorted by rarity bucket (mythic → rare → uncommon → common → bonus → special) then collector number to match the user's physical box order.

For Universes Beyond reskin printings (FCA, MAR, PZA, etc.) the `name` cell renders as `<flavor_name> / <oracle_name>` so the user can find the row by either the printed name (what they see on the card) or the canonical Magic name. Non-reskin rows show just the oracle name.

> **Upgrading from V1.2:** if your DB was populated before V1.3, the `flavor_name`/`is_reskin` columns will be NULL/0 on existing card rows. Run `uv run mm set sync <name>` once before the next `master-list` to backfill — the sync upserts every printing and the next XLSX will display merged names correctly.

## Examples

User: *"generate an inventory excel for the Final Fantasy sets."*

```bash
uv run mm set master-list "Final Fantasy"
```

If exit 0: tell them `checklists/final-fantasy-add-checklist.xlsx` is ready and `mm set ingest "Final Fantasy"` is the next command.
If exit 3: surface the readout, show the AskUserQuestion above.

User: *"give me an inventory checklist for OTJ but include the breaking news cards too."*

`pbig`, `big`, `otp` are already in the default family for `otj` (they're `set_type=expansion`/`promo`). The user's request is already covered by the default. Run:

```bash
uv run mm set master-list otj
```

User: *"include the FF tokens this time."*

```bash
uv run mm set master-list "Final Fantasy" --include token
```

## Caveats

- The inventory checklist is a **transient editing artifact**, not a source of truth. The DB is the source of truth. Tell the user to run `mm set ingest "<name>"` when they're done editing — that's when the data actually lands.
- Re-running `master-list` is safe (DB-backed cells re-pre-populate), but only after the previous intake has been ingested. If you see exit 3, do NOT pass `--force` without confirming with the user — XLSX-only edits will be silently discarded.
- A full Final Fantasy family sync touches Scryfall ~1,244 cards over 8 paginated calls (~4–6 seconds with the 500ms wrapper rate limit). OTJ is similar.
- Stale lock state: if `scryfall.sh` died mid-run, you may see `lock timeout`. Clear with `rm -rf "${TMPDIR}scryfall-state/lock"` and retry.
- **Variant exclusions baked into master-list output** (`is_excluded_variant()` at `sets.py`): prerelease-stamped, datestamped, stamped, promopack, japanshowcase, serialized, white/yellow-bordered, and **Arena/Alchemy rebalanced** (digital-only, e.g. `A-Vivi Ornitier`). These are dropped at write time so the inventory checklist only shows printings the user could realistically physically catalog. Override with `--include-variants` if needed (rarely).

## Not to be confused with: missing checklists

The XLSX written by `mm set master-list` is an **inventory checklist** — purpose: cataloging physical cards. The XLSX written by `mm query missing-set <CODE>` (the [[missing-from-set]] skill) is a **missing checklist** — purpose: shopping list of printings the user doesn't own. Different artifacts, different purposes, different rules:

| | Inventory checklist (add) | Inventory checklist (modify) | Missing checklist |
|---|---|---|---|
| **Produced by** | `mm set master-list` (default) | `mm set master-list --mode modify` | `mm query missing-set` |
| **File location** | `checklists/<slug>-add-checklist.xlsx` | `checklists/<slug>-modify-checklist.xlsx` | `queries/missing-<code>-checklist-<ts>.xlsx` |
| **`_meta.kind`** | `inventory` | `inventory` | `missing` |
| **`_meta.mode`** | `add` | `modify` | (n/a) |
| **Qty cells at gen** | Blank | Pre-filled from `inventory` | Pre-filled with quantity needed |
| **Ingest semantics** | additive (sum into DB) | replace (overwrite + zero missing in-partition) | (read-only) |
| **Spine** | full family universe (with safe variant exclusions) OR a rarity slice | same as add | printing-level union of what the user doesn't own |
| **Columns** | set, cn, name, rarity, treatment, mana_value, usd, usd_foil, **qty_normal, qty_foil** | same as add | set, cn, name, rarity, **finish**, qty, **unit_usd**, **line_value**, scryfall_id |
| **Filter philosophy** | Permissive — keeps `ext` / pure-`ff` / fancy-foil dupes (user might own incidental copies cracked from boosters, etc.). Drops only safe-to-exclude variants + Arena. | same as add | Strict — drops everything not "unique art that can't be obtained more cheaply." See [[missing-from-set]]'s `preferred` treatment class. |
| **Round-trips** | YES, via `mm set ingest` (auto-detected) | YES, via `mm set ingest` (auto-detected) | NO, read-only |
| **Use case** | New acquisitions (booster pack, precon, trade-in) | Correcting records (sold cards, audit pass) | Shopping list |

Mental model: **inventory checklist = "what could I own" (add for new, modify for correction); missing checklist = "what I want to buy."** Don't conflate them. If the user asks for "a checklist of FIN" without context, default to the inventory checklist with `--mode add` (this skill); if they say "what am I missing" / "what to buy" / "shopping list," route to the missing-from-set skill.
