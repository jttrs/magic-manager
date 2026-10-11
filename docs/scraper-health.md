# Scraper health — canaries and "temporarily down" flags

Every function that reads a third-party page, per site, is checked against a known public sample
on a schedule — deterministic, no agent. When a site changes something we depend on, that
scraper is flagged **temporarily down** in the app (with the reason code and since-when) until a
check passes again. Code: `magic_manager.scraper_health` (registry + status file),
`magic_manager.scrape_canary` (the live checks), `scripts/check_scrapers.py` (the runner).

## Inventory: every scraper, per site

Key = `<scraper>/<site>`. Stores come straight from `config/vendors.toml`, so a store added there is
covered with no other change (offline pin: its fixture + `EXPECT` row, which
`tests/test_vendor_recipes.py` already demands; live: its `sample_url`).

| Key | What it reads | Offline pin (every PR) | Live canary (daily) |
|---|---|---|---|
| `store-price/<shopify/meta store>` | store product page → price/stock/title via its recipe | `tests/test_vendor_recipes.py` (saved page per store) | HTTP: the store's `sample_url` |
| `store-price/<open-tab store>` (Best Buy, Target, eBay, …) | rendered page (companion reader / AppleScript) → recipe | `test_rendered_recipes_pick_the_right_price`, `companion-readers.spec.ts` | Browser: `[store.<key>]` in `config/scraper_canaries.toml` (or a `sample_url`). eBay: none (listings end) → real use only |
| `deck-import/archidekt` · `mtggoldfish` · `manabox` · `scryfall` | `scripts/import_deck.py` → `decksource.parse_*` | `tests/test_decksource.py` | HTTP: a public sample deck (same fetcher the app runs) |
| `deck-import/moxfield` | headed Chrome → the deck API response → `parse_moxfield` | `test_parse_moxfield_boards_and_finishes` | Browser: a public precon deck |
| `companion-deck/moxfield` | `extension/src/readers/moxfield-deck.js` → the app's strict model | `companion-readers.spec.ts` → `test_companion.py` | Browser: the same visit, reader injected verbatim |
| `companion-cart/manapool` | `extension/src/readers/manapool-cart.js` | `companion-readers.spec.ts` → `test_companion.py` | Browser: a guest (empty) cart must read as `cart.empty` — nothing is ever added to a cart |
| `companion-orders/manapool` · `tcgplayer` · `cardkingdom` | `extension/src/readers/*-orders.js` (order history, signed in) → `api/purchases.py` strict models | `companion-order-readers.spec.ts` → `test_companion_orders.py` | None — signed-in pages have no public sample. Real use only: a read that saves orders clears it; the app reports `orders.page_changed` (with the store) |
| `edhrec-commander` · `edhrec-card` · `edhrec-rankings` | EDHREC's unofficial JSON → `edhrec.cardlists` / `_plan_rankings` | `tests/test_edhrec.py` | HTTP: a commander page, a card page, the weekly ranking |

`tests/test_scraper_health.py::test_every_scraper_has_an_offline_pin` keeps this table honest.
Official APIs (Scryfall search, MTGJSON, Commander Spellbook, Mana Pool catalog, TCGCSV, eBay) are
out of scope by the owner's choice (2026-10-10).

## What a check says

| Outcome | Meaning | Effect |
|---|---|---|
| `ok` | read the sample and it matched what was validated | clears a down flag |
| `fail` | the page loaded but no longer reads as validated (`scrape.no_price`, `scrape.no_cards`, `scrape.shape_changed`, `scrape.expectation`, `scrape.error`, `cart.page_changed`, `moxfield.changed`) | flags **down** (since = first failure) |
| `unverified` | the check couldn't run: blocked (`scrape.blocked`), offline (`scrape.unreachable`), sample removed (`scrape.sample_gone`), no browser | never flags, never clears |

Browser checks run headless first; anything that didn't read is retried once in a visible real
Chrome window and that verdict stands (bot defenses serve headless browsers a stripped page —
Target hides its price, Best Buy drops the connection). The window opens briefly during the
06:30 run only when needed (usually Moxfield, Best Buy, Target). `--no-window` skips the retry;
those checks are then unverified, never down.

**Real use is the backup** for what the canary can't reach (eBay, your own cart, private decks):
a Deals read that finds no price flags the store; a read that works clears it; the companion
reports `cart.page_changed` / `moxfield.changed` / `orders.page_changed` + store (`POST /api/scrapers/report`); a server deck
fetch that parses no cards flags that builder; any successful EDHREC sync clears its flag.
Blocks, private decks and empty carts never flag.

## Status file

`scraper_health.json` beside the collection DB (`MM_SCRAPER_HEALTH` overrides). Not the collection
DB, not precious, no migration: delete it and the next run rebuilds it. One record per key:
`status`, `since`, `checked_at`, `last_ok`, `code`, `message`, `via` (canary | use), `detail`.
Written atomically under a file lock.

## Schedule (zero agents)

- **Local, daily 06:30** (missed runs happen on wake): launchd `com.magic-manager.scrape-canary`
  runs `scripts/check_scrapers.py --live --no-pins --record --notify` in the live worktree against
  the real DB's folder, so the running app reads the result. macOS notification only on a change
  (down / reading again / needs a new sample). Install: `scripts/launchd/install-scrape-canary.sh
  [--run-now | --uninstall]`. Log: `~/Library/Logs/magic-manager/scrape-canary.log`.
- **GitHub, nightly**: `.github/workflows/vendor-canary.yml` (`scripts/vendor_canary.py`, the store
  half) opens or comments on one issue when a store stops reading.

## In the app

`GET /api/scrapers/health` → every scraper with its status. Where a down scraper is offered:

- Add cards → Deck and Decks → Import: a ruled notice for the pasted link's builder (the
  companion reader when it will read a Moxfield deck).
- Collection → Check my Mana Pool cart: a notice above the ways to read it.
- Market → Deals: a rust **DOWN** mark beside the store (store sections, the table's best store,
  the inspector's store lines); its tooltip says why and since when.
- Explore: a notice above the sheet for the EDHREC read it uses (commander / card / rankings).

Notices never block: you can still try, and a read that works clears the flag.
CLI: `uv run mm scrapers health [--down]`.

## When something goes down

Follow the `scrape-doctor` skill. Run one check by hand:
`uv run python scripts/check_scrapers.py --live --no-pins --json`. A removed sample: pick a new
one in `config/scraper_canaries.toml` (or the store's `sample_url`) and re-validate it by hand.
