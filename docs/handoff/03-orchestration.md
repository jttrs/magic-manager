# 03 — How to orchestrate this repo

## Roles

- **Coordinator (you):** shape decisions with the owner (one `ask_user`-style question at a time,
  multiple choice, recommended option first), assign migration numbers, write builder briefs,
  gate and merge PRs, run real-DB upgrades (with the owner's OK), keep the plan docs current.
  Design/ambiguity stays with you; builders only implement settled specs.
- **Builders:** one small PR per item, in their own worktree off `origin/main`, following
  `tools/child-protocol.md` (binding). They never merge, never pick a migration number, never
  write the real DB.
- **Owner:** approves decisions, real-DB upgrades, anything touching their machine/accounts.

### How builders were launched this cycle (and what broke)

- Originally: Copilot-app **child sessions** (`create_session` with a kickoff prompt; ports per
  child; the child sends ONE handoff message back).
- Since 2026-11-01 ~14:45 PT, the Copilot app failed to start new sessions
  ("Failed to initialize standalone session tools: Session plugin inputs changed during reload"),
  even after an app restart and after disabling the `copilot-goal-skill@awesome-copilot` plugin
  (which logged an invalid inline hooks config). Workaround used for steps 7–10 + CI: the
  coordinator creates a worktree itself and runs a **background general-purpose agent** with a
  self-contained brief (worktree path, branch, ports, READ FIRST list, settled DECISIONS,
  rehearsal requirements, FINISH checklist, RETURN contract). This worked well; reuse it in any
  agent environment. Template = any of the step briefs summarized below.

### Builder brief skeleton (what every brief contained)

1. Objective quoted from §25.4 / the roadmap, "as one PR".
2. Worktree path + branch (created by the coordinator:
   `git worktree add -b torre/<slug> .worktrees/<slug> origin/main`, then `uv sync`,
   `npm --prefix web ci`). "Work ONLY there; never touch other worktrees, the main checkout,
   the real DB, the live app, the owner's Chrome profile."
3. READ FIRST: `tools/child-protocol.md`, CLAUDE.md rules 1–5 + the relevant module-map entries,
   the relevant §25 sections, and the bodies of the PRs it builds on.
4. Ports (unique per builder; never 8765/5173/5174/8766): API 87xx, Vite 51xx, `MM_E2E_PORT`.
5. Migration policy (none expected / assigned Vn + db-upgrade part A).
6. Numbered settled DECISIONS (the coordinator's design — no open questions left for the builder;
   "if forced, take the most security-conservative option and list it under Decisions taken").
7. Rehearsal on a fresh `.backup` copy of the real DB (split it with `mm db split` when hosted
   behaviour matters; mock OAuth helpers from #199/#200 tests), tmp copies deleted afterwards.
8. Security-review agent on the diff when it touches auth, isolation, files, network, extension.
9. FINISH: `/ce-code-review` → `/findings-review` (or `findings-evaluation`) → fix →
   `uv run python scripts/pr_review.py stamp --fixed N --deferred N --refuted N` into the PR
   body's `## Code review`; update CLAUDE.md (+ DESIGN.md for UI); rebase; push; `gh pr create`;
   wait for CI green; `scripts/pr_review.py check --pr <N>` OK. Do NOT merge.
10. RETURN: PR + summary + CI + security findings + stamp + owner actions.

## PR rules (CLAUDE.md rule 4 + ruleset)

- Every non-docs PR carries a review stamp in its body (from `scripts/pr_review.py stamp`); CI's
  `review-stamp` check verifies it fingerprints the PR's code. A clean rebase keeps it; any later
  code change needs a re-review of the delta and a fresh stamp. Docs-only PRs (Markdown outside
  `CLAUDE.md`, `.claude/`, `.github/`) are exempt.
- PR body follows `.github/pull_request_template.md` (What changes / Tests / Code review / After merge).
- Commits carry `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>` in
  this environment (use your environment's equivalent trailer).

## Merge gate — `tools/ci_gate.md <pr> "<squash title>"`

Copy it to `/tmp` (or run in place) from any checkout of the repo. It: updates the PR branch onto
main **on GitHub** (`update-branch`, rebase) if behind → waits (≤30 min) for `pytest`,
`web-check`, `e2e`, `extension`, `review-stamp` on the new head → runs `pr_review.py check`
locally against that head → merges via REST, squash, `sha=<head>` pinned. Exit 1 = CI failed,
2 = rebase conflict (rebase by hand; regenerate `web/openapi.json` + `web/src/core/api/*` with
`npm --prefix web run gen:api` on conflict), 3 = stamp missing/stale. `DRY=1` skips the merge.
Gate on exit codes, never on tail output. If a rebase changes code (conflict resolution), the
stamp is stale → re-review the delta and restamp.

The old local gates (`gate_merge.sh`, `coord_rebase.sh`, `c3_*.sh` in
`~/.claude/plans/coordinator-tools/`) ran the full suite locally (~15 min, flaky under load) —
retired since #203.

## Database changes — `.claude/skills/db-upgrade/SKILL.md` (no exceptions)

- Part A on the branch: additive migration with a `MIGRATION_TARGETS` target (>V36), idempotent
  backfill registered in `scripts/post_merge_upgrade.py`, tests, BOTH rehearsals
  (`scripts/rehearse_migration.py` and `post_merge_upgrade.py --db <pre-vN copy>`; split layout:
  `--layout split --data-dir <dir>`) with verdicts in the PR.
- Part B after merge (coordinator, owner OK required): in the main checkout
  (`git status` clean → `git pull --ff-only` → `uv sync`) run
  `uv run python scripts/post_merge_upgrade.py` (rehearsal on a copy) → show the owner → on OK:
  stop the live serve agent → `post_merge_upgrade.py --apply` → `mm audit ingest-ledger`,
  `mm audit catalog-refs`, `mm db integrity` → restart serve → run the deploy script once and
  confirm `/api/features` = 200. Report the snapshot path + `mm db restore` command.
  After cutover this happens on the Mac mini via `deploy/macos/bin/upgrade.sh --apply` (split-aware,
  pair-snapshots first, only the rehearsed commit).

## Tripwires

- Never touch the real DB without the owner's OK; rehearse on copies; never copy a worktree DB over it.
- §25.0 security-first: user derived only from the server session; per-user file isolation;
  admins can't act as users or read collections; secrets only in the host's secret store
  (gitignored `.env`), never in repo/logs/client; security review before outsiders.
- `extension/` changes: one builder at a time; bump the version; keep `extension/errors.json` ↔
  `config/analytics_events.toml` enum ↔ companion e2e in sync; `build_extension.py --check` must
  pass (`stores.js`, `tokens.css`, manifest host lists are generated — never hand-edit).
- Hooks block any bash command containing the EDHREC hostname (even in text — use file edit
  tools) and ad-hoc curl to Scryfall/MTGJSON/Mana Pool/EDHREC/deck sites — use the wrappers in
  `.claude/skills/*/` or the engine clients. `pkill`/`kill` without a numeric PID are blocked.
- `/tmp` gets wiped between days; keep tools in the repo/plans dir and copy as needed.
- Known e2e flakes under heavy local load (companion-extension "extension is reloaded", decks
  "add the whole deck") — CI runs them sharded; rerun alone before assuming a real failure.
- Every CLI command must run non-interactively with flags (CLAUDE.md rule 5).
- Other sessions/agents (Claude Code under `.claude/worktrees/`) also work in this repo — check
  `gh pr list` and worktrees before assigning overlapping work; rebase before fixing migration numbers.

## Plan files outside the repo (this machine)

- `~/.claude/plans/magic-manager-next.md` — running "what's left" list (kept current by the coordinator).
- `~/.claude/plans/magic-manager-fanout.md` — builder protocol (copied here as `tools/child-protocol.md`).
- `~/.claude/plans/coordinator-tools/` — `ci_gate.sh` (copied here), retired local gates.
- `~/.claude/plans/splits/*.md` — earlier split-off plans (all `status: done`, incl.
  `hosting-auth-profiles.md`, `webapp-chassis.md`).
- `~/.claude/plans/fanouts/mm-web-ux-r2*` + `audits/mm-web-ux-r2.audit.*` — web UX round-2 fan-out
  (status done; all 10 chunks merged #176, #188–#196).
