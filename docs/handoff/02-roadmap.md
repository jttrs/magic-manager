# 02 — Roadmap: what's left, in order

Priorities as the owner set them: **finish Phase 3 (hosting) → Chrome Web Store publish of the
companion → Phase 5**. Phase 3 code is done; the remaining Phase 3 items need the owner's hardware
and accounts, so plan engineering work that doesn't block on them in parallel.

## A. Phase 3 completion (owner-gated)

1. **Owner acquires the Mac mini** and follows `docs/home-server.md` from zero: dedicated non-admin
   user, FileVault, never sleep (`pmset`), firewall, key-only SSH; Homebrew, `git uv node@22`,
   Tailscale (MagicDNS + HTTPS, `tailscale serve --bg 8765`), Chrome; read-only GitHub deploy key,
   clone to `~/magic-manager/app`; **`brew install gnupg`** (signed-commit deploys from #206).
2. **Accounts** (owner): Discord + Google OAuth apps with redirect URIs
   `https://<mini>.<tailnet>.ts.net/api/auth/callback/{discord,google}` (add the domain's later at
   step 11); Cloudflare R2 bucket `magic-manager-backups` + two tokens (read/write for the mini,
   read-only for the laptop) + a billing notification. Secrets go only in the mini's `.env`
   (`MM_OAUTH_*`, `MM_OFFSITE_*`), check with `uv run mm secret status`.
3. **Install:** `deploy/macos/install.sh --origin https://<mini>… --trusted-proxy tailscale`
   (dry run), then `--apply`.
4. **Cutover** (rehearsed in #202 with a file:// replica; never run for real). Coordinator walks
   the owner through it and gets an explicit OK at each irreversible step:
   laptop: stop `com.magic-manager.serve` + `.deploy` → `cutover.sh prepare --to ~/mm-cutover --yes`
   → rsync to the mini → mini: `cutover.sh install-data` → sign in with the printed admin invite →
   `cutover.sh finish --user <auth-id>` → re-run `install.sh … --owner-id <id> --apply` → verify
   (ledger reconcile, catalog-refs, integrity, Litestream first replica). Rollback = pre-cutover
   snapshot or `mm host restore` from R2. After cutover the **mini is the source of truth**; the
   laptop's CLI/skills work on a local copy pulled with
   `mm db pull --from r2 --user <id> --to ~/mm-copy` (read-only token, Litestream 0.5.17 on the
   laptop). Writes to that copy are NOT real data (H3; owner confirmed 2026-11-01).
   Decide with the owner what happens to the laptop's launchd serve/deploy after cutover (likely:
   unload them, or keep a local read-only copy app on another port).
5. **Live OAuth sign-in test** (never done): sign in with Discord and with Google on the mini;
   `mm auth bind`; invite one friend (member) and verify isolation + owner-only paths refused.
6. **Monthly restore drill:** `mm-hosted host verify-replica` (no alerting on replication stalls
   yet — consider adding one as a small follow-up).
7. **Step 11 — external access:** buy the domain (~$10/yr), Cloudflare Tunnel to the mini (no open
   ports), `MM_PUBLIC_ORIGIN=https://<domain>`, re-run install with `--trusted-proxy cloudflare`
   (exactly one proxy in front of the app), add the domain's OAuth redirect URIs, re-pair the
   companion. HSTS is sent without `includeSubDomains` by design (#206). Re-run a focused
   security review of the exposed surface before inviting outsiders (§25.0).

## B. Chrome Web Store publish (can start now)

No longer blocked on the domain (#204: pairing accepts any https origin). Owner steps (from #188):
create the Chrome Web Store developer account ($5) → upload the first `--store-zip`
(`uv run python scripts/build_extension.py --store-zip out.zip`; see
`docs/browser-companion.md` § Chrome Web Store and `extension/store/README.md`) → paste
`extension/store/listing.md` into the listing + privacy tabs (`docs/privacy-companion.md`) → set
**Unlisted** → submit. After approval: set `url` + `extension_id` in `extension/store/store.toml`;
optionally add `CWS_CLIENT_ID/CWS_CLIENT_SECRET/CWS_REFRESH_TOKEN/CWS_PUBLISHER_ID/CWS_EXTENSION_ID`
repo secrets so `extension-release.yml` uploads drafts automatically. Edge Add-ons listing is
optional (#198). A stray `companion-store.zip` exists in a Claude worktree (see 04) — rebuild
from main rather than reuse it (it predates 0.5.0).
Engineering to check before submission: the listing copy and permission justifications must match
0.5.0 (optional host permission pool `https://*/*` from which ONE origin is requested at Pair —
reviewers will ask; justify it in `listing.md`).

## C. Phase 5 — DONE (2026-11-03; `docs/webapp-architecture-decision.md` §26)

Merged: #216 shared wrapper rate-limit library, #218 call-slot reservation under a kernel
`flock` (no stale locks, downloads overlap, a 429 stops queued callers), #214 timeouts on every
wrapper call (`util.run_wrapper`), #215 persistent cache dir on the mini/in Docker
(`install.sh --cache-dir`), #217 hosted server never drives a browser (Moxfield + Mac tabs via
the companion for everyone). Follow-ups: `scripts/import_deck.py` subprocess (`addcards`) has no
timeout; Linux/systemd kit + Docker vendor move stay deferred (H7).

## D. Follow-up backlog (small PRs, no owner hardware needed)

From Phase 3 PR "deferred" lists:
- #201: done in #210 (no orphan/recreated user file; per-user cache registry). Owner decided
  2026-11-03 to keep re-auth as is (no forced provider login). Pre-bind `owner` snapshots stay
  (decided in #201). Residual: CLI `mm auth delete-user` doesn't hold the web undo guard lock.
- #202: stall alert done in #209 (`mm host replica-lag` + `replica-check` agent); its 5-min
  `LAG_SLACK` is unmeasured against real Litestream timing — add a `replica-lag` step to
  `scripts/rehearse_home_deploy.py`, or watch for false alarms after cutover.
  `deploy/linux/` systemd kit still deferred.
- #204: no dedicated test for `pair.bridge_failed` / bridge reset on pairing change; verify on a
  real Chrome update that an existing `*.ts.net` pairing keeps its permission.
- #206: 2 deferred review items (see the PR's Code review section).
- Backup encryption (Litestream `age`) with an off-box key escrow plan (§25.2).
From the web UX round-2 fan-out (all chunks merged; open follow-ups):
- (Checked 2026-11-03, already done on main: "colour" copy — only the stable `colour_identity`
  API code remains; Explore family picker lists every paper family, owned first; `art.lookup`
  title no longer names a vendor.)
- `/api/ingest/precons` ~5 s on the owner's live server (didn't reproduce in tests) — profile live.
- `tests/test_card_earmarks.py::test_v37_migration_single_and_split` was reported flaky/order-
  dependent before #196 — confirm it's fixed in CI history.
Other:
- Issue #119 (vendor canary): fixed in #208 (CI forgives only a bot wall, `scrape.blocked`;
  closes its issue on a clean run). The close step hasn't fired live yet.
- `_open_split` now opens through `file:` URIs: no test covers data dirs with spaces/symlinks.
- Untracked `docs/sets/*.md` drafts for 14 families in a Claude worktree (see 04) — characterize-set
  output that was never committed.
