---
name: card-diff
description: Three-pool "diff vs collection" report for a Magic set family (or a collection-wide chart across every owned family) — missing printing (every art/frame variant not owned), missing functional (mechanically-unique cards owned in ZERO printings), and variant-chase (missing printings whose card you ALREADY own — the borderless/alt-art/fancy-foil chase). Triggers: "card diff", "variant chase", "what variants am I missing", "collection diff chart", "missing printing vs functional", "what alt-arts do I need for cards I already own".
---

# card-diff

Deterministic, script-driven. Claude invokes `mm query card-diff [code] [--pool …]` and relays stdout verbatim. No inline computation — the CLI command (`magic_manager.card_diff` + `magic_manager.missing`) is the single source of truth for counts, $ figures, and Scryfall URLs.

## The three pools

- **printing** — `missing.missing_printings`: every distinct art/frame printing not owned (the same union `mm query missing-set` buys against).
- **functional** — `missing.functional_missing`: mechanically-unique cards (by `oracle_id`) owned in ZERO printings — "cards I don't have access to at all," priced at the cheapest in-family fill.
- **variant-chase** — `missing.variant_chase_printings`: the complement of functional within printing-missing — printing-missing rows whose `oracle_id` you ALREADY own elsewhere in the family. This is the borderless / alt-art / fancy-foil chase for a card whose base copy you already have.

`printing = functional ∪ variant-chase` (candidate oracle_ids split into "owned zero printings" vs "owned ≥1 printing but missing this specific variant").

## Two modes

**No CODE → collection-wide chart.** `mm query card-diff` with no argument runs `card_diff.collection_diff()` over every owned+configured family and emits ONE table: `Family | Collection $ | Missing printing (n·$) | Missing functional (n·$) | Variant-chase (n·$)` + a bold Total row. **Counts/$ only — no URLs** (a chart over dozens of families can't usefully carry Scryfall links for all of them). Use this for "how much variant-chase do I have across my whole collection" / "collection diff chart".

**WITH a CODE → single-family drill-in.** `mm query card-diff <code>` resolves the family (any member or anchor code), prints an `Owned: P printings / Q cards · $X` line, then for each requested pool a `## <Pool> — N prints · $X` header followed by the SAME chunked Scryfall-URL table shape as [[missing-from-set]] (`| # | Printings | Price band | URL |`, cheapest-first, chunked at `--chunk-size` default 20). This is where you actually get shopping links.

## `--pool` filter

`--pool printing|functional|variant-chase|all` (default `all`) narrows the single-family report to one pool. Has no effect on the no-arg overview (which always shows all three columns).

## When to use

- "What variants am I missing for `<set>`?" / "variant chase for `<set>`" → single-family mode, `--pool variant-chase`.
- "How much would it cost to own every mechanically-unique card in `<set>`?" → single-family mode, `--pool functional`.
- "Collection diff chart" / "how's my variant-chase across everything" → no-arg mode.

**Don't** use for:
- The canonical buy-list workflow with XLSX + ManaPool/TCGplayer bulk-add files → [[missing-from-set]] (`mm query missing-set`) — card-diff emits chat-only URLs, no file artifacts.
- Family topology / owned-$ / precon counts / characterization status → [[set-status]].

## Guardrails

- **Read-only.** No DB writes, no `output/` artifacts — chat-only, like set-status.
- **Live prices**, same `/cards/collection` wrapper as set-status/missing-set — current as of the run, 24h-cached.
- An unresolvable or unconfigured code (no `FAMILY_DUPE_FOIL_PROMO_TYPES` entry) exits 2 with a stderr note — surface it rather than guessing.

## Cross-references

- `src/magic_manager/card_diff.py` — the engine (`family_diff`, `collection_diff`).
- `src/magic_manager/missing.py` — the three pool primitives (`missing_printings`, `functional_missing`, `variant_chase_printings`, `owned_oracle_ids`).
- `src/magic_manager/family_status.py` — shared family-resolution/owned-summary/live-price helpers (also used by `scripts/set_status.py`).
- `src/magic_manager/scryfall_urls.py` — the shared URL-chunking helper (also used by `mm query missing-set` and `mm query url --mode prints`).
- [[missing-from-set]] — the buy-list sibling (XLSX + bulk-add files, printing pool only).
- [[set-status]] — family topology + both missing figures as part of a broader status block (card-diff is the drill-down with URLs + the variant-chase split).
