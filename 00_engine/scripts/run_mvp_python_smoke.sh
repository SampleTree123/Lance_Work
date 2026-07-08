#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=ue_env.sh
source "$SCRIPT_DIR/ue_env.sh"

mode="${1:-nullrhi}"
case "$mode" in
  nullrhi)
    rhi_args=(-NullRHI)
    ;;
  renderoffscreen)
    rhi_args=(-RenderOffscreen -graphicsadapter=0 -ResX=640 -ResY=360 -ForceRes)
    ;;
  *)
    echo "Usage: $0 [nullrhi|renderoffscreen]" >&2
    exit 2
    ;;
esac

project="$DATAMAKE_ROOT/00_engine/projects/MVPProject/MVPProject.uproject"
script="$DATAMAKE_ROOT/00_engine/projects/MVPProject/Scripts/smoke_python.py"
timestamp="$(date +%Y%m%d_%H%M%S)"
log="$DATAMAKE_ROOT/00_engine/logs/mvpproject_python_smoke_${mode}_${timestamp}.log"
timeout_seconds="${UE_SMOKE_TIMEOUT_SECONDS:-300}"

echo "log=$log"
timeout "${timeout_seconds}s" "$SCRIPT_DIR/run_ue_cmd.sh" "$project" \
  -run=pythonscript \
  -script="$script" \
  "${rhi_args[@]}" \
  -Unattended \
  -NoSplash \
  -NoSound \
  -NoSourceControl \
  -NoCrashDialog \
  -stdout \
  -FullStdOutLogOutput \
  >"$log" 2>&1

status=$?
echo "status=$status"
rg -n "DATAMAKE_|rhiname=|gpu=|NVIDIA H200|Python script executed successfully|Fatal|Error|Assertion failed|LogExit: Exiting|Engine exit requested|LogDerivedDataCache: Local|ZenLocal" "$log" | tail -n 120 || true
exit "$status"
