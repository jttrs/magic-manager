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
| `tcgcsv` | tcgcsv.com | none | group + product id | **primary** |
| `tcgapi` | tcgapi.dev | `X-API-Key` | product **name** (search) | secondary |
| `chain` / `compare` | tcgcsv → tcgapi | as above | — | first-hit / side-by-side |
| `--ebay` (any mode) | eBay Browse | OAuth app token | product name (search) | **advisory only** |

Every provider request goes through a rate-limited, cached shell wrapper under
`.claude/skills/sealed-value/`; a matching PreToolUse guard hook in
`.claude/settings.json` blocks ad-hoc `curl` to each host (mirroring the
scryfall/mtgjson/manapool pattern). Secrets live only in the gitignored `.env`.

---

## 1. tcgcsv.com — primary (no setup)

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

**Advisory, never deterministic.** eBay prices vary per fetch, so `--ebay`
populates a separate `ebay_advisory_usd` line/column and NEVER enters the
deterministic artifact rows. Two important caveats from the API research:

- **Browse returns ACTIVE listings, not sold comps.** It's a "what it's listed
  at" ceiling. Real sold prices require eBay's **Marketplace Insights API**, a
  restricted/limited-release API needing separate approval — out of scope here.
  We take the **median** of active-listing prices to resist lot/lowball outliers.
- **App tokens expire in ~2 hours.** A static token in `.env` goes stale fast,
  so `ebay.sh` **mints one on demand** from your client id/secret and caches it
  with its expiry.

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
- Search: `GET /buy/browse/v1/item_summary/search?q=<name>&limit=50`.
- Cache: 1h (advisory data is intentionally fresh) under `$TMPDIR/ebay-cache`.

```bash
uv run python scripts/sealed_value.py m15 "2015 core set booster box" --market compare --ebay
```

---

## Where the code lives

- Providers: `src/magic_manager/{tcgcsv,tcgapi,ebay}.py` — each a thin client +
  a `sealed.MarketProvider` (`price(node_meta) -> float | None`), memoized.
- Wrappers: `.claude/skills/sealed-value/{tcgcsv,tcgapi,ebay}.sh` — cached,
  rate-limited, `.env`-reading (tcgapi/ebay). Exit 7 = "not configured" (soft;
  the Python provider catches it and drops itself).
- Guards: `.claude/hooks/{tcgcsv,tcgapi,ebay}-guard.sh`, registered in
  `.claude/settings.json` — block ad-hoc `curl` to each host.
- Seam + assembly: `sealed.MarketProvider` / `NullMarketProvider` /
  `ChainMarketProvider`; `scripts/sealed_value.py::_make_market_provider`.

## Secrets

`TCGAPI_KEY`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` (and optional
`EBAY_OAUTH_TOKEN`) live only in the gitignored `.env` at repo root. Never commit
or log them — same rule as the `MANAPOOL_*` secrets (see `CLAUDE.md`).
