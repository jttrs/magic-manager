#!/usr/bin/env bash
# PreToolUse Bash hook: blocks direct HTTP calls to external deck builders
# (Moxfield / Archidekt / MTGGoldfish) that don't go through the project's
# sanctioned deck-import scripts. Mirrors manapool-guard.sh.
#
# Rationale: Moxfield's api2 is Cloudflare-gated and needs the Playwright session
# handling in scripts/import_deck.py + scripts/moxfield_session.py (which manage
# the browser context and credentials correctly). Ad-hoc curl to it will just get
# a 403 and risks mishandling the login. Archidekt/MTGGoldfish are open, but we
# still funnel them through the one script so the fetch stays in the sanctioned,
# path-allowlisted home.
#
# Exits 0 for non-matching commands (tool runs normally). Emits a deny decision
# with guidance when blocking.

set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

# Only care about commands issuing HTTP to a deck-builder host (URL form).
case "$cmd" in
  *://api2.moxfield.com*|*://www.moxfield.com/decks*|*://moxfield.com/decks*|*://archidekt.com/api*|*://www.archidekt.com/api*|*mtggoldfish.com/deck*) ;;
  *) exit 0 ;;
esac

# Allow the sanctioned deck-import scripts (they own the fetch + auth handling).
case "$cmd" in
  *scripts/import_deck.py*) exit 0 ;;
  *scripts/moxfield_push.py*) exit 0 ;;
  *scripts/moxfield_session.py*) exit 0 ;;
esac

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct HTTP to Moxfield/Archidekt/MTGGoldfish is blocked. Use `scripts/import_deck.py <deck-url>` — it dispatches by source (Archidekt/MTGGoldfish plain fetch, Moxfield via a Playwright authed context) and emits normalized-cards JSON for `uv run mm deck import-deck`. For Moxfield when the browser path is blocked, use the bookmarklet in .claude/skills/import-deck/ and `--file -`."
  }
}
JSON
