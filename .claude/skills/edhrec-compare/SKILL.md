---
name: edhrec-compare
description: EDHREC "how do two commanders' recommended cards compare?" workflow. Given TWO commanders, partitions the union of their EDHREC recommended cards into Only-A / Both / Only-B, carrying each side's inclusion %, the biggest-disagreement shared cards, and local type/mana-value/lowest-USD. Always invokes `mm edhrec compare "<A>" "<B>"`, which emits a markdown report to chat plus JSON + XLSX + an image-first filterable HTML gallery under output/edhrec/reports/. Triggers "compare edhrec staples of X and Y", "what cards overlap between X and Y", "X vs Y commander comparison", "diff two commanders' recommended cards", "which cards are unique to X vs Y", "what do X and Y both run".
---

# EDHREC — compare two commanders (workflow D)

Deterministic, script-driven. Given two commanders, EDHREC's community data says which cards each one's decks run; this skill partitions the union — cards unique to each commander vs. cards both share — and surfaces where the two archetypes most disagree.

## When to use

- "Compare `<commander A>` and `<commander B>` on EDHREC" / "`<A>` vs `<B>`"
- "What cards do `<A>` and `<B>` both run?" / "what's unique to each?"
- "Which staples differ most between `<A>` and `<B>`?" (the disagreement view)

**Don't** use for:
- One commander's staples → [[edhrec-commander]] (workflow A).
- Which commanders run a card → [[edhrec-card]] (workflow B).
- General top-commanders/cards/salt rankings → [[edhrec-rankings]] (workflow C).

## The canonical recipe

```bash
uv run mm edhrec compare "<A>" "<B>"      # e.g. "Obeka, Brute Chronologist" "Edea, Possessed Sorceress"
```

Each `<commander>` is a name or a printing (`SET CN`, e.g. `cmm 425`). Both must be commander-eligible (the command gates on it). The command:

1. Resolves each ref to its oracle name, derives the EDHREC slug, and reads that commander's FULL recommendation set (every category list) from the local cache — syncing on demand (via the rate-limited `edhrec.sh` wrapper) only if the page isn't already cached.
2. Dedupes each commander's cards (one entry per card, categories kept as tags), then partitions the union by card into **Only A / Both / Only B** (keyed on oracle id).
3. Enriches every card with local type / mana value / lowest USD + a representative printing's image (via `sets.lowest_price_by_oracle`).
4. Emits a markdown report (three bucket tables + a biggest-disagreement table of shared cards by |A % − B %|) to chat, plus JSON + XLSX + a self-contained **HTML gallery** under `output/edhrec/reports/`.

## Flags

| Flag | Effect |
|---|---|
| `--top N` | Rows per bucket table in the markdown (default 25). The HTML gallery always carries every card. |
| `--sort inclusion\|synergy\|trend\|delta` | Markdown bucket-table sort axis (default: inclusion). The HTML gallery is interactively sortable across all four. |
| `--refresh` | Pricing is local-first by default; pass this to also re-sync stale (>7d) sets. Cards from unsynced sets show blank type/MV/price. |

## The HTML gallery

An image-first, filterable local HTML file (no server) — the visual counterpart to the markdown. Sections = the three buckets (Only A / Both / Only B); filter chips = EDHREC category tags (topcards, creatures, lands, …); each card shows a badge with each commander's inclusion %. Sort by value / name / collector-number / inclusion / synergy / trend / disagreement-Δ. Images lazy-load from Scryfall's CDN.

## Output

Relay the markdown report to chat and print the three `file://` artifact links (JSON + XLSX + HTML). Don't re-render the tables from the JSON — the script's stdout is the source of truth. Point the user at the HTML gallery for the image-first, filterable view. The JSON artifact is the machine-readable form (also the web-app data contract).
