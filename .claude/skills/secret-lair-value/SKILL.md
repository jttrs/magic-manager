---
name: secret-lair-value
description: Deterministic markdown table of the most recent N Secret Lair drops by release date (newest first), each valued from live Scryfall singles prices with NONFOIL and FOIL in separate columns, plus a per-finish FLOOR column (cheapest printing of each card anywhere on Scryfall — the cheapest way to get the cards into a deck). Drops are the merged base+Foil-Edition logical drop; each row links to a Scryfall search for that drop's exact collector numbers. Triggers: "/secret-lair-value", "value of recent Secret Lairs", "how much are the latest Secret Lair drops worth", "recent SLD drop values", "newest Secret Lairs value", "top N Secret Lair drops by value", "Secret Lair drop price table".
---

# Secret Lair Value

Deterministic, script-driven value table. Claude invokes `scripts/secret_lair_value.py [N]` and relays the script's stdout markdown block verbatim into chat, surfacing the stderr summary line briefly beneath. No inline computation, no eyeballing prices from a Scryfall page — the script is the single source of truth.

## When to use

- "What are the recent Secret Lair drops worth?" / "top N Secret Lair drops by value" / "how much would it cost to buy the latest SLDs?"

**Don't** use for:
- A single drop's card-by-card breakdown — follow that row's Scryfall search link instead and read prices off the page.
- What the user OWNS — that's [[inventory-query]] or [[set-status]]; this script never touches the DB.
- Adding SLD cards to inventory — that's [[bulk-add]].

## The canonical recipe

```bash
uv run python scripts/secret_lair_value.py [N]
```

`N` defaults to 10 (most recent 10 drops). `--limit N` also works and takes precedence if both are given. Relay the whole stdout block verbatim — title, legend, and table.

## Output shape

```
## Secret Lair Drop value — top 3 by release (newest first)

*Nonfoil $ / Foil $ sum live Scryfall singles for the drop's own Secret Lair printings. NF floor $ / Foil floor $ sum, per card, the CHEAPEST printing of that same card anywhere on Scryfall — the cheapest way to get these cards into a deck regardless of treatment. `$X (n)` = only n of the drop's cards are priced in that finish.*

| Drop | Release | Cards | Nonfoil $ | Foil $ | NF floor $ | Foil floor $ |
|---|---|---:|---:|---:|---:|---:|
| [Universes Beyond: Fallout](https://scryfall.com/search?q=set%3Asld+%28cn%3A1234+or+cn%3A1235%29) | 2025-06-09 | 8 | $42.10 (6) | $58.30 | $19.44 | $31.02 |
| [Heads I Win, Tails You Lose](https://scryfall.com/search?q=set%3Asld+%28cn%3A1240+or+cn%3A1241%29) | 2025-05-01 | 5 | $18.00 | — | $6.25 | $9.80 |
```

The `Nonfoil $`/`Foil $` columns price the Secret Lair printing itself; the `floor` columns price the cheapest way to assemble the same cards from any set. A foil-only drop shows `—` in the Nonfoil column but can still show an NF floor (a cheaper *nonfoil* printing exists elsewhere) — every drop renders, even with zero priced cards in a finish.

## Determinism guarantees

- Drops sort by `releaseDate` descending, with name ascending as the tie-break.
- Drop identity = base printing merged with any `... Foil Edition` sibling, by stripping the `" Foil Edition"` suffix from the MTGJSON deck name. A base entry's name/release date always win as canonical for the merged drop, regardless of encounter order.
- Each drop's card set is the de-duplicated union of Scryfall IDs across all its sibling decks, preserving first-seen order.
- The drop's own Secret Lair prices come from Scryfall's `/cards/collection` batch endpoint (batched 75/request, 24h-cached at the wrapper layer). Floor prices come from one `oracleid:<id> unique=prints` search per distinct card (de-duplicated by oracle id across all drops, since cards recur), taking the min `usd`/`usd_foil` over every printing. Both are 24h-cached, so same-day re-runs are byte-identical. A cold large-N run issues one search per distinct card (~1 min for N=25); warm runs are instant.
- Prices are current as of the run; they drift day to day like every live-priced skill in this repo.
- MTGJSON deck lookups are cached (forever — precon/SLD decks don't change once published).
- Each row's search URL is built from `set:sld (cn:... or ...)`, with collector numbers de-duped, any trailing `★` stripped, and ordered via `util.cn_sort_key`.
- No `Date.now()`/random — the only moving parts are Scryfall's live prices and the MTGJSON deck catalog, both cache-backed.

## Guardrails

- Read-only: no DB access, no `queries/` artifacts.
- Exit 0 on success; exit 2 on an MTGJSON or Scryfall lookup failure.
- A drop with no priced cards in a given finish renders `—` for that column — never crashes.

## Cross-references

- `scripts/secret_lair_value.py` — the script this skill drives.
- `src/magic_manager/mtgjson.py` — `deck_list`, `deck`, `deck_card_scryfall_ids`.
- `src/magic_manager/scryfall.py` — `collection` (the live batch price fetch).
- `src/magic_manager/util.py` — `fmt_usd`, `cn_sort_key`.
- [[foil-diff]] / [[set-status]] — sibling deterministic, script-driven skills.
- [[bulk-add]] — the natural upstream skill once the user decides to buy a drop.
