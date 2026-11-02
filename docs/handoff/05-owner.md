# 05 — The owner: to-dos, preferences, decisions this cycle

## Owner to-do list (in order)

1. **Reload the companion to 0.5.0** — download it from the app (header → plug icon →
   Developer install), replace the unpacked folder, ↻ on `chrome://extensions`; re-pair with
   `http://localhost:8766` if it says "Not connected".
2. **Buy the Mac mini** → follow `docs/home-server.md` §1 (includes `brew install gnupg` and
   `install.sh … --trusted-proxy tailscale` — without the GnuPG key import, deploys on the mini
   HOLD because they only accept GitHub-signed squash-merges).
3. **Register OAuth apps** (Discord + Google) with the mini's Tailscale redirect URIs; secrets →
   the mini's `.env` (`MM_OAUTH_DISCORD_CLIENT_ID/_SECRET`, `MM_OAUTH_GOOGLE_CLIENT_ID/_SECRET`).
4. **Cloudflare R2:** bucket `magic-manager-backups`, read/write token (mini), read-only token
   (laptop), billing notification.
5. **Cutover** with the coordinator (explicit OK at each irreversible step) → live sign-in test →
   invite a friend.
6. **Step 11:** buy the domain; Cloudflare Tunnel.
7. **Chrome Web Store:** developer account ($5) → upload → Unlisted → submit (see 02-roadmap §B).
8. Answer two parked UX questions (02-roadmap §D) when convenient.

## How the owner likes to work

- Concise, plain-language replies; no jargon dumps. One question at a time, multiple choice,
  recommended option first.
- Small PRs, merged after gates; the coordinator merges. Owner occasionally merges a ready PR
  manually — re-check state before acting.
- Security-first (§25.0) and "never harm users" are binding.
- Cost-conscious: minimal budget (domain + free tiers); anything costing more comes back to them.
- Prefers CI over local machine load for heavy checks (asked for it explicitly, 2026-11-01 → #203).
- Wants deterministic engine code with thin CLI/web/skill adapters, DRY (CLAUDE.md rules 1–2).
- Real DB is precious: ask before every apply; show rehearsal results first.

## Decisions made this cycle (2026-10-12 → 2026-11-01)

| Date | Decision |
|---|---|
| 10-12 | Home server = **Mac mini, native** (launchd) — to be bought (separate machine, not the laptop) |
| 10-12 | Budget = **minimal**: domain (~$10/yr) + free-tier R2 |
| 10-12 | Friends/general access = **Cloudflare Tunnel + own domain** (scales to general users); owner admin over Tailscale |
| 10-12 | V36 applied to the real DB (rehearsal → OK → apply; snapshot `db/bak/…221352-pre-v36`) |
| 10-12 | Step 4 OAuth: register real apps (not done yet); merge #177 without the live test |
| 11-01 | Step 5: keep `PROFILES_OPEN=False` until step 6 pinned owner-machine paths (then opened in #200) |
| 11-01 | Post-cutover CLI on the laptop = **local copy re-pulled from R2** (no two-way sync, H3) |
| 11-01 | Heavy gates → **GitHub CI** (public repo = free runners); local = targeted tests only; ruleset requires CI checks, strict |
| 11-01 | Step 10 hardening: fix all review items **except** client-side backup encryption (deferred; needs off-box key escrow) |
| (builder-level, accepted) | Members never reach the server's browser (companion only); EDHREC rankings fetch = admin-only, members see cached; 3-job cap for everyone; HSTS without includeSubDomains; pairing refuses IP/one-word hosts and reader sites |
