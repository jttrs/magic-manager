#!/bin/bash
# Installs the hosted magic-manager on a Mac (the home server, docs/home-server.md).
#
#   deploy/macos/install.sh [options]            dry run (default): show what would be installed
#   deploy/macos/install.sh --apply [options]    install / update (idempotent; re-run after the kit changes)
#
# Options (defaults in brackets):
#   --app DIR          the app checkout, a git clone of the repo   [the checkout this script is in]
#   --data DIR         the hosted data dir                         [$HOME/magic-manager/data]
#   --origin URL       MM_PUBLIC_ORIGIN, e.g. https://mini.tailnet.ts.net  (required)
#   --port N           the app's local port (127.0.0.1 only)       [8765]
#   --owner-id ID      your hosted user id (after `mm auth bind`)  [unset; upgrade.sh needs it]
#   --trusted-proxy P  MM_TRUSTED_PROXY: tailscale | cloudflare — the proxy in front whose
#                      client-IP header the rate limits trust      [unset: trust no header]
#   --kit DIR          where the wrapper scripts + Litestream go   [$HOME/Library/Application Support/magic-manager-hosted]
#   --logs DIR         log dir                                     [$HOME/Library/Logs/magic-manager-hosted]
#   --launch-agents DIR                                            [$HOME/Library/LaunchAgents]
#
# What it does with --apply: installs Litestream v$LITESTREAM_VERSION (pinned, SHA-256 checked) into the
# kit dir; imports GitHub's web-flow signing key (deploy/macos/web-flow.gpg, a copy of
# https://github.com/web-flow.gpg; fingerprint pinned in bin/common.sh) into the kit's own GnuPG keyring,
# so deploys accept only commits GitHub made (needs `gpg`: brew install gnupg); copies the wrapper
# scripts there, writes hosted.env (non-secret settings, 0600) and four launchd agents
# (com.magic-manager.hosted.{serve,litestream,deploy,catalog-backup}); makes the data dir (0700) and
# the checkout's .env private (0600); reloads agents that are already running. It doesn't
# start an agent for the first time (the cutover does: docs/home-server.md; launchd loads them at the next
# login, and each refuses to run until the cutover step it needs is done), never creates or changes a
# database, never deletes anything, never touches other launchd agents (e.g. com.magic-manager.serve),
# and never reads or prints a secret. Non-interactive.
set -euo pipefail

LITESTREAM_VERSION=0.5.17
SHA_darwin_arm64=e211f68ff7658d19f193f2914417afdf8f89a053ff8f263e5d6b3b1d3bbc7b08
SHA_darwin_x86_64=891875af09db152e93a4b31a8a79f538ce7ce702c132803cfe0a831e7cb1b7db
SERVICES="serve litestream deploy catalog-backup"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$(cd "$HERE/../.." && pwd)"
DATA="$HOME/magic-manager/data"
ORIGIN=""
PORT=8765
OWNER_ID=""
TRUSTED_PROXY=""
KIT="$HOME/Library/Application Support/magic-manager-hosted"
LOGS="$HOME/Library/Logs/magic-manager-hosted"
AGENTS="$HOME/Library/LaunchAgents"
APPLY=no

die() { echo "install.sh: $*" >&2; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) APPLY=yes ;;
    --dry-run) APPLY=no ;;
    --app) APP="${2:?}"; shift ;;
    --data) DATA="${2:?}"; shift ;;
    --origin) ORIGIN="${2:?}"; shift ;;
    --port) PORT="${2:?}"; shift ;;
    --owner-id) OWNER_ID="${2:?}"; shift ;;
    --trusted-proxy) TRUSTED_PROXY="${2?}"; shift ;;
    --kit) KIT="${2:?}"; shift ;;
    --logs) LOGS="${2:?}"; shift ;;
    --launch-agents) AGENTS="${2:?}"; shift ;;
    -h|--help) sed -n '2,29p' "$0"; exit 0 ;;
    *) die "unknown option $1 (see --help)" ;;
  esac
  shift
done

# ---- validate (refuse anything that could break a plist or a shell line) ----
for v in "$APP" "$DATA" "$KIT" "$LOGS" "$AGENTS"; do
  case "$v" in /*) ;; *) die "paths must be absolute: $v" ;; esac
  case "$v" in *[\&\<\>\"\'\$\`\\]*|*$'\n'*) die "unsupported character in path: $v" ;; esac
done
[ -n "$ORIGIN" ] || die "--origin is required (MM_PUBLIC_ORIGIN, e.g. https://<mini>.<tailnet>.ts.net)"
[[ "$ORIGIN" =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?$ || "$ORIGIN" =~ ^http://(localhost|127\.0\.0\.1)(:[0-9]+)?$ ]] \
  || die "--origin must be https://<host>[:port] (http only for localhost)"
{ [[ "$PORT" =~ ^[0-9]{2,5}$ ]] && [ "$PORT" -ge 1024 ] && [ "$PORT" -le 65535 ]; } || die "--port must be 1024-65535"
[ -z "$OWNER_ID" ] || [[ "$OWNER_ID" =~ ^[a-z0-9]{16}$ ]] || die "--owner-id must be a 16-character user id"
[ -z "$TRUSTED_PROXY" ] || [[ "$TRUSTED_PROXY" =~ ^(tailscale|cloudflare)$ ]] || die "--trusted-proxy must be tailscale or cloudflare"
[ -d "$APP/.git" ] || [ -f "$APP/.git" ] || die "$APP isn't a git checkout of the app"
[ -f "$APP/src/magic_manager/offsite.py" ] || die "$APP isn't the magic-manager app"
case "$DATA/" in "$APP"/*) die "keep the data dir outside the app checkout" ;; esac

arch=$(uname -m); [ "$arch" = arm64 ] || arch=x86_64
case "$arch" in arm64) LS_SHA="$SHA_darwin_arm64" ;; *) LS_SHA="$SHA_darwin_x86_64" ;; esac
LS_BIN="$KIT/bin/litestream"
WEBFLOW_FPR=$(sed -n 's/^MM_WEBFLOW_FPR=//p' "$HERE/bin/common.sh")
[[ "$WEBFLOW_FPR" =~ ^[0-9A-F]{40}$ ]] || die "bin/common.sh has no pinned MM_WEBFLOW_FPR"
KEYRING="$KIT/gnupg"
has_webflow() { GNUPGHOME="$1" gpg --batch --with-colons --fingerprint 2>/dev/null | grep -q "^fpr:::::::::$WEBFLOW_FPR:"; }

# ---- render ----
render_env() {
  printf '# Rendered by deploy/macos/install.sh — non-secret settings only (secrets: %s/.env).\n' "$APP"
  printf 'export %s=%q\n' \
    PATH "/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
    MM_APP "$APP" MM_KIT "$KIT" MM_LOGS "$LOGS" MM_LAUNCH_AGENTS "$AGENTS" \
    MM_MODE hosted MM_LAYOUT split MM_DATA_DIR "$DATA" MM_PUBLIC_ORIGIN "$ORIGIN" MM_PORT "$PORT" \
    MM_ANALYTICS_DB "$DATA/analytics.db" MM_LITESTREAM "$LS_BIN" MM_OWNER_ID "$OWNER_ID" \
    MM_TRUSTED_PROXY "$TRUSTED_PROXY"
}
render_plist() { sed -e "s|@KIT@|$KIT|g" -e "s|@LOGS@|$LOGS|g" "$HERE/launchd/$1.plist.in"; }

changes=0
plan() { # plan <target> <content-file>   (nothing is written)
  if [ ! -f "$1" ]; then echo "  + $1 (new)"; changes=$((changes+1))
  elif ! cmp -s "$1" "$2"; then echo "  ~ $1 (changed)"; changes=$((changes+1))
  else echo "  = $1"; fi
}

echo "magic-manager hosted install — $([ "$APPLY" = yes ] && echo APPLY || echo 'dry run (pass --apply)')"
echo "  app: $APP    data: $DATA    origin: $ORIGIN    port: 127.0.0.1:$PORT"
echo "files:"
plan "$KIT/hosted.env" <(render_env)
for f in "$HERE"/bin/*; do plan "$KIT/$(basename "$f")" "$f"; done
for s in $SERVICES; do plan "$AGENTS/com.magic-manager.hosted.$s.plist" <(render_plist "$s"); done
have_ls=$("$LS_BIN" version 2>/dev/null || true)
if [ "$have_ls" = "$LITESTREAM_VERSION" ]; then echo "  = $LS_BIN (v$LITESTREAM_VERSION)"
else echo "  + $LS_BIN (Litestream v$LITESTREAM_VERSION darwin-$arch, sha256 ${LS_SHA:0:12}…)"; changes=$((changes+1)); fi
[ -d "$DATA" ] && echo "  = $DATA/ (data dir)" || echo "  + $DATA/ (data dir, 0700, empty)"
if command -v gpg >/dev/null 2>&1 && [ -d "$KEYRING" ] && has_webflow "$KEYRING"; then echo "  = $KEYRING (GitHub web-flow key ${WEBFLOW_FPR:24})"
else echo "  + $KEYRING (GitHub web-flow key ${WEBFLOW_FPR:24}, from deploy/macos/web-flow.gpg)"; changes=$((changes+1)); fi
command -v gpg >/dev/null 2>&1 || echo "  ! gpg isn't installed — brew install gnupg (deploys verify each commit's GitHub signature)"
if [ -f "$APP/.env" ]; then
  mode=$(stat -f %Lp "$APP/.env" 2>/dev/null || stat -c %a "$APP/.env")
  [ "$mode" = 600 ] && echo "  = $APP/.env (0600)" || echo "  ~ $APP/.env (mode $mode → 0600)"
else
  echo "  ! $APP/.env is missing — put the OAuth + offsite secrets there (docs/home-server.md § Secrets)"
fi

if [ "$APPLY" = no ]; then
  echo
  echo "--- hosted.env (no secrets) ---"; render_env
  echo "$changes change(s). Dry run — nothing was written."
  exit 0
fi

[ "$(uname -s)" = Darwin ] || die "--apply needs macOS (deploy/linux is not built yet)"
command -v gpg >/dev/null 2>&1 || die "install GnuPG first (brew install gnupg): deploys verify GitHub's signature on each commit"
umask 077
mkdir -p "$KIT/bin" "$LOGS" "$AGENTS"
chmod 700 "$KIT" "$LOGS"
if [ ! -d "$DATA" ]; then mkdir -p "$DATA"; fi
chmod 700 "$DATA"
if [ -f "$APP/.env" ]; then chmod 600 "$APP/.env"; fi
stage="$KIT/.install-stage"
rm -rf "$stage"; mkdir -p "$stage"
trap 'rm -rf "$stage"' EXIT
render_env > "$stage/hosted.env"
for s in $SERVICES; do render_plist "$s" > "$stage/$s.plist"; done

if [ "$have_ls" != "$LITESTREAM_VERSION" ]; then
  tgz="$stage/litestream.tar.gz"
  url="https://github.com/benbjohnson/litestream/releases/download/v$LITESTREAM_VERSION/litestream-$LITESTREAM_VERSION-darwin-$arch.tar.gz"
  curl -fsSL --proto '=https' -o "$tgz" "$url"
  echo "$LS_SHA  $tgz" | shasum -a 256 -c - >/dev/null || die "Litestream download failed its SHA-256 check — not installed"
  tar -xzf "$tgz" -C "$stage" litestream
  install -m 0755 "$stage/litestream" "$LS_BIN"
  [ "$("$LS_BIN" version)" = "$LITESTREAM_VERSION" ] || die "installed Litestream doesn't report v$LITESTREAM_VERSION"
fi

if ! { [ -d "$KEYRING" ] && has_webflow "$KEYRING"; }; then
  mkdir -m 700 "$stage/gnupg"
  GNUPGHOME="$stage/gnupg" gpg --batch --quiet --import "$HERE/web-flow.gpg" 2>/dev/null || true
  has_webflow "$stage/gnupg" || die "deploy/macos/web-flow.gpg doesn't hold the pinned key $WEBFLOW_FPR — not installed"
  rm -rf "$KEYRING"; mv "$stage/gnupg" "$KEYRING"; chmod 700 "$KEYRING"
fi
install -m 0600 "$stage/hosted.env" "$KIT/hosted.env"
for f in "$HERE"/bin/*; do install -m 0700 "$f" "$KIT/$(basename "$f")"; done
domain="gui/$(id -u)"
for s in $SERVICES; do
  label="com.magic-manager.hosted.$s"
  dest="$AGENTS/$label.plist"
  if ! cmp -s "$stage/$s.plist" "$dest" 2>/dev/null; then
    install -m 0644 "$stage/$s.plist" "$dest"
    plutil -lint "$dest" >/dev/null || die "rendered $dest isn't a valid plist"
    if [ -z "${MM_INSTALL_NO_LAUNCHCTL:-}" ] && launchctl print "$domain/$label" >/dev/null 2>&1; then
      launchctl bootout "$domain/$label" || true
      launchctl bootstrap "$domain" "$dest"
      echo "reloaded $label"
    fi
  fi
done
echo "installed. Next: docs/home-server.md § Cutover (\"$KIT/mmctl\" status shows the agents)."
