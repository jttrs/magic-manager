#!/usr/bin/env bash
# eBay Browse API wrapper — ADVISORY active-listing comps for sealed product.
#
# eBay prices are NON-DETERMINISTIC (vary per fetch) — this source is advisory
# only and never feeds the deterministic artifact. The Browse API returns ACTIVE
# listings (a "what it's listed at" ceiling), NOT sold comps — real sold prices
# need eBay's Marketplace Insights API, a restricted/limited-release API that
# requires separate approval. Treat the number as a rough ceiling.
#
# AUTH: eBay application tokens (client_credentials grant) expire in ~2h, so a
# static token in .env goes stale fast. This wrapper MINTS a token on demand
# from EBAY_CLIENT_ID + EBAY_CLIENT_SECRET (App ID / Cert ID from
# developer.ebay.com) and caches it under STATE_DIR with its expiry. A
# pre-minted EBAY_OAUTH_TOKEN (env or .env) is honored as an OVERRIDE if present.
# Any of these may live in the repo .env.
#
# Usage:
#   ebay.sh search '<query>'    # active-listing summary for a product query
#   ebay.sh raw '/buy/browse/v1/item_summary/search?q=...'
#
# Short cache (1h) — advisory data is intentionally fresh, not pinned.

set -euo pipefail

BASE="${EBAY_BASE:-https://api.ebay.com}"
MARKETPLACE="${EBAY_MARKETPLACE:-EBAY_US}"
OAUTH_SCOPE="${EBAY_OAUTH_SCOPE:-https://api.ebay.com/oauth/api_scope}"
CACHE_DIR="${EBAY_CACHE_DIR:-${TMPDIR:-/tmp}/ebay-cache}"
STATE_DIR="${EBAY_STATE_DIR:-${TMPDIR:-/tmp}/ebay-state}"
CACHE_TTL_SECONDS=${EBAY_CACHE_TTL:-3600}
GAP_MS=500
LAST_CALL_FILE="$STATE_DIR/last_call_ms"
LOCK_FILE="$STATE_DIR/lock"
TOKEN_FILE="$STATE_DIR/token.json"

mkdir -p "$CACHE_DIR" "$STATE_DIR"

now_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }
now_s() { python3 -c 'import time; print(int(time.time()))'; }
sha() { python3 -c 'import sys,hashlib; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest())'; }
urlencode() { python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"; }

# Read a KEY=value from the repo .env (unquoted), empty if absent.
env_val() {
  local key="$1" env_file
  env_file="$(cd "$(dirname "$0")/../../.." && pwd)/.env"
  [ -f "$env_file" ] || return 0
  (grep -E "^${key}=" "$env_file" 2>/dev/null || true) | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'"
}

# Resolve credentials: env first, then .env.
: "${EBAY_OAUTH_TOKEN:=$(env_val EBAY_OAUTH_TOKEN)}"
: "${EBAY_CLIENT_ID:=$(env_val EBAY_CLIENT_ID)}"
: "${EBAY_CLIENT_SECRET:=$(env_val EBAY_CLIENT_SECRET)}"

# Mint (or reuse a cached) application access token via client_credentials.
# Echoes the bearer token on stdout, or exits 7 if no credentials at all.
get_token() {
  # 1) explicit pre-minted override always wins.
  if [ -n "${EBAY_OAUTH_TOKEN:-}" ]; then
    printf '%s' "$EBAY_OAUTH_TOKEN"
    return 0
  fi
  # 2) need client id + secret to mint.
  if [ -z "${EBAY_CLIENT_ID:-}" ] || [ -z "${EBAY_CLIENT_SECRET:-}" ]; then
    echo "ebay.sh: no EBAY_OAUTH_TOKEN and no EBAY_CLIENT_ID/EBAY_CLIENT_SECRET in .env. Skipping." >&2
    exit 7
  fi
  # 3) reuse a cached token if it hasn't (nearly) expired.
  if [ -f "$TOKEN_FILE" ]; then
    local cached exp
    cached=$(python3 -c "import json,sys;d=json.load(open('$TOKEN_FILE'));print(d.get('access_token',''))" 2>/dev/null || true)
    exp=$(python3 -c "import json,sys;d=json.load(open('$TOKEN_FILE'));print(int(d.get('expires_at',0)))" 2>/dev/null || echo 0)
    if [ -n "$cached" ] && [ "$(now_s)" -lt "$((exp - 60))" ]; then
      printf '%s' "$cached"
      return 0
    fi
  fi
  # 4) mint a fresh one.
  local basic body http_code tmp
  basic=$(printf '%s:%s' "$EBAY_CLIENT_ID" "$EBAY_CLIENT_SECRET" | base64 | tr -d '\n')
  tmp=$(mktemp)
  http_code=$(curl -sS -X POST "${BASE}/identity/v1/oauth2/token" \
    -H "Authorization: Basic $basic" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode 'grant_type=client_credentials' \
    --data-urlencode "scope=$OAUTH_SCOPE" \
    -o "$tmp" -w '%{http_code}') || { rm -f "$tmp"; echo "ebay.sh: token curl failed" >&2; exit 4; }
  if [ "$http_code" -ge 400 ]; then
    cat "$tmp" >&2; rm -f "$tmp"
    echo "ebay.sh: token mint HTTP $http_code (check EBAY_CLIENT_ID/SECRET)" >&2
    exit 6
  fi
  # persist with a computed absolute expiry (expires_in is seconds-from-now).
  python3 - "$tmp" "$TOKEN_FILE" "$(now_s)" <<'PY'
import json, sys
body = json.load(open(sys.argv[1]))
out = {"access_token": body.get("access_token", ""),
       "expires_at": int(sys.argv[3]) + int(body.get("expires_in", 7200))}
json.dump(out, open(sys.argv[2], "w"))
PY
  python3 -c "import json;print(json.load(open('$TOKEN_FILE'))['access_token'])"
  rm -f "$tmp"
}

acquire_lock() {
  local waited=0
  while ! mkdir "$LOCK_FILE" 2>/dev/null; do
    sleep 0.05; waited=$((waited+50))
    [ $waited -gt 30000 ] && { echo "ebay.sh: lock timeout" >&2; exit 2; }
  done
  trap 'rmdir "$LOCK_FILE" 2>/dev/null || true' EXIT
}

pace() {
  local need_ms=$1 last_ms cur_ms gap
  cur_ms=$(now_ms)
  if [ -f "$LAST_CALL_FILE" ]; then
    last_ms=$(cat "$LAST_CALL_FILE" 2>/dev/null || echo 0)
    gap=$(( cur_ms - last_ms ))
    [ "$gap" -lt "$need_ms" ] && python3 -c "import time; time.sleep($(( need_ms - gap ))/1000.0)"
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
  local token rc
  # get_token exits 7 (no creds) / 4 / 6 and writes its own stderr; capture and
  # propagate the code explicitly since a subshell exit inside $(...) won't
  # reliably trip set -e.
  token=$(get_token) || { rc=$?; exit "$rc"; }
  acquire_lock; pace $GAP_MS
  local tmp_body http_code
  tmp_body=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_body'; rmdir '$LOCK_FILE' 2>/dev/null || true" EXIT
  http_code=$(curl -sS \
    -H "Authorization: Bearer $token" \
    -H "X-EBAY-C-MARKETPLACE-ID: $MARKETPLACE" \
    -H 'Accept: application/json' \
    -o "$tmp_body" -w '%{http_code}' "$url") \
    || { echo "ebay.sh: curl failed for $url" >&2; exit 4; }
  if [ "$http_code" -ge 400 ]; then
    cat "$tmp_body"; echo "ebay.sh: HTTP $http_code from $url" >&2; exit 6
  fi
  cp "$tmp_body" "$cache_file"; cat "$tmp_body"
}

cmd="${1:-}"; shift || true
case "$cmd" in
  search) [ -z "${1:-}" ] && { echo "usage: ebay.sh search '<query>'" >&2; exit 1; }
          call_api "/buy/browse/v1/item_summary/search?q=$(urlencode "$1")&limit=50" ;;
  raw)    [ -z "${1:-}" ] && { echo "usage: ebay.sh raw '/buy/...'" >&2; exit 1; }
          call_api "$1" ;;
  *) echo "ebay.sh: unknown subcommand '$cmd' (search|raw)" >&2; exit 1 ;;
esac
