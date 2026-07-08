#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=ue_env.sh
source "$SCRIPT_DIR/ue_env.sh"

ddc_arg=("-ddc=NoZenLocalFallback")
for arg in "$@"; do
  if [[ "$arg" == -ddc=* ]]; then
    ddc_arg=()
    break
  fi
done

exec env HOME="$UE_USER_HOME" "$ENG" "$@" "${ddc_arg[@]}"
