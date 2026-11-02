# Home server — Mac mini runbook (Phase 3 §25.4 step 8)

The hosted app runs **natively** on a Mac mini in the house (§25.1 H7, §25.2): `mm serve` in
hosted mode as an always-on launchd agent, deployed by `git pull`, with its data in one
directory that **Litestream** copies offsite to **Cloudflare R2** (free tier, §25.2 budget).
The laptop keeps the CLI and skills and works on a **local copy** pulled from R2 when you
want it fresh (H3 — no two-way sync).

```
Mac mini (always on, FileVault, logged in)                     Cloudflare R2 (free tier)
  ~/magic-manager/app        git clone, auto-deployed            magic-manager-backups/
  ~/magic-manager/data/      0700, every file 0600                 auth.db/ltx/…          continuous
    auth.db                  sign-in (precious)   ── Litestream ─▶ users/<id>.db/ltx/…    continuous, 30 days
    users/<id>.db            one per person (precious) ────────▶
    catalog.db               shared card cache  ── weekly ──────▶ catalog/catalog-<ts>.db.gz  keep 2
    analytics.db             disposable (never offsite)
  127.0.0.1:8765  ◀── tailscale serve (https://<mini>.<tailnet>.ts.net, tailnet only)

Laptop: `mm db pull --from r2 --user <id> --to ~/mm-copy`  (read-only token) → local split copy
```

What is in the repo: `deploy/macos/` (installer, launchd templates, wrapper scripts,
cutover script), `magic_manager.offsite` (Litestream config, catalog snapshots, re-pull,
restore), `magic_manager.hostops` (the deploy hold, WAL, permissions) and the CLI twins
`mm host …` / `mm db pull`. The whole flow was rehearsed end to end on a copy of the real DB
with a local `file://` replica: `scripts/rehearse_home_deploy.py`.

## Costs (R2 free tier: 10 GB-month storage, 1M class-A ops, 10M class-B ops / month)

| What | Storage | Class-A ops / month |
|---|---|---|
| Your collection file (15 MB raw, ~9 MB per Litestream snapshot) — a new daily snapshot only on days it changed, kept 30 days | ≤ 0.3 GB | idle: 1,440 (the L0-retention sweep: 2 LISTs per hour) |
| `auth.db` + ~5 friends' files (small) | < 0.05 GB | idle: 1,440 per file → ~9k |
| Writes while people use the app (≤ 1 upload per 10 s sync + compactions ≈ 500 PUTs per busy hour per file); e.g. you 2 h/day, friends 2.5 h/day, auth.db whenever anyone is on | — | ~135k |
| Weekly catalog snapshot (157 MB gzip of the 645 MB catalog), keep 2 | 0.32 GB | < 50 |
| Weekly prune of deleted accounts | — | ~5 |
| **Total** | **≈ 0.7 GB (7 % of free)** | **≈ 150k (15 % of free)** |

Class-B (reads) only happen on restores, compactions and drills — far under 10M. Deletes are free.
The intervals that make this fit are in `offsite.py` (`SYNC_INTERVAL = 10s`,
`L0_RETENTION_CHECK = 1h`, snapshots daily, retention 720 h): Litestream's default 15-second
L0 sweep alone would cost ~170k LISTs per file per month. **Set a billing notification in
Cloudflare** (R2 needs a card on file even on the free tier; overage is $4.50 per million
class-A ops, $0.015/GB-month). The catalog is deliberately *not* continuously replicated: a
set sync rewrites thousands of pages, which would burn write ops on a cache we can rebuild.

## 1. Set up the Mac mini from zero

1. **macOS account.** Create one standard (non-admin) user for the server, e.g. `mm`, and do
   everything below as that user (use an admin account only for `sudo` steps). Turn
   **FileVault on** (the data dir holds people's collections and sign-in sessions). The
   agents run in that user's login session (they need it for the H9 Chrome/AppleScript
   features), so after a *power cut* someone unlocks the Mac at the keyboard; for planned
   restarts use `sudo fdesetup authrestart` (it comes back logged in).
2. **Always on** (admin):
   ```sh
   sudo pmset -a sleep 0 disksleep 0 autorestart 1 womp 1
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode on
   ```
   System Settings → General → Software Update: install *Security Responses and system
   files* automatically; install macOS updates by hand (they restart).
   System Settings → General → Sharing: **Remote Login** on, *only* for `mm`. Then key-only SSH:
   ```sh
   echo 'PasswordAuthentication no
   KbdInteractiveAuthentication no' | sudo tee /etc/ssh/sshd_config.d/100-keys-only.conf
   ```
3. **Tools** (as `mm`):
   ```sh
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   brew install git uv node@22 && brew link --force node@22
   brew install --cask tailscale google-chrome
   ```
   Litestream is installed by the installer (pinned v0.5.17, SHA-256 checked), not by brew.
4. **Tailscale.** Open Tailscale, sign in to your tailnet. In the admin console enable
   *MagicDNS* and *HTTPS Certificates*. Then publish the app to the tailnet only (not Funnel):
   ```sh
   tailscale serve --bg 8765
   tailscale serve status        # shows https://<mini>.<tailnet>.ts.net → 127.0.0.1:8765
   ```
   That https name is `MM_PUBLIC_ORIGIN` until Cloudflare Tunnel (§25.4 step 11).
5. **The app.** Add a **read-only deploy key** for this repo (GitHub → repo → Settings →
   Deploy keys; `ssh-keygen -t ed25519 -f ~/.ssh/mm_deploy`), then:
   ```sh
   mkdir -p ~/magic-manager && cd ~/magic-manager
   GIT_SSH_COMMAND='ssh -i ~/.ssh/mm_deploy' git clone git@github.com:jttrs/magic-manager.git app
   cd app && git config core.sshCommand 'ssh -i ~/.ssh/mm_deploy'
   uv sync --frozen && npm --prefix web ci && npm --prefix web run build
   uv run playwright install chromium        # only for the admin-only Moxfield import
   ```
6. **Cloudflare R2.** Cloudflare dashboard → R2 → *Create bucket* `magic-manager-backups`
   (Standard storage class — not Infrequent Access; no public access, no r2.dev URL). Then
   R2 → *Manage API tokens* → create **two** tokens, both *Apply to specific buckets only* →
   `magic-manager-backups`:
   - `mm-server` — **Object Read & Write** (the mini: Litestream, the catalog upload, pruning).
   - `mm-laptop-pull` — **Object Read only** (the laptop's `mm db pull`; it can never change a backup).

   Note each token's *Access Key ID* and *Secret Access Key* (shown once) and your S3 endpoint
   `https://<account-id>.r2.cloudflarestorage.com`. Add a billing notification.
7. **Sign-in apps** (H4). Redirect URIs to add now (replace the host with yours):
   - Discord (discord.com/developers → New Application → OAuth2 → Redirects):
     `https://<mini>.<tailnet>.ts.net/api/auth/callback/discord`
   - Google (console.cloud.google.com → APIs & Services → Credentials → OAuth client ID →
     Web application → Authorized redirect URIs):
     `https://<mini>.<tailnet>.ts.net/api/auth/callback/google`
     (OAuth consent screen: External, *Testing*, add your Google account as a test user.)

   At step 11 add the same paths on your own domain.
8. **Secrets** — only in `~/magic-manager/app/.env` (gitignored; the installer makes it 0600):
   ```sh
   cat >> ~/magic-manager/app/.env <<'EOF'
   MM_OAUTH_DISCORD_CLIENT_ID=…
   MM_OAUTH_DISCORD_CLIENT_SECRET=…
   MM_OAUTH_GOOGLE_CLIENT_ID=…
   MM_OAUTH_GOOGLE_CLIENT_SECRET=…
   MM_OFFSITE_URL=s3://magic-manager-backups/prod?endpoint=https://<account-id>.r2.cloudflarestorage.com
   MM_OFFSITE_ACCESS_KEY_ID=<mm-server key id>
   MM_OFFSITE_SECRET_ACCESS_KEY=<mm-server secret>
   EOF
   chmod 600 ~/magic-manager/app/.env
   cd ~/magic-manager/app && uv run mm secret status     # names + where they come from, never values
   ```
   The R2 secret is handed to Litestream through its environment only — never its config
   file, argv, the plists or a log.
9. **Install the agents** (non-interactive; dry run first):
   ```sh
   cd ~/magic-manager/app
   deploy/macos/install.sh --origin https://<mini>.<tailnet>.ts.net            # shows the plan, writes nothing
   deploy/macos/install.sh --origin https://<mini>.<tailnet>.ts.net --apply
   ```
   It installs Litestream into `~/Library/Application Support/magic-manager-hosted/bin/`,
   copies the wrapper scripts there with `hosted.env` (non-secret settings, 0600), writes four
   agents `com.magic-manager.hosted.{serve,litestream,deploy,catalog-backup}` (umask 077, logs
   in `~/Library/Logs/magic-manager-hosted/`) and creates the empty data dir (0700). It starts
   nothing yet — the cutover does. Add `~/Library/Application Support/magic-manager-hosted`
   to your `PATH` for `mmctl` (start/stop/status) and `mm-hosted` (the CLI with the hosted settings).

## 2. Cutover (laptop single DB → the mini) — owner's OK required

Do it when nobody is using the app. The laptop's real DB is only *read*.

1. **Laptop: stop the live app** (its agents are yours to stop; the script refuses while it runs):
   ```sh
   launchctl bootout gui/$(id -u)/com.magic-manager.deploy
   launchctl bootout gui/$(id -u)/com.magic-manager.serve
   ```
2. **Laptop: snapshot + split** (the same commit on both machines):
   ```sh
   cd ~/repos/personal/magic-manager && git pull
   deploy/macos/cutover.sh prepare --to ~/mm-cutover --yes
   ```
   → `db/bak/magic_manager.db.bak-<ts>-pre-cutover`, then `mm db split` (prints SPLIT OK:
   ledger 0 drift, catalog-refs 0, FK 0, integrity ok), then 0700/0600.
3. **Copy to the mini** over Tailscale:
   ```sh
   rsync -a --chmod=D700,F600 ~/mm-cutover/ mm@<mini>:magic-manager/data/
   ```
4. **Mini:** `deploy/macos/cutover.sh install-data` — checks the copied files are at this code's
   schema (`mm host deploy-check`), turns on **WAL** for every file (`mm host wal --apply`),
   starts the app and prints a single-use **admin invite** link.
5. **Sign in** with that link (Discord or Google) in a browser on your tailnet. Then
   `mm-hosted auth users` shows your id (16 characters).
6. **Mini:** `deploy/macos/cutover.sh finish --user <id>` — stops the app, `mm auth bind`
   (your split file becomes `users/<id>.db`; the empty first-sign-in profile is set aside),
   starts Litestream, waits until `mm host verify-replica` restores every file equal to live,
   uploads the first catalog snapshot, starts the app, auto-deploy and the weekly backup.
7. **Record your id** for upgrades: `deploy/macos/install.sh --origin https://… --owner-id <id> --apply`.
8. **Verify:** open the app — your decks and purchase history are there; `mmctl status` shows
   four agents; `tail ~/Library/Logs/magic-manager-hosted/litestream.log`.
9. **Laptop from now on:** leave `com.magic-manager.serve` stopped (or re-point it at a pulled
   copy) — the mini is the source of truth.

Litestream starts only after the bind (not before the first sign-in, as first sketched): the
bind renames files, and a replica started on `owner.db` would be orphaned under the old name.

### Rollback

- **Before anyone wrote on the mini:** stop the mini (`mmctl stop`), restart the laptop app
  (`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.magic-manager.serve.plist`, same
  for `.deploy`). The laptop DB was never changed; the pre-cutover snapshot is there too
  (`uv run mm db restore <snapshot>` only if something else changed it).
- **After writes on the mini:** those writes live only in the split files / R2. Pull a copy
  (`mm db pull`) to keep them, or restore the mini itself from R2 (below). Going back to the
  single file means re-entering them — there is no automatic split → single merge.

## 3. Running it

- **Auto-deploy** (`deploy` agent, every 5 min) rolls out `origin/main` — unless the new code's
  schema is newer than the catalog **or any user file** (`mm host deploy-check` → exit 3):
  then it **holds**, keeps the running build and notifies once. Upgrade with your OK:
  ```sh
  upgrade.sh             # rehearse: the new code upgrades COPIES of the catalog + your file
  upgrade.sh --apply     # only the rehearsed commit: stop, deploy, pair snapshot (data/bak/split.bak-…), upgrade + verify, start
  ```
  A commit that fails to deploy (build or health check) is rolled back and not retried; the
  next commit is.
  The app's start-up then migrates every other user's file (each snapshotted first, #199).
  When a deploy changes `deploy/macos/`, you get a notification to re-run `install.sh --apply`.
- **Restore drill** (monthly, when quiet): `mm-hosted host verify-replica` restores auth.db and
  every user file from R2 into a scratch dir and compares each table with live (exit 0 = equal).
- **Disaster recovery / a new server / the vendor move:** on the new machine, install as in §1,
  then `mm-hosted host restore --data-dir ~/magic-manager/data` (refuses a non-empty dir):
  auth.db, every account's file (deleted accounts stay deleted), the newest catalog snapshot,
  verified, WAL, 0600. Then `mmctl start`. Litestream picks up where the replica left off
  (rehearsed: a write after the restore replicates and `verify-replica` passes). If a restore
  stops half-way, the dir is no longer empty: move it aside and run the restore again.
  `mm host restore` warns about any account that has no offsite copy (it starts empty).
- **Deleted accounts** (H10): their local files and Litestream's local state go immediately;
  Litestream never deletes a replica, so the weekly job (`mm host prune-deleted --apply`)
  removes an id with no account and no file once its newest backup is 30 days old. From the
  CLI, `mm-hosted auth delete-user <id> --yes` needs `--force` while Litestream runs (it keeps
  each file's `-wal` open, which the CLI reads as "maybe in use"); the web's *Delete my
  account* is unaffected.
- **Logs**: `~/Library/Logs/magic-manager-hosted/*.log`. They grow slowly; trim by hand or add
  a `newsyslog` rule (`/etc/newsyslog.d/magic-manager.conf`, admin).
- **Replication has no alert yet**: if R2 is unreachable or the token is wrong, Litestream
  retries and logs to `litestream.log`, but nothing notifies you. The monthly restore drill
  (above) is the check until an alert exists.

## 4. The laptop's local copy (H3)

Put the **read-only** token in the laptop's `.env` (never the server's token):
```sh
MM_OFFSITE_URL=s3://magic-manager-backups/prod?endpoint=https://<account-id>.r2.cloudflarestorage.com
MM_OFFSITE_ACCESS_KEY_ID=<mm-laptop-pull key id>
MM_OFFSITE_SECRET_ACCESS_KEY=<mm-laptop-pull secret>
```
Install Litestream v0.5.17 on the laptop too (the same tarball the installer pins; `MM_LITESTREAM`
points at it if it isn't on `PATH`). Then:
```sh
uv run mm db pull --from r2 --user <id> --to ~/mm-copy            # first time (+ the newest weekly catalog)
uv run mm db pull --from r2 --user <id> --to ~/mm-copy --force    # refresh; the old copy → ~/mm-copy/replaced/
uv run mm db pull … --catalog keep                                # refresh only your file, keep the local catalog
MM_LAYOUT=split MM_DATA_DIR=~/mm-copy MM_USER=<id> uv run mm …    # use it
```
It restores into a staging dir, verifies (integrity, ledger reconciles, catalog-refs 0, FK), and
only then swaps in; it refuses to overwrite without `--force` and refuses any hosted data dir.
If your file uses printings newer than the weekly catalog snapshot, the pull still succeeds and
warns (those cards show without names until you `mm set sync` their set or pull after the next
snapshot).
**Changes made to the copy are not sent back** — `LOCAL-COPY.txt` in the dir says so.

## 5. Rules this setup relies on

- **WAL everywhere in the hosted data dir.** Litestream needs it; `mm host wal --apply` sets it
  once (it is stored in the file), `db.connect` never changes the journal mode, new user files
  are created WAL when the catalog is (`userfiles.create`), migration snapshots of a WAL file
  use the backup API (`db.snapshot`), and a restored file stays WAL. Litestream adds two
  bookkeeping tables (`_litestream_seq`, `_litestream_lock`; `layout.LITESTREAM_TABLES`) to
  each replicated file — the export leaves them out.
- **Cross-file writes stay safe under WAL** because catalog writes are committed before the user
  write that depends on them (`db.catalog_first`, #199, §25.3): a crash can leave a cached card,
  never a user row pointing at a missing card.
- **Exposure:** the app listens on 127.0.0.1 only; Tailscale Serve (tailnet-only) is the only way
  in until Cloudflare Tunnel (step 11). Nothing opens a port; the installer adds no network
  listener and never touches other agents (the laptop's `com.magic-manager.*` agents are untouched).
- **Linux/systemd** (`deploy/linux/`) is not built yet: the macOS kit is the beta's; the Docker
  image (CI) carries the same pinned Litestream for the vendor move (`mm host restore`, then
  `mm host replicate --exec "mm serve --host 0.0.0.0 --port 8765"`).
