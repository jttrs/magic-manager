# 04 — Where the work lives (branches, worktrees, sessions)

Main checkout: `/Users/torre/repos/personal/magic-manager` (branch `main`, keep it clean — it is
where db-upgrade part B runs). All worktrees below hang off it (`git worktree list`).

## Active / needs a decision

| Location | Branch | State | What to do |
|---|---|---|---|
| `.worktrees/live` | detached @ `789bdf4` | **Owner's live app** (`:8766`), auto-deployed by launchd | Never edit; it follows main automatically |
| `.worktrees/torre-orchestrator-handoff` | `torre/orchestrator-handoff` | This handoff (docs/handoff/) | Docs-only; merge its PR (exempt from review stamp) or keep as a branch |
| `.claude/worktrees/uncharacterized-set-families-905987` | `claude/uncharacterized-set-families-905987` (= main @ 8dbf86f, 0 commits ahead) | **14 untracked `docs/sets/*.md` drafts**: dmr, j22, mar, mb2, mdd, nau, ph22, ph23, rvr, scd, slz, unk, who (+ mbc, already on main via #205) — `characterize-set` output from a Claude Code session, never committed | Ask the owner whether that Claude Code session is still running. If not: review against `docs/sets/_TEMPLATE.md`, run `uv run pytest tests/test_config_schema.py` (config↔docs §8 sync), and open a docs PR (add any `config/families.toml` entries the docs' §8 reference) |
| `.claude/worktrees/magic-manager-audit-followups-51d16b` | `claude/magic-manager-audit-followups-51d16b` (merged; 0 ahead) | untracked `companion-store.zip` (Chrome Web Store upload built 2026-11-01 10:20, **pre-0.5.0**) | Don't upload it; rebuild with `build_extension.py --store-zip` from main. Worktree can be removed once the owner confirms the Claude session is done |
| `.claude/worktrees/magic-manager-rebrand-fc5d70` | `claude/magic-manager-live-checks-fdd45c` (0 ahead) | clean | Stale Claude Code worktree — remove after owner confirms |
| `.claude/worktrees/mbc-family-classification-7020d8` | detached | clean (MBC merged as #205) | Stale — remove after owner confirms |
| `.worktrees/copilot-prewarm-cautious-carnival` | detached @ 18a197f | clean | Copilot-app prewarm worktree — leave to the app |
| `.worktrees/torre-fluffy-train` | detached | clean | The previous coordinator's own worktree (branch `torre/phase3-coordinator` merged as #171) — scratch area for gates |

## Stale (merged) branches safe to clean

`.worktrees/retro-b-matching` (#144), `retro-b-store-reads` (#141), `retro-b-watching` (#142),
`retro-c-extension` (#154), `retro-c-scraper-health` (#153), `retro-c-store-ids` (#151),
`retro-c-vendors` (#150) — all MERGED (squash; their local commits show as "ahead" only because of
squash). Remove with `git worktree remove <path>` + `git branch -D <branch>` after confirming no
uncommitted changes (`git -C <path> status --short`).

Phase 3 builder worktrees (`torre-phase3-step7/8/9/10`, `torre-ci-heavy-gates`) were already
removed after merge. Remote branches of merged PRs may still exist on GitHub; deleting them is
harmless.

## Sessions

- Copilot app coordinator (this cycle): "Resume the magic-manager web app's remaining roadmap"
  (`9ac8416a-97ac-4b4e-baa5-4a1154cd15a2`), worktree `.worktrees/torre-fluffy-train`. Being retired
  by this handoff.
- All Phase 3 child sessions (steps 1–6, Best Buy/Target fixtures) are archived; steps 7–10 + CI
  were background agents of the coordinator (no session left behind).
- Earlier magic-manager Copilot sessions ("Web app UX audit" fan-out coordinator, "FIN loose card
  reconciliation", "test_undo …" previous coordinator) are archived / no longer listed.
- Claude Code sessions own `.claude/worktrees/*` (see above). Their state is not visible from the
  Copilot app — ask the owner.

## Key in-repo docs to extend

- `docs/webapp-architecture-decision.md` §25 — Phase 3 record. Update §25.2/§25.4 as the cutover
  and step 11 happen; add a Phase 5 section when it's shaped.
- `docs/home-server.md` — Mac mini runbook (update with anything learned during the real setup).
- `docs/browser-companion.md`, `docs/browser-companion-security.md` (incl. its review log),
  `docs/privacy-companion.md`, `extension/store/` — Chrome Web Store.
- `CLAUDE.md` — module map + rules; every PR keeps it current.
- `docs/sets/<anchor>.md` — per-family memory (read before set-specific work).
