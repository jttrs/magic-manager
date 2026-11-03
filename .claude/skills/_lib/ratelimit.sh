# shellcheck shell=bash
# Shared lock / pacing / 429-backoff helpers for the external-API wrappers
# (scryfall.sh, edhrec.sh, spellbook.sh, manapool.sh, mtgjson.sh, tcgcsv.sh,
# tcgapi.sh, ebay.sh). SOURCED, never executed: it defines functions only and
# changes no shell options. Bash 3.2 compatible (macOS).
#
# The caller sets, before calling any rl_ function:
#   RL_NAME         wrapper name used in messages (e.g. "scryfall.sh")
#   LOCK_FILE       mkdir-based mutex path        (rl_acquire_lock)
#   LAST_CALL_FILE  last call time in ms          (rl_pace)
#   BACKOFF_FILE    backoff-until time in ms      (rl_check_backoff, rl_set_backoff;
#                                                  only for wrappers that back off)
# Optional: RL_LOCK_TIMEOUT_MS (default 30000) bounds the lock wait (tests).
#
# Exit codes (unchanged from the per-wrapper copies): lock timeout 2,
# inside a backoff window 3.

rl_now_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }

# Acquire a coarse lock so concurrent invocations serialize their pacing logic.
# macOS lacks flock(1), so we use a mkdir-based mutex. Releases on EXIT; a
# wrapper that later re-sets the EXIT trap must keep the rmdir in it.
rl_acquire_lock() {
  local waited=0
  while ! mkdir "$LOCK_FILE" 2>/dev/null; do
    sleep 0.05
    waited=$((waited+50))
    if [ $waited -gt "${RL_LOCK_TIMEOUT_MS:-30000}" ]; then
      echo "$RL_NAME: lock timeout" >&2
      exit 2
    fi
  done
  trap 'rmdir "$LOCK_FILE" 2>/dev/null || true' EXIT
}

rl_check_backoff() {
  if [ -f "$BACKOFF_FILE" ]; then
    local until_ms cur_ms
    until_ms=$(cat "$BACKOFF_FILE" 2>/dev/null || echo 0)
    cur_ms=$(rl_now_ms)
    if [ "$cur_ms" -lt "$until_ms" ]; then
      local remaining=$(( (until_ms - cur_ms) / 1000 + 1 ))
      echo "$RL_NAME: in backoff window after a 429, ${remaining}s remaining. Aborting." >&2
      exit 3
    fi
    rm -f "$BACKOFF_FILE"
  fi
}

# $1 = required gap in ms since the previous call
rl_pace() {
  local need_ms=$1 last_ms cur_ms gap sleep_ms
  cur_ms=$(rl_now_ms)
  if [ -f "$LAST_CALL_FILE" ]; then
    last_ms=$(cat "$LAST_CALL_FILE" 2>/dev/null || echo 0)
    gap=$(( cur_ms - last_ms ))
    if [ "$gap" -lt "$need_ms" ]; then
      sleep_ms=$(( need_ms - gap ))
      python3 -c "import time; time.sleep($sleep_ms/1000.0)"
    fi
  fi
  rl_now_ms > "$LAST_CALL_FILE"
}

# $1 = seconds; persist a backoff window after an HTTP 429
rl_set_backoff() {
  echo $(( $(rl_now_ms) + $1 * 1000 )) > "$BACKOFF_FILE"
}
