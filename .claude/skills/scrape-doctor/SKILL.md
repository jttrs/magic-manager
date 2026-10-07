---
name: scrape-doctor
description: Diagnose and fix a deterministic scrape that stopped reading right — the browser companion's page readers (Mana Pool cart, open store tabs, Moxfield decks), the cart bookmarklet, the Deals vendor recipes (config/vendors.toml), and the deck-import parsers (decksource). Knows where each one is pinned, how to recapture a fixture safely, how to re-pin the goldens, and which error code a failure should surface. Triggers "the cart reader broke", "cart.page_changed", "moxfield.changed", "a store's price stopped reading", "vendor canary failed", "deck import returns no cards", "re-pin the readers", "check the scrapers", "/scrape-doctor".
---

# scrape-doctor

Every scrape in this repo is **deterministic code pinned against saved pages**. When a site changes,
a pinned test fails or users see a coded error. This skill is the protocol for diagnosing and fixing
it without guessing, and without weakening the security model
(`docs/browser-companion-security.md`).

## 0. Run the pins first

```bash
uv run python scripts/check_scrapers.py            # offline: python pins + real-Chromium reader/extension pins
uv run python scripts/check_scrapers.py --live     # + reads every server-read store's sample_url today
```

Use your own e2e port in a parallel worktree (`MM_E2E_PORT=<port>`). Close any Playwright MCP
browser before reading tabs on macOS (`docs/deals-scraping.md` failure mode 1).

## 1. Find the scrape and its pins

| Scrape | Code (single source of truth) | Saved page(s) | Pinned by |
|---|---|---|---|
| Mana Pool cart (extension + bookmarklet) | `extension/src/readers/manapool-cart.js` | `tests/fixtures/companion/manapool-cart*.html` | `web/e2e/companion-readers.spec.ts` → `manapool-cart.expected.json` → `tests/test_companion.py` |
| Open-tab store page (Deals, `rendered` stores) | `extension/src/readers/store-page.js` + recipe in `config/vendors.toml` | `store-rendered.html`, `tests/fixtures/vendors/*.html.gz` | same chain → `store-*.expected.json`; server parse in `vendors.read_listing` |
| Moxfield deck (extension) | `extension/src/readers/moxfield-deck.js` → `decksource.parse_moxfield` | `moxfield-deck.json` | same chain → `moxfield-deck.expected.json` |
| Server-read stores (`shopify`/`meta`) | `config/vendors.toml` + `storepage.py` | `tests/fixtures/vendors/*` | `tests/test_vendor_recipes.py`; nightly `scripts/vendor_canary.py` |
| Deck builders (server) | `decksource.parse_*`, `scripts/import_deck.py` | inline in `tests/test_decksource.py` | `tests/test_decksource.py` |

The whole companion path (pairing, approval window, refusals) is pinned by
`web/e2e/companion-extension.spec.ts`, which loads the real unpacked extension into Chromium.

## 2. Read the error code

Every failure the user sees carries a code from **`extension/errors.json`** (the one catalog —
`<area>.<reason>` → message + fix). A failure means one of these:

- `cart.page_changed` / `moxfield.changed` / a store with `No price found on the page`: **the site
  changed its page.** Go to step 3.
- `cart.empty` / `cart.sign_in` / `cart.signed_out` / `moxfield.private` / `moxfield.blocked`: **the
  user's situation.** The message already gives the fix. Change code only if the detection is wrong.
- `request.*` / `companion.*` / `permission.*`: **the companion protocol or the user's settings**
  (`extension/src/background.js`, `bridge.js`, `web/src/core/companion.ts`). Not a scrape problem.

A new failure shape that users would only see as a generic error is a bug. Add a code to
`errors.json` with a plain message and fix, and raise it where the shape is detected.
`tests/test_companion.py::test_every_code_used_anywhere_is_catalogued` keeps code and catalog in sync.

## 3. Recapture the page (safely)

- **Never commit personal data.** Capture from a guest/anonymous session where possible (Mana Pool
  carts work signed out). Otherwise hand-reduce the page to its structure and replace names,
  addresses, emails and order ids. Keep the HTML comment at the top saying when and where it came from.
- **Mana Pool cart:** add 2–3 cards to a guest cart covering nonfoil, foil ×2 and a treated
  printing. Save `section[aria-labelledby="cart-heading"]` into `manapool-cart.html`, then clear the
  cart. Do it through a headless Playwright browser (`npx playwright` script or the Playwright MCP —
  close it afterwards). Never curl Mana Pool's API (hooks block it, and the companion never uses it).
- **Store page:** save the product page, or let `scripts/vendor_canary.py` show what it reads.
  Server-read stores keep a gzipped fixture under `tests/fixtures/vendors/`.
- **Moxfield:** the deck JSON shape is what `api2.moxfield.com/v3/decks/all/<id>` returns. Update
  `moxfield-deck.json` keeping the extra fields the reader must DROP. The test asserts they're dropped.

## 4. Fix the reader, then re-pin

1. Change the reader (`extension/src/readers/*.js`) or the recipe (`config/vendors.toml`). Readers
   stay classic scripts. Use `textContent` only, never `innerHTML`/`eval`, no network beyond what
   they already do, and keep only the fields listed in their header comment.
2. If a recipe's hosts changed: `uv run python scripts/build_extension.py` (regenerates
   `extension/src/stores.js` + the manifest's store permissions; `--check` fails CI when stale).
3. Re-pin the goldens once the output is what a human checked against the real page:
   `UPDATE_GOLDEN=1 MM_E2E_PORT=<port> npm --prefix web run e2e -- companion-readers`
   Then read the diff of `tests/fixtures/companion/*.expected.json` line by line — it IS the behavior change.
4. `uv run python scripts/check_scrapers.py` must be green. Bump `extension/manifest.json` `version`
   when shipped extension code changed (the app tells older installs to update).

## 5. Don't

- Don't widen permissions to make a read work (no `<all_urls>`, `tabs`, `cookies`, `webRequest`,
  `externally_connectable`). A new site is an opt-in optional permission plus a security-doc entry.
- Don't read credentials, cookies or storage on any site. Don't write to any site.
- Don't loosen a pinned assertion to get green. Fix the reader, or re-pin with a reviewed diff.
- Don't move price logic into the extension. Recipes stay in `config/vendors.toml`, applied server-side.
