---
name: edhrec-commander
description: EDHREC "what do people run in this commander's deck?" workflow. Given a card that CAN be a commander, reports the cards with the highest inclusion rate across that commander's decks (workflow A), enriched with local type/mana-value/lowest-USD. Always invokes `mm edhrec commander "<card>"`, which emits a markdown table to chat plus JSON + XLSX artifacts under output/edhrec/reports/. Triggers: "what do people run with <commander>", "top cards for <commander> on edhrec", "edhrec staples for <commander>", "highest inclusion cards when <card> is my commander", "build around <commander>", "what goes in a <commander> deck".
---

# EDHREC — top cards for a commander (workflow A)

Deterministic, script-driven. Given a commander card, EDHREC's community data says which cards appear most often in that commander's decks. This skill relays that as a ranked, locally-enriched table.

## When to use

- "What do people run with `<commander>`?" / "EDHREC staples for `<commander>`?"
- "Top cards when `<card>` is my commander" / "highest inclusion cards for `<commander>`"
- "What goes in a `<commander>` deck?" / "help me build around `<commander>`"

**Don't** use for:
- "What commanders run `<card>`?" (the inverse) → [[edhrec-card]].
- General "top commanders / saltiest cards" rankings → [[edhrec-rankings]].
- "What am I missing from set X?" → [[missing-from-set]]. This skill is about community deck signal, not set completion.

## The canonical recipe

```bash
uv run mm edhrec commander "<card>"        # e.g. "Atraxa, Praetors' Voice"
```

`<card>` is a name or a printing (`SET CN`, e.g. `cmm 425`). The command up-levels any printing to its oracle name (all reprints collapse to one EDHREC page), derives the EDHREC slug, fetches via the rate-limited `edhrec.sh` wrapper, and:

1. Persists the raw page (`edhrec_pages`) + normalized rows (`edhrec_commander_cards`).
2. Resolves each recommended card's name → `oracle_id` (local-first; one batched Scryfall by-name call fills gaps from unsynced sets).
3. Enriches with local metadata: type, mana value, lowest USD across printings.
4. Emits a markdown table (inclusion %, decks, synergy, type, MV, lowest $) to chat + JSON + XLSX under `output/edhrec/reports/`.

## Flags

| Flag | Effect |
|---|---|
| `--top N` | Show at most N cards (default 25). |
| `--no-refresh` | Use local prices as-is; don't re-sync stale sets first. Cards from unsynced sets show blank type/MV/price. |

## Output

Relay the markdown table to chat and print the two `file://` artifact links (JSON + XLSX). Don't re-render the table from the JSON — the script's stdout is the source of truth. The JSON artifact is the machine-readable form (also the web-app data contract).
