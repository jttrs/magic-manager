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

# Supply chain (§25.4 step 10): only commits GitHub itself made land on the server. A PR's
# squash-merge (web UI or API) is signed by GitHub's web-flow key, and main's branch
# protection requires the PR checks first — a direct push, a force-push or a locally
# made commit isn't. install.sh --apply puts the key in "$MM_KIT/gnupg" and checks it
# against this pinned fingerprint (docs/home-server.md § Deploy verification).
MM_WEBFLOW_FPR=968479A1AFF927E37D1A566BB5690EEEBB952194

# verify_main <cur> <new>: every first-parent commit in cur..new is a single-parent commit
# signed by web-flow, and new descends from cur (no force-push). Prints why not; exit 1.
verify_main() {
  local cur="$1" new="$2" c n
  [ -d "$MM_KIT/gnupg" ] || { echo "no web-flow keyring at $MM_KIT/gnupg — re-run install.sh --apply"; return 1; }
  git merge-base --is-ancestor "$cur" "$new" || { echo "${new:0:7} doesn't descend from ${cur:0:7} (main was rewritten)"; return 1; }
  for c in $(git rev-list --first-parent "$cur..$new"); do
    n=$(git rev-list --parents -n 1 "$c" | wc -w)
    [ "$n" -eq 2 ] || { echo "${c:0:7} isn't a squash-merge (it has $((n - 1)) parents)"; return 1; }
    GNUPGHOME="$MM_KIT/gnupg" git verify-commit --raw "$c" 2>&1 \
      | grep -q "^\[GNUPG:\] VALIDSIG $MM_WEBFLOW_FPR " \
      || { echo "${c:0:7} isn't signed by GitHub (web-flow) — not merged through a pull request"; return 1; }
  done
}

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
