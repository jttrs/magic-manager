#!/usr/bin/env bash
# PostToolUse Bash hook: after a bulk-order buy-list is produced, copy the
# paste-ready text to the macOS clipboard so the user can paste it straight into
# the receiving portal.
#
# Two cases:
#   1. File producers (mm query missing-set / missing-jumpstart, jumpstart_buildable.py)
#      write both a ManaPool and a TCGplayer .txt. We copy the ManaPool file
#      (the *-manapool-*.txt whose path the command just printed).
#   2. Ad-hoc `mm export manapool|tcgplayer '<selector>'` prints paste-ready text
#      to stdout (comments go to stderr). We copy that stdout verbatim.
#
# Always exits 0 (never blocks / errors the tool). No-ops silently on
# non-matching commands and when pbcopy is unavailable (non-macOS).

set -euo pipefail

input=$(cat)

# Extract command + tool stdout in one exception-safe pass. tool_response may be
# a dict ({"stdout": ...}) or a bare string depending on the Bash tool schema —
# handle both. Any malformed input degrades to empty strings so the hook simply
# no-ops rather than erroring the tool. Emitted as: line 1 = command (always
# single-line), remaining lines = stdout — bash can't hold NUL, so we split on
# the first newline instead.
parsed=$(printf '%s' "$input" | python3 -c '
import sys, json
cmd = out = ""
try:
    d = json.load(sys.stdin)
    cmd = (d.get("tool_input", {}).get("command", "") or "").replace("\n", " ")
    r = d.get("tool_response", "")
    if isinstance(r, dict):
        out = r.get("stdout", "") or ""
    elif isinstance(r, str):
        out = r
except Exception:
    pass
sys.stdout.write(cmd + "\n" + out)
' 2>/dev/null || printf '\n')
cmd=${parsed%%$'\n'*}
out=${parsed#*$'\n'}

# Only act on the bulk-order producers / exports.
case "$cmd" in
  *"mm query missing-set"*|*"mm query missing-jumpstart"*|*jumpstart_buildable.py*)
    kind=file ;;
  *"mm export manapool"*|*"mm export tcgplayer"*)
    kind=stdout ;;
  *)
    exit 0 ;;
esac

# pbcopy is macOS-only; degrade gracefully elsewhere.
command -v pbcopy >/dev/null 2>&1 || exit 0

emit() {
  # $1 = additionalContext message
  python3 -c '
import sys, json
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": sys.argv[1],
}}))
' "$1"
}

if [ "$kind" = file ]; then
  # Pull the *-manapool-*.txt path the command printed. The stdout embeds it in
  # a file:// link and/or a bare path; grab the first buy-lists manapool token.
  file=$(printf '%s' "$out" | python3 -c '
import sys, re
m = re.search(r"(/[^\s()\]]*buy-lists/[^\s()\]]*manapool[^\s()\]]*\.txt)", sys.stdin.read())
print(m.group(1) if m else "")
')
  [ -n "$file" ] && [ -f "$file" ] || exit 0
  pbcopy < "$file"
  rows=$(grep -c '' "$file" 2>/dev/null || echo "?")
  emit "Copied the ManaPool buy-list ($rows rows) to the clipboard — paste directly into the portal. (A TCGplayer .txt was also written; ask to copy that one instead if needed.)"
  exit 0
fi

# kind = stdout: copy the export's paste-ready stdout. Empty (e.g. --out was
# passed, so text went to a file) → nothing to copy.
[ -n "$out" ] || exit 0
printf '%s' "$out" | pbcopy
case "$cmd" in
  *"mm export tcgplayer"*) target="TCGplayer" ;;
  *) target="ManaPool" ;;
esac
emit "Copied the $target export to the clipboard — paste directly into the portal."
exit 0
