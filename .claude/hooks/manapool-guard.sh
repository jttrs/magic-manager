#!/usr/bin/env bash
# PreToolUse Bash hook: blocks direct HTTP calls to Mana Pool hosts that don't
# go through the project's sanctioned wrapper (manapool.sh) or the cart script
# (manapool_cart.py). Mirrors scryfall-guard.sh.
#
# Rationale: the sanctioned API (manapool.com/api/v1) must go via manapool.sh so
# it stays paced + cached + 429-backed-off. The Supabase backend
# (sb-api.manapool.com) is only touched by scripts/manapool_cart.py (which
# handles the short-lived session JWT correctly) — direct ad-hoc curl to it from
# the agent is blocked to avoid mishandling credentials.
#
# Exits 0 for non-matching commands (tool runs normally). Emits a deny decision
# with guidance when blocking.

set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

# Only care about commands issuing HTTP to a Mana Pool host (URL form).
case "$cmd" in
  *://manapool.com/api*|*://sb-api.manapool.com*) ;;
  *) exit 0 ;;
esac

# Allow the sanctioned wrapper and the cart script (they own the auth handling).
case "$cmd" in
  *.claude/skills/manapool-search/manapool.sh*) exit 0 ;;
  */manapool-search/manapool.sh*) exit 0 ;;
  *scripts/manapool_cart.py*) exit 0 ;;
  *scripts/manapool_price_check.py*) exit 0 ;;
esac

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct HTTP to Mana Pool is blocked. For the sanctioned catalog/price API use .claude/skills/manapool-search/manapool.sh (paced + 24h-cached + 429 backoff), e.g. `manapool.sh products <scryfall_id>`. For the cart, use `scripts/manapool_cart.py` (handles the Supabase session JWT correctly). Don't curl sb-api.manapool.com directly — it mishandles the short-lived auth token."
  }
}
JSON
