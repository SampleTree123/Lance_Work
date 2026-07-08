#!/usr/bin/env bash
set -euo pipefail

ROOT="/scratch/prj0000000275/jcy/xks/DataMake"
RD_ROOT="$ROOT/00_engine/remote_desktop"
PROJECT="$ROOT/00_engine/projects/MVPProject/MVPProject.uproject"
UE_BIN="$ROOT/00_engine/unreal/UE_5.8/Engine/Binaries/Linux/UnrealEditor"

if [[ -z "${DISPLAY:-}" ]]; then
  echo "DISPLAY is not set. Start Xvnc first, then run: export DISPLAY=:97" >&2
  exit 2
fi

source "$ROOT/00_engine/scripts/ue_env.sh"

export HOME="$RD_ROOT/home"
export PATH="$RD_ROOT/runtime-tools/usr/bin:$RD_ROOT/turbovnc-3.3/opt/TurboVNC/bin:$PATH"
export LD_LIBRARY_PATH="$RD_ROOT/runtime-libs/usr/lib/x86_64-linux-gnu:$ROOT/00_engine/runtime/ubuntu2204-libs/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"

mkdir -p "$ROOT/00_engine/logs"

UE_LOG="$ROOT/00_engine/logs/ue_editor_existing_display_${DISPLAY#:}_$(date +%Y%m%d_%H%M%S).log"

echo "Starting UE Editor on DISPLAY=$DISPLAY"
echo "UE log: $UE_LOG"

exec "$UE_BIN" "$PROJECT" \
  -nosplash \
  -nop4 \
  -stdout \
  -FullStdOutLogOutput \
  -NoSound \
  -NoCrashDialog \
  -ddc=NoZenLocalFallback \
  "-ini:Engine:[ConsoleVariables]:r.WarnOfBadDrivers=0" \
  "$@" \
  >"$UE_LOG" 2>&1
