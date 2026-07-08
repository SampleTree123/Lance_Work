#!/usr/bin/env bash
set -euo pipefail

exec >"${HOME:-/tmp}/.vnc/xstartup.log" 2>&1
echo "xstartup pid=$$ display=${DISPLAY:-unset}"

xsetroot -solid '#202020' || true
xterm -fa Monospace -fs 10 -geometry 120x36+20+20 -title "DataMake TurboVNC" &

wait
