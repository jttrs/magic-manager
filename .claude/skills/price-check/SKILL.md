---
name: manapool-price-check
description: Before a large Mana Pool order, flag any card you're about to pay well over true market for — usually because ManaPool is thin on that specific card (limited availability). Fetches the live cart automatically (headless login), compares each line's price to Scryfall/TCGplayer market, and emits a deterministic markdown table sorted worst-first, flagging lines priced X%+ over market. Triggers: "check my manapool cart", "am I overpaying on manapool", "am I getting swindled", "grade my cart", "manapool cart vs market", "price-check my cart before I buy".
---

# manapool-price-check

Answers **"before I buy this cart, am I getting swindled on any card?"** —
i.e. paying well over true market because ManaPool happens to be thin on that
specific card. It is NOT an optimizer-efficiency verdict; it's a per-card sanity
check against the broader (TCGplayer/Scryfall) market.

## The pipeline (two scripts)

```bash
# 1. fetch the live cart (auto), 2. grade it
uv run python scripts/manapool_cart.py | uv run python scripts/manapool_price_check.py
```

`manapool_cart.py` emits normalized cart JSON; `manapool_price_check.py` maps
each line to a Scryfall id, pulls Mana Pool + Scryfall prices, and renders the
table. Relay the table + the footer verbatim.

## Cart fetch — two paths (auto: headless, else bookmarklet)

`manapool_cart.py` tries the automatic path first:

- **headless (default, no browser).** Uses `MANAPOOL_EMAIL` +
  `MANAPOOL_PASSWORD` from the gitignored `.env` to mint a short-lived Supabase
  session token (in memory only, never written), reads your RLS-scoped cart
  server-side, enriches it. Fully hands-off. **This is what runs if the password
  is set** — nothing for the user to do.
- **bookmarklet (manual fallback, always works).** If headless is unavailable
  (no password, or the undocumented backend changed), install the bookmarklet
  from `.claude/skills/manapool-price-check/cart-bookmarklet.js`, click it on
  `manapool.com/cart`, then:
  `pbpaste | uv run python scripts/manapool_cart.py --file -`.

Force one path with `--method headless|bookmarklet`. The script prints which
path succeeded on stderr.

## What the table shows

Columns, per cart line (matched on scryfall_id + finish — never name, so
borderless/foil/etched variants compare to their own printing):
`Card (hyperlinked) | Fin | Your $ | MP cheapest | Scry/TCG market | Over market ($/%)`

- **Your $** — what the cart charges you (the seller listing the optimizer picked).
- **MP cheapest** — the lowest current ManaPool listing for that finish
  (`variants[].low_price`, same price basis as your cart line). Corroboration:
  if this equals your price, even ManaPool's *floor* is that high.
- **Scry/TCG market** — Scryfall's TCGplayer-derived price, refreshed live. The
  benchmark.
- **Over market** — $ and % your price is above Scryfall market.

Sorted by **% over market, descending** — worst offenders on top. Cards with no
Scryfall price are listed separately (can't be judged).

## Reading it correctly

- **⚠️ = a real overpay** (≥ threshold, default 50%, over true market). This is
  the swindle signal — a card ManaPool is thin on / has priced far above market.
- **MP cheapest ≈ your price** on a flagged card means it's a **scarcity/
  availability premium**, not the optimizer picking a pricier seller (even MP's
  floor is high). **MP cheapest < your price** on a flagged card means the
  optimizer chose a costlier seller for consolidation — usually fine.
- A big **%** on a cheap card is small money (+38% on a $2 card = +$0.86); the
  footer's "total $ over market on flagged lines" is the real exposure.
- Cards priced *under* market show negative % — you're getting a deal there.

## Flags / options

| Flag | Effect |
|---|---|
| `--file PATH` / `--file -` | Read cart JSON from a file / stdin (bookmarklet output). |
| `--method headless\|bookmarklet` (on manapool_cart.py) | Force one fetch path. |
| `--over-market-pct N` | ⚠️ flag threshold: %% over Scryfall market. Default 50. |

## Guardrails

- **Read-only.** No writes to the DB or to ManaPool; never modifies the cart.
- **Secrets only from `.env`** (gitignored): `MANAPOOL_EMAIL`,
  `MANAPOOL_ACCESS_TOKEN` (sanctioned API), `MANAPOOL_PASSWORD` (headless cart
  fetch). The Supabase session JWT is held in memory only — never logged/written.
- **Sanctioned API for prices** goes through `.claude/skills/manapool-search/manapool.sh`
  (paced, 24h-cached, 429 backoff). The `manapool-guard.sh` PreToolUse hook
  blocks ad-hoc curl to Mana Pool hosts.
- **Undocumented backend caveat:** tiers 2/3 read Mana Pool's Supabase backend
  (`sb-api.manapool.com`), which is undocumented and may change without notice.
  Tier 1 (bookmarklet, rides the live site) and the price comparison (sanctioned
  `/products/singles` API) are the durable core; if tier 3 breaks, fall to tier 1.

## Cross-references

- `.claude/skills/manapool-search/manapool.sh` — sanctioned catalog/price wrapper.
- `scripts/manapool_cart.py` — cart fetch (headless, else bookmarklet).
- `scripts/manapool_price_check.py` — the comparison table.
- `.claude/skills/manapool-price-check/cart-bookmarklet.js` — tier-1 bookmarklet.
- [[foil-diff]] — sibling price-analysis skill (foil vs nonfoil gap).
- [[missing-from-set]] — produces want-lists you could also run the optimizer on.
