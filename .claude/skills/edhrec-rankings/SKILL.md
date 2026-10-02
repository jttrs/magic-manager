---
name: edhrec-rankings
description: EDHREC general-rankings workflow — top commanders by deck count, top played cards, or the saltiest cards, OPTIONALLY FILTERED (commanders only) by color identity (--color), creature type or theme (--tag), or set/set-family (--set). Always invokes `mm edhrec rankings <commanders|cards|salt> [--color … | --tag … | --set …]`, which emits a ranked markdown table to chat plus JSON + XLSX artifacts under output/edhrec/reports/, enriched with local type/mana-value/lowest-USD. Triggers: "top commanders on edhrec", "most popular commanders", "top played cards this week", "saltiest cards", "top mono-red / azorius / bant commanders", "best 5-color commanders", "top goblin/elf/dragon commanders", "top treasure/aristocrats commanders", "top commanders from <set>", "edhrec rankings", "most used cards in commander".
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

## Filtered commander rankings

Narrow the COMMANDER ranking by one axis (mutually exclusive; commanders scope only):

```bash
uv run mm edhrec rankings commanders --color mono-red    # or: wu, azorius, bant, five-color, colorless
uv run mm edhrec rankings commanders --color wu          # WUBRG letters → the guild (azorius)
uv run mm edhrec rankings commanders --tag goblins       # creature type
uv run mm edhrec rankings commanders --tag treasure      # theme (same /tags/ namespace)
uv run mm edhrec rankings commanders --set fin           # set family (unions all its codes)
```

- `--color`: WUBRG letters in any order (`wu`, `rgw`, `wubrg`), a guild/shard/wedge/nephilim name (`azorius`, `bant`, `yore-tiller`), or `mono-<color>`/`five-color`/`colorless`. Supports `--timeframe`.
- `--tag`: a creature type (`goblins`, `elves`, `dragons`) OR a theme (`treasure`, `aristocrats`) — EDHREC serves both from one namespace. **All-time only** (timeframe not supported by EDHREC for tags).
- `--set`: a set name or code; expanded to its family via `sets.resolve` and unioned. Timeframe N/A.
- Filters **do not stack** — pick one. (EDHREC has no combined mono-red+goblins ranking.)

## Flags

| Flag | Effect |
|---|---|
| `--timeframe week\|month\|year` | Ranking window for `commanders`/`cards` (default `week`; ignored for `salt`, `--tag`, `--set`). |
| `--color` / `--tag` / `--set` | Commander-only filters (mutually exclusive) — see above. |
| `--top N` | Show at most N entries (default 50). |
| `--refresh` | Pricing is local-first by default (missing sets always sync, stale sets just warn); pass this to also re-sync stale (>7d) sets. |

## Output

Relay the markdown table to chat and print the two `file://` artifact links (JSON + XLSX). Don't re-render from the JSON — the script's stdout is the source of truth.
