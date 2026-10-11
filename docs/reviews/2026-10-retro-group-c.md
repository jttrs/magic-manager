# Retro code review, group C: companion, carts, canaries, purchases (Oct 2026)

These six PRs merged to `main` with a security review but without the general
review (`/ce-code-review` + `/findings-review`) that rule 4 now requires. Each
was reviewed after the fact against its squash commit (`base:<sha>^`, using a
detached checkout of that commit). Every PR got the full multi-agent pass:
correctness, adversarial, project standards (`CLAUDE.md`) and testing. Some
PRs also got reliability, API contract, data migration (#133) or async-race
reviewers (#125, #134). Security was skipped because each PR had already had
a security review.

There was no cross-model pass because no other provider's CLI is installed,
so the adversarial lens ran on the same model. A separate validator checked
each PR's findings at the merged commit. Then `/findings-review` re-checked
every surviving finding against **today's `main` (`d240057`)**. Only findings
that are still present are listed. Nits and coverage notes that aren't
actionable are left out.

| PR | Commit | Verdict |
|----|--------|---------|
| #133 order history → purchases (V34) | b21b67d | Ready with fixes (1 P1). V34 migration and ledger invariant OK |
| #125 browser companion + cross-site write guard | 8e514f1 | Ready with fixes (1 P1). Write guard OK on the default `127.0.0.1` bind |
| #134 Watching via background tabs | 4f74c48 | Ready with fixes (1 P2: test gap) |
| #135 TCGplayer / Card Kingdom carts + `store_ids` | 467fcaf | Ready with fixes (2 P2) |
| #132 scrape canaries + health flags | b4047b2 | Ready with fixes (1 P1, 3 P2) |
| #131 Amazon / Walmart / GameStop recipes | 0b52310 | Ready with fixes (1 P1) |

## P1

| # | PR | File:line (on `main`) | Finding | Suggested fix |
|---|----|-----------------------|---------|---------------|
| 1 | #133 | `src/magic_manager/purchases.py:349-500` (`_matchable_sources` → `ingest.reattribute`), `provenance.py:347-370` (`_held`) | **The same physical copy can be matched to two orders.** `_held` subtracts an earlier removal from the *newest* acquisition. Once a match moves copies onto the new `purchase` event, that removal counts against the purchase event instead. The original bucket then looks as if it still holds the copy, so the next review lists it as matchable again. Repro: 3 copies of unknown origin, remove 1 (2 owned), order #1 matches 2, order #2 matches 1: 3 matched against 2 owned, and order #1 shows 1 held. `inventory == SUM(delta)` still holds. Per-order provenance and paid / worth-today are wrong. | When computing matchable/held copies, subtract a removal only from acquisitions older than it, or treat a purchase event as the oldest acquisition. After `apply`, assert that held(order) == matched + added and roll back if not. Add a regression test: remove-then-match. |
| 2 | #125 | `extension/src/background.js:69-89`, `extension/src/approve.js:91-94` | **Send can deliver data the approval window didn't show.** `fromApp` checks `pending` *before* the slow reader `await`, but only writes it *after*. Two overlapping app requests both pass the busy check and both open windows; the second overwrites `pending`. `decide()` re-reads `pending` when the user clicks, so Send in window 1 (showing A) sends B's data. A then hangs until the app's timeout. Reachable with two app tabs, or the cart dialog plus Deals at the same time. | Claim the slot synchronously before any `await`: write a placeholder `pending` `{id, stage:'reading'}` and clear it in `finally` if the read fails. Pass the request id to `approve.html?id=…` and send that id from `decide()`. Add an e2e test that sends two requests back to back. |
| 3 | #132 | `src/magic_manager/scrape_canary.py:291-300` (`check_moxfield`) | **An offline or slow canary run marks both Moxfield scrapers DOWN.** The bare `except` around `page.goto`/`expect_response` returns `fail`/`scrape.shape_changed` for any navigation error unless the page is a bot wall. The visible-Chrome retry fails the same way, and its verdict stands. That raises a false "temporarily down" notice plus a macOS notification. Sibling checks (`check_rendered_store`, `check_cart`) map the same errors to `unverified`. | Return `_unverified(..., "scrape.unreachable")` for both keys on a navigation error (timeout, `net::ERR_*`, page still `about:blank`). Keep `shape_changed` for a page that loaded but never made the deck call. |
| 4 | #131 | `src/magic_manager/vendors.py:131-140` (`_not_counted`), `config/vendors.toml:201-206` | **An Amazon page with no buy box records a marketplace price as Amazon's.** A seller is rejected only when one is *seen*. Amazon's `no_offer_pattern` covers only "Currently unavailable". On a page that says "No featured offers available / $95.00 (12 new offers)", `read_listing` returns price 95.0, seller None, not skipped. A watched link then appends that price to its history, which is the outcome the PR exists to prevent. | Fail closed for recipes that set `sellers`: no seller found → `NotCounted`. Every first-party fixture already has a seller, so nothing that works today changes. Also widen Amazon's `no_offer_pattern` to `No featured offers available`, and add the synthetic test. |

## P2

| # | PR | File:line (on `main`) | Finding | Suggested fix |
|---|----|-----------------------|---------|---------------|
| 5 | #135 | `extension/src/readers/tcgplayer-cart.js:55,80` → `src/magic_manager/api/companion.py:79` | A non-Magic line in a TCGplayer cart sends a number like `025/165`. That fails `CartLineIn.number`'s pattern, and strict validation rejects the **whole** cart check with a 422. | Send `number: kind === 'single' ? number : null`, as `cardkingdom-cart.js:77` already does. Add the line to the reader fixture. |
| 6 | #135 | `src/magic_manager/store_ids.py:75-82` (`_ck_index`) | `@lru_cache` around a body that returns `{}` on any MTGJSON error. One transient failure is cached for the life of `mm serve`, and that set's Card Kingdom ids then go unidentified with no error shown. | Cache an inner loader that raises (`lru_cache` doesn't cache an exception), and return `{}` from an uncached wrapper. Test: first call fails, second succeeds. |
| 7 | #132 | `src/magic_manager/scraper_health.py:320-347` (`classify_error`) | The wrappers' "in backoff window after a 429 … Aborting." message falls through to `unknown`, and the canary treats `unknown` as `fail`. One EDHREC 429 during the canary flags EDHREC DOWN. | Add `backoff window` / `\b429\b` to the blocked pattern so the result is `unverified`/`scrape.blocked`. Test with the exact wrapper string. |
| 8 | #132 | `scripts/import_deck.py:207-209`, `scraper_health.py:334-335`, `addcards.py:445-450`; `extension/src/readers/moxfield-deck.js:61` | Importing a deck that is really empty flags that importer DOWN for everyone. The script prints the same "no cards parsed" message for an empty deck and a changed page. The companion's Moxfield reader returns `moxfield.changed` for zero cards, which is reported as a page change. | Give an empty-but-well-formed deck its own message and treat it as `unverified`. On the companion side, add a `moxfield.empty` code that is never reported as a scraper failure. |
| 9 | #132 | `src/magic_manager/scrape_canary.py:313-315`, `:403-418` | `page.evaluate("readMoxfieldDeck…")` sits outside any `except`. A reader error escapes to `_browser_pass`'s catch-all, which marks Moxfield **and the not-yet-run cart checks** as `unverified`. A broken reader is never flagged and the cart canary is skipped. | Wrap the evaluate so a reader error records `fail`/`moxfield.changed` for the reader only. Guard `run_one` per target. |
| 10 | #134 | `extension/src/watched.js:55-97` | Four mid-read safety paths have no test that runs them: stop after *Don't read* (`alive()`), skipping a user tab that has moved to another page, the load timeout, and the 3-tab cap. Two of these were fixes from the PR's own security review. Today they are covered only by substring checks on the source text. | Add a Node test of `readWatched`/`readOne` with stubbed `chrome.tabs`, `inject`, `loaded` and `alive`. |

## What was checked and found sound

- **V34** (`ingest_events` rebuild to allow `method='purchase'`): it keeps every row and every `ingest_id`. The purchase tables are created after the rebuild. `apply` writes through the ledger seam and runs `reconcile_inventory_ledger` before commit. The new tables are in undo's `USER_TABLES`.
- **Cross-site write guard** (#125): all non-GET `/api/` writes are covered. One limit to note: browsers send `Sec-Fetch-Site` only to trustworthy origins, so `mm serve --host <LAN IP>` over plain http would let cross-site POSTs through. The default `127.0.0.1` bind is fine. DNS rebinding is already documented as deferred.
- **Project standards**: no `CLAUDE.md` violations in any of the six PRs. The missing `pr_review.py` stamp predates rule 4 (#136).

## Lower-priority notes (not carried forward as fixes)

- #125: *Read prices again* re-sends the cached companion page snapshot, so a watched open-tab link can record an old price with a new timestamp. JSON-LD over 100 kB on a single store tab fails the whole tabs payload.
- #134: if the companion fails, the whole watchlist refresh stops, including the stores the server reads. Watched URLs are matched verbatim, so a non-canonical stored URL reads as `COMPANION_UNREAD`.
- #132: in real use, Deals records `fail`/`scrape.no_price` for any page with no price, including a sold-out page or a half-rendered tab, so stores can flap DOWN.
- #135: the TCGplayer reader treats an MTG line without a collector number as sealed. Unverified whether that happens.
- Rejected by the validators: #134 "companion chosen without the Deals permission" (this is the documented design: `permission.deals_off` tells the user how to fix it), and #134 "an open tab closed before the read is opened in a background tab" (the approval text already covers it).
