# Orchestrator handoff — magic-manager (2026-11-01)

You are taking over as **coordinator/orchestrator** of the magic-manager web app roadmap from a
GitHub Copilot app session ("Resume the magic-manager web app's remaining roadmap", session
`9ac8416a-97ac-4b4e-baa5-4a1154cd15a2`). Read these in order; together they are authoritative for
*where we are, what's next, and how work gets done here*.

| # | File | What it gives you |
|---|---|---|
| 1 | [01-state.md](01-state.md) | Exact current state: main, DB, live app, companion, CI, what Phase 3 shipped (PR by PR) |
| 2 | [02-roadmap.md](02-roadmap.md) | What's left, in order: owner hardware/accounts → cutover → step 11 → Chrome Web Store → Phase 5, plus the follow-up backlog |
| 3 | [03-orchestration.md](03-orchestration.md) | How to run the work: roles, PR rules, the CI merge gate, review stamp, db-upgrade, builder briefs, ports, tripwires |
| 4 | [04-work-locations.md](04-work-locations.md) | Every branch / worktree / session / plan file that holds work, and what to do with each |
| 5 | [05-owner.md](05-owner.md) | The owner's to-do list, how they like to work, and the decisions they made this cycle |
| — | [tools/ci_gate.sh](tools/ci_gate.sh) | The merge gate script (rebase on GitHub → wait for CI → verify stamp → merge pinned sha) |
| — | [tools/child-protocol.md](tools/child-protocol.md) | The builder ("child") protocol every implementation agent follows |

Then read, in the repo: `CLAUDE.md` (binding engineering rules 1–5 + module map),
`docs/webapp-architecture-decision.md` §25 (Phase 3 design, decisions H1–H14, build order),
`docs/home-server.md` (the Mac mini runbook), `PRODUCT.md`, `DESIGN.md`.

**One-paragraph summary.** magic-manager (`mm`) is the owner's local-first MTG collection app:
Python engine (`src/magic_manager/*`), FastAPI thin adapter + React/TS SPA (`web/`), MV3 browser
companion (`extension/`), SQLite. Phase 3 (hosting, invite-only login, per-user profiles) is
**code-complete and merged** (steps 1–10 of §25.4, PRs #171–#206). Nothing is hosted yet: the
cutover to a home Mac mini waits on the owner buying the hardware and creating accounts
(OAuth apps, Cloudflare R2). The owner's laptop still runs the app in local single-file mode on
`:8766`, auto-deployed from `main`. CI now runs all heavy gates; merges go through
`tools/ci_gate.sh`. Next engineering work that does *not* need the Mac mini: Chrome Web Store
listing (owner account needed), Phase 5 scoping, and the follow-up backlog in 02-roadmap.md.
