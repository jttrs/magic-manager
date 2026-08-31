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
- **Char** column is `✓`/`✗`; `✗` (or a `—` in Missing) marks an uncharacterized family. Offer to characterize any `✗` family the user names (see below), not all of them unprompted.

## Uncharacterized families — offer to characterize

If the report shows **Characterized: no** and/or **Missing: not configured**, the family has no `docs/sets/<parent>.md` and isn't set up for missing-set. After relaying the report, use **AskUserQuestion** to ask whether to run `/characterize-set <parent>` now. If yes, invoke the [[characterize-set]] skill on the **parent** code (the one in the report title, not the member the user typed) and follow its full protocol; afterward, re-run `set_status.py <parent>` to show the now-complete report (Missing $ + Characterized: yes).

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
