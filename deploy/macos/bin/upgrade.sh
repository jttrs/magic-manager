#!/bin/bash
# The owner's explicit database upgrade for the hosted server (deploy.sh only holds).
#
#   upgrade.sh            rehearse: origin/main's code upgrades COPIES of catalog.db + your file
#                         (scripts/post_merge_upgrade.py; nothing live changes)
#   upgrade.sh --apply    (only the commit the last rehearsal passed on)
#                         stop the app, deploy it, pair-snapshot catalog + your file,
#                         upgrade + verify them, start the app (its start-up migrates every other
#                         user's file, each snapshotted first)
#
# Needs MM_OWNER_ID (your user id, set by install.sh --owner-id). Never prompts.
# shellcheck source=deploy/macos/bin/common.sh
. "$(dirname "$0")/common.sh"
apply=no
case "${1:-}" in
  "") ;;
  --apply) apply=yes ;;
  *) echo "usage: upgrade.sh [--apply]" >&2; exit 2 ;;
esac
if [ -z "${MM_OWNER_ID:-}" ]; then
  echo "MM_OWNER_ID isn't set — re-run install.sh --apply --owner-id <your user id> (mm-hosted auth users)" >&2
  exit 2
fi
take_lock || { echo "a deploy is running — try again in a minute" >&2; exit 1; }
cd "$MM_APP" || exit 1
git fetch -q origin main || { echo "git fetch failed" >&2; exit 1; }
new=$(git rev-parse origin/main); cur=$(git rev-parse HEAD)

if [ "$apply" = no ]; then
  wt="$MM_KIT/upgrade-rehearsal"
  rm -rf "$wt"; git worktree prune
  git worktree add -q --detach "$wt" "$new" || exit 1
  trap 'git -C "$MM_APP" worktree remove --force "$wt" >/dev/null 2>&1; rmdir "$MM_KIT/deploy.lock" 2>/dev/null' EXIT
  (cd "$wt" && uv sync -q --frozen && uv run --frozen python scripts/post_merge_upgrade.py \
     --layout split --data-dir "$MM_DATA_DIR" --user "$MM_OWNER_ID")
  rc=$?
  echo
  if [ "$rc" -eq 0 ]; then
    echo "$new" > "$MM_KIT/rehearsed"
    echo "REHEARSAL OK for ${new:0:7}. Apply with: $MM_KIT/upgrade.sh --apply"
  else
    rm -f "$MM_KIT/rehearsed"
    echo "REHEARSAL FAILED (exit $rc) — don't apply; nothing live was changed."
  fi
  exit "$rc"
fi

if [ "$(cat "$MM_KIT/rehearsed" 2>/dev/null)" != "$new" ]; then
  echo "origin/main (${new:0:7}) isn't the commit the last rehearsal passed on — run upgrade.sh (no --apply) first" >&2
  exit 2
fi
log "upgrade ${cur:0:7} → ${new:0:7} (apply)"
"$MM_KIT/mmctl" stop serve deploy
git checkout -q --detach "$new" || exit 1
uv sync -q --frozen || { echo "uv sync failed; still stopped at ${new:0:7} — check out ${cur:0:7} to go back" >&2; exit 1; }
if ! { npm --prefix web ci --silent && npm --prefix web run build; } >/dev/null 2>&1; then
  echo "web build failed; the app is stopped" >&2; exit 1
fi
if ! uv run --frozen python scripts/post_merge_upgrade.py --layout split --data-dir "$MM_DATA_DIR" \
       --user "$MM_OWNER_ID" --apply; then
  echo "UPGRADE FAILED — the app stays stopped. To go back: $MM_KIT/mmctl stop litestream, restore the pair" >&2
  echo "snapshot it printed (mm-hosted db restore …), git checkout ${cur:0:7}, then: $MM_KIT/mmctl start" >&2
  notify "Database upgrade failed — the app is stopped"
  exit 1
fi
"$MM_KIT/mmctl" start serve deploy
"$MM_KIT/mmctl" restart litestream
log "upgraded to ${new:0:7}"
notify "Upgraded to ${new:0:7}"
