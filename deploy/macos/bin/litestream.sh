#!/bin/bash
# launchd: com.magic-manager.hosted.litestream (KeepAlive). Continuous offsite replication of
# auth.db + every users/<id>.db (magic_manager.offsite). Credentials come from the checkout's
# .env inside the process; they never appear in the config, argv or this log.
# shellcheck source=deploy/macos/bin/common.sh
. "$(dirname "$0")/common.sh"
if [ ! -f "$MM_DATA_DIR/auth.db" ]; then
  log "no auth.db in $MM_DATA_DIR yet — Litestream starts after the cutover's first sign-in"
  exit 1
fi
if [ -e "$MM_DATA_DIR/users/owner.db" ]; then
  log "the cutover isn't finished (users/owner.db not bound yet) — cutover.sh finish starts Litestream"
  exit 1
fi
cd "$MM_APP" || exit 1
exec uv run --frozen mm host replicate
