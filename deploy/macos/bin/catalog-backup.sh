#!/bin/bash
# launchd: com.magic-manager.hosted.catalog-backup (weekly). Uploads a VACUUM INTO copy of
# catalog.db (keep 2), then ages out the replicas of deleted accounts (30-day retention).
# shellcheck source=deploy/macos/bin/common.sh
. "$(dirname "$0")/common.sh"
log "catalog backup"
if ! mmh host catalog-backup; then
  notify "Weekly catalog backup failed — see ~/Library/Logs/magic-manager-hosted/catalog-backup.log"
  exit 1
fi
mmh host prune-deleted --apply || notify "Pruning deleted accounts' backups failed"
