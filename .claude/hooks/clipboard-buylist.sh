#!/usr/bin/env bash
# PostToolUse Bash hook: after a bulk-order buy-list is produced, copy the
# paste-ready text to the macOS clipboard so the user can paste it straight into
# the receiving portal.
#
# Two cases:
#   1. File producers (any `mm` subcommand or `python scripts/*.py` that writes
#      both a ManaPool and a TCGplayer .txt via util.output_dir(type,"buy-lists"))
#      — we copy the ManaPool file (the *-manapool-*.txt whose file:// path the
#      command just printed; last match wins on a chained multi-producer run).
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
    # Check the stdout exports FIRST (exact command-name match — irreducible,
    # since they have no file to grep) so they are not swallowed by the
    # generic file-producer match below.
    if re.search(boundary + r"mm\s+export\s+manapool\b", cmd):
        kind, target = "stdout", "manapool"
    elif re.search(boundary + r"mm\s+export\s+tcgplayer\b", cmd):
        kind, target = "stdout", "tcgplayer"
    # Any other `mm` subcommand or repo python script run at a command
    # boundary is a candidate file producer. The real determinant is the
    # file-path grep below (over stdout) — no path found there is a no-op
    # (the bash `[ -n "$file" ]` guard exits 0), so this stays a loose match
    # and never needs updating when a new buy-list producer is added.
    elif re.search(boundary + r"(?:mm|python\S*\s+scripts/)\b", cmd):
        kind = "file"
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
  # Pull the *-manapool-*.txt path the command printed. The stdout embeds it as
  # a file:// link; take the LAST match so a chained multi-producer run copies
  # the most-recently-written file.
  file=$(printf '%s' "$out" | python3 -c '
import sys, re
ms = re.findall(r"file://(/[^\s()\]]*buy-lists/[^\s()\]]*manapool[^\s()\]]*\.txt)", sys.stdin.read())
print(ms[-1] if ms else "")
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
printf '%s\n' "$out" | pbcopy
[ "$target" = "tcgplayer" ] && label="TCGplayer" || label="ManaPool"
emit "Copied the $label export to the clipboard — paste directly into the portal."
exit 0
