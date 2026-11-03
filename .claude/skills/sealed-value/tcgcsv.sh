#!/usr/bin/env bash
# tcgcsv.com API wrapper — free, no-auth TCGplayer price mirror.
#
# tcgcsv.com republishes TCGplayer's public price + product data keyed by
# TCGplayer's own categoryId (Magic = 1) and groupId (== MTGJSON's
# tcgplayerGroupId). We use it for SEALED product market prices, which
# MTGJSON's own price feed does not carry.
#
# Usage:
#   tcgcsv.sh prices <groupId> [categoryId=1]   # all products' prices in a group
#   tcgcsv.sh products <groupId> [categoryId=1]  # product metadata (names) in a group
#   tcgcsv.sh raw '/tcgplayer/1/1293/prices'     # arbitrary path
#
# Caches responses for 24h and paces requests. All output is the raw JSON body.
# Exits non-zero with a message on HTTP errors.

set -euo pipefail

UA='ClaudeCode-magic-manager-SealedValue/1.0 (respectful cached client)'
CACHE_DIR="${TCGCSV_CACHE_DIR:-${TMPDIR:-/tmp}/tcgcsv-cache}"
STATE_DIR="${TCGCSV_STATE_DIR:-${TMPDIR:-/tmp}/tcgcsv-state}"
CACHE_TTL_SECONDS=${TCGCSV_CACHE_TTL:-86400}   # 24h
GAP_MS=250
LAST_CALL_FILE="$STATE_DIR/last_call_ms"
LOCK_FILE="$STATE_DIR/lock"

mkdir -p "$CACHE_DIR" "$STATE_DIR"

RL_NAME=tcgcsv.sh
# shellcheck source=../_lib/ratelimit.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_lib/ratelimit.sh"

sha() { python3 -c 'import sys,hashlib; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest())'; }

call_api() {
  # $1 = path (e.g. /tcgplayer/1/1293/prices)
  local path="$1"
  local url="https://tcgcsv.com${path}"

  local cache_key cache_file
  cache_key=$(printf '%s' "$url" | sha)
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
  rl_pace $GAP_MS

  local tmp_body http_code
  tmp_body=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_body'; rmdir '$LOCK_FILE' 2>/dev/null || true" EXIT

  http_code=$(curl -sS \
    -H "User-Agent: $UA" \
    -H 'Accept: application/json' \
    -o "$tmp_body" \
    -w '%{http_code}' \
    "$url") || {
      echo "tcgcsv.sh: curl failed for $url" >&2
      exit 4
    }

  if [ "$http_code" -ge 400 ]; then
    cat "$tmp_body"
    echo "tcgcsv.sh: HTTP $http_code from $url" >&2
    exit 6
  fi

  cp "$tmp_body" "$cache_file"
  cat "$tmp_body"
}

cmd="${1:-}"; shift || true
case "$cmd" in
  prices)
    group="${1:-}"; cat_id="${2:-1}"
    [ -z "$group" ] && { echo "usage: tcgcsv.sh prices <groupId> [categoryId=1]" >&2; exit 1; }
    call_api "/tcgplayer/${cat_id}/${group}/prices"
    ;;
  products)
    group="${1:-}"; cat_id="${2:-1}"
    [ -z "$group" ] && { echo "usage: tcgcsv.sh products <groupId> [categoryId=1]" >&2; exit 1; }
    call_api "/tcgplayer/${cat_id}/${group}/products"
    ;;
  raw)
    path="${1:-}"
    [ -z "$path" ] && { echo "usage: tcgcsv.sh raw '/tcgplayer/1/1293/prices'" >&2; exit 1; }
    call_api "$path"
    ;;
  *)
    cat >&2 <<EOF
tcgcsv.sh: unknown subcommand '$cmd'
Subcommands:
  prices   <groupId> [categoryId=1]   all products' prices in a TCGplayer group
  products <groupId> [categoryId=1]   product metadata (names) in a group
  raw      '/tcgplayer/1/1293/prices' arbitrary path
EOF
    exit 1
    ;;
esac
