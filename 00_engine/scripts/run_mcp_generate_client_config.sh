#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DATAMAKE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
PROJECT="$DATAMAKE_ROOT/00_engine/projects/MVPProject/MVPProject.uproject"
PY_SCRIPT="$DATAMAKE_ROOT/00_engine/projects/MVPProject/Scripts/generate_mcp_client_config.py"

"$SCRIPT_DIR/run_ue_cmd.sh" "$PROJECT" \
  -run=pythonscript \
  -script="$PY_SCRIPT" \
  -NullRHI \
  "-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False" \
  -unattended \
  -nop4 \
  -nosplash \
  -stdout \
  -FullStdOutLogOutput
