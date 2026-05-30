#!/usr/bin/env bash
# MTGJSON.com data wrapper.
# Caches every fetched resource at ${TMPDIR}/mtgjson-cache/<resource>; cache
# is content-addressed and never expires automatically. Use `check-stale` to
# compare cached SHA-256 against the published .sha256 sidecar, and `refresh`
# to delete a cached copy so the next fetch re-downloads it.
#
# Why no auto-TTL? Per-deck files are immutable historical records. Per-set
# files change rarely (the FIC chocobotrackfoil printings dropped weeks
# post-release). Stale-checking is a 64-byte HEAD-equivalent so it's cheap
# when the user opts in.
#
# Usage:
#   mtgjson.sh meta
#   mtgjson.sh set FIC
#   mtgjson.sh deck CounterBlitz_FIC
#   mtgjson.sh decklist
#   mtgjson.sh sha256 FIC.json
#   mtgjson.sh raw '/api/v5/SetList.json'
#   mtgjson.sh check-stale FIC.json
#   mtgjson.sh refresh FIC.json
#
# All output is the raw bytes from MTGJSON. Exits non-zero with a message
# on HTTP errors.

set -euo pipefail

UA='ClaudeCode-magic-manager-MTGJSONSkill/1.0 (https://mtgjson.com; +read-only)'
BASE='https://mtgjson.com/api/v5'
CACHE_DIR="${MTGJSON_CACHE_DIR:-${TMPDIR:-/tmp}/mtgjson-cache}"
STATE_DIR="${MTGJSON_STATE_DIR:-${TMPDIR:-/tmp}/mtgjson-state}"
POLITE_GAP_MS=100   # static-file CDN; no rate limit, but be polite
LAST_CALL_FILE="$STATE_DIR/last_call_ms"
LOCK_FILE="$STATE_DIR/lock"

mkdir -p "$CACHE_DIR" "$STATE_DIR"

now_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }
sha256_file() { python3 -c 'import sys,hashlib; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"; }

# Acquire a coarse lock so concurrent invocations serialize. Same mkdir-mutex
# pattern as scryfall.sh because macOS lacks flock(1).
acquire_lock() {
  local waited=0
  while ! mkdir "$LOCK_FILE" 2>/dev/null; do
    sleep 0.05
    waited=$((waited+50))
    if [ $waited -gt 30000 ]; then
      echo "mtgjson.sh: lock timeout" >&2
      exit 2
    fi
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
      sleep_ms=$(( need_ms - gap ))
      python3 -c "import time; time.sleep($sleep_ms/1000.0)"
    fi
  fi
  now_ms > "$LAST_CALL_FILE"
}

# Translate a logical resource path (e.g. "FIC.json", "decks/CounterBlitz_FIC.json")
# to the on-disk cache path under $CACHE_DIR.
cache_path_for() { printf '%s/%s' "$CACHE_DIR" "$1"; }

# Fetch a URL into a target file. Honors cache (returns immediately if present
# and force=0). Set force=1 to bypass cache.
fetch_to_cache() {
  # $1 = resource path under /api/v5/  (e.g. "FIC.json", "decks/X_Y.json", "FIC.json.sha256")
  # $2 = force (0 or 1)
  local resource="$1" force="${2:-0}"
  local url="${BASE}/${resource}"
  local cache_file
  cache_file="$(cache_path_for "$resource")"

  if [ "$force" = "0" ] && [ -s "$cache_file" ]; then
    return 0
  fi

  acquire_lock
  pace $POLITE_GAP_MS

  mkdir -p "$(dirname "$cache_file")"
  local tmp_body http_code
  tmp_body=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_body'; rmdir '$LOCK_FILE' 2>/dev/null || true" EXIT

  http_code=$(curl -sS \
    -H "User-Agent: $UA" \
    -H 'Accept: application/json,application/octet-stream;q=0.8,*/*;q=0.5' \
    -o "$tmp_body" \
    -w '%{http_code}' \
    "$url") || {
      echo "mtgjson.sh: curl failed for $url" >&2
      exit 4
    }

  if [ "$http_code" -ge 400 ]; then
    cat "$tmp_body" >&2
    echo "mtgjson.sh: HTTP $http_code from $url" >&2
    exit 6
  fi

  mv "$tmp_body" "$cache_file"
}

emit_cached() {
  # $1 = resource path
  local cache_file
  cache_file="$(cache_path_for "$1")"
  cat "$cache_file"
}

cmd="${1:-}"; shift || true
case "$cmd" in
  meta)
    fetch_to_cache "Meta.json" 0
    emit_cached "Meta.json"
    ;;
  set)
    code="${1:-}"
    [ -z "$code" ] && { echo "usage: mtgjson.sh set <SETCODE>" >&2; exit 1; }
    code_upper=$(printf '%s' "$code" | tr '[:lower:]' '[:upper:]')
    fetch_to_cache "${code_upper}.json" 0
    emit_cached "${code_upper}.json"
    ;;
  deck)
    name="${1:-}"
    [ -z "$name" ] && { echo "usage: mtgjson.sh deck <FILENAME>  (no .json suffix; e.g. CounterBlitz_FIC)" >&2; exit 1; }
    # Strip .json if user passed it.
    name="${name%.json}"
    fetch_to_cache "decks/${name}.json" 0
    emit_cached "decks/${name}.json"
    ;;
  decklist)
    fetch_to_cache "DeckList.json" 0
    emit_cached "DeckList.json"
    ;;
  setlist)
    fetch_to_cache "SetList.json" 0
    emit_cached "SetList.json"
    ;;
  sha256)
    resource="${1:-}"
    [ -z "$resource" ] && { echo "usage: mtgjson.sh sha256 <RESOURCE_PATH>" >&2; exit 1; }
    fetch_to_cache "${resource}.sha256" 1   # always re-fetch sidecar; it's 64 bytes
    emit_cached "${resource}.sha256"
    ;;
  raw)
    path="${1:-}"
    [ -z "$path" ] && { echo "usage: mtgjson.sh raw '/api/v5/...'" >&2; exit 1; }
    # Strip leading /api/v5/ if present so the cache path stays relative.
    relative="${path#/api/v5/}"
    relative="${relative#/}"
    fetch_to_cache "$relative" 0
    emit_cached "$relative"
    ;;
  check-stale)
    resource="${1:-}"
    [ -z "$resource" ] && { echo "usage: mtgjson.sh check-stale <RESOURCE_PATH>" >&2; exit 1; }
    cache_file="$(cache_path_for "$resource")"
    if [ ! -s "$cache_file" ]; then
      echo "absent"
      exit 0
    fi
    # Always pull a fresh sidecar to compare against.
    fetch_to_cache "${resource}.sha256" 1
    published="$(awk '{print $1; exit}' "$(cache_path_for "${resource}.sha256")")"
    actual="$(sha256_file "$cache_file")"
    if [ "$published" = "$actual" ]; then
      echo "fresh"
    else
      echo "stale"
    fi
    ;;
  refresh)
    resource="${1:-}"
    [ -z "$resource" ] && { echo "usage: mtgjson.sh refresh <RESOURCE_PATH>" >&2; exit 1; }
    cache_file="$(cache_path_for "$resource")"
    rm -f "$cache_file" "${cache_file}.sha256" "$(cache_path_for "${resource}.sha256")"
    echo "removed: $cache_file"
    ;;
  cache-path)
    # Diagnostic helper — print where a resource would be cached.
    resource="${1:-}"
    [ -z "$resource" ] && { echo "usage: mtgjson.sh cache-path <RESOURCE_PATH>" >&2; exit 1; }
    cache_path_for "$resource"
    ;;
  *)
    cat >&2 <<EOF
mtgjson.sh: unknown subcommand '$cmd'
Subcommands:
  meta                          Meta.json (build date + version)
  set <SETCODE>                 <SETCODE>.json (case-insensitive)
  deck <FILENAME>               decks/<FILENAME>.json (e.g. CounterBlitz_FIC)
  decklist                      DeckList.json (every deck's metadata)
  setlist                       SetList.json (every set's metadata)
  sha256 <RESOURCE_PATH>        <RESOURCE_PATH>.sha256 (always fresh)
  raw '/api/v5/<path>'          arbitrary path (escape hatch)
  check-stale <RESOURCE_PATH>   compare cached file's SHA-256 to the published one;
                                prints 'fresh', 'stale', or 'absent'
  refresh <RESOURCE_PATH>       delete cached copy; next fetch re-downloads
  cache-path <RESOURCE_PATH>    print where a resource would be cached
EOF
    exit 1
    ;;
esac
