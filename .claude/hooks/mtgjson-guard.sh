#!/usr/bin/env bash
# PreToolUse Bash hook: blocks any direct call to mtgjson.com that doesn't
# go through the project's mtgjson.sh wrapper.
#
# Exits 0 always (so the tool runs normally for non-matching commands).
# When blocking, emits hookSpecificOutput with permissionDecision=deny and
# a human-readable reason telling Claude to use the wrapper instead.

set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

# Match URLs to mtgjson.com (with or without www). Use the URL form
# (://...mtgjson.com) to avoid false positives from log lines etc.
case "$cmd" in
  *://mtgjson.com*|*://www.mtgjson.com*) ;;
  *) exit 0 ;;
esac

# Allow if the command goes through the project wrapper.
case "$cmd" in
  *.claude/skills/mtgjson-search/mtgjson.sh*) exit 0 ;;
  */mtgjson-search/mtgjson.sh*) exit 0 ;;
esac

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct curl to mtgjson.com is blocked. Use the project wrapper at .claude/skills/mtgjson-search/mtgjson.sh — it caches every fetch under ${TMPDIR}/mtgjson-cache and supports content-hash staleness checks via the .sha256 sidecars. Example: .claude/skills/mtgjson-search/mtgjson.sh deck CounterBlitz_FIC. Or use the CLI: uv run mm mtgjson deck CounterBlitz_FIC."
  }
}
JSON
