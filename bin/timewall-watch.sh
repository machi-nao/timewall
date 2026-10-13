#!/bin/bash
~/.local/bin/timewall.py
stdbuf -oL dbus-monitor --session "type='signal',sender='org.kde.KWin',path='/VirtualDesktopManager'" 2>/dev/null |
while read -r line; do
  case "$line" in
    *member=currentChanged*|*member=PropertiesChanged*) ~/.local/bin/timewall.py ;;
  esac
done
