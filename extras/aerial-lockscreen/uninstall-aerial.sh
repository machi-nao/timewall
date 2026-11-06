#!/bin/bash
# Restore the lock screen file from the backup made by install-aerial.sh
set -e
DIR="${LOCKSCREEN_DIR:-/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen}"
TARGET="$DIR/LockScreenUi.qml"

if [ "$(id -u)" = 0 ]; then
  echo "Run this as your normal user (it asks for sudo only when needed)."
  exit 1
fi
BAK="$(ls -1 "$TARGET".pre-aerial* 2>/dev/null | sort | head -1)"
if [ -z "$BAK" ]; then
  echo "No backup found ($TARGET.pre-aerial*). Nothing was changed."
  exit 1
fi
SUDO=""
[ -w "$DIR" ] || SUDO="sudo"
$SUDO install -m 644 "$BAK" "$TARGET"
echo "Restored from $BAK"

if [ -z "$LOCKSCREEN_DIR" ]; then
  systemctl --user disable --now aerial-lockframe-watcher.service 2>/dev/null || true
  rm -f "$HOME/.config/systemd/user/aerial-lockframe-watcher.service" "$HOME/.local/bin/aerial-lockframe-watcher.sh"
  systemctl --user daemon-reload
fi
