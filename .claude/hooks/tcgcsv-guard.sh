#!/usr/bin/env bash
# PreToolUse Bash hook: blocks any direct call to tcgcsv.com that doesn't go
# through the project's tcgcsv.sh wrapper.
#
# Exits 0 always (so the tool runs normally for non-matching commands).
# When blocking, emits hookSpecificOutput with permissionDecision=deny and a
# human-readable reason telling Claude to use the wrapper instead.

set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

# Only care about commands that actually issue an HTTP request to tcgcsv.com.
case "$cmd" in
  *://tcgcsv.com*) ;;
  *) exit 0 ;;
esac

# Allow if the command path goes through the project wrapper.
case "$cmd" in
  *.claude/skills/sealed-value/tcgcsv.sh*) exit 0 ;;
  */sealed-value/tcgcsv.sh*) exit 0 ;;
esac

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct curl to tcgcsv.com is blocked. Use the project wrapper at .claude/skills/sealed-value/tcgcsv.sh — it caches responses for 24h and paces requests. Example: .claude/skills/sealed-value/tcgcsv.sh prices 1293"
  }
}
JSON
