#!/usr/bin/env bash
set -euo pipefail

ROOT="/scratch/prj0000000275/jcy/xks/DataMake"
RD_ROOT="$ROOT/00_engine/remote_desktop"
TVNC="$RD_ROOT/turbovnc-3.3/opt/TurboVNC"
DISPLAY_NUM="${1:-97}"
GEOMETRY="${GEOMETRY:-1600x900}"
DEPTH="${DEPTH:-24}"
RFB_PORT="${RFB_PORT:-$((5900 + DISPLAY_NUM))}"

export HOME="$RD_ROOT/home"
export PATH="$RD_ROOT/runtime-tools/usr/bin:$TVNC/bin:$PATH"
export LD_LIBRARY_PATH="$RD_ROOT/runtime-libs/usr/lib/x86_64-linux-gnu:$ROOT/00_engine/runtime/ubuntu2204-libs/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"

mkdir -p "$RD_ROOT/logs" "$HOME/.vnc"

"$TVNC/bin/Xvnc" ":$DISPLAY_NUM" \
  -geometry "$GEOMETRY" \
  -depth "$DEPTH" \
  -localhost \
  -securitytypes None \
  -rfbport "$RFB_PORT" \
  >"$RD_ROOT/logs/xvnc-${DISPLAY_NUM}.log" 2>&1 &

XVNC_PID=$!

cleanup() {
  kill "$XVNC_PID" >/dev/null 2>&1 || true
  wait "$XVNC_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

sleep 2

DISPLAY=":$DISPLAY_NUM" xterm -fa Monospace -fs 10 -geometry 120x36+20+20 -title "DataMake TurboVNC direct" &

echo "Xvnc started on display :$DISPLAY_NUM, VNC localhost port $RFB_PORT"
echo "Log: $RD_ROOT/logs/xvnc-${DISPLAY_NUM}.log"
echo "Keep this process running while using the desktop. Press Ctrl-C to stop it."

wait "$XVNC_PID"
