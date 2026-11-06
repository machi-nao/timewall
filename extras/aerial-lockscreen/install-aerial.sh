#!/bin/bash
# Install the Aerial (video) lock screen patch for pearOS NiceC0re
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="${LOCKSCREEN_DIR:-/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen}"
TARGET="$DIR/LockScreenUi.qml"

if [ "$(id -u)" = 0 ]; then
  echo "Run this as your normal user (it asks for sudo only when needed)."
  exit 1
fi

install_watcher() {
  [ -z "$LOCKSCREEN_DIR" ] || return 0
  mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"
  install -m 755 "$HERE/aerial-lockframe-watcher.sh" "$HOME/.local/bin/"
  install -m 644 "$HERE/aerial-lockframe-watcher.service" "$HOME/.config/systemd/user/"
  systemctl --user daemon-reload
  if pgrep -f lock-chime-watcher.py >/dev/null 2>&1; then
    echo "A lock chime watcher is running and already hands over the frame."
    echo "The frame watcher was installed but not enabled."
  else
    systemctl --user enable --now aerial-lockframe-watcher.service
    echo "Frame watcher enabled (keeps the frozen lock screen frame after unlock)."
  fi
}

command -v patch >/dev/null || { echo "patch is required: sudo pacman -S patch"; exit 1; }
[ -f "$TARGET" ] || { echo "Not found: $TARGET"; exit 1; }

if grep -q "aerialPlayer" "$TARGET"; then
  echo "Aerial is already installed in $TARGET"
  install_watcher
  exit 0
fi

want="$(cat "$HERE/BASE.sha256")"
have="$(sha256sum "$TARGET" | cut -d' ' -f1)"
if [ "$want" != "$have" ]; then
  echo "Your lock screen file is different from the one this patch was made for."
  echo "Aerial was NOT installed (nothing was changed)."
  echo "  expected: $want"
  echo "  found:    $have"
  exit 1
fi

TMPD="$(mktemp -d)"
if ! sed "s#@HOME@#$HOME#g" "$HERE/LockScreenUi.qml.patch" | patch -s -o "$TMPD/new.qml" "$TARGET"; then
  rm -rf "$TMPD"
  echo "The patch did not apply. Nothing was changed."
  exit 1
fi

SUDO=""
[ -w "$DIR" ] || SUDO="sudo"
BAK="$TARGET.pre-aerial"
[ -e "$BAK" ] && BAK="$TARGET.pre-aerial-$(date +%Y%m%d-%H%M%S)"
$SUDO cp -p "$TARGET" "$BAK"
$SUDO install -m 644 "$TMPD/new.qml" "$TARGET"
rm -rf "$TMPD"

mkdir -p "$HOME/.cache/aerial" "$HOME/Videos/aerial"
echo "Aerial installed. Backup: $BAK"
install_watcher
echo "Put videos in ~/Videos/aerial and choose one in TimeWall. Lock the screen to test."
echo "After a plasma-desktop update, run this script again."
