---
name: edhrec-rankings
description: EDHREC general-rankings workflow — top commanders by deck count, top played cards, or the saltiest cards. Always invokes `mm edhrec rankings <commanders|cards|salt>`, which emits a ranked markdown table to chat plus JSON + XLSX artifacts under output/edhrec/reports/, enriched with local type/mana-value/lowest-USD. Triggers: "top commanders on edhrec", "most popular commanders", "top played cards this week", "saltiest cards", "what are the most salt-inducing cards", "edhrec rankings", "most used cards in commander".
---

# EDHREC — general rankings (workflow C)

Deterministic, script-driven. EDHREC publishes site-wide rankings; this skill relays three of them as locally-enriched tables. Not tied to a specific card or commander.

## When to use

- "Top commanders on EDHREC" / "most popular commanders (this week)"
- "Top played cards" / "most-used cards in Commander"
- "Saltiest cards" / "most salt-inducing cards"

**Don't** use for:
- Card-specific signal ("top cards for `<commander>`" → [[edhrec-commander]]; "which commanders run `<card>`" → [[edhrec-card]]).

## The canonical recipe

```bash
uv run mm edhrec rankings commanders --timeframe week   # top commanders by deck count
uv run mm edhrec rankings cards --timeframe week         # top played cards
uv run mm edhrec rankings salt                           # saltiest cards (timeframe ignored)
```

Scope is one of:

| Scope | Endpoint | Metric shown |
|---|---|---|
| `commanders` | `/pages/commanders/<timeframe>.json` | deck count (with a real rank) |
| `cards` | `/pages/top/<timeframe>.json` | deck count |
| `salt` | `/pages/top/salt.json` | salt score (0–4) |

Each fetches via the rate-limited `edhrec.sh` wrapper, persists to `edhrec_rankings` + `edhrec_pages`, resolves entity names → `oracle_id`, enriches with local type/mana-value/lowest-USD, and emits a ranked markdown table + JSON + XLSX under `output/edhrec/reports/`.

## Flags

| Flag | Effect |
|---|---|
| `--timeframe week\|month\|year` | Ranking window for `commanders`/`cards` (default `week`; ignored for `salt`). |
| `--top N` | Show at most N entries (default 50). |
| `--no-refresh` | Use local prices as-is; don't re-sync stale sets first. |

## Output

Relay the markdown table to chat and print the two `file://` artifact links (JSON + XLSX). Don't re-render from the JSON — the script's stdout is the source of truth.
