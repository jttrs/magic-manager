# Future work

The one list of work that is known, agreed and not yet done. Keep it current: when an item lands,
delete it in the same PR; when a review defers something or a decision parks it, add it here.
Design detail lives in the linked docs, not here.

Last reviewed: 2026-11-04 (main `0a15987`, companion 0.5.1).

## 1. Waiting on the owner (hardware, accounts, money)

Nothing here can be done from code alone. Agents can prepare and walk the owner through it, and
need an explicit OK at every irreversible step.

| # | Item | Notes / where |
|---|---|---|
| O1 | **Set up the Mac mini** | `docs/home-server.md` §1: non-admin user, FileVault, no sleep, firewall, key-only SSH, Homebrew (`git uv node@22 gnupg`), Tailscale (MagicDNS + HTTPS), Chrome, read-only deploy key. |
| O2 | **Create the accounts** | Discord + Google OAuth apps (redirects `https://<mini>.<tailnet>.ts.net/api/auth/callback/{discord,google}`); Cloudflare R2 bucket `magic-manager-backups` + read/write token (mini) + read-only token (laptop) + billing alert. Secrets go only in `.env` (`uv run mm secret status`). |
| O3 | **Install and cut over** | `deploy/macos/install.sh --origin … --trusted-proxy tailscale` (dry run, then `--apply`), then `cutover.sh prepare` → `install-data` → `finish` (rehearsed, never run for real). Afterwards the mini is the source of truth; the laptop works on `mm db pull` copies. Decide what happens to the laptop's own launchd serve/deploy. |
| O4 | **Live sign-in test** | Sign in with Discord and Google on the mini, `mm auth bind`, invite one friend, check isolation and that owner-only paths are refused. |
| O5 | **External access (step 11)** | Buy the domain, Cloudflare Tunnel (no open ports), `MM_PUBLIC_ORIGIN`, re-install with `--trusted-proxy cloudflare`, add the domain's OAuth redirects, re-pair the companion, then a focused security review before inviting outsiders (§25.0). |
| O6 | **Chrome Web Store** | **Paused until the rebrand** (owner, 2026-11-05) — the name, icons and listing copy change with it. Runbook (rebrand pre-flight, Chrome + Edge steps, post-approval PR, optional upload secrets): `docs/companion-store-publishing.md`. Developer account ($5) → `scripts/build_extension.py --store-zip` → listing from `extension/store/listing.md` → Unlisted → submit; then fill `extension/store/store.toml`. Check the listing's permission text matches 0.5.x (the optional `https://*/*` pool, one origin requested at Pair). Steps: `docs/browser-companion.md` § Chrome Web Store. |

## 2. Checks that need the live server

Live tests: the owner clicks in their own Chrome, an agent verifies (DB read-only with
`sqlite3 -readonly`; never press Import / Add during a check unless intended).

### Can run now (laptop live app `:8766`, companion paired)

Done 2026-11-05 on companion 0.5.1→0.5.2: Moxfield collection read, Moxfield binder (list →
per-binder read), Archidekt deck via the companion, and a read with an unloaded Archidekt tab open
(the `archidekt.blocked` fix, #230).

- **Private Archidekt deck:** the 2026-11-05 run used a public deck (`private: false`); repeat
  Add cards → Add decklist or product → a *private* deck URL → Read deck, signed in to Archidekt.
- **Moxfield binder card count:** the binder-list approval's Cards column is blank —
  `extension/src/readers/moxfield-collection.js` guesses `totalCards` / `cardCount` /
  `totalOverall`. One signed-in probe of Moxfield's `/v1/trade-binders` response names the real
  field; then fix the reader (companion 0.5.3) and pin it with a fixture.

### After the mini (O3, some after O5)

- **Tailscale proxy header:** confirm `tailscale serve` sets `X-Forwarded-For` on the mini, so the
  login rate limiter keys on the real client (`MM_TRUSTED_PROXY=tailscale`; #206 deferred item).
- **Replica lag allowance:** measure real R2 replication timing against `offsite.LAG_SLACK`
  (5 min); the rehearsal only measures a `file://` replica. Watch `replica-check` for false alarms.
- **Monthly restore drill:** `mm-hosted host verify-replica`.
- **Companion update keeps pairing:** on a real Chrome update, an existing `*.ts.net` pairing keeps
  its permission and bridge.
- **`/api/ingest/precons` speed:** ~5 s on the owner's live server, not reproduced in tests —
  profile it live.
- **Vendor canary auto-close:** the step that closes issue #119 on a clean nightly run has not
  fired live yet (#208).

## 3. Engineering backlog (no owner hardware needed)

Small PRs, one per item.

- **CLI account delete and undo:** `mm auth delete-user` doesn't hold the web undo guard lock
  (the web route does) — a restore in flight could race the delete.
- **Split paths with spaces/symlinks:** `db._open_split` opens through `file:` URIs; no test covers
  a data dir whose path has spaces or symlinks.
- **Flaky earmark migration test:** confirm
  `tests/test_card_earmarks.py::test_v37_migration_single_and_split` is stable in CI history
  (reported order-dependent before #196).
- **Set docs branch:** a characterize-set session committed ~36 `docs/sets/*.md` docs on branch
  `claude/uncharacterized-set-families-905987` (5 commits ahead of main as of 2026-11-04, no PR
  yet; one more draft, `plst.md`, still untracked). If that session has finished: check the docs
  against `docs/sets/_TEMPLATE.md`, run `uv run pytest tests/test_config_schema.py`, open a docs PR.
- **Flag reads when auth.db is unreadable:** once `auth.db` exists, every `features.enabled()`
  reads it (`features.instance_flags`), and the first `auth.store.connect()` per process writes
  its schema. A corrupt, locked or foreign-owned file (e.g. an `mm …` CLI run on the mini as a
  different OS user than the server; the file is 0600) then fails every flag-gated route and
  command. Hardening: catch `sqlite3.Error` in `instance_flags()`, log it, fall back to the file
  layers; read `defaults()` through a read-only connection.
- **Deploy scripts key on a bare `auth.db`:** `deploy/macos/cutover.sh` (install-data),
  `bin/litestream.sh` and `bin/replica-check.sh` treat `$MM_DATA_DIR/auth.db` as "cut over".
  A local (non-hosted) `mm flags set` against that dir before `install-data` would create it.
  `offsite._is_hosted_dir` now checks for accounts instead; the scripts could do the same.
- **Flag picker leftovers:** `feature_defaults` rows for a flag removed from `features.toml` are
  never cleared (re-declaring the name brings the old value back); closing the picker mid-toggle
  and toggling the same flag again can send overlapping PUTs (last write wins); tests missing for
  clearing a just-me override via the API, a pinned flag via the API/CLI, and `mm flags ls`
  text output / `mm flags set --json`.
- **"What counts" preference leftovers** (`collection_prefs.py`, review of the prefs PR):
  `update()` reads and writes the one JSON blob on two connections with no transaction, so two
  concurrent PUTs on different keys (two tabs, or the CLI while the web app saves) can lose one —
  wrap both in one `BEGIN IMMEDIATE`; a `get()` that started before an `update()` can put the old
  value back in the cache for up to 30 s (a generation counter bumped by `clear_cache` fixes it);
  `mm prefs set` from a terminal reaches a running `mm serve` only after its 30 s cache expires;
  a forget function that raises after the write commits turns a saved PUT into a 500.

## 4. Deferred by decision

Agreed not to do now; revisit only when the reason changes.

| Item | Why deferred | Ref |
|---|---|---|
| Backup encryption (Litestream `age`) | Needs an off-box key escrow plan first | `docs/webapp-architecture-decision.md` §25.2 |
| Linux / systemd deploy kit (`deploy/linux/`) | Mac mini is the only host | §26, H7 |
| Docker vendor move | Same | §26, H7 |
| Forced provider re-login before account delete | Owner kept the 10-min fresh sign-in + typed confirm (2026-11-03) | `docs/handoff/05-owner.md` |
