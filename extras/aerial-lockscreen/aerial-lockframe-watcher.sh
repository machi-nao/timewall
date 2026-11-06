#!/bin/bash
# TimeWall + Aerial: after unlock, hand the frozen lock screen frame over to the wallpaper
LOCKFRAME="$HOME/.cache/lockframe.png"
TW="$HOME/.local/bin/timewall.py"
expect=0
last_v=""
last_t=0

handle() {
  local v="$1" now
  now=$(date +%s%N)
  # KDE sends this signal twice (two object paths); ignore the repeat
  if [ "$v" = "$last_v" ] && [ $(( (now - last_t) / 1000000 )) -lt 1500 ]; then
    return
  fi
  last_v="$v"
  last_t="$now"
  if [ "$v" = true ]; then
    rm -f "$LOCKFRAME"
    [ -n "$AERIAL_DEBUG" ] && echo "locked: old frame removed"
  else
    [ -n "$AERIAL_DEBUG" ] && echo "unlocked: handing over the frame"
    ( sleep 0.8; "$TW" --lockframe ) &
  fi
}

stdbuf -oL dbus-monitor --session "type='signal',interface='org.freedesktop.ScreenSaver',member='ActiveChanged'" 2>/dev/null |
while read -r line; do
  case "$line" in
    *member=ActiveChanged*) expect=1 ;;
    *"boolean true"*)  [ "$expect" = 1 ] && { expect=0; handle true; } ;;
    *"boolean false"*) [ "$expect" = 1 ] && { expect=0; handle false; } ;;
  esac
done
