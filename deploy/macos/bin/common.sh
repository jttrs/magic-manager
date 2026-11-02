#!/bin/bash
# Shared by the hosted wrapper scripts (sourced, not run). The installer copies this
# directory to the kit dir and writes hosted.env beside it (non-secret settings only;
# secrets stay in the app checkout's .env, read by magic_manager.secrets).
set -u
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -r "$KIT/hosted.env" ]; then
  echo "no $KIT/hosted.env — run deploy/macos/install.sh --apply" >&2
  exit 1
fi
# shellcheck source=/dev/null
. "$KIT/hosted.env"
umask 077

log() { echo "$(date '+%F %T') $*"; }

# A macOS notification; the text is passed as an argument, never spliced into AppleScript.
notify() {
  osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title "magic-manager (hosted)"' \
    -e 'end run' "$1" >/dev/null 2>&1 || true
}

# Run the app's CLI from the checkout with the hosted settings.
mmh() { (cd "$MM_APP" && uv run --frozen mm "$@"); }

# The deploy lock (shared by deploy.sh and upgrade.sh so they never overlap). It holds the
# owner's PID; a lock whose process is gone (a crash, a power cut) is taken over, not obeyed.
take_lock() {
  local lock="$MM_KIT/deploy.lock" pid
  if ! mkdir "$lock" 2>/dev/null; then
    pid=$(cat "$lock/pid" 2>/dev/null || true)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      log "skipped: another deploy/upgrade (pid $pid) is running"
      return 1
    fi
    log "taking over a stale deploy lock (pid ${pid:-unknown} is gone)"
    rm -rf "$lock"
    mkdir "$lock" 2>/dev/null || return 1
  fi
  echo $$ > "$lock/pid"
  trap 'rm -rf "$MM_KIT/deploy.lock"' EXIT
}
