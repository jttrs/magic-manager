#!/bin/bash
# launchd: com.magic-manager.hosted.serve (KeepAlive). The hosted web app on 127.0.0.1 only —
# Tailscale Serve (later Cloudflare Tunnel) is the only way in; no port is opened.
# shellcheck source=deploy/macos/bin/common.sh
. "$(dirname "$0")/common.sh"
if [ ! -f "$MM_DATA_DIR/catalog.db" ]; then
  log "no catalog in $MM_DATA_DIR — finish the cutover first (docs/home-server.md)"
  exit 1
fi
cd "$MM_APP" || exit 1
exec uv run --frozen mm serve --host 127.0.0.1 --port "$MM_PORT"
