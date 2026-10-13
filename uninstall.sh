#!/bin/bash
# TimeWall uninstaller. Your images and ~/.config/timewall.json are kept unless you ask.
#   ./uninstall.sh            remove the program only
#   ./uninstall.sh --purge    also remove ~/.config/timewall.json
set -e
systemctl --user disable --now timewall.timer timewall-watch.service 2>/dev/null || true
rm -f "$HOME"/.config/systemd/user/timewall.service \
      "$HOME"/.config/systemd/user/timewall.timer \
      "$HOME"/.config/systemd/user/timewall-watch.service
systemctl --user daemon-reload
rm -f "$HOME"/.local/bin/timewall.py "$HOME"/.local/bin/timewall-watch.sh \
      "$HOME"/.local/bin/timewall-settings.py
rm -f "$HOME"/.local/share/applications/timewall-settings.desktop \
      "$HOME"/.local/share/icons/timewall.svg
rm -rf "$HOME"/.cache/timewall
[ "$1" = "--purge" ] && rm -f "$HOME"/.config/timewall.json
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true
echo "TimeWall removed. Your images in ~/Pictures/wp were not touched."

