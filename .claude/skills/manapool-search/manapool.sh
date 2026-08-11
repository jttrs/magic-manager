#!/usr/bin/env bash
# Mana Pool sanctioned public-API wrapper (https://manapool.com/api/docs/v1).
# Mirrors scryfall.sh: paces requests, caches 24h, backs off on 429.
#
# Auth: reads MANAPOOL_EMAIL + MANAPOOL_ACCESS_TOKEN from the repo-root .env
# (or the environment). Sends them as X-ManaPool-Email / X-ManaPool-Access-Token.
# This wrapper ONLY talks to the sanctioned API (manapool.com/api/v1) with the
# mpat_ token — it never touches the Supabase backend or the session JWT (the
# cart tiers in scripts/manapool_cart.py handle that separately).
#
# Usage:
#   manapool.sh products <scryfall_id> [<scryfall_id> ...]   # GET /products/singles
#   manapool.sh product-ids <product_id> [...]               # GET /products/singles by MP product_id
#   manapool.sh optimizer <body.json>                        # POST /buyer/optimizer (body from file or stdin)
#   manapool.sh raw GET|POST '/path' [qs] [body]
#
# All output is the raw JSON body. Exits non-zero on rate-limit / HTTP errors.

set -euo pipefail

UA='ClaudeCode-magic-manager-ManaPool/1.0 (personal collection tool; respects rate-limits)'
CACHE_DIR="${MANAPOOL_CACHE_DIR:-${TMPDIR:-/tmp}/manapool-cache}"
STATE_DIR="${MANAPOOL_STATE_DIR:-${TMPDIR:-/tmp}/manapool-state}"
CACHE_TTL_SECONDS=${MANAPOOL_CACHE_TTL:-86400}   # 24h; MP publishes a daily catalog, prices move slowly
GAP_MS=${MANAPOOL_GAP_MS:-400}                   # conservative: no documented rate limit, so be polite
BACKOFF_FILE="$STATE_DIR/backoff_until"
LAST_CALL_FILE="$STATE_DIR/last_call_ms"
LOCK_FILE="$STATE_DIR/lock"
API_BASE="https://manapool.com/api/v1"

mkdir -p "$CACHE_DIR" "$STATE_DIR"

# ---- load .env (repo root, two dirs up from this skill) ----
_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_repo_root="$(cd "$_here/../../.." && pwd)"
if [ -f "$_repo_root/.env" ]; then
  # Only export the MANAPOOL_* keys; ignore comments/blanks.
  while IFS='=' read -r k v; do
    case "$k" in
      MANAPOOL_EMAIL|MANAPOOL_ACCESS_TOKEN) export "$k=$v" ;;
    esac
  done < <(grep -E '^MANAPOOL_(EMAIL|ACCESS_TOKEN)=' "$_repo_root/.env" 2>/dev/null || true)
fi

if [ -z "${MANAPOOL_EMAIL:-}" ] || [ -z "${MANAPOOL_ACCESS_TOKEN:-}" ]; then
  echo "manapool.sh: missing MANAPOOL_EMAIL / MANAPOOL_ACCESS_TOKEN (set them in $_repo_root/.env)" >&2
  exit 2
fi

now_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }
sha() { python3 -c 'import sys,hashlib; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest())'; }

acquire_lock() {
  local waited=0
  while ! mkdir "$LOCK_FILE" 2>/dev/null; do
    sleep 0.05
    waited=$((waited+50))
    if [ $waited -gt 30000 ]; then
      echo "manapool.sh: lock timeout" >&2
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
      echo "manapool.sh: in backoff window after a 429, ${remaining}s remaining. Aborting." >&2
      exit 3
    fi
    rm -f "$BACKOFF_FILE"
  fi
}

pace() {
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
  # $1 method  $2 path  $3 query-string(encoded, may be empty)  $4 body(may be empty)
  local method="$1" path="$2" qs="${3:-}" body="${4:-}"
  local url="${API_BASE}${path}"
  [ -n "$qs" ] && url="${url}?${qs}"

  local cache_key cache_file
  cache_key=$(printf '%s\n%s\n%s' "$method" "$url" "$body" | sha)
  cache_file="$CACHE_DIR/$cache_key.json"

  if [ -f "$cache_file" ]; then
    local age
    age=$(( $(date +%s) - $(stat -f %m "$cache_file" 2>/dev/null || stat -c %Y "$cache_file") ))
    if [ "$age" -lt "$CACHE_TTL_SECONDS" ]; then
      cat "$cache_file"; return 0
    fi
  fi

  acquire_lock
  check_backoff
  pace "$GAP_MS"

  local tmp_body http_code
  tmp_body=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_body'; rmdir '$LOCK_FILE' 2>/dev/null || true" EXIT

  if [ "$method" = "POST" ]; then
    http_code=$(curl -sS -X POST \
      -H "User-Agent: $UA" -H 'Accept: application/json' -H 'Content-Type: application/json' \
      -H "X-ManaPool-Email: $MANAPOOL_EMAIL" -H "X-ManaPool-Access-Token: $MANAPOOL_ACCESS_TOKEN" \
      --data-binary "$body" -o "$tmp_body" -w '%{http_code}' "$url") \
      || { echo "manapool.sh: curl POST failed for $url" >&2; exit 4; }
  else
    http_code=$(curl -sS \
      -H "User-Agent: $UA" -H 'Accept: application/json' \
      -H "X-ManaPool-Email: $MANAPOOL_EMAIL" -H "X-ManaPool-Access-Token: $MANAPOOL_ACCESS_TOKEN" \
      -o "$tmp_body" -w '%{http_code}' "$url") \
      || { echo "manapool.sh: curl failed for $url" >&2; exit 4; }
  fi

  if [ "$http_code" = "429" ]; then
    local until_ms=$(( $(now_ms) + 35000 ))
    echo "$until_ms" > "$BACKOFF_FILE"
    echo "manapool.sh: HTTP 429. Backing off 35s. Do NOT retry." >&2
    cat "$tmp_body" >&2
    exit 5
  fi
  if [ "$http_code" -ge 400 ]; then
    cat "$tmp_body"
    echo "manapool.sh: HTTP $http_code from $url" >&2
    exit 6
  fi

  cp "$tmp_body" "$cache_file"
  cat "$tmp_body"
}

urlencode() { python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"; }

# Build a repeated-param query string: $1=param name, rest=values.
# ManaPool rejects comma-joined UUID arrays; repeated key=val is required.
repeated_qs() {
  local key="$1"; shift
  local qs=""
  for v in "$@"; do
    [ -n "$qs" ] && qs="${qs}&"
    qs="${qs}$(urlencode "$key")=$(urlencode "$v")"
  done
  printf '%s' "$qs"
}

cmd="${1:-}"; shift || true
case "$cmd" in
  products)
    [ "$#" -eq 0 ] && { echo "usage: manapool.sh products <scryfall_id> [...]" >&2; exit 1; }
    call_api GET /products/singles "$(repeated_qs scryfall_ids "$@")" ""
    ;;
  product-ids)
    [ "$#" -eq 0 ] && { echo "usage: manapool.sh product-ids <product_id> [...]" >&2; exit 1; }
    call_api GET /products/singles "$(repeated_qs product_ids "$@")" ""
    ;;
  optimizer)
    src="${1:-}"
    if [ -n "$src" ] && [ -f "$src" ]; then body=$(cat "$src"); else body=$(cat); fi
    [ -z "$body" ] && { echo "usage: manapool.sh optimizer <body.json>  (or pipe JSON on stdin)" >&2; exit 1; }
    call_api POST /buyer/optimizer "" "$body"
    ;;
  raw)
    method="${1:-GET}"; path="${2:-}"; qs="${3:-}"; body="${4:-}"
    [ -z "$path" ] && { echo "usage: manapool.sh raw GET|POST '/path' [qs] [body]" >&2; exit 1; }
    call_api "$method" "$path" "$qs" "$body"
    ;;
  *)
    cat >&2 <<EOF
manapool.sh: unknown subcommand '$cmd'
Subcommands:
  products     <scryfall_id> [...]   GET /products/singles?scryfall_ids=... (repeated)
  product-ids  <product_id> [...]    GET /products/singles?product_ids=...  (repeated)
  optimizer    <body.json>           POST /buyer/optimizer   (body from file or stdin)
  raw          GET|POST '/path' [qs] [body]
EOF
    exit 1
    ;;
esac
