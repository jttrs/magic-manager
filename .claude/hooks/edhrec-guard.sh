#!/usr/bin/env bash
# PreToolUse Bash hook: blocks any direct call to json.edhrec.com / edhrec.com
# that doesn't go through the project's edhrec.sh wrapper.
#
# Exits 0 always (so the tool runs normally for non-matching commands).
# When blocking, emits hookSpecificOutput with permissionDecision=deny and
# a human-readable reason telling Claude to use the wrapper instead.

set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

# Only care about commands that actually issue an HTTP request to EDHREC. Match
# on the URL form (://…edhrec.com) so log lines / commit messages that mention
# the domain as text don't get blocked.
case "$cmd" in
  *://json.edhrec.com*|*://edhrec.com*|*://www.edhrec.com*) ;;
  *) exit 0 ;;
esac

# Allow if the command path goes through the project wrapper.
case "$cmd" in
  *.claude/skills/edhrec-search/edhrec.sh*) exit 0 ;;
  */edhrec-search/edhrec.sh*) exit 0 ;;
esac

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct curl to json.edhrec.com is blocked. Use the project wrapper at .claude/skills/edhrec-search/edhrec.sh — it paces requests, caches responses for 24h, and backs off on HTTP 429. Example: .claude/skills/edhrec-search/edhrec.sh commander atraxa-praetors-voice. Or use the CLI: uv run mm edhrec commander 'Atraxa, Praetors Voice'."
  }
}
JSON
