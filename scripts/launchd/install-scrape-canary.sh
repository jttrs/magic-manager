#!/bin/bash
# Install (or update) the daily scrape canary next to the deploy/serve agents:
#   scripts/launchd/install-scrape-canary.sh            # install + load
#   scripts/launchd/install-scrape-canary.sh --run-now  # … and run once now
#   scripts/launchd/install-scrape-canary.sh --uninstall
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
APP="$HOME/Library/Application Support/magic-manager-live"
AGENT="$HOME/Library/LaunchAgents/com.magic-manager.scrape-canary.plist"
LABEL="gui/$(id -u)/com.magic-manager.scrape-canary"
launchctl bootout "$LABEL" 2>/dev/null || true
if [ "${1:-}" = "--uninstall" ]; then rm -f "$AGENT" "$APP/scrape-canary.sh"; echo "removed"; exit 0; fi
mkdir -p "$APP" "$HOME/Library/Logs/magic-manager"
install -m 755 "$HERE/scrape-canary.sh" "$APP/scrape-canary.sh"
install -m 644 "$HERE/com.magic-manager.scrape-canary.plist" "$AGENT"
launchctl bootstrap "gui/$(id -u)" "$AGENT"
echo "installed: daily 06:30 → $HOME/Library/Logs/magic-manager/scrape-canary.log"
if [ "${1:-}" = "--run-now" ]; then launchctl kickstart "$LABEL"; echo "running now"; fi
