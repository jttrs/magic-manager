# Sealed-product market-price providers

The [`sealed-value`](../.claude/skills/sealed-value/SKILL.md) skill values a
sealed product two ways: **intrinsic** (card EV + deck singles, fully offline,
deterministic) and **market** (the external sealed price a store charges).
MTGJSON does NOT publish sealed-product prices (its price feed keys only on
single-card uuids — verified 0/26 M15 sealed uuids present), so market pricing
comes from external providers wired behind a pluggable seam.

**Read this** to set up (or troubleshoot) a market provider. **Update this** when
a provider's API/auth changes or a new one is added. Setup instructions here are
the durable record of the API research; the code refs are in §"Where the code
lives".

## The provider model

`scripts/sealed_value.py --market <mode>` selects the source; `sealed.py` calls
each provider's `price(node_meta) -> float | None`. **All providers are opt-in
and degrade to `None`** — an unconfigured or unreachable provider never crashes
the run; the report just shows `(manual)` with the product's TCGplayer link. The
intrinsic (EV/deck/singles) valuation always works offline regardless.

| `--market` | Providers tried | Auth | Keyed by | Role |
|---|---|---|---|---|
| `null` (default) | none | — | — | offline; market shows `(manual)` + link |
| `manapool` | manapool.com API | `X-ManaPool-Email/Token` | MTGJSON **uuid** (exact) | exact join + real sold comps |
| `tcgcsv` | tcgcsv.com | none | group + product id | broadest coverage |
| `tcgapi` | tcgapi.dev | `X-API-Key` | product **name** (search) | secondary |
| `chain` | tcgcsv → manapool → tcgapi | as above | — | first-hit (tcgcsv/TCGplayer primary) |
| `compare` | tcgcsv + tcgapi + manapool | as above | — | side-by-side table |
| `--ebay` (any mode) | eBay Browse | OAuth app token | product name (search) | **advisory only** |

Most provider requests go through a rate-limited, cached shell wrapper under
`.claude/skills/sealed-value/`; a matching PreToolUse guard hook in
`.claude/settings.json` blocks ad-hoc `curl` to each host (mirroring the
scryfall/mtgjson/manapool pattern). **Mana Pool is the exception** — it reuses
the pre-existing `.claude/skills/manapool-search/manapool.sh` wrapper +
`manapool-guard.sh` hook (no new wrapper/guard/settings). Secrets live only in
the gitignored `.env`.

---

## Mana Pool — exact-uuid join + real sold comps (chain primary)

The strongest sealed source: it joins by **exact MTGJSON uuid** (the same
`node_meta["uuid"]` every sealed `ProductNode` carries — no fuzzy name/id search
like tcgapi/eBay), and it uniquely returns **real recent-sold comps**. It's the
primary source in `--market chain`.

**Setup:** none beyond the Mana Pool creds you already use for the cart tools —
`MANAPOOL_EMAIL` + `MANAPOOL_ACCESS_TOKEN` in `.env` (sent as
`X-ManaPool-Email` / `X-ManaPool-Access-Token`). Reuses the existing
`.claude/skills/manapool-search/manapool.sh` wrapper (a new `sealed` subcommand)
and the existing `manapool-guard.sh` hook — **no new wrapper, guard, or
`settings.json` change.**

- **Endpoint:** `GET /products/sealed?mtgjson_uuids=<uuid>[&mtgjson_uuids=…]`
  (`manapool.sh sealed <uuid…>`). A row carries `set_code`, `name`,
  `tcgplayer_product_id`, `low_price`, `price_market`, `available_quantity`, and
  `recent_sales[]` — all prices in **cents**.
- **Deterministic market $** = `price_market` when > 0 (populated on liquid
  products), else `low_price` (the lowest available ask / floor). Returns `None`
  on a miss (`{"data":[]}`) or an all-zero illiquid row.
- **Sold comps (`recent_sales`)** are genuine settled transactions
  (timestamp + cents) — the data eBay's Browse API can't give. Their median is
  shown on an **advisory** `Mana Pool: $X market / $Y floor / sold-median $Z
  (n=…) / N available` line, NOT baked into the deterministic market column (the
  recent-sales set drifts per fetch). Printed whenever manapool is in play
  (`manapool`/`chain`/`compare`), independent of `--ebay`.
- Cache: 24h under `$TMPDIR/manapool-cache` (shared with the singles wrapper).

Verified live 2026-09-06: M15 Booster Box → market/floor via uuid join; CLB
Commander Decks Set-of-4 → $800 floor (matched the lone eBay sealed listing);
AFR Commander Deck Display → $399.95, tracking tcgcsv's $367.61 closely.

```bash
uv run python scripts/sealed_value.py clb "Commander Decks Set of 4" --market manapool
uv run python scripts/sealed_value.py m15 "booster box" --market chain     # tcgcsv (TCGplayer) first
```

---

## 1. tcgcsv.com — broadest coverage (no setup)

Free, no-auth mirror of TCGplayer's public price + product data. **Works out of
the box** — nothing to configure. Keyed by TCGplayer's `categoryId` (Magic = 1)
and `groupId` (== MTGJSON's `tcgplayerGroupId`, on every set file) plus each
product's `tcgplayerProductId`. Returns `lowPrice/midPrice/highPrice/
marketPrice/directLowPrice` per product subtype; we use `marketPrice`
(falling back to `midPrice`), preferring the `Normal` subtype for sealed.

Verified live: M15 Booster Box (product 90786) → `marketPrice` $375.83.

```bash
uv run python scripts/sealed_value.py m15 "2015 core set booster box" --market tcgcsv
```

No `.env` keys. Cache: 24h under `$TMPDIR/tcgcsv-cache`.

---

## 2. tcgapi.dev (TCG API) — secondary cross-check

Independent TCGplayer price data behind an API key. Useful for `--market compare`
to eyeball tcgcsv's numbers.

**Setup:**
1. Go to <https://tcgapi.dev> → **"Get API Key"** → sign up (no credit card).
2. Copy the key from your dashboard.
3. Add to the repo `.env`:
   ```
   TCGAPI_KEY=your_key_here
   ```

- **Base URL** `https://api.tcgapi.dev/v1`, header `X-API-Key`.
- **Free tier: 100 requests/day**, current prices only, non-commercial.
- **Search-only endpoint, but matched by id.** tcgapi has no lookup-by-productId
  endpoint — only `GET /v1/search?q=<query>&game=magic` (paginated via
  `meta.has_more`). BUT each result row carries `tcgplayer_id` (== MTGJSON's
  `tcgplayerProductId`). tcgapi names products `<set> - <product>` (e.g. "Magic
  2015 (M15) - Booster Box"), so a *product*-name search misses — our provider
  searches the **set name** (surfacing all the set's products at once) and
  matches back by `tcgplayer_id`, an **exact id join** as robust as tcgcsv's. No
  id match → `None`. (Verified live 2026-09-04: M15 Booster Box $375.83, same as
  tcgcsv.)
- Response fields: `id, name, tcgplayer_id, product_type ('Sealed Products' /
  'Cards'), market_price, low_price, median_price, total_listings` (we read
  `market_price` → `median_price` → `low_price`). Sealed products covered.
- `--market compare` shows tcgcsv and tcgapi **side-by-side** per product (an
  accuracy cross-check); `--market chain` uses the first source that answers.
- Cache: 24h under `$TMPDIR/tcgapi-cache`.

```bash
uv run python scripts/sealed_value.py m15 "2015 core set booster box" --market compare
```

---

## 3. eBay Browse API — advisory only (non-deterministic)

**Advisory, never deterministic.** eBay has no product-id join (unlike
tcgcsv/tcgapi), so its price is a title-matched heuristic over noisy keyword
results — `--ebay` therefore populates a separate `ebay_advisory_usd` line and
NEVER enters the deterministic artifact rows. It's a rough "street price" sanity
check, not a source of truth. Caveats from the API research + live testing:

- **Browse returns ACTIVE listings, not sold comps.** It's a "what it's listed
  at" signal. Real *settled/sold* prices require eBay's **Marketplace Insights
  API**, a restricted/approval-gated API (separate from Browse) — out of scope.
  So the advisory is labeled `active listings, not sold comps`.
- **App tokens expire in ~2 hours.** A static token in `.env` goes stale fast,
  so `ebay.sh` **mints one on demand** from your client id/secret and caches it
  with its expiry.
- **Production keyset must be activated.** A fresh production keyset returns
  `invalid_client` on token mint until you complete eBay's **Marketplace Account
  Deletion/Closure notification** step (configure an endpoint OR claim the
  exemption) on developer.ebay.com. This is an eBay-account gate, not a code
  issue — `invalid_client` with correct-format keys means "keyset not yet
  entitled for the client_credentials grant."

**How the advisory is computed (not a bare median).** A plain median of eBay's
keyword results is misleading — a "Booster Box" search returns single packs,
empty display boxes, wrong-set 2015 products (Modern Masters 2015, Fate
Reforged, Origins…), and foreign-language editions. So `ebay.py`:
1. **Buy-it-now only** (`filter=buyingOptions:{FIXED_PRICE}`) — no auctions /
   active bidding wars (and Browse can't see settled auction prices anyway).
2. **Condition filter** — New/Factory-Sealed by default; `--ebay-inspection`
   also admits like-new / near-mint "opened for inspection" listings.
3. **Title match** — requires ALL product-type tokens (a `booster box` query
   needs both `booster` AND `box`, excluding single packs), a discriminator
   (year/set-code like `2015`/`m15`), and FULL overlap of the set-identity words
   (`core`/`set`), so a shared year can't collapse M15 onto Modern Masters 2015.
   Negative markers (`empty`, `promo booster`, `6-card`, lot `10x`/`5x`, `pack
   case`…) and non-English editions are excluded.
4. **Interquartile-trimmed median** over the survivors, with the reported
   **range** taken over the same trimmed core (so one keyword-bait listing skews
   neither the median nor the range).
5. **Confidence + candidates** — returns `EbayAdvisory{price, low, high,
   n_matched, conditions, confidence (none/low/medium/high from sample size +
   spread), candidates[]}`. The report prints the price WITH its range,
   confidence, condition breakdown, and the top matched listings (title + item
   URL + image URL) so a human — or a vision check on the image — can confirm
   the SKU before trusting the number. Fewer than 3 matches → `None` (an honest
   "can't confidently price" over a noisy guess).

**Setup:**
1. Register at <https://developer.ebay.com> → create a **Production keyset**.
2. From the keyset, copy the **App ID (Client ID)** and **Cert ID (Client Secret)**.
3. Add to the repo `.env`:
   ```
   EBAY_CLIENT_ID=your_app_id
   EBAY_CLIENT_SECRET=your_cert_id
   ```
   (Optional override: set `EBAY_OAUTH_TOKEN=<pre-minted bearer>` instead — but
   it expires in ~2h, so the client-id/secret path is preferred.)

The wrapper exchanges them for an application token via the client_credentials
grant:
```
POST https://api.ebay.com/identity/v1/oauth2/token
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded
grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope
```
→ `{access_token, expires_in, token_type}`; cached under `$TMPDIR/ebay-state/
token.json` and reused until ~60s before expiry.

- Default marketplace `EBAY_US` (override `EBAY_MARKETPLACE`); default scope
  `.../oauth/api_scope` (override `EBAY_OAUTH_SCOPE`).
- Search: `GET /buy/browse/v1/item_summary/search?q=<name>&limit=100&filter=buyingOptions:{FIXED_PRICE}`.
- Cache: 1h (advisory data is intentionally fresh) under `$TMPDIR/ebay-cache`.

```bash
uv run python scripts/sealed_value.py m15 "2015 core set booster box" --market compare --ebay
uv run python scripts/sealed_value.py m15 "2015 core set booster box" --ebay --ebay-inspection
```

Live-verified 2026-09-05: M15 Booster Box → `$349.95 range $325–$380 [medium
confidence, n=5 Factory Sealed]`, all matched listings confirmed as genuine M15
English Core Set boxes (title + image cross-check) — vs tcgcsv/tcgapi's
deterministic $375.83 (a sensible eBay active-listing discount).

---

## Where the code lives

- Providers: `src/magic_manager/{tcgcsv,tcgapi,ebay,manapool}.py` — each a thin
  client + a `sealed.MarketProvider` (`price(node_meta) -> float | None`),
  memoized. `manapool.py` + `ebay.py` also expose `full()` for the advisory line.
- Wrappers: `.claude/skills/sealed-value/{tcgcsv,tcgapi,ebay}.sh` (cached,
  rate-limited, `.env`-reading; exit 7 = "not configured"). **Mana Pool reuses
  `.claude/skills/manapool-search/manapool.sh`** (`sealed` subcommand; exit 2 =
  missing creds) — not a new wrapper.
- Guards: `.claude/hooks/{tcgcsv,tcgapi,ebay}-guard.sh`, registered in
  `.claude/settings.json` — block ad-hoc `curl` to each host. Mana Pool reuses
  the pre-existing `manapool-guard.sh` (already allowlists its wrapper).
- Seam + assembly: `sealed.MarketProvider` / `NullMarketProvider` /
  `ChainMarketProvider` / `CompareMarketProvider`; `sealed.make_market_provider`.

## Secrets

`TCGAPI_KEY`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` (and optional
`EBAY_OAUTH_TOKEN`) live only in the gitignored `.env` at repo root. Never commit
or log them — same rule as the `MANAPOOL_*` secrets (see `CLAUDE.md`).
