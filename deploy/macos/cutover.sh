#!/bin/bash
# Cutover: the laptop's single collection DB becomes the hosted server's data (docs/home-server.md
# § Cutover). Three phases, each non-interactive; the sign-in between phases 2 and 3 is yours.
#
#   On the LAPTOP (this repo's main checkout, your real DB):
#     deploy/macos/cutover.sh prepare --to DIR --yes
#        refuses while the laptop app (com.magic-manager.serve) is loaded — stop it first;
#        snapshot (db/bak, label pre-cutover) → mm db split --to DIR (verified) → private permissions.
#        Then copy DIR to the mini (the command is printed).
#
#   On the MINI (after deploy/macos/install.sh --apply):
#     deploy/macos/cutover.sh install-data
#        checks the copied catalog.db + users/owner.db (schema = this code), WAL on, 0700/0600,
#        starts the app, prints an ADMIN invite link. Open it and sign in (Discord/Google).
#     deploy/macos/cutover.sh finish --user <your id from: mm-hosted auth users>
#        stops the app, mm auth bind (owner.db becomes yours), starts Litestream, waits until the
#        replica restores equal to live (mm host verify-replica), uploads the first catalog
#        snapshot, starts the app + auto-deploy + weekly backup.
#
# Rollback: docs/home-server.md § Rollback. Nothing here deletes data.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$(cd "$HERE/../.." && pwd)"
die() { echo "cutover: $*" >&2; exit 2; }
phase="${1:-}"; shift || true

kit() {  # the installed kit (mini phases)
  KIT="${MM_KIT:-$HOME/Library/Application Support/magic-manager-hosted}"
  [ -r "$KIT/hosted.env" ] || die "no $KIT/hosted.env — run deploy/macos/install.sh --apply first"
  # shellcheck source=/dev/null
  . "$KIT/hosted.env"
}
health() {
  for _ in $(seq 1 45); do
    sleep 2
    curl -sf -o /dev/null "http://127.0.0.1:$MM_PORT/api/features" && return 0
  done
  return 1
}

case "$phase" in
prepare)
  to=""; yes=no
  while [ $# -gt 0 ]; do
    case "$1" in --to) to="${2:?}"; shift ;; --yes) yes=yes ;; *) die "unknown option $1" ;; esac
    shift
  done
  [ -n "$to" ] || die "prepare needs --to DIR (a new directory)"
  [ "$yes" = yes ] || die "prepare reads your real DB and takes a snapshot of it — pass --yes once you've OK'd the cutover"
  if launchctl print "gui/$(id -u)/com.magic-manager.serve" >/dev/null 2>&1; then
    die "the laptop app (com.magic-manager.serve) is running — stop it first so nothing is written after the split:
  launchctl bootout gui/$(id -u)/com.magic-manager.deploy; launchctl bootout gui/$(id -u)/com.magic-manager.serve"
  fi
  if [ -e "$to" ] && [ -n "$(ls -A "$to" 2>/dev/null)" ]; then die "$to isn't empty"; fi
  cd "$APP" || exit 1
  echo "1/3 snapshot of the single DB"
  uv run --frozen mm db snapshot --label pre-cutover || die "snapshot failed — nothing else was done"
  echo "2/3 split → $to"
  uv run --frozen mm db split --to "$to" || die "split failed or didn't verify — nothing was written to $to"
  echo "3/3 private permissions"
  uv run --frozen mm host permissions --data-dir "$to" --apply
  echo
  echo "Ready. Copy it to the mini (Tailscale), e.g.:"
  echo "  rsync -a --chmod=D700,F600 \"$to/\" <mini>:magic-manager/data/"
  echo "Keep the laptop app stopped (or point it at a pulled copy: mm db pull) — the mini is the source of truth from now on."
  ;;
install-data)
  kit
  { [ -f "$MM_DATA_DIR/catalog.db" ] && [ -f "$MM_DATA_DIR/users/owner.db" ]; } \
    || die "copy the split first: $MM_DATA_DIR needs catalog.db + users/owner.db"
  [ -e "$MM_DATA_DIR/auth.db" ] && die "$MM_DATA_DIR/auth.db exists — install-data already ran; next: finish --user <id>"
  "$KIT/mm-hosted" host deploy-check --ref HEAD --repo "$MM_APP" \
    || die "the copied files aren't at this code's schema version — check out the same commit on both machines"
  "$KIT/mm-hosted" host wal --apply || die "couldn't turn on WAL"
  "$KIT/mm-hosted" host permissions --apply >/dev/null
  "$KIT/mmctl" start serve
  health || die "the app didn't come up — see $MM_LOGS/serve.log"
  echo "The app is up. Sign in as the admin with this single-use link (Discord or Google):"
  "$KIT/mm-hosted" auth invite --admin --expires 1d
  echo "Then: $KIT/mm-hosted auth users   (your id)   and:   deploy/macos/cutover.sh finish --user <id>"
  ;;
finish)
  kit
  user=""
  while [ $# -gt 0 ]; do
    case "$1" in --user) user="${2:?}"; shift ;; *) die "unknown option $1" ;; esac
    shift
  done
  [[ "$user" =~ ^[a-z0-9]{16}$ ]] || die "finish needs --user <16-character id> (mm-hosted auth users)"
  "$KIT/mmctl" stop serve
  sleep 2
  if [ -f "$MM_DATA_DIR/users/$user.db" ] && [ ! -e "$MM_DATA_DIR/users/owner.db" ]; then
    echo "already bound (users/owner.db is now users/$user.db) — continuing"   # a re-run after a later step failed
  else
    "$KIT/mm-hosted" auth bind --user "$user" || die "bind failed — the app is stopped; fix and re-run finish"
  fi
  "$KIT/mm-hosted" host wal --apply >/dev/null || die "couldn't turn on WAL"
  "$KIT/mm-hosted" host permissions --apply >/dev/null
  "$KIT/mmctl" start litestream
  ok=no
  for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
    sleep 10
    if "$KIT/mm-hosted" host verify-replica; then ok=yes; break; fi
    echo "  (replica not complete yet — try $i/12)"
  done
  [ "$ok" = yes ] || die "the offsite replica didn't verify — see $MM_LOGS/litestream.log; the app stays stopped"
  "$KIT/mm-hosted" host catalog-backup || die "the first catalog backup failed — see the error; the app stays stopped"
  "$KIT/mmctl" start serve deploy catalog-backup
  health || die "the app didn't come up — see $MM_LOGS/serve.log"
  echo
  echo "CUTOVER DONE. Record your id for upgrades:"
  echo "  deploy/macos/install.sh --apply --origin $MM_PUBLIC_ORIGIN --owner-id $user"
  ;;
*)
  sed -n '2,24p' "$0"
  exit 2
  ;;
esac
