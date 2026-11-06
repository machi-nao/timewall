#!/bin/bash
# TimeWall installer (user level, no sudo needed)
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin"
UNIT="$HOME/.config/systemd/user"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons"
CFG="$HOME/.config/timewall.json"

pkgs=""
python3 -c "import astral" 2>/dev/null || pkgs="$pkgs python-astral"
python3 -c "import PIL" 2>/dev/null || pkgs="$pkgs python-pillow"
python3 -c "import PyQt6" 2>/dev/null || pkgs="$pkgs python-pyqt6"
if [ -n "$pkgs" ]; then
  echo "Missing Python packages:$pkgs"
  echo "On Arch: sudo pacman -S$pkgs"
  exit 1
fi
command -v qdbus6 >/dev/null || { echo "qdbus6 (Qt6 tools) is required."; exit 1; }

mkdir -p "$BIN" "$UNIT" "$APPS" "$ICONS"

if [ -e "$CFG" ]; then
  BAK="$CFG.bak-$(date +%Y%m%d-%H%M%S)"
  cp -p "$CFG" "$BAK"
  echo "Existing settings backed up: $BAK"
fi

install -b -m 755 "$SRC/bin/timewall.py" "$SRC/bin/timewall-watch.sh" "$SRC/bin/timewall-settings.py" "$BIN/"
install -b -m 644 "$SRC"/systemd/* "$UNIT/"
install -b -m 644 "$SRC/desktop/timewall.svg" "$ICONS/"

cat > "$APPS/timewall-settings.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=TimeWall
Comment=Per-desktop wallpaper scheduler
Exec=$BIN/timewall-settings.py
Icon=$ICONS/timewall.svg
Terminal=false
Categories=Settings;DesktopSettings;
DESK

[ -e "$CFG" ] || cp "$SRC/examples/timewall.json" "$CFG"

for i in 1 2 3 4 5 6 7 8; do
  mkdir -p "$HOME/Pictures/wp/desktop$i" "$HOME/Pictures/wp/desktop$i-slideshow"
done
mkdir -p "$HOME/Videos/aerial"

systemctl --user daemon-reload
systemctl --user enable --now timewall.timer timewall-watch.service
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true

echo "Done. Put your images in ~/Pictures/wp/desktopN/ and open TimeWall to choose a mode."
echo "Optional (pearOS NiceC0re only): Aerial lock screen video, see extras/aerial-lockscreen/ and the README."
