#!/bin/bash
# TimeWall backup:  ./backup.sh [--with-images] [output-dir]
set -e
WITH_IMAGES=0
[ "$1" = "--with-images" ] && { WITH_IMAGES=1; shift; }
OUT="${1:-$HOME/Backups}"
mkdir -p "$OUT"
FILE="$OUT/timewall-$(date +%Y%m%d-%H%M).tar.gz"

FILES=()
for f in "$HOME"/.local/bin/timewall* \
         "$HOME/.config/timewall.json" \
         "$HOME"/.config/systemd/user/timewall* \
         "$HOME/.local/share/applications/timewall-settings.desktop" \
         "$HOME/.local/share/icons/timewall.svg"; do
  case "$f" in *.bak*|*~) continue ;; esac
  [ -e "$f" ] && FILES+=("$f")
done
if [ "$WITH_IMAGES" = 1 ] && [ -d "$HOME/Pictures/wp" ]; then
  FILES+=("$HOME/Pictures/wp")
fi

tar czf "$FILE" "${FILES[@]}"
echo "saved: $FILE"
echo "restore: tar xzf $FILE -C /   then: systemctl --user daemon-reload"
