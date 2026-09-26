---
name: edhrec-card
description: EDHREC "which commanders run this card?" workflow. Given any card, reports the most common commanders whose decks include it in the 99 (workflow B — the inverse of edhrec-commander), enriched with local type/mana-value/lowest-USD. Always invokes `mm edhrec card "<card>"`, which emits a markdown table to chat plus JSON + XLSX artifacts under output/edhrec/reports/. Triggers: "which commanders run <card>", "what decks use <card>", "top commanders for <card> on edhrec", "who plays <card>", "best commanders for <card>", "where does <card> get played".
---

# EDHREC — top commanders running a card (workflow B)

Deterministic, script-driven. The inverse of [[edhrec-commander]]: given a card, EDHREC says which commanders most often run it in the 99. This skill relays that as a ranked, locally-enriched table.

## When to use

- "Which commanders run `<card>`?" / "who plays `<card>`?"
- "Top commanders for `<card>` on EDHREC" / "best commanders for `<card>`"
- "What decks use `<card>`?" / "where does `<card>` get played?"

**Don't** use for:
- "What do people run WITH `<commander>`?" (the forward direction) → [[edhrec-commander]].
- General "top commanders / saltiest cards" rankings → [[edhrec-rankings]].

## The canonical recipe

```bash
uv run mm edhrec card "<card>"        # e.g. "Sol Ring"
```

`<card>` is a name or a printing (`SET CN`). The command up-levels any printing to its oracle name (all reprints collapse to one EDHREC page), fetches via the rate-limited `edhrec.sh` wrapper, and:

1. Persists the raw page (`edhrec_pages`) + normalized rows (`edhrec_card_commanders`).
2. Resolves each commander's name → `oracle_id` (local-first; one batched Scryfall by-name call fills gaps).
3. Enriches with local metadata: type, mana value, lowest USD.
4. Emits a markdown table (decks, inclusion %, type, MV, lowest $) to chat + JSON + XLSX under `output/edhrec/reports/`.

Note: EDHREC's card-page commander lists carry deck counts but no synergy/lift, so those columns are absent for this workflow (that's expected, not a bug).

## Flags

| Flag | Effect |
|---|---|
| `--top N` | Show at most N commanders (default 25). |
| `--no-refresh` | Use local prices as-is; don't re-sync stale sets first. |

## Output

Relay the markdown table to chat and print the two `file://` artifact links (JSON + XLSX). Don't re-render from the JSON — the script's stdout is the source of truth.
