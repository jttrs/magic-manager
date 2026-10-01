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

# Classify the command + extract tool stdout in one exception-safe pass.
# tool_response may be a dict ({"stdout": ...}) or a bare string depending on the
# Bash tool schema — handle both. Any malformed input degrades to a no-op rather
# than erroring the tool.
#
# CRITICAL: a bulk-order invocation is matched by STRUCTURE, not loose substring —
# the producer must appear at a command boundary (start of string, or after
# && / || / ; / | / newline), with an optional `uv run` prefix. This mirrors the
# guard hooks' URL-form matching, and prevents false positives where the text
# appears only inside an argument to another command (e.g. a `git commit -m` whose
# message mentions `mm export manapool`, or an `echo`).
#
# Output: line 1 = "<kind>:<target>" (kind ∈ file|stdout|none; target ∈
# manapool|tcgplayer|-), remaining lines = stdout. bash can't hold NUL, so we
# split on the first newline.
parsed=$(printf '%s' "$input" | python3 -c '
import sys, json, re
kind, target, out = "none", "-", ""
try:
    d = json.load(sys.stdin)
    cmd = (d.get("tool_input", {}).get("command", "") or "").replace("\n", " ")
    r = d.get("tool_response", "")
    if isinstance(r, dict):
        out = r.get("stdout", "") or ""
    elif isinstance(r, str):
        out = r
    # Command boundary: start, or after a shell separator (&& || ; | newline).
    boundary = r"(?:^|&&|\|\||[;|])\s*(?:uv\s+run\s+)?"
    if re.search(boundary + r"mm\s+query\s+missing-set\b", cmd) \
            or re.search(boundary + r"mm\s+query\s+missing-jumpstart\b", cmd) \
            or re.search(boundary + r"(?:uv\s+run\s+)?python\S*\s+scripts/jumpstart_buildable\.py\b", cmd):
        kind = "file"
    elif re.search(boundary + r"mm\s+export\s+manapool\b", cmd):
        kind, target = "stdout", "manapool"
    elif re.search(boundary + r"mm\s+export\s+tcgplayer\b", cmd):
        kind, target = "stdout", "tcgplayer"
except Exception:
    pass
sys.stdout.write(f"{kind}:{target}\n" + out)
' 2>/dev/null || printf 'none:-\n')
header=${parsed%%$'\n'*}
out=${parsed#*$'\n'}
kind=${header%%:*}
target=${header#*:}

[ "$kind" = "none" ] && exit 0

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
[ "$target" = "tcgplayer" ] && label="TCGplayer" || label="ManaPool"
emit "Copied the $label export to the clipboard — paste directly into the portal."
exit 0
