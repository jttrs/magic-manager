#!/usr/bin/env bash
# EDHREC JSON wrapper.
# EDHREC has no official API; its Next.js front-end fetches name-keyed JSON from
# json.edhrec.com/pages/… (the /pages/ prefix is mandatory — without it the host
# 403s; there is no api.edhrec.com). This wrapper is the sanctioned access path:
# it paces requests (200ms; EDHREC publishes no rate limit, so be conservative),
# caches responses for 24h, and backs off on HTTP 429.
#
# Usage:
#   edhrec.sh commander  <slug>            # GET /pages/commanders/<slug>.json
#   edhrec.sh card       <slug>            # GET /pages/cards/<slug>.json
#   edhrec.sh commanders <segment>         # GET /pages/commanders/<segment>.json (week|month|year)
#   edhrec.sh top        <segment>         # GET /pages/top/<segment>.json        (week|month|salt|…)
#   edhrec.sh raw        <path>            # GET /pages/<path>[.json] (escape hatch, still host-locked)
#
# All output is the raw JSON body from EDHREC.
# Exits non-zero with a message on rate-limit or HTTP errors.

set -euo pipefail

UA='ClaudeCode-magic-manager-EdhrecSkill/1.0 (personal collection manager; respects rate-limits)'
CACHE_DIR="${EDHREC_CACHE_DIR:-${TMPDIR:-/tmp}/edhrec-cache}"
STATE_DIR="${EDHREC_STATE_DIR:-${TMPDIR:-/tmp}/edhrec-state}"
CACHE_TTL_SECONDS=${EDHREC_CACHE_TTL:-86400}      # 24h — EDHREC aggregates change slowly
GAP_MS=200                                        # conservative spacing (no published limit)
BACKOFF_FILE="$STATE_DIR/backoff_until"
LAST_CALL_FILE="$STATE_DIR/last_call_ms"
LOCK_FILE="$STATE_DIR/lock"

mkdir -p "$CACHE_DIR" "$STATE_DIR"

RL_NAME=edhrec.sh
# shellcheck source=../_lib/ratelimit.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_lib/ratelimit.sh"

sha() { python3 -c 'import sys,hashlib; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest())'; }

# $1 = path under the host (e.g. /pages/commanders/atraxa-praetors-voice.json)
call_api() {
  local path="$1"
  local url="https://json.edhrec.com${path}"

  local cache_key cache_file
  cache_key=$(printf 'GET\n%s' "$url" | sha)
  cache_file="$CACHE_DIR/$cache_key.json"

  if [ -f "$cache_file" ]; then
    local age
    age=$(( $(date +%s) - $(stat -f %m "$cache_file" 2>/dev/null || stat -c %Y "$cache_file") ))
    if [ "$age" -lt "$CACHE_TTL_SECONDS" ]; then
      cat "$cache_file"
      return 0
    fi
  fi

  rl_acquire_lock
  rl_check_backoff
  rl_pace $GAP_MS

  local tmp_body
  tmp_body=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_body'; rmdir '$LOCK_FILE' 2>/dev/null || true" EXIT

  # Transient server errors get a few retries with backoff.
  local http_code attempt=0
  while : ; do
    http_code=$(curl -sS \
      -H "User-Agent: $UA" \
      -H 'Accept: application/json;q=0.9,*/*;q=0.8' \
      -o "$tmp_body" \
      -w '%{http_code}' \
      "$url") || {
        echo "edhrec.sh: curl failed for $url" >&2
        exit 4
      }
    case "$http_code" in
      500|502|503|504)
        attempt=$((attempt+1))
        if [ "$attempt" -ge 3 ]; then break; fi
        echo "edhrec.sh: HTTP $http_code (transient), retry $attempt/2 after ${attempt}s…" >&2
        python3 -c "import time; time.sleep($attempt)"
        ;;
      *) break ;;
    esac
  done

  if [ "$http_code" = "429" ]; then
    rl_set_backoff 35
    echo "edhrec.sh: HTTP 429 from EDHREC. Backing off for 35s. Do NOT retry." >&2
    exit 5
  fi

  if [ "$http_code" -ge 400 ]; then
    cat "$tmp_body" >&2
    echo "edhrec.sh: HTTP $http_code from $url" >&2
    exit 6
  fi

  cp "$tmp_body" "$cache_file"
  cat "$tmp_body"
}

# Sanitize a caller-supplied slug/segment: keep it to a single path component
# (no slashes, no traversal) so the URL is always host-locked to /pages/….
safe_component() {
  printf '%s' "$1" | tr -d '/' | tr -d '\n'
}

cmd="${1:-}"; shift || true
case "$cmd" in
  commander)
    slug="$(safe_component "${1:-}")"
    [ -z "$slug" ] && { echo "usage: edhrec.sh commander '<slug>'" >&2; exit 1; }
    call_api "/pages/commanders/${slug}.json"
    ;;
  card)
    slug="$(safe_component "${1:-}")"
    [ -z "$slug" ] && { echo "usage: edhrec.sh card '<slug>'" >&2; exit 1; }
    call_api "/pages/cards/${slug}.json"
    ;;
  commanders)
    seg="$(safe_component "${1:-week}")"
    call_api "/pages/commanders/${seg}.json"
    ;;
  top)
    seg="$(safe_component "${1:-week}")"
    call_api "/pages/top/${seg}.json"
    ;;
  raw)
    path="${1:-}"
    [ -z "$path" ] && { echo "usage: edhrec.sh raw '<path-under-pages>'" >&2; exit 1; }
    # Reject traversal; ensure a single clean path under /pages/.
    case "$path" in
      *..*) echo "edhrec.sh: '..' not allowed in raw path" >&2; exit 1 ;;
    esac
    path="${path#/}"           # strip leading slash if present
    path="${path#pages/}"      # strip a redundant pages/ prefix if the caller added one
    case "$path" in
      *.json) : ;;
      *) path="${path}.json" ;;
    esac
    call_api "/pages/${path}"
    ;;
  *)
    cat >&2 <<EOF
edhrec.sh: unknown subcommand '$cmd'
Subcommands:
  commander   '<slug>'            /pages/commanders/<slug>.json
  card        '<slug>'            /pages/cards/<slug>.json
  commanders  '<segment>'         /pages/commanders/<segment>.json  (week|month|year)
  top         '<segment>'         /pages/top/<segment>.json         (week|month|salt|…)
  raw         '<path-under-pages>'
EOF
    exit 1
    ;;
esac
