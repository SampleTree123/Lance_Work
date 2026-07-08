#!/usr/bin/env bash
set -euo pipefail

ROOT="/scratch/prj0000000275/jcy/xks/DataMake"
RD_ROOT="$ROOT/00_engine/remote_desktop"
TVNC="$RD_ROOT/turbovnc-3.3/opt/TurboVNC"
DISPLAY_NUM="${1:-97}"
GEOMETRY="${GEOMETRY:-1920x1080}"
DEPTH="${DEPTH:-24}"
RFB_PORT="${RFB_PORT:-$((5900 + DISPLAY_NUM))}"
PROJECT="$ROOT/00_engine/projects/MVPProject/MVPProject.uproject"
UE_BIN="$ROOT/00_engine/unreal/UE_5.8/Engine/Binaries/Linux/UnrealEditor"

source "$ROOT/00_engine/scripts/ue_env.sh"

export HOME="$RD_ROOT/home"
export PATH="$RD_ROOT/runtime-tools/usr/bin:$TVNC/bin:$PATH"
export LD_LIBRARY_PATH="$RD_ROOT/runtime-libs/usr/lib/x86_64-linux-gnu:$ROOT/00_engine/runtime/ubuntu2204-libs/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"

mkdir -p "$RD_ROOT/logs" "$HOME/.vnc" "$ROOT/00_engine/logs"

"$TVNC/bin/Xvnc" ":$DISPLAY_NUM" \
  -geometry "$GEOMETRY" \
  -depth "$DEPTH" \
  -localhost \
  -securitytypes None \
  -rfbport "$RFB_PORT" \
  >"$RD_ROOT/logs/xvnc-${DISPLAY_NUM}-ue-editor.log" 2>&1 &

XVNC_PID=$!

cleanup() {
  kill "$XVNC_PID" >/dev/null 2>&1 || true
  wait "$XVNC_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

sleep 2

DISPLAY=":$DISPLAY_NUM" xterm -fa Monospace -fs 10 -geometry 120x36+20+20 -title "DataMake UE Shell" &

UE_LOG="$ROOT/00_engine/logs/ue_editor_xvnc_${DISPLAY_NUM}_$(date +%Y%m%d_%H%M%S).log"

echo "Xvnc started on display :$DISPLAY_NUM, VNC localhost port $RFB_PORT"
echo "UE log: $UE_LOG"
echo "Connect through an SSH tunnel, then open VNC viewer at localhost:$RFB_PORT."
echo "Keep this process running. Press Ctrl-C here to stop UE and Xvnc."

DISPLAY=":$DISPLAY_NUM" "$UE_BIN" "$PROJECT" \
  -nosplash \
  -nop4 \
  -stdout \
  -FullStdOutLogOutput \
  -NoSound \
  -ddc=NoZenLocalFallback \
  "-ini:Engine:[ConsoleVariables]:r.WarnOfBadDrivers=0" \
  >"$UE_LOG" 2>&1
