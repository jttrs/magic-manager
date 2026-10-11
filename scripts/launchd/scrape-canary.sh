#!/bin/bash
# Daily scrape canary for the local app (launchd: com.magic-manager.scrape-canary, 06:30;
# a run missed while asleep happens on wake). Reads a known public sample for every
# scraper, per site, records the outcome where the app reads it ("temporarily down"
# notices) and posts a macOS notification when a scraper goes down or recovers.
# Zero agent involvement. Design: docs/scraper-health.md. Installed by
# scripts/launchd/install-scrape-canary.sh — never edit the installed copy by hand.
set -u
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
REPO=/Users/torre/repos/personal/magic-manager
LIVE=$REPO/.worktrees/live
export MAGIC_MANAGER_DB=$REPO/db/magic_manager.db   # the status file lands beside it
LOCK=/tmp/magic-manager-scrape-canary.lock
DEPLOY_LOCK=/tmp/magic-manager-deploy.lock
log() { echo "$(date '+%F %T') $*"; }
mkdir "$LOCK" 2>/dev/null || { log "already running"; exit 0; }
trap 'rmdir "$LOCK"' EXIT
# Don't read the code while the deploy job is checking out a new build.
for _ in $(seq 1 10); do [ -d "$DEPLOY_LOCK" ] || break; sleep 30; done
cd "$LIVE" || { log "no live worktree"; exit 1; }
log "scrape canary start ($(git rev-parse --short HEAD))"
uv run --frozen python scripts/check_scrapers.py --live --no-pins --record --notify
rc=$?
log "scrape canary done (exit $rc: 0 = every scraper reads, 1 = something is down)"
exit 0
