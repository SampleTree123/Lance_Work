#!/usr/bin/env bash
# Source this file before running Unreal Engine commands from this workspace.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
export DATAMAKE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"

export UE_ROOT="$DATAMAKE_ROOT/00_engine/unreal/UE_5.8"
export ENG="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"

export UE_USER_HOME="$DATAMAKE_ROOT/00_engine/cache/ue_home"
export UE_LocalDataCachePath="$DATAMAKE_ROOT/00_engine/cache/ddc"
export TMPDIR="$DATAMAKE_ROOT/00_engine/cache/tmp"

export UE_RUNTIME_LIB_DIR="$DATAMAKE_ROOT/00_engine/runtime/ubuntu2204-libs/usr/lib/x86_64-linux-gnu"
if [[ -d "$UE_RUNTIME_LIB_DIR" ]]; then
  export LD_LIBRARY_PATH="$UE_RUNTIME_LIB_DIR:${LD_LIBRARY_PATH:-}"
fi

mkdir -p "$UE_USER_HOME" "$UE_LocalDataCachePath" "$TMPDIR" "$DATAMAKE_ROOT/00_engine/logs"
