# Deals: reading open tabs and store prices — design + known failure modes

Status: design for the internal `deals` feature (plan item B). The rules below come from a real
session that hit every one of these; the deterministic tools MUST handle them, not an agent.

## Pipeline

1. **Tabs → URLs** (local, macOS, internal flag `deals`). Read every open tab of the user's
   browser with `osascript` (same approach as the `scrape-browser-tab-urls` skill). Output
   `{url, title, window, tab}`; **key everything by URL**, never by tab index.
2. **URL → vendor recipe.** A catalog (`magic_manager/vendors/`) matches the host to a recipe.
   Unknown shopping hosts are listed as "no recipe yet"; non-shopping hosts are dropped.
3. **Recipe → listing** `{title, price (face, USD), sold_out, identifiers?, source}` via the
   recipe's read mode (below).
4. **Listing → product.** Sealed products resolve to an MTGJSON `sealedProduct`; singles resolve
   to a printing. Unresolved listings ask the user to confirm a candidate.
5. **Deal** = face price vs market (sealed market / cards inside / single's price), in Market's
   engine.

## Read modes (per recipe)

| Mode | How | When | CI-checkable |
|---|---|---|---|
| `shopify` | server GET `<product-url>.json` (or `.js`) → variant price, `available` | Shopify stores (Many Realms, PokeBox, most card shops) | yes — live canary + fixtures |
| `meta` | server GET page → `meta[property="og:price:amount"]` / `product:price:amount`, JSON-LD `Product.offers.price` | stores that serve structured data to plain GETs | yes |
| `rendered` | read the **already-rendered tab** in the user's browser via AppleScript `execute javascript` | bot-blocked and JS-priced retailers (Best Buy, eBay, Amazon) | fixtures only (needs a real browser session) |

Never fetch a `rendered` vendor server-side: big retailers bot-block automated fetches (timeouts,
closed sockets) and their prices are JS-rendered, absent from raw HTML anyway.

## Failure modes the tools must handle

1. **AppleScript latches onto one Chrome window/instance.** A second Chrome (Playwright/automation,
   launched with `--user-data-dir=…/ms-playwright-mcp/…`) competes for the bundle id; `count windows`
   then under-reports. *Tool behavior:* enumerate per window; compare the window count to the number
   of windows that returned tabs; detect a second `MacOS/Google Chrome` process (non-Helper) via
   `ps` and report "another Chrome (automation) is running — quit it or bring your shopping window
   to the front, then read again". The state is flaky: re-read on demand, never cache tab sets.
   *Reproduced 2026-10-05:* with the Playwright MCP browser open (a Chrome with
   `--user-data-dir=…/ms-playwright-mcp/…`), the read attached to IT — 1 window, a localhost tab —
   and the warning fired; closing it restored all 3 windows / 62 product pages. **When verifying the
   deals UI with Playwright, read the tabs through the API with the Playwright browser closed.**
2. **localhost / dev-server tabs.** Always drop `localhost`, `127.0.0.1`, and the app's own origin
   (and other non-shopping hosts) programmatically.
3. **Server fetches are blocked for big retailers** → `rendered` mode (above).
4. **Chrome "Allow JavaScript from Apple Events" is off by default.** The error text is *"Executing
   JavaScript through AppleScript is turned off."* *Tool behavior:* detect it and show the one-time
   fix: Chrome menu → View → Developer → Allow JavaScript from Apple Events. Only `rendered`
   recipes need it.
5. **Reading the right price.** A body-wide `$NN.NN` regex catches installments (price ÷ 4),
   free-shipping thresholds, banners, shipping. Per recipe:
   - Shopify → `og:price:amount` / `product:price:amount` (or the `.json` variant price).
   - eBay → the **first** `US $NN.NN` (primary price element); ignore installment/shipping lines.
   - Best Buy → the **first** `$NN.NN` (the second is the ÷ 4 installment).
   - Always capture **sold out** (`/sold out|out of stock/i`).
6. **Tabs move and close.** Indices shift between reads; tabs close mid-session. Key by URL; a URL
   missing from a fresh read is reported as *closed*, not guessed.
7. **Store title ≠ MTGJSON product name / wrong set guess.** Resolve through the sealed-product
   resolver with a substring, refining on ambiguity ("draft booster" → 3 matches → "Draft Booster
   Pack"). Known traps: *Final Fantasy Starter Kit* is `fin`, not `fic`; *Secrets of Strixhaven* is
   `sos`, not `stx`. Brand-new products may not be in MTGJSON yet → "not in the catalog yet".
8. **Singles aren't sealed products.** Value them as printings (set + collector number, batched
   Scryfall collection lookup) at the **finish shown** (foil vs nonfoil). Report sealed and singles
   separately.
9. **Store metadata mislabels set/collector number.** If the set+CN lookup's card name doesn't match
   the listing title, distrust the store: search the exact card name across its set family and
   disambiguate by price (and image) — same-name variants (base / borderless / stamped / extended
   art) differ wildly (e.g. PFDN 11p stamped $21 vs FDN 11 $2.53). Flag for confirmation, never
   silently pick.
10. **Tax.** Deltas are **face price vs pre-tax market** — never pre-discount a no-tax store's price.
    "No sales tax" is a per-vendor attribute used only as a cross-store tiebreaker for the SAME
    item (gross up taxed competitors ≈ × 1.10).

## Recipe book + CI

- Each recipe ships with saved fixture pages (`tests/fixtures/vendors/<vendor>/…`) and unit tests
  that parse them (every PR).
- `shopify` / `meta` recipes also get a **nightly live canary** (one known URL per vendor) that opens
  an issue when title or price stops parsing. `rendered` recipes can't run in CI; their fixtures
  are saved DOM snapshots captured from a real tab.
- Fetching is polite: cached, rate-limited per host, honest User-Agent, robots-respecting.
