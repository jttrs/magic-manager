#!/bin/bash
# launchd: com.magic-manager.hosted.replica-check (every 15 min). Asks `mm host replica-lag`
# whether the offsite replica keeps up with the local writes; notifies once when it stops
# (behind / never replicated / store unreachable) and once when it recovers.
# shellcheck source=deploy/macos/bin/common.sh
. "$(dirname "$0")/common.sh"
# Nothing replicates before the cutover finishes (same guards as litestream.sh): don't check.
if [ ! -f "$MM_DATA_DIR/auth.db" ] || [ -e "$MM_DATA_DIR/users/owner.db" ]; then
  log "the cutover isn't finished — not checking replication yet"
  exit 0
fi
state_file="$MM_KIT/replica-check.state"
prev=ok
[ -r "$state_file" ] && prev=$(cat "$state_file")
logfile="Library/Logs/magic-manager-hosted/replica-check.log"
mmh host replica-lag
rc=$?
case "$rc" in
  0)
    log "replication ok"
    [ "$prev" != bad ] || notify "Offsite backups caught up"
    echo ok > "$state_file" ;;
  1)
    log "replication behind"
    [ "$prev" = bad ] || notify "Offsite backups are behind — see ~/$logfile"
    echo bad > "$state_file" ;;
  *)
    log "couldn't check replication (exit $rc)"
    [ "$prev" = bad ] || notify "Couldn't check the offsite backups — see ~/$logfile"
    echo bad > "$state_file" ;;
esac
exit "$rc"
