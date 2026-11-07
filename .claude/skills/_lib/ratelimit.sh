# shellcheck shell=bash
# Shared lock / pacing / 429-backoff helpers for the external-API wrappers
# (scryfall.sh, edhrec.sh, spellbook.sh, manapool.sh, mtgjson.sh, tcgcsv.sh,
# tcgapi.sh, ebay.sh). SOURCED, never executed: it defines functions only and
# changes no shell options. Bash 3.2 compatible (macOS).
#
# The caller sets, before calling any rl_ function:
#   RL_NAME         wrapper name used in messages (e.g. "scryfall.sh")
#   LOCK_FILE       base path; the kernel lock file is "$LOCK_FILE.flock"
#                   (a new name, so a leftover old mkdir-lock DIRECTORY at
#                   "$LOCK_FILE" is simply ignored)          (rl_reserve)
#   LAST_CALL_FILE  last reserved slot in ms                 (rl_reserve)
#   BACKOFF_FILE    backoff-until time in ms      (rl_check_backoff, rl_set_backoff;
#                                                  only for wrappers that back off)
# Optional: RL_LOCK_TIMEOUT_MS (default 30000) bounds the lock wait.
#
# Exit codes (unchanged from the per-wrapper copies): lock timeout 2,
# inside a backoff window 3.

rl_now_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }

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

# $1 = seconds; persist a backoff window after an HTTP 429
rl_set_backoff() {
  echo $(( $(rl_now_ms) + $1 * 1000 )) > "$BACKOFF_FILE"
}

# $1 = required gap in ms between call slots. ONE python3 call claims the next
# slot under a kernel flock (LOCK_EX|LOCK_NB, retried every ~20 ms until
# RL_LOCK_TIMEOUT_MS): it honours the backoff when BACKOFF_FILE is set (prints
# the remaining seconds, exit 3), then writes max(now, last + gap) to
# LAST_CALL_FILE and prints "<wait_ms> <slot_ms>". The kernel drops the lock
# when python exits, even on SIGKILL, so there is no stale lock to clean up.
# The caller then sleeps until its slot OUTSIDE the lock (calls are spaced
# >= gap machine-wide, downloads overlap) and re-checks the backoff, so a 429
# recorded while it slept stops it too. RL_DEBUG_SLOT=1 echoes the slot (stderr).
rl_reserve() {
  local gap=$1 out rc=0 wait_ms slot lock_path="${LOCK_FILE}.flock"
  out=$(python3 -c '
import fcntl, os, sys, time
lock, last_f, backoff_f, gap, timeout = sys.argv[1:6]
gap, timeout = int(gap), int(timeout)
def now():
    return int(time.time() * 1000)
fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
start = now()
while True:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        break
    except OSError:
        if now() - start > timeout:
            sys.exit(2)
        time.sleep(0.02)
t = now()
if backoff_f and os.path.exists(backoff_f):
    try:
        until = int(open(backoff_f).read().strip())
    except (OSError, ValueError):
        until = 0
    if until > t:
        print((until - t) // 1000 + 1)
        sys.exit(3)
    try:
        os.remove(backoff_f)
    except OSError:
        pass
try:
    last = int(open(last_f).read().strip())
except (OSError, ValueError):
    last = 0
nxt = max(t, last + gap)
if nxt - t > 60000:  # no real queue reaches a minute out: a clock that stepped back
    nxt = t
with open(last_f, "w") as f:
    f.write(str(nxt) + "\n")
print(nxt - t, nxt)
' "$lock_path" "$LAST_CALL_FILE" "${BACKOFF_FILE:-}" "$gap" "${RL_LOCK_TIMEOUT_MS:-30000}") || rc=$?
  case "$rc" in
    0) ;;
    2) echo "$RL_NAME: lock timeout" >&2; exit 2 ;;
    3) echo "$RL_NAME: in backoff window after a 429, ${out}s remaining. Aborting." >&2; exit 3 ;;
    *) echo "$RL_NAME: rate-limit reservation failed (rc $rc)" >&2; exit 2 ;;
  esac
  wait_ms=${out%% *}
  slot=${out##* }
  [ -z "${RL_DEBUG_SLOT:-}" ] || echo "$slot" >&2
  if [ "$wait_ms" -gt 0 ]; then
    python3 -c 'import sys, time; time.sleep(int(sys.argv[1]) / 1000.0)' "$wait_ms"
  fi
  if [ -n "${BACKOFF_FILE:-}" ]; then
    rl_check_backoff
  fi
}
