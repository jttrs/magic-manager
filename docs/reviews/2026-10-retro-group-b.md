# Retroactive code review — group B (Deals, earmarks, price targets, Docker CI)

Date: 2026-10-11. Reviewed against `origin/main` @ `d240057`.

Merged PRs that skipped CLAUDE.md rule 4 were each re-reviewed with `/ce-code-review` scoped to the
merged squash commit (`base:<sha>^`, scratch worktree at the commit). Findings were then validated
against the code (`/findings-review` step 4) and **re-checked on today's main**. Only findings still
present on main are listed below; already-fixed ones are listed at the end.

| PR | Commit | Topic | Depth | Raw → validated | Still on main |
|---|---|---|---|---|---|
| #100 | 2a327df | Deals B1 tab reader | full | 7 → 1 | 1 |
| #101 | 623a676 | B2 store recipes + canary | full | 23 → 9 | 9 |
| #102 | 3f47f09 | B3 listing matching + compare | full | 13 → 9 | 8 |
| #103 | bb65382 | Watch + price history (V32), Deals table | full | 17 → 10 | 9 |
| #104 | e7df342 | Single-card earmarks (V31) | full | 9 → 4 | 4 |
| #113 | 5e3f48c | Docker CI build (code/CI only) | lite | 9 → 4 | 4 |
| #127 | a262a9f | Test isolation | lite | 2 → 2 | 2 |
| #129 | 57e7452 | P3 fixes | full | 11 → 3 | 3 |
| #130 | 9b59ff8 | 7-day target staleness | focused | 3 → 1 | 1 |

**Coverage limits.** No cross-model peer ran (no different-provider CLI is installed); the adversarial
lens ran as a local subagent. Several runs folded lenses into combined reviewers and did merge/validation
in-context rather than via the skill's leaf agents. Findings are from code reading plus small offline
repros (pure functions, in-memory SQLite); no full test suites were run at the old commits.

## P1

| id | PR | file:line (main) | evidence | fix |
|---|---|---|---|---|
| B103-A | #103 | `src/magic_manager/deals.py:312` (`unwatch`) → `earmarks.py:443`; `deals.py:331` | `unwatch` only deletes the link; the product row survives. `watchlist()` still lists the link-less product, the web shows it as watching with no stores, and a second *Stop watching* sends no URLs. Only `mm earmark rm-product` clears it. | Drop the product (CASCADE → targets, history) when its last link goes, in the same transaction. |
| B102-F1 | #102 | `src/magic_manager/listing_match.py:265` | Single finish = foil unless `non-foil`/`nonfoil`; a title with `Non Foil` (space) prices at the foil price → a fake below-market deal. | One shared `non[\s-]?foil` test. |

## P2

| id | PR | file:line (main) | evidence | fix |
|---|---|---|---|---|
| B102-F2 | #102 | `src/magic_manager/sld.py:77` | `edition_from_name("… \| Nonfoil")` → `foil` (only `non foil`/`non-foil` excluded). | Same shared `non[\s-]?foil` test. |
| B102-F3 | #102 | `src/magic_manager/listing_match.py:190` | The language check runs only for sealed; `Lightning Bolt (Japanese) (146) (M10)` is `matched` at the English price. | Apply `_LANG` for every kind → ambiguous. |
| B102-F4 | #102 | `src/magic_manager/listing_match.py:220` | Token Jaccard 5/6 ≥ `MATCH_AT` 0.75 → a *Collector's Edition* deck title silently matches the regular deck. | Refuse when a distinguishing word (e.g. `collector`) is missing from the product. |
| B102-F7 | #102 | `web/src/views/market/DealsPanel.tsx:246` | *not this?* shows only with >1 candidate; matched singles/SLD return none, so a wrong match can't be corrected. | Always offer the correction (or return alternative printings/editions). |
| B103-B | #103 | `src/magic_manager/storepage.py:193-202` | A `?variant=` that no longer exists falls back to the cheapest *other* variant, and that price is recorded into the watched link's history. | Requested-but-missing variant → no price / error. |
| B101-F1 | #101 | `config/vendors.toml:168,177`; `vendors.py:110` | Best Buy/Target sold-out regexes scan ≤40k chars of page text (`not available` matches "pickup not available") and override other stock signals. | Anchor to buy-box wording; add real tab fixtures. |
| B101-F2 | #101 | `src/magic_manager/storefetch.py:111` | `osascript` has no timeout; a hung Chrome/permission prompt blocks the serialized job runner indefinitely. | `timeout=` + per-URL error. |
| B101-F3 | #101 | `src/magic_manager/storefetch.py:72` | 401/403/429 responses are cached 30 min; *Read prices again* replays the block. | Cache only 200/404. |
| B104-F2 | #104 | `src/magic_manager/earmarks.py:113` | Single earmark lookup uses `db.upsert_card` directly, so the set looks synced; bypasses `sets.upsert_lookup_cards` (`sets.partial`) that CLAUDE.md requires for lookups. | Use `sets.upsert_lookup_cards`. |
| B129-F1 | #129 | `src/magic_manager/deals.py:368` (also `:439`) | A failed read is excluded from targets only inside the refresh job; failures aren't stored, so after a reload the instant watchlist/web can count a store whose last read failed (bounded to 7 days by #130). | Persist the last read error per link and exclude it in `_target_met` + web mirror. |
| B127-B1 | #127 | `tests/test_cart.py:26-32`, `tests/test_companion.py:31`, `tests/test_deals_tabs.py:12` | `_copy_real_config` copies `features.local.toml` (git-ignored) into the tmp config; on the owner's checkout (`cart_check = true`) the flag-gate test fails. | Skip `features*.toml`; lift the helper into `conftest.py` (also fixes B127-B2). |
| B113-F1 | #113 | `Dockerfile:19-20,25,31` | `uv.lock*` glob + `uv sync` without `--locked`; `uv run` at start re-resolves — the image needn't match the lock. | `COPY uv.lock`, `uv sync --locked`, `uv run --frozen`. |

## P3

| id | PR | file:line (main) | summary |
|---|---|---|---|
| B100-C3 | #100 | `web/src/views/MarketView.tsx:221` | Collapsed sidebar summary shows a stale deck name on `subject=deals`. |
| B101-F4 | #101 | `storepage.py:120` | JSON-LD walk pops last-first → a related product's price wins. |
| B101-F5 | #101 | `storepage.py:82-83,153-157` | Meta `content=` regex stops at an apostrophe (`Collector's` → `Collector`). |
| B101-F6 | #101 | `storepage.py:162` | `read_text` is dead; logic duplicated in `vendors.read_listing`. |
| B101-F7 | #101 | `storefetch.py:117` → `deals.py:128` | osascript failure surfaces as generic "(RuntimeError)". |
| B101-F8 | #101 | `storepage.py:76`; `deals.py:121` | 5xx parsed as a page → "page may have changed" instead of "store unavailable". |
| B101-F9 | #101 | `docs/deals-scraping.md:171` | Doc promises robots.txt respect + honest UA; neither implemented. |
| B102-F5 | #102 | `listing_match.py:127-129` | Any `(digits)` classifies as a single (`Booster Box (36)`, `(2024)`). |
| B102-F8 | #102 | `deals.py:182,196-203` | Confirmed Scryfall-only candidate loses its price (not stored locally). |
| B102-F9 | #102 | `listing_match.py:124-125` | `mystery` / `sleeves` patterns skip real products ("Mystery Booster 2"). |
| B103-H | #103 | `DealInspector.tsx:26,61-64`; `market.py:91-93` | SLD rows render Contents via the sealed identifier, which can fail on SLD names. |
| B103-J | #103 | `market.py:184-196` | `product_cost` memo caches free/buy counts 30 min across inventory writes. |
| B103-N | #103 | `api/deals.py:119-125,288-294` | `deals.read_prices` / `deals.watchlist` write `earmark_prices` without `mutates=True` (undo guard skipped). |
| B103-L | #103 | `earmarks.py:317`; `deals.py:438` | Cached page reads recorded as fresh history points. |
| B103-K | #103 | `DealInspector.tsx:~146-160` | Watch earmarks only the best store, Stop says "all N stores". |
| B103-E | #103 | `scripts/rehearse_migration.py:327-328` | `SELECT *` hashing flags earmark tables as DIVERGED after V31 adds columns. |
| B103-P | #103 | `deals.py:325`; `tests/test_deals_watch.py:49` | Tests cover only the unused `values=True` path. |
| B104-F1 | #104 | `earmarks.py:125`; `cli.py:5077` | `--finish etched` passes resolve then crashes `earmark add` with a traceback. |
| B104-F3 | #104 | `earmarks.py:94` vs `listing_match.py:301` | Two set+CN+name checks; DFC face flavor names accepted by one only. |
| B104-F4 | #104 | `CLAUDE.md:37,179` | Still says "sealed-product watchlist". |
| B113-F2 | #113 | `Dockerfile` | Runs as root. |
| B113-F3 | #113 | `.dockerignore` | `config/features.local.toml` not ignored (local builds bake owner flags). |
| B113-F4 | #113 | `.github/workflows/docker-build.yml:17-19` | Actions/base images not pinned by SHA/digest (low exposure: read-only, no secrets, no push). |
| B127-B2 | #127 | three test modules | `_copy_real_config` duplicated ×3. |
| B129-F3 | #129 | `undo.py:175-189` | Restore can resurrect a stale `sets.partial` list. |
| B129-F5 | #129 | `ArtSwapTab.tsx:237-241` | Swaps refresh lost if the Lookup unmounts mid-job. |
| B130-A1 | #130 | `PriceTarget.tsx:93`; `core/deals.ts:209` | Status text uses an untrusted (stale) best price while *met* uses trusted ones. |

## Already fixed on main

- **B102-F6** — a confirmation answer kept overriding later price reads: removed in bb65382 (#103), confirmations now patch the query cache.
- **B103-C** — `known_floor` was 0.00 instead of None with no floors: fixed in 07012d5 (#112).
- **B129-F1** partly mitigated by #130 (staleness now capped at 7 days).

## Refuted (summary)

#100: 6 (osascript injection — none, args are fixed; others speculative/pre-existing). #101: 14 (mostly
nitpicks/speculative). #102: 4. #103: 7 (pre-existing patterns or speculative). #104: 5. #113: 5 (no
secrets/DB in image, no push, read-only perms). #129: 8. #130: 2.
