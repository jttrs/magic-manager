#!/usr/bin/env bash
# TCG API (tcgapi.dev) wrapper — independent TCGplayer price data, X-API-Key auth.
#
# A secondary/cross-check market source to tcgcsv.com. Free tier 100 req/day.
# Reads TCGAPI_KEY from the repo .env. tcgapi.dev is SEARCH-KEYED (by name), not
# productId-keyed — it has no lookup-by-TCGplayer-productId endpoint. Sealed
# products (booster boxes, ETBs, cases) are covered.
#
# Usage:
#   tcgapi.sh search '<product name>' [game=magic]   # search; returns market_price etc.
#   tcgapi.sh raw '/v1/search?q=...&game=magic'
#
# Base URL https://api.tcgapi.dev/v1; header X-API-Key. Caches 24h; paces
# requests. Raw JSON on stdout. Response fields include name/set_name/
# product_type/market_price/low_price/median_price/total_listings.

set -euo pipefail

BASE="${TCGAPI_BASE:-https://api.tcgapi.dev}"
UA='ClaudeCode-magic-manager-SealedValue/1.0'
CACHE_DIR="${TCGAPI_CACHE_DIR:-${TMPDIR:-/tmp}/tcgapi-cache}"
STATE_DIR="${TCGAPI_STATE_DIR:-${TMPDIR:-/tmp}/tcgapi-state}"
CACHE_TTL_SECONDS=${TCGAPI_CACHE_TTL:-86400}
GAP_MS=400
LAST_CALL_FILE="$STATE_DIR/last_call_ms"
LOCK_FILE="$STATE_DIR/lock"

mkdir -p "$CACHE_DIR" "$STATE_DIR"

# Load TCGAPI_KEY from repo .env if not already exported.
if [ -z "${TCGAPI_KEY:-}" ]; then
  ENV_FILE="$(cd "$(dirname "$0")/../../.." && pwd)/.env"
  if [ -f "$ENV_FILE" ]; then
    TCGAPI_KEY=$( (grep -E '^TCGAPI_KEY=' "$ENV_FILE" 2>/dev/null || true) | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
  fi
fi
if [ -z "${TCGAPI_KEY:-}" ]; then
  echo "tcgapi.sh: TCGAPI_KEY not set (add it to .env). Skipping." >&2
  exit 7
fi

now_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }
sha() { python3 -c 'import sys,hashlib; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest())'; }
urlencode() { python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"; }

acquire_lock() {
  local waited=0
  while ! mkdir "$LOCK_FILE" 2>/dev/null; do
    sleep 0.05; waited=$((waited+50))
    [ $waited -gt 30000 ] && { echo "tcgapi.sh: lock timeout" >&2; exit 2; }
  done
  trap 'rmdir "$LOCK_FILE" 2>/dev/null || true' EXIT
}

pace() {
  local need_ms=$1 last_ms cur_ms gap sleep_ms
  cur_ms=$(now_ms)
  if [ -f "$LAST_CALL_FILE" ]; then
    last_ms=$(cat "$LAST_CALL_FILE" 2>/dev/null || echo 0)
    gap=$(( cur_ms - last_ms ))
    if [ "$gap" -lt "$need_ms" ]; then
      python3 -c "import time; time.sleep($(( need_ms - gap ))/1000.0)"
    fi
  fi
  now_ms > "$LAST_CALL_FILE"
}

call_api() {
  local path="$1"
  local url="${BASE}${path}"
  local cache_key cache_file
  cache_key=$(printf '%s' "$url" | sha)
  cache_file="$CACHE_DIR/$cache_key.json"
  if [ -f "$cache_file" ]; then
    local age
    age=$(( $(date +%s) - $(stat -f %m "$cache_file" 2>/dev/null || stat -c %Y "$cache_file") ))
    [ "$age" -lt "$CACHE_TTL_SECONDS" ] && { cat "$cache_file"; return 0; }
  fi
  acquire_lock; pace $GAP_MS
  local tmp_body http_code
  tmp_body=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_body'; rmdir '$LOCK_FILE' 2>/dev/null || true" EXIT
  http_code=$(curl -sS -H "User-Agent: $UA" -H "X-API-Key: $TCGAPI_KEY" \
    -H 'Accept: application/json' -o "$tmp_body" -w '%{http_code}' "$url") \
    || { echo "tcgapi.sh: curl failed for $url" >&2; exit 4; }
  if [ "$http_code" -ge 400 ]; then
    cat "$tmp_body"; echo "tcgapi.sh: HTTP $http_code from $url" >&2; exit 6
  fi
  cp "$tmp_body" "$cache_file"; cat "$tmp_body"
}

cmd="${1:-}"; shift || true
case "$cmd" in
  search)  [ -z "${1:-}" ] && { echo "usage: tcgapi.sh search '<product name>' [game=magic]" >&2; exit 1; }
           game="${2:-magic}"
           call_api "/v1/search?q=$(urlencode "$1")&game=$(urlencode "$game")" ;;
  raw)     [ -z "${1:-}" ] && { echo "usage: tcgapi.sh raw '/v1/...'" >&2; exit 1; }
           call_api "$1" ;;
  *) echo "tcgapi.sh: unknown subcommand '$cmd' (search|raw)" >&2; exit 1 ;;
esac
