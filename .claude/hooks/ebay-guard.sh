#!/usr/bin/env bash
# PreToolUse Bash hook: blocks direct calls to eBay's API that don't go through
# the project's ebay.sh wrapper. Exits 0 for non-matching commands.

set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

case "$cmd" in
  *://*ebay.com/buy/*|*://api.ebay.com*|*://svcs.ebay.com*) ;;
  *) exit 0 ;;
esac

case "$cmd" in
  *.claude/skills/sealed-value/ebay.sh*) exit 0 ;;
  */sealed-value/ebay.sh*) exit 0 ;;
esac

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct curl to eBay's API is blocked. Use the project wrapper at .claude/skills/sealed-value/ebay.sh — it reads EBAY_* OAuth credentials from .env. Note: eBay sold-comps are ADVISORY only (non-deterministic) and never enter the deterministic artifact."
  }
}
JSON
