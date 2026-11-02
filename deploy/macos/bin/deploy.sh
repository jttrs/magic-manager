#!/bin/bash
# launchd: com.magic-manager.hosted.deploy (every 5 min). Auto-deploys origin/main to the
# hosted app — but NEVER upgrades a database: when the new code's schema is newer than the
# catalog OR any user file (`mm host deploy-check`, exit 3), it holds, keeps the running
# build and notifies once. The owner upgrades explicitly with upgrade.sh (snapshot first).
# It also holds any commit GitHub didn't make (verify_main: squash-merges of PRs only), and
# installs web dependencies with --ignore-scripts (no package install hooks run here).
# shellcheck source=deploy/macos/bin/common.sh
. "$(dirname "$0")/common.sh"
take_lock || exit 0
cd "$MM_APP" || { log "no app checkout at $MM_APP"; exit 1; }
git fetch -q origin main || { log "fetch failed"; exit 0; }
cur=$(git rev-parse HEAD); new=$(git rev-parse origin/main)
[ "$cur" = "$new" ] && exit 0
[ -e "$MM_KIT/failed-$new" ] && exit 0   # tried once and rolled back; wait for the next commit

if ! why=$(verify_main "$cur" "$new"); then
  flag="$MM_KIT/hold-$new"
  if [ ! -e "$flag" ]; then
    log "HOLD ${new:0:7}: not deployed — $why"
    notify "Update held: ${new:0:7} wasn't merged through a pull request — see deploy.log"
    touch "$flag"
  fi
  exit 0
fi

# The CURRENT code decides (it reads the new db.py as text; nothing new runs yet).
msg=$(uv run --frozen mm host deploy-check --ref "$new" --repo "$MM_APP" 2>&1); rc=$?
if [ "$rc" -ne 0 ]; then
  flag="$MM_KIT/hold-$new"
  if [ ! -e "$flag" ]; then
    if [ "$rc" -eq 3 ]; then
      log "HOLD ${new:0:7}: $msg"
      log "  upgrade with your OK: $MM_KIT/upgrade.sh (rehearse), then $MM_KIT/upgrade.sh --apply"
      notify "Update waiting: database upgrade needs your OK (upgrade.sh)"
    else
      log "HOLD ${new:0:7}: the deploy check itself failed (exit $rc): $msg"
      notify "Update held: the deploy check failed — see deploy.log"
    fi
    touch "$flag"
  fi
  exit 0
fi

log "deploying ${cur:0:7} → ${new:0:7}"
lock_before=$(git show "$cur:web/package-lock.json" 2>/dev/null | shasum)
lock_after=$(git show "$new:web/package-lock.json" 2>/dev/null | shasum)
restarted=no
rollback() {
  log "FAILED ($1) — rolling back to ${cur:0:7}; ${new:0:7} won't be retried (a newer commit will)"
  touch "$MM_KIT/failed-$new"
  git checkout -q --detach "$cur"
  uv sync -q --frozen
  npm --prefix web ci --ignore-scripts --silent >/dev/null 2>&1
  npm --prefix web run build >/dev/null 2>&1
  [ "$restarted" = yes ] && "$MM_KIT/mmctl" restart serve litestream >/dev/null
  notify "Deploy of ${new:0:7} failed ($1); kept ${cur:0:7}"
  exit 1
}
git checkout -q --detach "$new" || rollback checkout
uv sync -q --frozen || rollback "uv sync"
if [ "$lock_before" != "$lock_after" ] || [ ! -d web/node_modules ]; then
  npm --prefix web ci --ignore-scripts --silent >/dev/null 2>&1 || rollback "npm ci"
fi
npm --prefix web run build >/dev/null 2>&1 || rollback "web build"
restarted=yes
"$MM_KIT/mmctl" restart serve litestream >/dev/null
for _ in $(seq 1 30); do
  sleep 2
  if curl -sf -o /dev/null "http://127.0.0.1:$MM_PORT/api/features"; then
    log "deployed ${new:0:7} ($(git log -1 --format=%s))"
    notify "Updated to: $(git log -1 --format=%s | cut -c1-80)"
    if ! git diff --quiet "$cur" "$new" -- deploy/macos; then
      log "the deploy kit changed — re-run: $MM_APP/deploy/macos/install.sh --apply"
      notify "The deploy kit changed — re-run deploy/macos/install.sh --apply"
    fi
    exit 0
  fi
done
rollback "health check"
