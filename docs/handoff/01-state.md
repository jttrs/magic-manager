# 01 — Current state (as of 2026-11-01 20:40 PT)

## Repository

- **Repo:** `jttrs/magic-manager` (PUBLIC on GitHub). Local clone (main checkout):
  `/Users/torre/repos/personal/magic-manager` — branch `main`, clean.
- **origin/main:** `789bdf4` — "Phase 3 step 10: hosted hardening …" (#206).
- **Open PRs:** none (besides this handoff branch's PR, if opened).
- **Open issues:** #119 "Vendor recipe canary failing" (2026-10-07; opened automatically by the
  nightly `vendor-canary.yml`). Check whether it is still current before acting on it.
- **gh auth:** the default `gh` account on this machine may be an Adobe EMU account that cannot act
  on this personal repo. Always:
  `GH_TOKEN=$(env -u GH_TOKEN gh auth token --hostname github.com --user jttrs) gh …`.
  Never switch gh accounts globally.

## Database

- Real DB: `/Users/torre/repos/personal/magic-manager/db/magic_manager.db` — single-file layout,
  schema **V37**. `db.CURRENT_VERSION` on main = 37. **Next free migration: V38**, and every entry
  after V36 must declare `db.MIGRATION_TARGETS[v] = "catalog" | "user"` (a test enforces it).
- V36 (Phase 3 step 2) made the schema splittable: no user-table FKs into `cards`
  (`db.require_cards` guards writes; `mm audit catalog-refs` is the backstop), `catalog_settings`
  table. V37 (#180) = card earmarks (target `user`).
- Snapshots in `db/bak/` (e.g. `…221352-pre-v36`). Restore: `uv run mm db restore <snapshot>`.
- **Never** write the real DB without the owner's explicit OK; never copy a worktree DB over it.
  Rehearse on `sqlite3 <real> ".backup <copy>"` copies.

## The owner's live app (laptop)

- `http://localhost:8766`, served from the detached worktree
  `/Users/torre/repos/personal/magic-manager/.worktrees/live` (now at `789bdf4`), local mode,
  single-file, against the real DB.
- launchd agents (OUT of repo; don't edit without the owner): `com.magic-manager.serve`,
  `com.magic-manager.deploy` (every 5 min: fetch main → `uv sync` → `npm ci` → build → kickstart
  serve; **holds** if main needs a migration the real DB lacks, and notifies), and
  `com.magic-manager.scrape-canary` (daily 06:30). Scripts: `~/Library/Application Support/magic-manager-live/{serve,deploy,scrape-canary}.sh`.
  Logs: `~/Library/Logs/magic-manager/{serve,deploy}.log`.
- Live per-machine flags (`.worktrees/live/config/features.local.toml`): `cart_check`, `deals`,
  `companion`, `purchases` = true.
- To stop/start the live server for a DB upgrade:
  `launchctl bootout gui/$(id -u)/com.magic-manager.serve` … `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.magic-manager.serve.plist`.
- The in-repo `deploy/macos/` kit (step 8) is for the **Mac mini**, not this laptop; the laptop
  keeps its out-of-repo scripts.

## Browser companion

- `extension/` at **0.5.0** on main (#204). Owner's Chrome Profile 1 has it unpacked from
  `.worktrees/live/extension`, paired with `http://localhost:8766`, one "Allow access" switch on.
  The owner has been asked to reload to 0.5.0 (and re-pair if it says "Not connected").
- Chrome Web Store: listing assets are ready in `extension/store/` (#188 — `listing.md`,
  screenshots, `store.toml` with empty `url`/`extension_id`), release workflow
  `.github/workflows/extension-release.yml` (SHA-pinned, #198). **Not published** — needs the
  owner's developer account. Since #204 the companion pairs with ANY https origin (exact-origin
  permission requested at Pair), so publishing is no longer blocked on the domain.
- Security model (binding): `docs/browser-companion-security.md` — exact-origin pairing, approve
  every read in the extension's own window (shows "Goes to <origin>"), lines only, no
  cookies/tokens to the app, extension never calls the API (the paired page posts with the user's
  session + CSRF).

## CI and merge protection

- `.github/workflows/ci.yml` (#203) on every PR + push to main: `pytest` (xdist, ~1.7 min),
  `web-check` (~30 s), `e2e` (4 shards + aggregator, ~4 min), `extension` (~12 s). Plus
  `pr-review.yml` (`review-stamp`), `docker-build.yml` (`image`), `vendor-recipes.yml`
  (`recipes`), nightly `vendor-canary.yml`, `extension-release.yml`.
- Ruleset **24885345** on `main`: required checks `review-stamp`, `pytest`, `web-check`, `e2e`,
  `extension` (GitHub Actions integration 15368), **strict** (branch must be up to date), no
  bypass. Merge via REST with the head sha pinned — `tools/ci_gate.md` does it.

## Phase 3 — what shipped (docs/webapp-architecture-decision.md §25.4)

| Step | PR | What |
|---|---|---|
| decisions | #171 | §25.2 resolved: Mac mini native; budget = domain + free-tier R2; friends via Cloudflare Tunnel + own domain |
| 1 | #172 | `layout.py` table registry (USER/CATALOG/INFRA/LEGACY) + `MM_LAYOUT=single|split` layout-aware `db.connect` |
| 2 | #174 | **V36**: drop user→cards FKs (`db.require_cards`), `catalog_settings`, `MIGRATION_TARGETS`, `db.migrate_split_file`, `mm audit catalog-refs` (applied to real DB 2026-10-12) |
| 3 | #175 | `mm db split --to <dir>` (catalog.db ≈614 MB + users/<id>.db ≈14 MB), split snapshots, split rehearsals |
| 4 | #177 | `auth.db` (own schema), invite-only Discord + Google OAuth (state+PKCE, OIDC verify), sessions, CSRF + Origin, rate limits, `mm auth invite/users/revoke`, sign-in UI; hosted = `MM_MODE=hosted` |
| 5 | #199 | per-request user binding (`layout.bind_user`, fails closed), `userfiles.py`, per-user undo, jobs carry + bind the user (others get 404), `db.catalog_first`, `mm auth bind` |
| 6 | #200 | per-user flag overrides (auth.db v2) + `/admin` page, `owner_machine.py` pins owner-machine paths admin-only, `PROFILES_OPEN = True` |
| 7 | #201 | Download my data (zip: user DB + CSVs + README; `mm account export`) + delete my account (≤10-min reauth, typed confirm, last-admin, crash-safe; `mm auth delete-user`) |
| 8 | #202 | Litestream → R2 (auth.db + users/*.db continuous, 30 d; catalog weekly `VACUUM INTO`, keep 2), `deploy/macos/` kit + installer, `docs/home-server.md`, `mm db pull`, `mm host restore|verify-replica`, rehearsed cutover script (NOT executed) |
| CI | #203 | heavy gates moved to GitHub Actions; ruleset requires them |
| 9 | #204 | companion pairs with any https origin (exact), members use only the companion (no server browser for them), extension 0.5.0 |
| 10 | security review on `8dbf86f` (0 vulnerabilities) → #206 hardening: CSP + headers, API docs off when hosted, scraper-health admin-only writes, identifier validation, store-fetch redirect checks, job scopes (catalog-wide = admin) + 3-job cap + live-read rate limit, coded errors, signed-commit deploys (GitHub web-flow key), `MM_TRUSTED_PROXY`, disabled users' jobs cancelled |

Other merges this cycle (from other sessions): #173 (Best Buy/Target recipes, companion 0.4.5),
#176/#188–#197 (web UX audit round 2 fan-out, all merged), #180 (V37 card earmarks), #198
(companion release hygiene), #205 (characterize MBC).

## Not done / deferred (carried into 02-roadmap.md)

- **Cutover** to the Mac mini (owner hardware + accounts first).
- **Step 11**: Cloudflare Tunnel + domain (+ `--trusted-proxy cloudflare`).
- **Live OAuth sign-in test** never run (no OAuth apps registered yet).
- **Backup client-side encryption** (Litestream `age`) — deferred, recorded in §25.2.
- systemd/Linux deploy kit (`deploy/linux/`) — deferred in #202.
