---
name: card-floor
description: "Cheapest-printing \"floor\" report for any set of cards — given a selector (set:/cards:/deck:/inventory/wishlist:) or a pasted decklist, reports for each printing its own price AND the cheapest printing of the same card (by oracle id) at a chosen scope, so you see the cheapest way to get each card's mechanics into a deck. Scopes: anywhere (live batched Scryfall floor across every set — the default), in-family (local floor within the selection's set family), local (local floor across all synced printings). Finish modes: either (cheaper finish, nonfoil-preferred) or preserve (keep nonfoil/foil floors distinct). Triggers: \"/card-floor\", \"cheapest printing of these cards\", \"cheapest way to get <cards> into a deck\", \"floor price for <selector>\", \"what's the cheapest version of <card> anywhere\", \"cheapest in-family printing\", \"cheapest reprint of these\", \"floor these cards keeping finish\"."
---

# card-floor

Deterministic, script-driven. Claude invokes `scripts/card_floor_report.py <selector>` (or `--stdin` for a pasted block) and **relays the script's stdout markdown table verbatim** into chat. No inline computation, no eyeballing prices — the engine (`magic_manager.card_floor`) is the single source of truth for every floor figure. Any stderr notes (counts, unresolved cards, where artifacts were written) are surfaced briefly beneath the table.

## What a "floor" is

The **cheapest printing of a card** — by `oracle_id`, since every printing of a card plays identically, so the floor is the cheapest *functional equivalent* regardless of art/frame/treatment. It answers "what's the cheapest way to get this card's mechanics into a deck." For each printing in the selection the report shows two things:

- **This print ($)** — the price of the exact printing the selector named (finish-aware, local).
- **Floor** — the cheapest printing of the same card at the chosen `--scope` (with its set / collector-number / finish), which can be a totally different, cheaper reprint.

## Scopes (`--scope`)

- **anywhere** (default) — LIVE, batched `oracleid:` Scryfall search across every set a card was ever printed in. This is the "absolute cheapest anywhere" floor. Batched (⌈N/20⌉ requests, not one per card) and 24h-cached at the wrapper.
- **in-family** — LOCAL floor restricted to the resolved set *family* of the selection (e.g. a `set:fin` selection folds in its 8 siblings). "Cheapest I can get it from within this family." No network.
- **local** — LOCAL floor across every synced printing in the DB. No network.

## Finish modes (`--finish`)

- **either** (default) — one floor column: the cheaper finish, nonfoil preferred on a tie.
- **preserve** — two floor columns (nonfoil / foil) kept distinct, since a print may exist in only one finish and the cheapest nonfoil vs cheapest foil can live in *different* sets. Use this when the finish matters (e.g. "cheapest foil of each of these").

## The canonical recipe

```bash
uv run python scripts/card_floor_report.py '<selector>'                       # anywhere, either (default)
uv run python scripts/card_floor_report.py '<selector>' --scope in-family     # within the family, local
uv run python scripts/card_floor_report.py '<selector>' --finish preserve     # keep nonfoil/foil distinct
printf '1 Sol Ring (CMM) 425\n' | uv run python scripts/card_floor_report.py --stdin
```

`<selector>` is the universal selector DSL — `set:CODE[+related]`, `cards:SCRYFALL_QUERY`, `scryfall:Q`, `deck:SLUG`, `inventory`, `wishlist:CATEGORY`, with any modifiers (`missing`, `rarity=`, `treatment=`, `cn>=`, …). Reuse it so a floor report rides the same "set of cards" grammar as the rest of the read side. For an ad-hoc pasted list, pipe a Moxfield-style block and pass `--stdin` (exactly one of a selector OR `--stdin`).

Relay the entire stdout markdown block verbatim.

## Output shape

A title line + one table, one row per printing in the selection, sorted by card name then set then CN:

| Column | Meaning |
|---|---|
| Card | the printing named by the selector (Scryfall-hyperlinked by name) |
| CN | its set + collector number |
| This print ($) | that printing's own price, in the row's finish (local) |
| Cheapest floor (set/finish) | `either` mode: the cheapest printing at the scope — `$X.XX (SET #cn, finish)` |
| Floor nonfoil / Floor foil | `preserve` mode instead: the cheapest printing in each finish, distinctly |

Example (anywhere, preserve): Temporal Trespass's cheapest nonfoil is the original **FRF #55** while its cheapest foil is **ACR #160** — different sets per finish, which `preserve` surfaces and `either` would collapse.

**Prices are live** for `--scope anywhere` (fetched each run via the rate-limited Scryfall wrapper, 24h-cached), so the anywhere $ figures are current and NOT byte-identical day-to-day — that's intended. `in-family` / `local` scopes use the DB's last-synced prices (deterministic between syncs).

## Artifacts

Writes JSON + XLSX under `output/card-floor/reports/` (`card-floor-<scope>-<finish>-<timestamp>.{json,xlsx}`), matching the edhrec / sealed-value artifact pattern — the JSON doubles as the web-app data contract (one row per printing: identity + `this_print_usd` + the floor object(s) with usd/finish/set/cn). Mention the file paths beneath the table; the markdown is the chat deliverable.

## When to use

- "What's the cheapest way to get these cards into a deck?" → default (anywhere, either).
- "Cheapest version of each of these anywhere" / "cheapest reprint" → anywhere.
- "Cheapest I can get these from within <family>" → `--scope in-family`.
- "Keep foil vs nonfoil separate" / "cheapest foil of each" → `--finish preserve`.

**Don't** use for:
- The canonical family buy-list with ManaPool/TCGplayer bulk-add files → [[missing-from-set]] (`mm query missing-set`).
- Foil-vs-nonfoil *premium* ranking (how much extra foil costs) → [[foil-diff]].
- Family topology / owned-$ / missing summary → [[set-status]] (it already shows the in-family + anywhere functional-missing floors for a whole family).
- Secret Lair drop valuation (includes its own floor column) → [[secret-lair-value]].

## Guardrails

- **Read-only.** No DB writes; the only side effect is the `output/card-floor/reports/` artifacts.
- **Scryfall is hook-gated** — the script only reaches the network through `magic_manager.card_floor` → `scryfall.py` → the rate-limited wrapper. Never hand-roll a floor lookup or ad-hoc `curl`; that's exactly the duplication this engine consolidated.
- Thin relay: don't recompute or re-sort in chat. If the selector is bad the script exits 2 with a message on stderr — surface it; don't guess a fix.
