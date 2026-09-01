---
name: set-status
description: Concise, script-driven status report for a Magic set FAMILY — family topology (set codes + types), # checklist ingests, owned prints/qty/$ value, precon count by format, missing $ + count, and whether the family is characterized (docs/sets/<parent>.md exists). Accepts the family anchor OR any member code (snc, ncc, tmt, tle, eoc, …) and normalizes to the true parent. With NO argument, prints a collection-wide overview of every owned family (one row each). Prices are live. Triggers: "/set-status", "status of <set>", "how complete is my <set>", "where am I on <set>", "give me a <set> status report", "<set> collection status", "how am I doing on <set>", "collection overview", "all my sets", "how's my whole collection".
---

# set-status

Deterministic, script-driven family status. Claude invokes `scripts/set_status.py <anchor>`, then **relays the script's stdout markdown block verbatim into chat**. No inline computation, no eyeballing counts or prices — the script is the single source of truth. Any stderr notes (unsynced family, "not configured", heuristic fallback) are surfaced briefly beneath the table.

The `<anchor>` may be the family parent (`snc`, `tmt`) **or any member** (`ncc`, `tle`, `eoc`, `pncc`) — the script resolves the member up to the true parent automatically and reports the whole family.

**No argument → collection overview.** Run `scripts/set_status.py` with no anchor for a high-level, collection-wide table: one compact row per family the user owns cards in (plus any registered-but-not-yet-owned family from `set_targets`), sorted by owned $ descending, with a grand-total row. Use this for "how's my whole collection", "collection overview", "all my sets", "/set-status" with no set named.

## When to use

- "How am I doing on <set>?" / "status of <set>" / "<set> collection status" — a one-glance snapshot of a family.
- Before deciding whether to buy/characterize a set — shows owned vs missing $ and whether it's configured.

**Don't** use for:
- The actual shopping list → [[missing-from-set]] (`mm query missing-set`).
- Auditing a Mana Pool cart → [[cart-check]].
- Per-scene completion tables → `scripts/scene_table.py`.
- Free-form DB questions → [[inventory-query]].

## The canonical recipe

```bash
uv run python scripts/set_status.py <anchor>   # one family
uv run python scripts/set_status.py             # collection-wide overview (all owned families)
```

That's the whole happy path. `<anchor>` = a parent OR member code; omit it for the overview. Relay the entire stdout markdown block verbatim.

## Output shape

A title line + one compact `Metric | Value` table:

| Metric | Meaning |
|---|---|
| Family | parent code + # family set codes |
| Set codes | every family code with its `set_type` |
| Ingests | # successful checklist ingests for the family (`set:`/`jumpstart:`/`precon:` labels) |
| Owned | distinct printings / total physical cards · **live** $ value |
| Precons | count by format (commander / jumpstart / …), via the `source_set_code` hard link; omits zero buckets |
| Missing | **live** $ value / # missing printings — or `not configured` if the family has no `FAMILY_DUPE_FOIL_PROMO_TYPES` entry |
| Characterized | `yes → docs/sets/<parent>.md` or `no` |

**Prices are live** (fetched each run via the rate-limited Scryfall wrapper), so the $ figures are current and the output is NOT byte-identical day-to-day — that's intended.

### Overview shape (no-arg mode)

`scripts/set_status.py` with no anchor emits `## Collection overview · N families` + a table: `Family | Owned (prints/qty) | $ (owned) | Precons | Missing | Char`, sorted by owned $ desc, ending in a bold **Total** row. Relay it verbatim, same as the single-family table.

Two deliberate differences from the single-family report, worth stating in one line beneath the table if the user might wonder:
- **Missing is a print COUNT** (`165 prints`), not a live $ — the overview does ONE bulk owned-price fetch and skips the per-family missing-$ call to stay fast. For the live missing $ of one family, run `/set-status <anchor>`.
- **Char column is 3-state:** `✓` = characterized · `✗` = characterizable but not yet done · **`-` = n/a** (not a characterizable family). `-` is the universal n/a marker in these chart outputs (also appears in Missing/Precons when not applicable). Only offer to characterize a `✗` family the user names (see below) — NEVER a `-` family.

**`-` (non-family) sets** are grab-bag collector/promo products that reprint cards from many OTHER sets and don't form a coherent family — `sld` (Secret Lair Drop), `spg` (Special Guests), `pw25`, `pmei`, `sch` (the `NON_FAMILY_SETS` frozenset in `scripts/set_status.py`). They have no meaningful "missing from set" notion and are never characterized. Their owned $/counts are still real and shown.

**Family grouping is set_targets-authoritative.** The overview (and single-anchor metrics) honor the user's registered `set_targets.related_codes` over the raw Scryfall `parent_set_code` graph — so e.g. `mar` (Marvel Universe, which Scryfall roots separately) folds into the `spm` row instead of floating as its own family. A code the user grouped under an anchor counts under that anchor everywhere.

## Uncharacterized families — auto-characterize (don't ask)

If the report shows **Characterized: no** and/or **Missing: not configured**, the family has no `docs/sets/<parent>.md` and isn't set up for missing-set. **Do NOT ask whether to characterize — just do it** (user directive, 2026-08-30). After relaying the report, immediately invoke the [[characterize-set]] skill on the **parent** code (the one in the report title, not the member the user typed) and follow its full protocol; afterward, re-run `set_status.py <parent>` to show the now-complete report (Missing $ + Characterized: yes).

This applies to the single-anchor mode. In the **no-arg overview**, do NOT auto-characterize every `✗` family (that could be a dozen at once) — instead auto-characterize only when the user names a specific `✗` family to act on.

**NEVER auto-characterize a `-` (non-family) set** — `sld`/`spg`/`pw25`/`pmei`/`sch` are grab-bag collector/promo sets that reprint cards from other sets; they don't form a family and have no missing-from-set notion. If the user asks to characterize one, explain it's not a characterizable family rather than running the protocol.

## Guardrails

- **Read-only.** No DB writes, no `queries/` artifacts (unlike cart-check / missing-set). The only external calls are read-side Scryfall price fetches via the rate-limited wrapper.
- **Live prices** come from `/cards/collection` (batched, 24h-cached at the wrapper) — current as of the run, subject to the cache window.
- **Member normalization** is automatic; always report the parent the script resolved (shown in the title), not the member the user typed.

## Cross-references

- `scripts/set_status.py` — the script this skill drives.
- `src/magic_manager/sets.py:resolve` — family resolution; note `.code` stays the member, so the script derives the true parent from the null-`parent_set_code` member.
- `src/magic_manager/missing.py:missing_printings` — the missing metric source (side-effect-free; never shell `mm query missing-set` here, it writes files).
- `src/magic_manager/decks.py` — `source_set_code` hard link the precon count uses.
- [[characterize-set]] — onboarding protocol offered when a family is uncharacterized.
- [[missing-from-set]] — the buy-list follow-up.
- [[cart-check]] / [[foil-diff]] — sibling deterministic, script-driven skills.
