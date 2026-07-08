#!/usr/bin/env bash
set -euo pipefail

ROOT="/scratch/prj0000000275/jcy/xks/DataMake"
RD_ROOT="$ROOT/00_engine/remote_desktop"
TVNC="$RD_ROOT/turbovnc-3.3/opt/TurboVNC"
DISPLAY_NUM="${1:-97}"

export HOME="$RD_ROOT/home"
export PATH="$RD_ROOT/runtime-tools/usr/bin:$TVNC/bin:$PATH"
export LD_LIBRARY_PATH="$RD_ROOT/runtime-libs/usr/lib/x86_64-linux-gnu:$ROOT/00_engine/runtime/ubuntu2204-libs/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"

exec "$TVNC/bin/vncserver" -kill ":$DISPLAY_NUM"
