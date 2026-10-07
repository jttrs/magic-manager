# Post-merge code reviews — second fan-out wave (Oct 2026)

These PRs merged to `main` without a formal review. Each was reviewed after the
merge against its squash commit (`base:<sha>^`, using a detached checkout of that
commit). `ce-code-review` ran on #114, #117, #120 and #121 in full depth. For
#115, #118 and #122 its run directory could not be created, so those got the
same lenses as a manual review instead. The `security-review` agent checked
#122 and #121's change to `scryfall.sh`. #107 got a quick review because the
diff is only 12 lines. There was no cross-model pass, because code may not
leave the machine; the adversarial lens ran on the same model instead. Nits
are dropped. Every finding below was still open on `main` (7e6dbd9) when it
was reviewed.

Skipped: #108–#112 were already reviewed; #113 and #123 are docs only; #116 is
an empty duplicate of #118.

| PR | Commit | Verdict |
|----|--------|---------|
| #107 dev/e2e ports from env | 950466c | Clean |
| #114 foil premium + cheapest printing | 9f2c1ee | Ready with fixes (1 P1) |
| #115 price targets + history (V33) | 45d35de | Ready with fixes. The migration and db-upgrade checks pass |
| #117 Jumpstart in the app | a3fc017 | Ready with fixes |
| #118 on-theme art swaps | 7882360 | Ready with fixes |
| #120 Scenes in Collection | a42cc90 | Ready with fixes |
| #121 card surfer | a4d76e3 | Ready with fixes (1 P1). Security review clean |
| #122 Keychain login | 33f97ed | Ready with fixes (1 P1). Security review clean |
| #124 analytics layer | b262bd2 | Ready with fixes (1 P1: `main` was red). Manual review; no `db.MIGRATIONS` change |

## P1

| # | PR | File:line (at merge) | Finding | Suggested fix |
|---|----|----------------------|---------|---------------|
| 1 | #122 | `web/src/views/collection/CartCheckDialog.tsx:49,52` | The cart dialog still tells you to put `MANAPOOL_EMAIL`, `MANAPOOL_PASSWORD` and `MANAPOOL_ACCESS_TOKEN` in `.env`. `.env` is now ignored for the personal login, so following these steps never works and leaves a plaintext password on disk. | Point to `uv run mm secret set MANAPOOL_EMAIL` / `MANAPOOL_PASSWORD` (Keychain). Drop `ACCESS_TOKEN`. |
| 2 | #114 | `src/magic_manager/market.py:172` → `collection_view.buy_lines` (`if sid in by_id`) | Live deck cost ("check every set on Scryfall") can choose a cheapest printing from a set that isn't synced. The buy list then drops that card silently, while the floor total on screen still counts it. | Upsert the live-chosen printings into `cards` (the `addcards`/`art_swap` pattern), or have `buy_lines` report the ids it can't find. Add a test that goes from live deck cost to the buy list. |
| 3a | #124 | `src/magic_manager/web/telemetry.py:92-94` | `catalog.load().triggers_for(route)` runs unguarded after the response. With `MAGIC_MANAGER_CONFIG_DIR` redirected (as `test_cart_route_is_gated_by_the_flag` and `test_deals_route_is_gated` do), `ConfigError` escapes, so **both tests fail on `main`**. This also breaks the promise that analytics never fails a request. | Guard it the way `record_response` already does, and log a warning. |
| 3 | #121 | `web/src/views/explore/surf/CardSurfer.tsx:154` | In *Your cards*, each page scans at most 120 printings. A page can come back empty but not exhausted, for example with an artist or flavor filter. The view then says "None of your cards match", and because the sentinel is only drawn when there are cards, nothing more is ever fetched. | Show the empty note only when `!cards.length && !hasNextPage`. Otherwise keep the sentinel and a "Searching…" state. |

## P2

| # | PR | File:line | Finding | Suggested fix |
|---|----|-----------|---------|---------------|
| 4 | #117 | `src/magic_manager/jumpstart.py:167` | `ensure_ready` → `sets.ensure_priced` swallows sync errors. The `jumpstart.read` job then reports success while `is_ready` is still False, and the sheet sits on "Reading the packs" with no Retry. Reliability rated this P1. | After syncing, check `unsynced_set_codes` and raise if any remain. The view should treat "succeeded but still not ready" as an error. |
| 5 | #117 | `web/src/views/JumpstartView.tsx:56` | `void start('jumpstart.read')` throws away the submit error, so the progress bar spins at zero forever. | Keep the error, reset `startedRef`, and show the error with Retry. |
| 6 | #117 | `src/magic_manager/api/jumpstart.py:117` | The set picker's `owned_packs` counts only deck rows keyed by fileName. The sheet also counts older `pack:<theme>-<code>` rows, so the two numbers disagree. | One `jumpstart.owned_file_names(code)` helper used in all three places. |
| 7 | #117 | `jumpstart.py:167`, `scripts/jumpstart_reference.py:63` | The reference XLSX stopped refreshing prices: it gives no stale warning, has no `--refresh`, and prints no "Prices fetched" footer (see CLAUDE.md § Price freshness). | Thread `refresh_stale` and `log` through `ensure_ready`, and add the warning and footer. |
| 8 | #114 | `src/magic_manager/market.py:271` | When the live floor lookup fails, the whole deck cost returns 502. Because `live=true` is saved in the URL, Retry and reload hit the same error. | Catch `ScryfallError`, fall back to local floors, and return `live_error`. |
| 9 | #115 | `src/magic_manager/earmarks.py:357,365` | `set_target` validates before it rounds. A pct of 99.996 or a price of 0.004 passes validation, then fails the CHECK constraint, and the route returns 500. | Round first, then validate. Map `IntegrityError` to 422. |
| 10 | #118 | `web/src/core/deckDraft.ts:96`, `core/artSwap.ts:26` | A swap labelled "free" keeps the row's finish, and the free count ignores finish and quantity. Saving a built deck can then leave it short. | Return free counts per finish and use a finish that is actually free. Call a swap free only when free ≥ the row's count. |
| 11 | #118 | `src/magic_manager/art_swap.py:112` | `lookup_scryfall` swallows every `ScryfallError`, so a network failure reads as "Scryfall has nothing new". | Ignore only not-found errors and re-raise the rest (502). |
| 12 | #121 | `src/magic_manager/api/surf.py:24` | Unknown treatment keys are accepted. With only unknown keys, `build_query` sends an empty `()` to Scryfall and `matches` rejects every card. | Filter to the `surf.TREATMENTS` keys and skip the clause when none remain. |
| 13 | #121 | `web/src/views/explore/surf/ArtTagField.tsx:49` | Pressing Enter can add the top suggestion from the previous, debounced search. | Use `hits[0]` only when it belongs to the current text. |
| 14 | #122 | `src/magic_manager/secrets.py:21,37` | The personal and service credentials share the name `MANAPOOL_EMAIL`, and the environment wins. A host env that exports the service email would therefore shadow the personal Keychain email. Locally `.env` isn't loaded into `os.environ`, so this is latent until hosting. | Give the personal email its own key, or read it from the Keychain only. |
| 15 | #122 | `scripts/manapool_cart.py:11,24` | The docstrings still say the password is read from `.env`. | Update them to the Keychain / `mm secret set`. |
| 14a | #124 | `src/magic_manager/web/telemetry.py:81-82`, `web/runtime.py:149-151` | Coded 500s and failed-job events include `str(e)` and a traceback. That's fine locally, but it leaks SQL, paths and row data when hosted (§25.0). The coordinator flagged this one. | Add the detail only when not `MM_MODE=hosted`. Hosted keeps the type, code and `request_id`, and the full detail goes to the server log. |
| 14b | #124 | `analytics/consent.py:80-91`, `undo.py` | Consent lives in `settings`, which `undo.restore` swaps back. So opting out and then pressing Undo turns usage tracking back on. | Never roll back consent on restore. |
| 16 | #120 | `web/src/views/collection/SceneHead.tsx:38` | This is the fourth copy of the store list and the Card Kingdom note. The others are in CollectionView, JumpstartView and MarketView. | Lift a shared store-targets helper. |

## P3 (recorded, not scheduled)

- **#124**
  - Job completion waits on the analytics write. Fixed: the terminal event now goes first.
  - **Deferred to hosting (§25.4):** the analytics `user_key` is always `local`, so under hosting every user would share one key and delete-my-data would delete everyone's events. The 600/min event limit is global rather than per user.

- **#115**
  - `deals._with_target_prices` catches every exception, so a code bug looks like a missing market price.
  - `target_met` can rest on an old snapshot when later reads keep failing.
  - The NEW/DIVERGED classification in `rehearse_migration` has no test.
  - Pre-existing: `earmark_prices` isn't in `_EARMARK_TABLES` or `OWNERSHIP`.
- **#118**
  - Look-up upserts make never-synced sets look synced.
  - `POST /api/art/lookup` does long writes inside the request instead of as a job.
  - Quick-pick chips assume a tag's label equals its slug.
  - Swapping onto a printing already in the deck loses the undo.
- **#121**
  - `surf._list` duplicates `util.decode_json_list`.
  - The token layout check is hard-coded.
  - `tcgplayerSearch` is copied from CardInspector.
  - The "every card" stop message can show while fewer than `total` cards are on screen.
  - Cmd-click on a card link closes the surfer.
- **#117**
  - `row_value` duplicates `cli._row_line_value`.
  - The engine hard-codes the `mtgjson.sh` cache layout.
- **#120**
  - `SceneOut.kind` isn't validated against the config.
  - `scene_table.py` now reads only local cards.
  - The scene exemption reaches Market → Cards, and that isn't documented.
- **#122**
  - The Keychain calls have no timeout.
  - No test covers the `security` arguments.
- **#114**
  - Live scans of basic lands are slow.
  - Etched-only printings get a different label in the web than in the script.

## Fix status

All P1 and P2 findings were fixed in the follow-up PR on branch
`torre/post-merge-code-reviews`, one commit per area. The cheap P3s that sat in
the same code were fixed alongside them. The rest of the P3s are recorded above.

Decisions:
- **#122 (finding 14):** the Keychain items keep their names. `secrets.get` now
  reads the personal login (`MANAPOOL_EMAIL`/`MANAPOOL_PASSWORD`) from the
  Keychain first and falls back to the environment, so an exported
  service-account email can no longer shadow it.
- **#124 user identity:** deferred to the hosting session layer.
