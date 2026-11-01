# Browser companion

A Manifest V3 Chrome extension (`extension/`) plus a cart bookmarklet. They read, in the user's
**own** browser, what the server can't or shouldn't: the Mana Pool cart, open store tabs (Deals),
Moxfield and Archidekt decks, and your Moxfield collection / binders. They hand the app only the normalized lines, after the user approves each time.
This replaces the local-only paths (H9): the .env cart login, AppleScript tab reads and the
headed-Chrome Moxfield import. Those keep working on the owner's Mac when the companion isn't
connected. Security design: [`browser-companion-security.md`](browser-companion-security.md).

## Using it (beta)

1. Turn on the flag: `MM_FEATURES=companion` (plus `cart_check` / `deals` for those features) or
   `config/features.local.toml`. Restart `mm serve`.
2. App header → plug icon → **Add to Chrome** (the Chrome Web Store listing — shown once published,
   see *Chrome Web Store* below). Until then, or as a fallback, the dialog's **Developer install**:
   **Download the companion**, unzip, `chrome://extensions` → Developer mode → **Load unpacked**.
3. Companion icon → paste the app's exact address (the app's header → **Browser companion** shows it with a copy button; the field starts empty, no default port) → **Pair** (Chrome asks to allow it) → reload the app tab. The settings page then says whether that address has checked in (the worker records the paired app's last hello, `storage.local` `lastHello`); "hasn't checked in yet" means the app isn't open at exactly that address.
4. Optional: switch on **Allow access** on the companion's settings page (0.4.3: ONE switch, owner
   2026-10-11, replacing the six per-feature switches). It asks Chrome once for every site the readers
   use (`ALL_ACCESS_ORIGINS` in `protocol.js`: TCGplayer + Card Kingdom carts, the Deals stores,
   Moxfield, Archidekt, TCGplayer + Card Kingdom order history) and switching it off removes them all.
   Mana Pool is install-time (always on). Partly allowed (an older version's switches, or a store
   added since) reads Off with a note; switching on asks for the rest. Chrome's own *Site access* page
   still lists each site separately — that's Chrome's UI. The hello `features` map is still derived
   per reader from what's granted, and the `permission.*` error codes are unchanged (their fix now
   points at Allow access).

Where it shows up: Collection → Purchase history → *Read my orders* (flag `purchases`; Mana Pool,
TCGplayer, Card Kingdom order history — see [`purchases.md`](purchases.md), incl. what is and isn't
verified per store), Collection → *Check my cart* (pick Mana Pool, TCGplayer or Card Kingdom, then **Read my cart**;
the bookmarklet paste and .env login are Mana Pool only — see *Other carts* below), Market → Deals → **Read my open tabs** (tabs + open-tab store prices), Market → Deals →
Watching → **Read watched prices** (the watched open-tab store pages), Add cards → Deck and
Decks → Import (Moxfield links; Archidekt links once Allow access is on — private decks too),
Add cards → **Import a collection** → *Live from Moxfield* (your collection, one binder, or a shared link — each one button that reads). Without a connected companion each falls back to the existing path.

## Chrome Web Store

The trusted install is an **unlisted** Chrome Web Store item (anyone with the link can install; not
searchable); the unpacked zip stays as the setup dialog's collapsed *Developer install*.

- **Store URL (configurable until published):** `[chrome_web_store] url` in `extension/store/store.toml`,
  overridden by `MM_COMPANION_STORE_URL`. `companion.store_url()` accepts only
  `https://chromewebstore.google.com/detail/…`; anything else is ignored. `GET /api/companion` returns it
  as `store_url` (null = not published → the dialog leads with the developer install, open).
  `privacy_url` links the policy.
- **Listing kit** (`extension/store/`, never in the zip): `listing.md` — summary, description, single
  purpose, per-permission justifications, data-use answers, reviewer test instructions;
  `screenshots/*.png` (1280×800) + `promo-small.png` (440×280), captured from the real extension pages
  by `uv run python scripts/capture_store_assets.py`. Icons `extension/icons/icon-{16,32,48,128}.png`
  are generated from the favicon shapes by `scripts/build_extension.py` (`companion.icon_png`; `--check`
  keeps them current). Privacy policy: [`privacy-companion.md`](privacy-companion.md).
- **Release:** bump in a PR — `uv run python scripts/build_extension.py --bump patch` (the store refuses
  a version that isn't higher) — merge, then tag `companion-v<version>`. The `extension-release`
  workflow checks the tag matches the manifest, runs `tests/test_companion.py`, builds both
  reproducible zips (`--zip` folder zip for Load unpacked, `--store-zip` with the manifest at the root
  for the store) + `SHA256SUMS`, attaches them to a GitHub release and, when the four secrets
  `CWS_CLIENT_ID` / `CWS_CLIENT_SECRET` / `CWS_REFRESH_TOKEN` / `CWS_EXTENSION_ID` exist, uploads the
  store zip as a **draft** (never publishes).
- **Owner actions (one-time):** register a Chrome Web Store developer account ($5); create the item by
  uploading the first `--store-zip`; paste `listing.md` into the Store listing / Privacy practices tabs;
  set visibility *Unlisted*; submit for review. After approval put the item's URL in `store.toml`
  (and its id in `extension_id`); optionally add the four secrets for automatic draft uploads. Store
  installs auto-update; an existing developer install keeps working (a store install gets a new
  extension id, so pair it again and remove the unpacked copy).

## The bridge survives a reload or update (0.4.3)

Chrome drops dynamically registered content scripts (`chrome.scripting.registerContentScripts`) when
the extension is reloaded (↻ in `chrome://extensions`) or updated — `persistAcrossSessions` or not —
while `storage.local` (the pairing) stays. Before 0.4.3 the bridge was registered only by Pair, so a
reload left a paired app "Not connected". Now the worker owns it: `ensureBridge` (background.js) runs
at every worker start and on `runtime.onStartup` / `onInstalled`, (re)registers `bridgeScript(pattern)`
for the stored `appOrigin` (only while that address's permission is granted; unregisters when
unpaired), and after an install/update — or a Pair/Unpair from the settings page (`{type:'bridge'}`)
— injects a fresh bridge into app tabs already open on the exact paired origin, so they reconnect
without a reload. `bridge.js` keeps one live bridge per page: a bridge left from a reloaded extension
(its runtime has no id) goes silent, a second injection into a live page steps aside. A 0.4.2 bridge
still in an app tab from before this update can't be silenced; reload that tab once. Pinned by
`companion-extension.spec.ts` (pair → relaunch → connected; open tab connects on Pair, answers once).

## How it fits

| Piece | Where | Role |
|---|---|---|
| Readers | `extension/src/readers/*.js` | Deterministic page reads (classic scripts, shared with the bookmarklet). Carts: `manapool-cart.js`, `tcgplayer-cart.js`, `cardkingdom-cart.js`. Order history: `manapool-orders.js`, `tcgplayer-orders.js`, `cardkingdom-orders.js`. Decks: `moxfield-deck.js`, `archidekt-deck.js`. Moxfield collection / binders: `moxfield-collection.js`. `moxfield-api.js` = the shared Moxfield API helper (anonymous first, Moxfield's own sign-in only when needed), injected before the Moxfield readers. |
| Order reads | `extension/src/orders.js` | `order_list` / `orders` requests: its own background tab on the store's order pages, follows the pager, never your tabs, never a form. |
| Watched pages | `extension/src/watched.js` | Plan (re-check the app's URL list) → you approve → read from your tab or a background tab it closes. |
| Worker | `extension/src/background.js` | Validates the asker, runs a reader, opens the approval window, delivers the result. |
| Bridge | `extension/src/bridge.js` | Content script on the paired app origin only; relays postMessage ↔ worker. |
| Approval / settings | `extension/src/approve.*`, `options.*` | The extension's own pages. |
| Generated | `extension/src/stores.js`, manifest permissions, `extension/src/tokens.css` | Stores/permissions from `config/vendors.toml`, colour + type tokens from `web/tokens/*.tokens.json`, via `scripts/build_extension.py` (`--check` in tests). The Archivo face is bundled in `extension/src/fonts/` (OFL). |
| Error catalog | `extension/errors.json` | Every `<area>.<reason>` code → message + fix, used by extension, app and server. |
| App protocol | `web/src/core/companion.ts` | Request/response over postMessage, zod-validated, coded errors. |
| App hooks | `web/src/app/useCompanion.ts`, `useBrowserDeck.ts` | Detection (hello/ping), version check, reads. |
| Server | `api/companion.py` → `cart.audit` (+ `store_ids` for TCGplayer / Card Kingdom product ids), `deals.supplied_tabs`, `storefetch.page_from_extract`, `decksource.payload_from_moxfield` / `payload_from_archidekt` → `addcards.deck_lines_from_payload`; `api/collection_import.py` → `collection_sync.preview_lines` / `apply_lines` | Thin adapters over existing engines. |
| Engine helpers | `magic_manager/companion.py` | Generated files, reproducible zip, bookmarklet, error catalog. |

Routes: `POST /api/purchases/orders` (+ the `/api/purchases*` review/apply routes), `GET /api/companion` (version + error catalog, unflagged), `GET /api/companion/extension.zip`
and `/bookmarklet`, `POST /api/cart/lines`, `POST /api/deals/tabs`,
`POST /api/ingest/deck-from-browser` (`source` = `moxfield` | `archidekt`), `POST /api/collection/import/preview` + `/apply`, and `pages` on the `deals.read_prices` and `deals.watchlist` job
inputs (the latter with `in_browser`).

Request kinds: `cart` (`params.store` = `manapool` (default) | `tcgplayer` | `cardkingdom`), `tabs`, `moxfield`, `archidekt` (`params.url`), `moxfield_collection` (`params.what` = `collection` | `binder` + `params.binder`, or a share `params.url`), `moxfield_binders`, and `watched` (`params.urls`, ≤ 50). `watched` is the only
two-step request: the approval window first shows the list (stage `confirm`, *Read these pages* /
*Don't read*; nothing opened yet), then the readings (stage `send`, *Send* / *Don't send*).

## Other carts: TCGplayer and Card Kingdom (extension 0.3.0)

Same seam as Mana Pool: the companion reads the cart page in your browser (your open cart tab, or a
background tab it closes), you approve the lines, the app posts them to `POST /api/cart/lines` with
`store`, and `cart.audit` runs the four checks. Both stores are covered by the Allow access switch (`www.tcgplayer.com`,
`www.cardkingdom.com`); the bookmarklet stays Mana Pool only.

- **Identifying printings.** TCGplayer lines carry the TCGplayer product id (from the product link) →
  Scryfall `/cards/tcgplayer/<id>`. Card Kingdom lines carry Card Kingdom's product id (from the card
  image; nonfoil and foil are separate products) → MTGJSON `identifiers.cardKingdomId` /
  `cardKingdomFoilId`, looked up in the set files of the card's printings, the sets whose names best
  match Card Kingdom's edition first ("Final Fantasy Variants Foil" → FIN, "3rd Edition" → Revised,
  "Promotional" → the set holding the promo), ≤ 12 set files per card. Exact or unidentified, never
  guessed (`store_ids.py`, shared with purchases). First check of a Card Kingdom cart downloads those
  MTGJSON set files (~15 s); they're cached after.
- **Sellers / conditions / languages (owner, 2026-10-10).** TCGplayer's many sellers don't matter:
  every line is compared with the card's market price (Scryfall's TCGplayer market). Market prices are
  Near Mint English, so only NM English lines can be **over market**; played (LP/MP/HP/DMG, Card
  Kingdom's EX/VG/G) and non-English lines are shown with their condition/language and counted as
  "left out". For *bought twice* and *already owned* any condition/language is the same printing.
- **Not cards.** Sealed products (and other games) in a cart are listed under *Not single cards*,
  counted in the cart total, never checked. TCGplayer's sealed name comes from the catalog (image
  alt), not a seller's listing title.
- **Verified** against guest carts saved from the live sites (singles NM/played/foil/non-English, a
  sealed product, quantity 2; real-data identification of every line checked by hand). A signed-in
  cart uses the same page — the owner will confirm with his own carts.

## Private Archidekt decks; Moxfield collection and binders (extension 0.4.0)

- **Archidekt decks** (Allow access, `archidekt.com`): the reader fetches the deck's own page in an
  archidekt.com tab, the way your browser loads it. Archidekt server-renders the deck into the page
  (`__NEXT_DATA__` → `props.pageProps.redux.deck.cardMap`) with your session, so your private decks
  come through; no token is touched. Lines keep Archidekt's own deck-API shape, so
  `decksource.parse_archidekt` reads both paths (`payload_from_archidekt`, also used by
  `scripts/import_deck.py`). The app sends an Archidekt link to the companion only once Archidekt is
  switched on; otherwise the server reads the public deck as before. Verified on a public deck
  (live canary); a signed-in private deck uses the same page, so the owner confirms it live.
- **Moxfield collection / binders** (Allow access): Add cards → *Import a collection* → *Live from Moxfield*
  → *Read my collection*, *Choose a binder…* (lists your binders; pressing one reads it), or a share link + *Read link*
  (`moxfield.com/collection/<id>`, `moxfield.com/binders/<id>`). The reader pages through Moxfield's
  own API (`/v1/collections/search[/<id>]`, `/v1/trade-binders[/<id>/search]`, 5,000 a page, ≤ 60,000
  printings). Share links are read **anonymously**. Your own collection, your binder list and private
  links need Moxfield's sign-in: Moxfield keeps its access token only in page memory, so the reader
  asks for one the way moxfield.com does (`POST /v1/account/token/refresh`, using the browser's own
  refresh cookie). It uses the token only for that read and never stores or returns it (owner-approved
  exception, 2026-10-11; see the security doc). The same helper now also lets the deck reader open
  **your private Moxfield decks**: it tries anonymously first and signs in only if Moxfield says private.
- **Import semantics (owner, 2026-10-11).** One `collection-import` ingest event per import, labelled
  `web:moxfield collection` / `web:moxfield binder · <name>` / `web:moxfield shared collection`
  (binders only choose *what* to import; the name lives only in the label). **Add or replace is chosen
  per import**: *add* sums onto what you own; *replace* sets each listed printing to Moxfield's count
  (3 → 5 nets +2). Printings the read doesn't list are never touched. Inventory is printing × finish:
  condition and language merge, **etched counts as foil**, and **proxies and digital (Arena/MTGO)
  copies are skipped** and counted. *Replace* never goes below copies pledged to built decks: the
  whole import is refused (409, all-or-nothing like the web checklist) and the review says so first. An identical read already imported needs explicit confirmation
  to add again (replace is idempotent). Large reads: the approval window lists **every** line in a
  scrollable table (added 2,000 rows at a time so a 60,000-line read doesn't freeze it); the app shows
  the full change list, virtualized.
- **Real-sized collections (0.4.4).** Two bugs made *Read my collection* fail with the misleading
  `request.invalid` ("the app sent a request it doesn't understand"): (1) the bridge's parameter
  allowlist dropped `what`/`binder`, so *Read my collection* and *read a binder* never reached the
  reader intact (only *Read link* worked); (2) Chrome's `storage.session` (10 MB) counts a stored
  object at its in-memory size, so a ~40,000-printing collection (~5 MB as JSON) overflowed it. The
  pending request now holds the read **packed** (gzipped JSON in one base64 string, `packData` /
  `unpackData` in `protocol.js`; 60,000 printings ≈ 3 MB) and unpacks it for the approval window and
  for Send — what is sent is unchanged. Caps: 60,000 printings (reader, app schema, server
  `MAX_LINES`), 24 MB as JSON (`MAX_COLLECTION_BYTES`), 8 MB packed (`SESSION_BUDGET_BYTES`). Over a
  cap is `request.too_large` (with its size as the detail); an unexpected exception in the worker is
  `reader.crashed`; app-side data that fails its schema is `companion.data_invalid`. `request.invalid`
  now means only what it says. The app shows a failure's short `detail` beside its code.
- **Unverified:** a signed-in Moxfield read (your collection, binder list, private link/deck) was
  pinned against a fake API built from the bundle's own request shapes. The binder-list response shape
  is assumed (array or `{data}`; `publicId`, `name`, a card count). The owner confirms both live.

## Tests (pinned behaviour)

`uv run python scripts/check_scrapers.py` runs all of them. When a site changes, use the
`scrape-doctor` skill.

- `web/e2e/companion-import-readers.spec.ts` → `tests/test_companion_imports.py`: the Archidekt deck and
  Moxfield collection / binder readers (incl. the signed-in path against a fake api2, and the token never
  leaving the reader) → strict models → `collection_sync` preview/apply (ledger reconciles).
- `web/e2e/companion-import.spec.ts`: the app's Moxfield collection tab and Archidekt links.
- `web/e2e/companion-readers.spec.ts`: readers in real Chromium against saved pages
  (`tests/fixtures/companion/`), writing the `*.expected.json` goldens.
- `web/e2e/companion-cart-readers.spec.ts` → `tests/test_companion_carts.py`: the TCGplayer and Card
  Kingdom cart readers → strict models → `cart.audit` (product ids → printings faked offline).
- `tests/test_companion.py`: goldens → strict server models → engines, least privilege, no remote
  code, one error catalog, reproducible zip, the cross-site write guard.
- `web/e2e/companion-extension.spec.ts`: the real unpacked extension end to end (approve, deny,
  close, busy, other site, other port, pairing validation).
- `web/e2e/companion-watched.spec.ts`: the real extension's watched read (list approved before any tab
  opens, bogus URLs dropped, background tab closed, your tab kept, a forged send of the list refused).
- `web/e2e/companion.spec.ts` + `web/src/core/companion.test.ts`: app flows and the protocol client.

## Pinned follow-ups (owner, 2026-10-07)

- ~~Order history → Purchase history~~ — built (V34, flag `purchases`): [`purchases.md`](purchases.md).
  Still open there: TCGplayer pages 2+, Card Kingdom single cards, a live end-to-end run of the
  extension's order flow.
- ~~**Other carts**: TCGplayer and Card Kingdom carts through the same `cart.audit` seam.~~ Done 2026-10-10
  (extension 0.3.0): see *Other carts* above. Still open: the owner's signed-in carts as a live check.
- ~~**Bot-walled stores** as Deals `rendered` recipes: Amazon, Walmart, GameStop.~~ Done 2026-10-10
  (extension 0.1.1): open-tab recipes that count only the store's own new offers
  (`docs/deals-scraping.md` failure mode 10).
- ~~**Private Archidekt decks; Moxfield collection/binders.**~~ Done 2026-10-11 (extension 0.4.0): see
  above. Still open: the owner's live check of the signed-in paths.
- ~~Deals **Watching → refresh** still reads open-tab stores on this Mac.~~ Done 2026-10-10 (extension
  0.2.1): the companion's `watched` request reads them, opening background tabs for pages that aren't open.
- Chrome Web Store distribution, plus pairing with a hosted domain (beyond `*.ts.net`) once Phase 3
  hosting picks one.
