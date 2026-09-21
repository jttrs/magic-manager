#!/usr/bin/env bash
# Commander Spellbook API wrapper.
# Enforces ~750ms spacing between requests (~80 req/min), caches responses for
# 24h, and backs off on HTTP 429.
#
# Usage:
#   spellbook.sh find-my-combos    [path-to-body.json]   (or pipe JSON body on stdin)
#   spellbook.sh estimate-bracket  [path-to-body.json]   (or pipe JSON body on stdin)
#
# All output is the raw JSON body from Commander Spellbook.
# Exits non-zero with a message on rate-limit or HTTP errors.

set -euo pipefail

UA='ClaudeCode-magic-manager-SpellbookSkill/1.0'
CACHE_DIR="${SPELLBOOK_CACHE_DIR:-${TMPDIR:-/tmp}/spellbook-cache}"
STATE_DIR="${SPELLBOOK_STATE_DIR:-${TMPDIR:-/tmp}/spellbook-state}"
CACHE_TTL_SECONDS=${SPELLBOOK_CACHE_TTL:-86400}      # 24h
GAP_MS=750   # ~80 req/min
BACKOFF_FILE="$STATE_DIR/backoff_until"
LAST_CALL_FILE="$STATE_DIR/last_call_ms"
LOCK_FILE="$STATE_DIR/lock"

mkdir -p "$CACHE_DIR" "$STATE_DIR"

now_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }
sha() { python3 -c 'import sys,hashlib; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest())'; }

# Acquire a coarse lock so concurrent invocations serialize their pacing logic.
# macOS lacks flock(1), so we use a mkdir-based mutex.
acquire_lock() {
  local waited=0
  while ! mkdir "$LOCK_FILE" 2>/dev/null; do
    sleep 0.05
    waited=$((waited+50))
    if [ $waited -gt 30000 ]; then
      echo "spellbook.sh: lock timeout" >&2
      exit 2
    fi
  done
  trap 'rmdir "$LOCK_FILE" 2>/dev/null || true' EXIT
}

check_backoff() {
  if [ -f "$BACKOFF_FILE" ]; then
    local until_ms cur_ms
    until_ms=$(cat "$BACKOFF_FILE" 2>/dev/null || echo 0)
    cur_ms=$(now_ms)
    if [ "$cur_ms" -lt "$until_ms" ]; then
      local remaining=$(( (until_ms - cur_ms) / 1000 + 1 ))
      echo "spellbook.sh: in backoff window after a 429, ${remaining}s remaining. Aborting." >&2
      exit 3
    fi
    rm -f "$BACKOFF_FILE"
  fi
}

pace() {
  # $1 = required gap in ms
  local need_ms=$1 last_ms cur_ms gap sleep_ms
  cur_ms=$(now_ms)
  if [ -f "$LAST_CALL_FILE" ]; then
    last_ms=$(cat "$LAST_CALL_FILE" 2>/dev/null || echo 0)
    gap=$(( cur_ms - last_ms ))
    if [ "$gap" -lt "$need_ms" ]; then
      sleep_ms=$(( need_ms - gap ))
      python3 -c "import time; time.sleep($sleep_ms/1000.0)"
    fi
  fi
  now_ms > "$LAST_CALL_FILE"
}

call_api() {
  # $1 = path (e.g. /find-my-combos)
  # $2 = JSON body for POST
  local path="$1" body="${2:-}"
  local url="https://backend.commanderspellbook.com${path}"

  local cache_key cache_file
  cache_key=$(printf '%s\n%s\n%s' "POST" "$url" "$body" | sha)
  cache_file="$CACHE_DIR/$cache_key.json"

  if [ -f "$cache_file" ]; then
    local age
    age=$(( $(date +%s) - $(stat -f %m "$cache_file" 2>/dev/null || stat -c %Y "$cache_file") ))
    if [ "$age" -lt "$CACHE_TTL_SECONDS" ]; then
      cat "$cache_file"
      return 0
    fi
  fi

  acquire_lock
  check_backoff
  pace $GAP_MS

  local tmp_body
  tmp_body=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_body'; rmdir '$LOCK_FILE' 2>/dev/null || true" EXIT

  # Transient server errors (500/502/503/504) get a few retries with backoff —
  # a bare abort would kill a whole batch on an occasional 503.
  local http_code attempt=0
  while : ; do
    http_code=$(curl -sS -X POST \
      -H "User-Agent: $UA" \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      --data-binary "$body" \
      -o "$tmp_body" \
      -w '%{http_code}' \
      "$url") || {
        echo "spellbook.sh: curl POST failed for $url" >&2
        exit 4
      }
    case "$http_code" in
      500|502|503|504)
        attempt=$((attempt+1))
        if [ "$attempt" -ge 3 ]; then break; fi
        echo "spellbook.sh: HTTP $http_code (transient), retry $attempt/2 after ${attempt}s…" >&2
        python3 -c "import time; time.sleep($attempt)"
        ;;
      *) break ;;
    esac
  done

  if [ "$http_code" = "429" ]; then
    # Persist a backoff window of 35s to be safe.
    local until_ms=$(( $(now_ms) + 35000 ))
    echo "$until_ms" > "$BACKOFF_FILE"
    echo "spellbook.sh: HTTP 429 from Commander Spellbook. Backing off for 35s. Do NOT retry." >&2
    cat "$tmp_body" >&2
    exit 5
  fi

  if [ "$http_code" -ge 400 ]; then
    # Surface error JSON to caller but still exit non-zero so caller notices.
    cat "$tmp_body"
    echo "spellbook.sh: HTTP $http_code from $url" >&2
    exit 6
  fi

  cp "$tmp_body" "$cache_file"
  cat "$tmp_body"
}

read_body() {
  # $1 = optional path to a JSON file; else read stdin.
  local src="${1:-}"
  if [ -n "$src" ] && [ -f "$src" ]; then
    cat "$src"
  else
    cat
  fi
}

cmd="${1:-}"; shift || true
case "$cmd" in
  find-my-combos)
    body=$(read_body "${1:-}")
    [ -z "$body" ] && { echo "usage: spellbook.sh find-my-combos [path-to-body.json]  (or pipe JSON on stdin)" >&2; exit 1; }
    call_api /find-my-combos "$body"
    ;;
  estimate-bracket)
    body=$(read_body "${1:-}")
    [ -z "$body" ] && { echo "usage: spellbook.sh estimate-bracket [path-to-body.json]  (or pipe JSON on stdin)" >&2; exit 1; }
    call_api /estimate-bracket "$body"
    ;;
  *)
    cat >&2 <<EOF
spellbook.sh: unknown subcommand '$cmd'
Subcommands:
  find-my-combos    [path-to-body.json]   (or pipe JSON body on stdin)
  estimate-bracket  [path-to-body.json]   (or pipe JSON body on stdin)
EOF
    exit 1
    ;;
esac
