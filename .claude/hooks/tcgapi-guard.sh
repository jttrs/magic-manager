#!/usr/bin/env bash
# PreToolUse Bash hook: blocks any direct call to the TCG API (tcgapi.dev /
# api.tcgapi.*) that doesn't go through the project's tcgapi.sh wrapper.
#
# Exits 0 always (so the tool runs normally for non-matching commands).

set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

case "$cmd" in
  *://*tcgapi.dev*|*://api.tcgplayer-alt*) ;;
  *) exit 0 ;;
esac

case "$cmd" in
  *.claude/skills/sealed-value/tcgapi.sh*) exit 0 ;;
  */sealed-value/tcgapi.sh*) exit 0 ;;
esac

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct curl to the TCG API is blocked. Use the project wrapper at .claude/skills/sealed-value/tcgapi.sh — it reads TCGAPI_KEY from .env, caches for 24h, and paces requests."
  }
}
JSON
