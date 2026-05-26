#!/usr/bin/env bash
# Scryfall API wrapper.
# Enforces 500ms spacing for /cards/* endpoints, 100ms otherwise,
# caches responses for 24h, and backs off on HTTP 429.
#
# Usage:
#   scryfall.sh search 't:dragon c:r f:modern' [order=edhrec] [unique=cards]
#   scryfall.sh raw    '/cards/search' 'q=t:dragon&order=edhrec'
#   scryfall.sh named  'Lightning Bolt'
#
# All output is the raw JSON body from Scryfall.
# Exits non-zero with a message on rate-limit or HTTP errors.

set -euo pipefail

UA='ClaudeCode-magic-manager-ScryfallSkill/1.0 (https://scryfall.com/docs/api; respects rate-limits)'
CACHE_DIR="${SCRYFALL_CACHE_DIR:-${TMPDIR:-/tmp}/scryfall-cache}"
STATE_DIR="${SCRYFALL_STATE_DIR:-${TMPDIR:-/tmp}/scryfall-state}"
CACHE_TTL_SECONDS=${SCRYFALL_CACHE_TTL:-86400}      # 24h per Scryfall guidance
SLOW_GAP_MS=500   # /cards/search, /cards/named, /cards/random, /cards/collection
FAST_GAP_MS=100   # all other endpoints
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
      echo "scryfall.sh: lock timeout" >&2
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
      echo "scryfall.sh: in backoff window after a 429, ${remaining}s remaining. Aborting." >&2
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
  # $1 = method (GET|POST)
  # $2 = path (e.g. /cards/search)
  # $3 = query string already URL-encoded (may be empty)
  # $4 = JSON body for POST (may be empty)
  local method="$1" path="$2" qs="${3:-}" body="${4:-}"
  local url="https://api.scryfall.com${path}"
  [ -n "$qs" ] && url="${url}?${qs}"

  local cache_key cache_file
  cache_key=$(printf '%s\n%s\n%s' "$method" "$url" "$body" | sha)
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

  case "$path" in
    /cards/search|/cards/named|/cards/random|/cards/collection) pace $SLOW_GAP_MS ;;
    *) pace $FAST_GAP_MS ;;
  esac

  local tmp_body
  tmp_body=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_body'; rmdir '$LOCK_FILE' 2>/dev/null || true" EXIT

  local http_code
  if [ "$method" = "POST" ]; then
    http_code=$(curl -sS -X POST \
      -H "User-Agent: $UA" \
      -H 'Accept: application/json;q=0.9,*/*;q=0.8' \
      -H 'Content-Type: application/json' \
      --data-binary "$body" \
      -o "$tmp_body" \
      -w '%{http_code}' \
      "$url") || {
        echo "scryfall.sh: curl POST failed for $url" >&2
        exit 4
      }
  else
    http_code=$(curl -sS \
      -H "User-Agent: $UA" \
      -H 'Accept: application/json;q=0.9,*/*;q=0.8' \
      -o "$tmp_body" \
      -w '%{http_code}' \
      "$url") || {
        echo "scryfall.sh: curl failed for $url" >&2
        exit 4
      }
  fi

  if [ "$http_code" = "429" ]; then
    # Per Scryfall: 30s lockout. Persist a backoff window of 35s to be safe.
    local until_ms=$(( $(now_ms) + 35000 ))
    echo "$until_ms" > "$BACKOFF_FILE"
    echo "scryfall.sh: HTTP 429 from Scryfall. Backing off for 35s. Do NOT retry." >&2
    cat "$tmp_body" >&2
    exit 5
  fi

  if [ "$http_code" -ge 400 ]; then
    # Surface error JSON to caller but still exit non-zero so caller notices.
    cat "$tmp_body"
    echo "scryfall.sh: HTTP $http_code from $url" >&2
    exit 6
  fi

  cp "$tmp_body" "$cache_file"
  cat "$tmp_body"
}

urlencode() { python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"; }

cmd="${1:-}"; shift || true
case "$cmd" in
  search)
    q="${1:-}"; shift || true
    [ -z "$q" ] && { echo "usage: scryfall.sh search '<query>' [extra=val ...]" >&2; exit 1; }
    parts="q=$(urlencode "$q")"
    for kv in "$@"; do
      k="${kv%%=*}"; v="${kv#*=}"
      parts="${parts}&$(urlencode "$k")=$(urlencode "$v")"
    done
    call_api GET /cards/search "$parts" ""
    ;;
  named)
    name="${1:-}"; shift || true
    [ -z "$name" ] && { echo "usage: scryfall.sh named '<exact name>'" >&2; exit 1; }
    call_api GET /cards/named "exact=$(urlencode "$name")" ""
    ;;
  collection)
    # Reads a JSON body from stdin or a file. Body must match Scryfall's
    # /cards/collection schema: {"identifiers":[ ... up to 75 ... ]}
    # Each identifier is one of:
    #   {"name": "Lightning Bolt"}
    #   {"name": "Lightning Bolt", "set": "leb"}
    #   {"set": "leb", "collector_number": "162"}
    #   {"id": "<scryfall-uuid>"}
    src="${1:-}"
    if [ -n "$src" ] && [ -f "$src" ]; then
      body=$(cat "$src")
    else
      body=$(cat)
    fi
    [ -z "$body" ] && { echo "usage: scryfall.sh collection [path-to-body.json]  (or pipe JSON on stdin)" >&2; exit 1; }
    call_api POST /cards/collection "" "$body"
    ;;
  raw)
    path="${1:-}"; qs="${2:-}"
    [ -z "$path" ] && { echo "usage: scryfall.sh raw '/path' 'qs=already&encoded'" >&2; exit 1; }
    call_api GET "$path" "$qs" ""
    ;;
  *)
    cat >&2 <<EOF
scryfall.sh: unknown subcommand '$cmd'
Subcommands:
  search     '<scryfall syntax>' [order=edhrec] [unique=cards] [dir=asc] [page=N]
  named      '<exact card name>'
  collection [path-to-body.json]   (or pipe JSON body on stdin; up to 75 identifiers per call)
  raw        '/api/path' 'already=encoded&query=string'
EOF
    exit 1
    ;;
esac
