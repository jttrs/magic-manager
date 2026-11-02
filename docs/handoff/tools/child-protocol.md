# magic-manager fan-out — child session protocol (authoritative)

You are a **builder** for the coordinator that briefed you. The coordinator owns **schema migration numbers, merge order, real-DB upgrades and deploys**. You own building ONE item well and handing back a PR.

## Setup
1. Your worktree is fresh off `origin/main`. Commit to your session's branch; don't create other branches. If the app asks you to rename the branch, use the `rename_branch` tool once with a short kebab name for your item.
2. **Dev DB** (worktrees start without one): take a READ-ONLY consistent copy of the real DB:
   `sqlite3 /Users/torre/repos/personal/magic-manager/db/magic_manager.db ".backup db/magic_manager.db"`
   Never write to the real DB. Never run `scripts/post_merge_upgrade.py --apply`.
3. **Ports** (yours are in your kickoff — never use 8765/5173/5174/8766, other sessions + the owner's live app use them):
   - API: `uv run mm serve --port $MM_API_PORT` (with `MM_FEATURES=deals,cart_check` if you need internal flags)
   - Vite: `MM_WEB_PORT=<web> MM_API_PORT=<api> npm --prefix web run dev`
   - e2e: `MM_E2E_PORT=<e2e> npm --prefix web run e2e`
   Stop your own servers by numeric PID when done (`lsof -tiTCP:<port> -sTCP:LISTEN`; `pkill`/`kill` without a PID are blocked).
4. `npm --prefix web install` once if `web/node_modules` is missing.

## Rules
- **CLAUDE.md is binding** (read it first): engine logic lives in `src/magic_manager/*`; a script becomes a thin driver over a lifted engine module (DRY — reuse `market`, `valuation`, `sets`, `edhrec`, `provenance`, `ingest`, `exports`, …); web/API are thin adapters; CLI is `uv run mm …`.
- **Schema**: you may NOT pick a migration number or append to `db.MIGRATIONS` on your own. Prefer designs with no schema change. If you truly need one, send the coordinator a `needs_input` message with the proposed SQL and why; wait for the assigned version, then follow `.claude/skills/db-upgrade/SKILL.md` part A (rehearsals on a copy of the real DB).
- **Shared files**: put your work in NEW modules/components/views; keep edits to shared screens (`web/src/views/MarketView.tsx`, `CollectionView`, `DecksView`/`DeckEditorView`, `ExploreView`, `web/src/components/AppShell.tsx`, `src/magic_manager/web/app.py`, `web/src/core/search.ts`, `web/src/app/queries.ts`) to small, additive hooks. Generated client files (`web/openapi.json`, `web/src/core/api/*`) — on conflict, regenerate with `npm --prefix web run gen:api` (offline).
- **UI**: use the `impeccable` skill (shape with the owner via `ask_user`, one question at a time with choices → build; load its `reference/craft-floor.md` before editing UI). `DESIGN.md` + `PRODUCT.md` are binding (tokens only, ruled guide sheet, amber accent, light + dark, icon actions with tooltips, no cards/lift/eyebrows). Visual-check desktop AND phone once, fix in one batch.
- **Browser**: prefer the headless e2e suite / small `npx playwright` scripts for visual checks. If you use the Playwright MCP browser, close it when done; never kill a Chrome process you didn't start.
- Hooks block bash commands containing the EDHREC hostname (even in text — use edit/create tools) and ad-hoc curl to Scryfall/MTGJSON/Mana Pool/EDHREC — use the sanctioned wrappers / engine clients.
- Concise replies to the owner; plain language.

## Done = PR + handoff (do NOT merge)
0. **Review first (CLAUDE.md rule 4):** run `/ce-code-review` on your branch, then `/findings-review` on its output, fix what survives, and put the output of `uv run python scripts/pr_review.py stamp --fixed N --deferred N --refuted N` in the PR body's `## Code review` section. Re-stamp after any later code change. Your handoff message says "review stamp: OK" (from `scripts/pr_review.py check --pr <N>`).
1. Gates = CI green on the PR (`ci.yml`: `pytest` / `web-check` / `e2e` / `extension`, required on main — read with `gh pr checks <N>`). Locally: targeted tests for what you touched + `npm --prefix web run check` when web changed (no full local pytest/e2e). Add tests for what you build (engine pytest + vitest for core view-models + e2e with mocked API routes).
2. Update `DESIGN.md` (UI patterns you added) and `CLAUDE.md` (engine/API map) concisely.
3. `git fetch && git rebase origin/main` (regen client on conflict), push, then
   `GH_TOKEN=$(env -u GH_TOKEN gh auth token --hostname github.com --user jttrs) gh pr create --base main …` (never switch gh accounts globally).
4. Send the coordinator ONE `handoff` message (`send_session_message`, `purpose: "handoff"`, to your creator session): PR number, 3-line summary, gate results, migration (none / assigned Vn), anything the owner must do.
5. If the coordinator asks you to rebase after another PR merges: `git fetch && git rebase origin/main`, regenerate the client, re-run the gates, `git push --force-with-lease`, reply briefly.

## Browser companion (`extension/`) etiquette (added 2026-10-10)
- Shared files: `extension/src/background.js`, `protocol.js`, `extension/errors.json`, `extension/manifest.json`. Put new readers in NEW files under `extension/src/readers/`; keep shared-file edits small and additive.
- Generated files (`extension/src/stores.js`, manifest host lists): never hand-edit — regenerate with `uv run python scripts/build_extension.py`; `--check` must pass. On a rebase conflict, regenerate.
- Every new failure gets an `<area>.<reason>` code in `extension/errors.json` (message + fix) and stays in sync with `config/analytics_events.toml` (a test enforces it).
- Security rules in `docs/browser-companion-security.md` are binding: click-to-read, the user approves exactly what is sent, lines only (no cookies/tokens/emails/addresses/order totals beyond what the feature needs), least-privilege opt-in host permissions, no remote code. Run the security-review agent on the finished diff and put its findings in the PR.
