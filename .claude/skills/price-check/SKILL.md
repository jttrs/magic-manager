---
name: price-check
description: Check whether the prices you're about to pay for cards are sane vs true (TCGplayer/Scryfall) market — flagging any card priced X%+ over market, usually a scarcity/limited-availability premium. Organized by marketplace MODE; the only mode implemented today is `manapool` (fetches your live Mana Pool cart automatically and grades each line). Triggers: "price-check my cart", "check my manapool cart", "am I overpaying on manapool", "am I getting swindled", "is this cart a good deal", "grade my cart vs market".
---

# price-check

Answers **"before I buy, am I paying a sane price for each card vs the broader
market?"** — catching cards priced well over true market, usually because a
marketplace is thin on that specific printing (limited availability). It is a
per-card sanity check against TCGplayer/Scryfall market, NOT a marketplace
optimizer-efficiency verdict.

## Modes (by marketplace)

This skill is organized around per-marketplace **modes**. Each mode knows how to
(a) obtain the list of cards + the prices you'd pay on that marketplace, and
(b) hand them to the shared comparison against Scryfall/TCG market.

| Mode | Status | What it does |
|---|---|---|
| `manapool` | ✅ implemented | Fetch your live Mana Pool cart, grade each line vs market. |
| `tcgplayer` | 🔜 planned | (future) Same idea for a TCGplayer cart/list. Not built yet. |

Default/only mode today is `manapool`. When the user says "price-check my cart"
without naming a marketplace, assume `manapool`.

---

## Mode: `manapool`

### Pipeline (two scripts)

```bash
# 1. fetch the live cart (auto), 2. grade it vs market
uv run python scripts/manapool_cart.py | uv run python scripts/manapool_price_check.py
```

`manapool_cart.py` emits normalized cart JSON; `manapool_price_check.py` maps
each line to a Scryfall id, pulls Mana Pool + Scryfall prices, and renders the
table. Relay the table + the footer verbatim.

### Cart fetch — two paths (auto: headless, else bookmarklet)

`manapool_cart.py` tries the automatic path first:

- **headless (default, no browser).** Uses `MANAPOOL_EMAIL` +
  `MANAPOOL_PASSWORD` from the gitignored `.env` to mint a short-lived Supabase
  session token (in memory only, never written), reads your RLS-scoped cart
  server-side, enriches it. Fully hands-off. **This is what runs if the password
  is set** — nothing for the user to do.
- **bookmarklet (manual fallback, always works).** If headless is unavailable
  (no password, or the undocumented backend changed), install the bookmarklet
  from `.claude/skills/price-check/cart-bookmarklet.js`, click it on
  `manapool.com/cart`, then:
  `pbpaste | uv run python scripts/manapool_cart.py --file -`.

Force one path with `--method headless|bookmarklet`. The script prints which
path succeeded on stderr.

### What the table shows

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

### Reading it correctly

- **⚠️ = a real overpay** (≥ threshold, default 50%, over true market). This is
  the swindle signal — a card the marketplace is thin on / has priced far above market.
- **MP cheapest ≈ your price** on a flagged card means it's a **scarcity/
  availability premium**, not the optimizer picking a pricier seller (even MP's
  floor is high). **MP cheapest < your price** on a flagged card means the
  optimizer chose a costlier seller for consolidation — usually fine.
- A big **%** on a cheap card is small money (+38% on a $2 card = +$0.86); the
  footer's "total $ over market on flagged lines" is the real exposure.
- Cards priced *under* market show negative % — you're getting a deal there.

### Flags / options

| Flag | Effect |
|---|---|
| `--file PATH` / `--file -` | Read cart JSON from a file / stdin (bookmarklet output). |
| `--method headless\|bookmarklet` (on manapool_cart.py) | Force one fetch path. |
| `--over-market-pct N` | ⚠️ flag threshold: %% over Scryfall market. Default 50. |

---

## Adding a mode (e.g. `tcgplayer`)

A mode needs two things, then it reuses the shared market comparison:
1. **Get the cards + your prices** — a `scripts/<market>_cart.py`-style fetcher
   emitting normalized line JSON (`card_id`/scryfall_id, price_cents, finish).
2. **Map + compare** — reuse the `manapool_price_check.py` shape: map each line
   to a scryfall_id, pull Scryfall market via `scryfall.collection`, flag
   over-market lines. The comparison + table are marketplace-agnostic; only the
   fetch + the "your price" source differ.

Keep any marketplace's raw-API access behind a rate-limited wrapper + guard hook
(see `manapool-search/manapool.sh` + `.claude/hooks/manapool-guard.sh` as the
template), and secrets in the gitignored `.env`.

## Guardrails

- **Read-only.** No writes to the DB or to any marketplace; never modifies a cart.
- **Secrets only from `.env`** (gitignored): e.g. `MANAPOOL_EMAIL`,
  `MANAPOOL_ACCESS_TOKEN`, `MANAPOOL_PASSWORD`. Session JWTs are held in memory
  only — never logged/written.
- **Sanctioned APIs via rate-limited wrappers** (`manapool-search/manapool.sh`),
  with a PreToolUse guard hook blocking ad-hoc curl to marketplace hosts.
- **Undocumented-backend caveat (manapool):** the headless cart path reads Mana
  Pool's Supabase backend (`sb-api.manapool.com`), undocumented and subject to
  change. The bookmarklet path and the price comparison (sanctioned
  `/products/singles` API) are the durable core; if headless breaks, fall to the
  bookmarklet.

## Cross-references

- `.claude/skills/manapool-search/manapool.sh` — sanctioned catalog/price wrapper (manapool mode).
- `scripts/manapool_cart.py` — manapool cart fetch (headless, else bookmarklet).
- `scripts/manapool_price_check.py` — the comparison table.
- `.claude/skills/price-check/cart-bookmarklet.js` — manapool bookmarklet (fallback fetch).
- [[foil-diff]] — sibling price-analysis skill (foil vs nonfoil gap).
- [[missing-from-set]] — produces want-lists you could also run through a marketplace optimizer.
