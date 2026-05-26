#!/usr/bin/env bash
# PreToolUse Bash hook: blocks any direct call to api.scryfall.com that
# doesn't go through the project's scryfall.sh wrapper.
#
# Exits 0 always (so the tool runs normally for non-matching commands).
# When blocking, emits hookSpecificOutput with permissionDecision=deny and
# a human-readable reason telling Claude to use the wrapper instead.

set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

# Only care about commands that actually issue an HTTP request to the
# Scryfall API. Match on the URL form ("://api.scryfall.com") rather than
# the bare hostname so commit messages, log lines, etc. that mention the
# domain as text don't get blocked.
case "$cmd" in
  *://api.scryfall.com*) ;;
  *) exit 0 ;;
esac

# Allow if the command path goes through the project wrapper.
case "$cmd" in
  *.claude/skills/scryfall-search/scryfall.sh*) exit 0 ;;
  */scryfall-search/scryfall.sh*) exit 0 ;;
esac

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct curl to api.scryfall.com is blocked. Use the project wrapper at .claude/skills/scryfall-search/scryfall.sh — it enforces the 500ms-per-request rate limit, caches responses for 24h, and backs off on HTTP 429. Example: .claude/skills/scryfall-search/scryfall.sh search 't:dragon c:r f:modern' order=edhrec"
  }
}
JSON
