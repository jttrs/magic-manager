# Browser companion

A Manifest V3 Chrome extension (`extension/`) plus a cart bookmarklet. They read, in the user's
**own** browser, what the server can't or shouldn't: the Mana Pool cart, open store tabs (Deals),
and Moxfield decks. They hand the app only the normalized lines, after the user approves each time.
This replaces the local-only paths (H9): the Keychain cart login, AppleScript tab reads and the
headed-Chrome Moxfield import. Those keep working on the owner's Mac when the companion isn't
connected. Security design: [`browser-companion-security.md`](browser-companion-security.md).

## Using it (beta)

1. Turn on the flag: `MM_FEATURES=companion` (plus `cart_check` / `deals` for those features) or
   `config/features.local.toml`. Restart `mm serve`.
2. App header → plug icon → **Download the companion**, unzip, `chrome://extensions` → Developer mode
   → **Load unpacked**.
3. Companion icon → enter the app address → **Pair** (Chrome asks to allow it) → reload the app tab.
4. Optional: switch on **Deals** and/or **Moxfield** on the companion's settings page (each asks
   Chrome for just its sites).

Where it shows up: Collection → *Check my Mana Pool cart* (**Read my cart**, plus the bookmarklet
paste), Market → Deals → **Read my open tabs** (tabs + open-tab store prices), Add cards → Deck and
Decks → Import (Moxfield links). Without a connected companion each falls back to the existing path.

## How it fits

| Piece | Where | Role |
|---|---|---|
| Readers | `extension/src/readers/*.js` | Deterministic page reads (classic scripts, shared with the bookmarklet). |
| Worker | `extension/src/background.js` | Validates the asker, runs a reader, opens the approval window, delivers the result. |
| Bridge | `extension/src/bridge.js` | Content script on the paired app origin only; relays postMessage ↔ worker. |
| Approval / settings | `extension/src/approve.*`, `options.*` | The extension's own pages. |
| Generated | `extension/src/stores.js`, manifest permissions | From `config/vendors.toml` via `scripts/build_extension.py` (`--check` in tests). |
| Error catalog | `extension/errors.json` | Every `<area>.<reason>` code → message + fix, used by extension, app and server. |
| App protocol | `web/src/core/companion.ts` | Request/response over postMessage, zod-validated, coded errors. |
| App hooks | `web/src/app/useCompanion.ts`, `useBrowserDeck.ts` | Detection (hello/ping), version check, reads. |
| Server | `api/companion.py` → `cart.audit`, `deals.supplied_tabs`, `storefetch.page_from_extract`, `decksource.payload_from_moxfield` → `addcards.deck_lines_from_payload` | Thin adapters over existing engines. |
| Engine helpers | `magic_manager/companion.py` | Generated files, reproducible zip, bookmarklet, error catalog. |

Routes: `GET /api/companion` (version + error catalog, unflagged), `GET /api/companion/extension.zip`
and `/bookmarklet`, `POST /api/cart/lines`, `POST /api/deals/tabs`,
`POST /api/ingest/deck-from-browser`, and `pages` on the `deals.read_prices` job input.

## Tests (pinned behaviour)

`uv run python scripts/check_scrapers.py` runs all of them. When a site changes, use the
`scrape-doctor` skill.

- `web/e2e/companion-readers.spec.ts`: readers in real Chromium against saved pages
  (`tests/fixtures/companion/`), writing the `*.expected.json` goldens.
- `tests/test_companion.py`: goldens → strict server models → engines, least privilege, no remote
  code, one error catalog, reproducible zip, the cross-site write guard.
- `web/e2e/companion-extension.spec.ts`: the real unpacked extension end to end (approve, deny,
  close, busy, other site, other port, pairing validation).
- `web/e2e/companion.spec.ts` + `web/src/core/companion.test.ts`: app flows and the protocol client.

## Pinned follow-ups (owner, 2026-10-07)

- **Order history → Purchase history** (new idea, don't lose it): read the user's own order history
  (Mana Pool first, then TCGplayer and Card Kingdom) in their browser and record each order as an
  acquisition in the V19 ledger, with the real price paid and date. Same rules: click-to-read,
  approve, lines only, deduped by store + order id. Likely needs a new ingest method, so ask the
  coordinator before any schema change.
- **Other carts**: TCGplayer and Card Kingdom carts through the same `cart.audit` seam.
- **Bot-walled stores** as Deals `rendered` recipes: Amazon, Walmart, GameStop.
- **Private Archidekt decks; Moxfield collection/binders.**
- Deals **Watching → refresh** still reads open-tab stores on this Mac. Route it through the companion
  when connected.
- Chrome Web Store distribution, plus pairing with a hosted domain (beyond `*.ts.net`) once Phase 3
  hosting picks one.
