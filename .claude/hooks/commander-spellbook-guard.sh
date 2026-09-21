#!/usr/bin/env bash
# PreToolUse Bash hook: blocks any direct call to backend.commanderspellbook.com
# that doesn't go through the project's spellbook.sh wrapper.
#
# Exits 0 always (so the tool runs normally for non-matching commands).
# When blocking, emits hookSpecificOutput with permissionDecision=deny and
# a human-readable reason telling Claude to use the wrapper instead.

set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

# Only care about commands that actually issue an HTTP request to the
# Commander Spellbook API. Match on the URL form
# ("://backend.commanderspellbook.com") rather than the bare hostname so
# commit messages, log lines, etc. that mention the domain as text don't
# get blocked.
case "$cmd" in
  *://backend.commanderspellbook.com*) ;;
  *) exit 0 ;;
esac

# Allow if the command path goes through the project wrapper.
case "$cmd" in
  *.claude/skills/commander-spellbook/spellbook.sh*) exit 0 ;;
  */commander-spellbook/spellbook.sh*) exit 0 ;;
esac

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct curl to backend.commanderspellbook.com is blocked. Use the project wrapper at .claude/skills/commander-spellbook/spellbook.sh — it enforces pacing, caches responses for 24h, and backs off on HTTP 429. Example: .claude/skills/commander-spellbook/spellbook.sh find-my-combos [path-to-body.json]"
  }
}
JSON
