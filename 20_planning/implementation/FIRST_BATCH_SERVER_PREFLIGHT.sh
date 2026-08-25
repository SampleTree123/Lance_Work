#!/usr/bin/env bash

# First-batch Linux/NVIDIA server preflight for datatry_02.
#
# This script is read-only with respect to the Unreal project. It writes only to
# REPORT_ROOT. It validates the server environment first, then validates the
# project and performs two UE 5.8 Vulkan offscreen startup smoke tests when an
# .uproject is supplied.
#
# Full run:
#   UE_EDITOR=/opt/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor \
#   UPROJECT=/data/datatry_02/datatry_02.uproject \
#   bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh
#
# Environment-only run before the project is uploaded:
#   bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh --environment-only
#
# Optional overrides:
#   REPORT_ROOT=/data/reports/server_preflight_001
#   EXPECTED_SLURM_JOB_ID=113764
#   VULKAN_EVIDENCE_LOG=/data/logs/ue_vulkan_probe.log
#   MIN_STEP_CPUS=8
#   MIN_FREE_GB=100
#   UE_TIMEOUT_SEC=1800
#
# Exit codes:
#   0 = PASS or PASS_WITH_WARNINGS
#   2 = PARTIAL_ENVIRONMENT_ONLY (project checks were not run)
#   3 = FAIL

set -uo pipefail

ENVIRONMENT_ONLY=0
POSITIONAL=()
while (( $# > 0 )); do
  case "$1" in
    -h|--help)
      sed -n '1,35p' "$0"
      exit 0
      ;;
    --environment-only)
      ENVIRONMENT_ONLY=1
      shift
      ;;
    --)
      shift
      POSITIONAL+=("$@")
      break
      ;;
    -*)
      printf 'Unknown option: %s\n' "$1" >&2
      exit 64
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DATAMAKE_ROOT="${DATAMAKE_ROOT:-}"
if [[ -z "$DATAMAKE_ROOT" && -d "$SCRIPT_DIR/00_engine" ]]; then
  DATAMAKE_ROOT="$SCRIPT_DIR"
elif [[ -z "$DATAMAKE_ROOT" && -d "$SCRIPT_DIR/../../00_engine" ]]; then
  DATAMAKE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
fi

EXPECTED_UE_VERSION="${EXPECTED_UE_VERSION:-5.8}"
EXPECTED_PROJECT_NAME="${EXPECTED_PROJECT_NAME:-datatry_02}"
EXPECTED_RL_PLUGIN_VERSION="${EXPECTED_RL_PLUGIN_VERSION:-2.03}"
EXPECTED_SLURM_JOB_ID="${EXPECTED_SLURM_JOB_ID:-}"
VULKAN_EVIDENCE_LOG="${VULKAN_EVIDENCE_LOG:-}"
MIN_STEP_CPUS="${MIN_STEP_CPUS:-8}"
MIN_FREE_GB="${MIN_FREE_GB:-100}"
UE_TIMEOUT_SEC="${UE_TIMEOUT_SEC:-1800}"

DEFAULT_UE_EDITOR=""
if [[ -n "$DATAMAKE_ROOT" ]]; then
  DEFAULT_UE_EDITOR="$DATAMAKE_ROOT/00_engine/unreal/UE_5.8/Engine/Binaries/Linux/UnrealEditor"
fi

UE_EDITOR="${UE_EDITOR:-${POSITIONAL[0]:-$DEFAULT_UE_EDITOR}}"
UPROJECT="${UPROJECT:-${POSITIONAL[1]:-}}"
if (( ENVIRONMENT_ONLY == 1 )); then
  UPROJECT=""
fi
STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_BASE="${HOME:-$PWD}"
if [[ -n "$DATAMAKE_ROOT" ]]; then
  REPORT_BASE="$DATAMAKE_ROOT/00_engine/outputs/server_preflight"
fi
REPORT_ROOT="${REPORT_ROOT:-${POSITIONAL[2]:-$REPORT_BASE/${HOSTNAME:-host}_$STAMP}}"

UE_RUNTIME_LIB_DIR="${UE_RUNTIME_LIB_DIR:-}"
if [[ -z "$UE_RUNTIME_LIB_DIR" && -n "$DATAMAKE_ROOT" ]]; then
  UE_RUNTIME_LIB_DIR="$DATAMAKE_ROOT/00_engine/runtime/ubuntu2204-libs/usr/lib/x86_64-linux-gnu"
fi
if [[ -d "$UE_RUNTIME_LIB_DIR" ]]; then
  export LD_LIBRARY_PATH="$UE_RUNTIME_LIB_DIR:${LD_LIBRARY_PATH:-}"
fi

mkdir -p "$REPORT_ROOT"/{system,project,logs,temp,outputs}
STATUS_TSV="$REPORT_ROOT/status.tsv"
SUMMARY_MD="$REPORT_ROOT/preflight_summary.md"
printf 'check_id\tstatus\tdetail\n' > "$STATUS_TSV"
printf 'datamake_root=%s\nue_runtime_lib_dir=%s\nld_library_path=%s\n' \
  "${DATAMAKE_ROOT:-NOT_FOUND}" \
  "${UE_RUNTIME_LIB_DIR:-NOT_SET}" \
  "${LD_LIBRARY_PATH:-}" \
  > "$REPORT_ROOT/system/runtime_environment.txt"

FAIL_COUNT=0
WARN_COUNT=0
NOT_RUN_COUNT=0

record() {
  local check_id="$1"
  local status="$2"
  local detail="$3"
  detail="${detail//$'\t'/ }"
  detail="${detail//$'\n'/ }"
  printf '%s\t%s\t%s\n' "$check_id" "$status" "$detail" >> "$STATUS_TSV"
  case "$status" in
    FAIL) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    WARN) WARN_COUNT=$((WARN_COUNT + 1)) ;;
    NOT_RUN) NOT_RUN_COUNT=$((NOT_RUN_COUNT + 1)) ;;
  esac
  printf '[%s] %-8s %s\n' "$check_id" "$status" "$detail"
}

capture() {
  local output_file="$1"
  shift
  "$@" > "$output_file" 2>&1
}

echo "Report root: $REPORT_ROOT"
echo "Started: $(date --iso-8601=seconds)"

# SVR-00: Preserve and, when requested, enforce the exact Slurm allocation.
{
  printf 'SLURM_JOB_ID=%s\n' "${SLURM_JOB_ID:-}"
  printf 'SLURM_JOB_NODELIST=%s\n' "${SLURM_JOB_NODELIST:-}"
  printf 'SLURM_STEP_ID=%s\n' "${SLURM_STEP_ID:-}"
  printf 'SLURM_STEP_GPUS=%s\n' "${SLURM_STEP_GPUS:-}"
  printf 'SLURM_CPUS_PER_TASK=%s\n' "${SLURM_CPUS_PER_TASK:-}"
  printf 'SLURM_CPUS_ON_NODE=%s\n' "${SLURM_CPUS_ON_NODE:-}"
  printf 'SLURM_MEM_PER_NODE=%s\n' "${SLURM_MEM_PER_NODE:-}"
  printf 'CUDA_VISIBLE_DEVICES=%s\n' "${CUDA_VISIBLE_DEVICES:-}"
  printf 'visible_cpus=%s\n' "$(nproc 2>/dev/null || printf 'unknown')"
} > "$REPORT_ROOT/system/slurm_environment.txt"

if [[ -n "$EXPECTED_SLURM_JOB_ID" ]]; then
  if [[ "${SLURM_JOB_ID:-}" == "$EXPECTED_SLURM_JOB_ID" ]]; then
    record SVR-00 PASS "Running inside the requested Slurm job $EXPECTED_SLURM_JOB_ID on ${SLURM_JOB_NODELIST:-unknown-node}."
  else
    record SVR-00 FAIL "Expected Slurm job $EXPECTED_SLURM_JOB_ID, found ${SLURM_JOB_ID:-none}."
  fi
elif [[ -n "${SLURM_JOB_ID:-}" ]]; then
  record SVR-00 PASS "Running inside Slurm job $SLURM_JOB_ID on ${SLURM_JOB_NODELIST:-unknown-node}."
else
  record SVR-00 WARN "Not running inside a Slurm allocation; GPU/render conclusions are not authoritative."
fi

VISIBLE_CPUS="$(nproc 2>/dev/null || printf '0')"
if [[ -n "${SLURM_JOB_ID:-}" ]]; then
  if [[ "$VISIBLE_CPUS" =~ ^[0-9]+$ ]] && (( VISIBLE_CPUS >= MIN_STEP_CPUS )); then
    record SVR-00A PASS "The Slurm step exposes $VISIBLE_CPUS CPUs; minimum requested for UE preflight is $MIN_STEP_CPUS."
  else
    record SVR-00A WARN "The Slurm step exposes only ${VISIBLE_CPUS:-unknown} CPUs; launch UE with --cpus-per-task at least $MIN_STEP_CPUS."
  fi
else
  record SVR-00A NOT_RUN "Slurm step CPU affinity was not evaluated outside an allocation."
fi

# SVR-01: Host inventory. This is evidence, not a performance benchmark.
capture "$REPORT_ROOT/system/uname.txt" uname -a
UNAME_CODE=$?
if [[ -r /etc/os-release ]]; then
  cp /etc/os-release "$REPORT_ROOT/system/os-release.txt"
else
  printf 'Missing /etc/os-release\n' > "$REPORT_ROOT/system/os-release.txt"
fi
command -v lscpu >/dev/null 2>&1 && capture "$REPORT_ROOT/system/lscpu.txt" lscpu
command -v free >/dev/null 2>&1 && capture "$REPORT_ROOT/system/memory.txt" free -h
capture "$REPORT_ROOT/system/filesystems.txt" df -hT
bash -lc 'ulimit -a' > "$REPORT_ROOT/system/ulimit.txt" 2>&1
if [[ $UNAME_CODE -eq 0 && -r /etc/os-release ]]; then
  record SVR-01 PASS "Linux host inventory captured."
else
  record SVR-01 FAIL "Could not capture a complete Linux host inventory."
fi

# SVR-02: NVIDIA driver, GPU visibility, and VRAM.
NVIDIA_READY=0
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L > "$REPORT_ROOT/system/nvidia_gpu_list.txt" 2>&1
  NVIDIA_LIST_CODE=$?
  nvidia-smi \
    --query-gpu=index,name,uuid,driver_version,memory.total,memory.free,temperature.gpu \
    --format=csv,noheader \
    > "$REPORT_ROOT/system/nvidia_gpu_query.csv" 2>&1
  NVIDIA_QUERY_CODE=$?
  nvidia-smi > "$REPORT_ROOT/system/nvidia_smi.txt" 2>&1
  if [[ $NVIDIA_LIST_CODE -eq 0 && $NVIDIA_QUERY_CODE -eq 0 && -s "$REPORT_ROOT/system/nvidia_gpu_query.csv" ]]; then
    record SVR-02 PASS "NVIDIA GPU, driver, VRAM, and temperature are visible."
    NVIDIA_READY=1
  else
    record SVR-02 FAIL "nvidia-smi exists but GPU inventory failed."
  fi
else
  printf 'nvidia-smi not found\n' > "$REPORT_ROOT/system/nvidia_smi.txt"
  record SVR-02 FAIL "nvidia-smi is not installed or not on PATH."
fi

# SVR-03: Vulkan must work independently of nvidia-smi.
VULKAN_PROVISIONAL=0
if command -v vulkaninfo >/dev/null 2>&1; then
  if command -v timeout >/dev/null 2>&1; then
    timeout 120 vulkaninfo --summary > "$REPORT_ROOT/system/vulkan_summary.txt" 2>&1
  else
    vulkaninfo --summary > "$REPORT_ROOT/system/vulkan_summary.txt" 2>&1
  fi
  VULKAN_CODE=$?
  if [[ $VULKAN_CODE -eq 0 ]] && grep -Eqi 'deviceName|GPU[[:space:]]|VkPhysicalDevice' "$REPORT_ROOT/system/vulkan_summary.txt"; then
    record SVR-03 PASS "Vulkan enumerated a physical GPU."
    VULKAN_READY=1
  else
    record SVR-03 FAIL "vulkaninfo could not enumerate a physical GPU."
    VULKAN_READY=0
  fi
else
  printf 'vulkaninfo not found\n' > "$REPORT_ROOT/system/vulkan_summary.txt"
  if [[ -n "$VULKAN_EVIDENCE_LOG" && -r "$VULKAN_EVIDENCE_LOG" ]]; then
    printf 'source_log=%s\n' "$VULKAN_EVIDENCE_LOG" > "$REPORT_ROOT/system/vulkan_evidence_log.txt"
    sha256sum "$VULKAN_EVIDENCE_LOG" > "$REPORT_ROOT/system/vulkan_evidence_log.sha256" 2>/dev/null || true
    if grep -aEqi 'rhiname=.Vulkan|LogVulkanRHI' "$VULKAN_EVIDENCE_LOG" \
      && grep -aq 'NVIDIA H200' "$VULKAN_EVIDENCE_LOG" \
      && grep -aq 'DATAMAKE_UE_PYTHON_SMOKE_OK' "$VULKAN_EVIDENCE_LOG" \
      && ! grep -aEqi 'Fatal error|Assertion failed|Segmentation fault|Out of video memory' "$VULKAN_EVIDENCE_LOG"; then
      record SVR-03 PASS "vulkaninfo is unavailable; supplied UE log proves Vulkan/H200 initialization and clean Python smoke completion."
      VULKAN_READY=1
    else
      record SVR-03 FAIL "The supplied VULKAN_EVIDENCE_LOG does not satisfy the Vulkan/H200 smoke contract."
      VULKAN_READY=0
    fi
  elif [[ -n "$VULKAN_EVIDENCE_LOG" ]]; then
    record SVR-03 FAIL "VULKAN_EVIDENCE_LOG is not readable: $VULKAN_EVIDENCE_LOG"
    VULKAN_READY=0
  elif (( NVIDIA_READY == 1 )); then
    record SVR-03 WARN "vulkaninfo is unavailable; Vulkan proof is deferred to the UE -vulkan project smoke log."
    VULKAN_READY=1
    VULKAN_PROVISIONAL=1
  else
    record SVR-03 NOT_RUN "vulkaninfo is unavailable and no NVIDIA GPU is visible on this node."
    VULKAN_READY=0
  fi
fi

# SVR-04: Exact UE binary, version, and shared-library closure.
UE_READY=0
if [[ -z "$UE_EDITOR" ]]; then
  record SVR-04 FAIL "UE_EDITOR is empty. Point it to Engine/Binaries/Linux/UnrealEditor."
elif [[ ! -x "$UE_EDITOR" ]]; then
  record SVR-04 FAIL "UE_EDITOR is not an executable file: $UE_EDITOR"
else
  UE_ENGINE_DIR="$(cd "$(dirname "$UE_EDITOR")/../.." && pwd -P)"
  UE_BUILD_VERSION="$UE_ENGINE_DIR/Build/Build.version"
  UE_VERSION_CODE=1
  if [[ -r "$UE_BUILD_VERSION" ]] && command -v python3 >/dev/null 2>&1; then
    python3 - "$UE_BUILD_VERSION" > "$REPORT_ROOT/system/unreal_version.txt" 2>&1 <<'PY'
import json
import pathlib
import sys

data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
print(f"{data['MajorVersion']}.{data['MinorVersion']}.{data['PatchVersion']}")
print(f"changelist={data.get('Changelist', '')}")
print(f"branch={data.get('BranchName', '')}")
PY
    UE_VERSION_CODE=$?
  elif command -v timeout >/dev/null 2>&1; then
    timeout 120 "$UE_EDITOR" -version > "$REPORT_ROOT/system/unreal_version.txt" 2>&1
    UE_VERSION_CODE=$?
  else
    "$UE_EDITOR" -version > "$REPORT_ROOT/system/unreal_version.txt" 2>&1
    UE_VERSION_CODE=$?
  fi

  LDD_CODE=0
  if command -v ldd >/dev/null 2>&1; then
    ldd "$UE_EDITOR" > "$REPORT_ROOT/system/unreal_ldd.txt" 2>&1
    LDD_CODE=$?
    grep -F 'not found' "$REPORT_ROOT/system/unreal_ldd.txt" > "$REPORT_ROOT/system/unreal_missing_libraries.txt" || true
  else
    printf 'ldd not found\n' > "$REPORT_ROOT/system/unreal_ldd.txt"
    : > "$REPORT_ROOT/system/unreal_missing_libraries.txt"
    LDD_CODE=127
  fi

  if [[ $UE_VERSION_CODE -ne 0 ]]; then
    record SVR-04 FAIL "UnrealEditor -version exited with code $UE_VERSION_CODE."
  elif ! grep -Eq "${EXPECTED_UE_VERSION//./\\.}([. -]|$)" "$REPORT_ROOT/system/unreal_version.txt"; then
    record SVR-04 FAIL "Unreal version output does not contain expected version $EXPECTED_UE_VERSION."
  elif [[ $LDD_CODE -ne 0 ]]; then
    record SVR-04 FAIL "Could not inspect UnrealEditor shared-library dependencies with ldd."
  elif [[ -s "$REPORT_ROOT/system/unreal_missing_libraries.txt" ]]; then
    record SVR-04 FAIL "UnrealEditor has unresolved shared-library dependencies."
  else
    record SVR-04 PASS "UnrealEditor $EXPECTED_UE_VERSION manifest and shared-library closure passed."
    UE_READY=1
  fi
fi

# SVR-05: Report/output roots and provisional disk headroom.
WRITE_TEST="$REPORT_ROOT/temp/write_test_$STAMP"
if printf 'write-ok\n' > "$WRITE_TEST" && rm -f "$WRITE_TEST"; then
  df -Pk "$REPORT_ROOT" > "$REPORT_ROOT/system/report_root_disk_kb.txt" 2>&1
  FREE_KB="$(df -Pk "$REPORT_ROOT" | awk 'NR==2 {print $4}')"
  FREE_GB=$((FREE_KB / 1024 / 1024))
  if (( FREE_GB < MIN_FREE_GB )); then
    record SVR-05 WARN "Roots are writable, but only ${FREE_GB} GiB is free; provisional target is ${MIN_FREE_GB} GiB before the 10-node size benchmark."
  else
    record SVR-05 PASS "Roots are writable and ${FREE_GB} GiB is free."
  fi
else
  record SVR-05 FAIL "REPORT_ROOT is not writable: $REPORT_ROOT"
fi

PROJECT_READY=0
PROJECT_ROOT=""

if [[ -z "$UPROJECT" ]]; then
  record SVR-06 NOT_RUN "UPROJECT was not supplied; environment-only validation completed."
  record SVR-07 NOT_RUN "Project plugin policy was not checked."
  record SVR-08 NOT_RUN "First UE project offscreen smoke was not run."
  record SVR-09 NOT_RUN "Repeat UE project offscreen smoke was not run."
elif [[ ! -f "$UPROJECT" ]]; then
  record SVR-06 FAIL "UPROJECT does not exist: $UPROJECT"
  record SVR-07 NOT_RUN "Project plugin policy was not checked."
  record SVR-08 NOT_RUN "First UE project offscreen smoke was not run."
  record SVR-09 NOT_RUN "Repeat UE project offscreen smoke was not run."
else
  PROJECT_ROOT="$(cd "$(dirname "$UPROJECT")" && pwd -P)"
  printf '%s\n' "$PROJECT_ROOT" > "$REPORT_ROOT/project/project_root.txt"
  sha256sum "$UPROJECT" > "$REPORT_ROOT/project/uproject.sha256"

  PROJECT_PARSE_OK=0
  PROJECT_ENGINE=""
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$UPROJECT" > "$REPORT_ROOT/project/uproject_summary.txt" 2>&1 <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8-sig"))
print(f"project={path.stem}")
print(f"engine_association={data.get('EngineAssociation', '')}")
for plugin in data.get("Plugins", []):
    print(f"plugin={plugin.get('Name')} enabled={plugin.get('Enabled')}")
PY
    PROJECT_PARSE_OK=$?
    if [[ $PROJECT_PARSE_OK -eq 0 ]]; then
      PROJECT_ENGINE="$(grep '^engine_association=' "$REPORT_ROOT/project/uproject_summary.txt" | cut -d= -f2-)"
    fi
  else
    printf 'python3 not found; .uproject JSON was not parsed\n' > "$REPORT_ROOT/project/uproject_summary.txt"
  fi

  MISSING_PROJECT_PATHS=0
  for required_path in \
    "$PROJECT_ROOT/Config" \
    "$PROJECT_ROOT/Content/DataMake" \
    "$PROJECT_ROOT/Content/CC_Shaders"; do
    if [[ ! -e "$required_path" ]]; then
      printf 'MISSING %s\n' "$required_path" >> "$REPORT_ROOT/project/missing_required_paths.txt"
      MISSING_PROJECT_PATHS=$((MISSING_PROJECT_PATHS + 1))
    fi
  done
  : > "${REPORT_ROOT}/project/missing_required_paths.txt.tmp"
  rm -f "${REPORT_ROOT}/project/missing_required_paths.txt.tmp"

  find "$PROJECT_ROOT" -type f -printf '%P\n' 2>/dev/null \
    | LC_ALL=C sort -f \
    | uniq -di \
    > "$REPORT_ROOT/project/case_collisions.txt"

  SCAN_TARGETS=("$UPROJECT")
  [[ -d "$PROJECT_ROOT/Config" ]] && SCAN_TARGETS+=("$PROJECT_ROOT/Config")
  [[ -d "$PROJECT_ROOT/DataMake" ]] && SCAN_TARGETS+=("$PROJECT_ROOT/DataMake")
  grep -RInE --binary-files=without-match '([A-Za-z]:\\|[A-Za-z]:/)' "${SCAN_TARGETS[@]}" \
    > "$REPORT_ROOT/project/windows_absolute_paths.txt" 2>/dev/null || true

  if [[ $PROJECT_PARSE_OK -ne 0 ]]; then
    record SVR-06 FAIL "The .uproject file is not valid readable JSON."
  elif [[ "$(basename "$UPROJECT" .uproject)" != "$EXPECTED_PROJECT_NAME" ]]; then
    record SVR-06 FAIL "Expected project $EXPECTED_PROJECT_NAME, found $(basename "$UPROJECT" .uproject)."
  elif [[ -n "$PROJECT_ENGINE" && "$PROJECT_ENGINE" != "$EXPECTED_UE_VERSION" ]]; then
    record SVR-06 FAIL "Project EngineAssociation is $PROJECT_ENGINE, expected $EXPECTED_UE_VERSION."
  elif (( MISSING_PROJECT_PATHS > 0 )); then
    record SVR-06 FAIL "Required project paths are missing; inspect project/missing_required_paths.txt."
  elif [[ -s "$REPORT_ROOT/project/case_collisions.txt" ]]; then
    record SVR-06 FAIL "Case-insensitive path collisions were found; inspect project/case_collisions.txt."
  elif [[ -s "$REPORT_ROOT/project/windows_absolute_paths.txt" ]]; then
    record SVR-06 WARN "Windows absolute paths were found in runtime text inputs; review project/windows_absolute_paths.txt before rendering."
    PROJECT_READY=1
  else
    record SVR-06 PASS "Project identity, required paths, and case-collision scan passed."
    PROJECT_READY=1
  fi

  # Reallusion Auto Setup 2.03 is an import-time Windows editor plugin. Its
  # local descriptor allows Win64 only. The Linux bundle should retain
  # Content/CC_Shaders but normally omit Plugins/RLPlugin.
  RL_DESCRIPTOR="$PROJECT_ROOT/Plugins/RLPlugin/RLPlugin.uplugin"
  if [[ -f "$RL_DESCRIPTOR" ]]; then
    cp "$RL_DESCRIPTOR" "$REPORT_ROOT/project/RLPlugin.uplugin"
    RL_VERSION=""
    RL_ALLOW_LIST=""
    if command -v python3 >/dev/null 2>&1; then
      RL_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8-sig")).get("VersionName", ""))' "$RL_DESCRIPTOR" 2>/dev/null || true)"
      RL_ALLOW_LIST="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8-sig")); print(",".join(d.get("Modules", [{}])[0].get("PlatformAllowList", [])))' "$RL_DESCRIPTOR" 2>/dev/null || true)"
    fi
    if [[ "$RL_VERSION" != "$EXPECTED_RL_PLUGIN_VERSION" || "$RL_ALLOW_LIST" != *Win64* ]]; then
      record SVR-07 FAIL "Unexpected RLPlugin descriptor; expected Auto Setup $EXPECTED_RL_PLUGIN_VERSION with Win64-only module."
      PROJECT_READY=0
    else
      record SVR-07 WARN "RLPlugin $RL_VERSION is present but Win64-only. Omit Plugins/RLPlugin from the Linux production bundle; keep Content/CC_Shaders. The smoke log must contain no plugin-load failure."
    fi
  else
    record SVR-07 PASS "Windows-only RLPlugin is absent from the Linux bundle; CC_Shaders remains present."
  fi

  if [[ -d "$PROJECT_ROOT" ]]; then
    df -hT "$PROJECT_ROOT" > "$REPORT_ROOT/project/project_root_disk.txt" 2>&1
  fi

  run_ue_smoke() {
    local run_id="$1"
    local check_id="$2"
    local ue_log="$REPORT_ROOT/logs/${run_id}_ue.log"
    local stdout_log="$REPORT_ROOT/logs/${run_id}_stdout.log"
    local fatal_log="$REPORT_ROOT/logs/${run_id}_fatal_matches.txt"
    local suspect_log="$REPORT_ROOT/logs/${run_id}_suspect_messages.txt"
    local vulkan_log="$REPORT_ROOT/logs/${run_id}_vulkan_evidence.txt"
    local timing_file="$REPORT_ROOT/logs/${run_id}_timing.txt"
    local start_epoch end_epoch code elapsed

    start_epoch="$(date +%s)"
    timeout "${UE_TIMEOUT_SEC}s" \
      "$UE_EDITOR" "$UPROJECT" \
      -Unattended \
      -NoSplash \
      -NoSound \
      -NoP4 \
      -RenderOffscreen \
      -vulkan \
      -stdout \
      -FullStdOutLogOutput \
      "-AbsLog=$ue_log" \
      "-ExecCmds=Quit" \
      > "$stdout_log" 2>&1
    code=$?
    end_epoch="$(date +%s)"
    elapsed=$((end_epoch - start_epoch))
    printf 'exit_code=%s\nelapsed_seconds=%s\n' "$code" "$elapsed" > "$timing_file"

    cat "$stdout_log" "$ue_log" 2>/dev/null \
      | grep -Eini 'Fatal error|Assertion failed|Unhandled Exception|Out of video memory|Out of memory|LogPluginManager: Error|Plugin .+ failed to load|Missing or incompatible module|LogVulkanRHI: Error|Failed to initialize Vulkan|Cannot find a compatible Vulkan device|Segmentation fault' \
      > "$fatal_log" || true

    cat "$stdout_log" "$ue_log" 2>/dev/null \
      | grep -Eini 'warning|error|failed|missing' \
      | sed -n '1,1000p' \
      > "$suspect_log" || true

    cat "$stdout_log" "$ue_log" 2>/dev/null \
      | grep -Eini 'LogVulkanRHI|RHI[^[:alnum:]]*Vulkan|rhiname=.Vulkan|Vulkan.*NVIDIA' \
      > "$vulkan_log" || true

    if [[ $code -ne 0 ]]; then
      record "$check_id" FAIL "$run_id exited with code $code after ${elapsed}s."
      return 1
    elif [[ -s "$fatal_log" ]]; then
      record "$check_id" FAIL "$run_id logged a fatal/plugin/Vulkan failure; inspect $fatal_log."
      return 1
    elif (( VULKAN_PROVISIONAL == 1 )) && [[ ! -s "$vulkan_log" ]]; then
      record "$check_id" FAIL "$run_id completed but did not log positive Vulkan evidence."
      return 1
    else
      record "$check_id" PASS "$run_id completed in ${elapsed}s with exit code 0 and no fatal signature."
      return 0
    fi
  }

  if [[ $UE_READY -eq 1 && $VULKAN_READY -eq 1 && $PROJECT_READY -eq 1 ]] && command -v timeout >/dev/null 2>&1; then
    if run_ue_smoke run_01_cold SVR-08; then
      run_ue_smoke run_02_repeat SVR-09 || true
    else
      record SVR-09 NOT_RUN "Repeat smoke was skipped because the first project launch failed."
    fi
  else
    record SVR-08 NOT_RUN "Prerequisites failed or timeout is unavailable; UE project smoke was not run."
    record SVR-09 NOT_RUN "Repeat UE project smoke was not run."
  fi
fi

record SVR-10 PASS "Structured report files were generated under $REPORT_ROOT."

if (( FAIL_COUNT > 0 )); then
  VERDICT="FAIL"
  EXIT_CODE=3
elif (( NOT_RUN_COUNT > 0 )); then
  VERDICT="PARTIAL_ENVIRONMENT_ONLY"
  EXIT_CODE=2
elif (( WARN_COUNT > 0 )); then
  VERDICT="PASS_WITH_WARNINGS"
  EXIT_CODE=0
else
  VERDICT="PASS"
  EXIT_CODE=0
fi

{
  echo "# First-Batch Server Preflight Result"
  echo
  echo "- Timestamp: $(date --iso-8601=seconds)"
  echo "- Verdict: \`$VERDICT\`"
  echo "- Host: \`$(hostname)\`"
  echo "- Slurm job: \`${SLURM_JOB_ID:-NOT_SET}\`"
  echo "- Slurm node: \`${SLURM_JOB_NODELIST:-NOT_SET}\`"
  echo "- CUDA visible devices: \`${CUDA_VISIBLE_DEVICES:-NOT_SET}\`"
  echo "- Visible step CPUs: \`${VISIBLE_CPUS:-NOT_SET}\`"
  echo "- Expected UE: \`$EXPECTED_UE_VERSION\`"
  echo "- UE editor: \`${UE_EDITOR:-NOT_SET}\`"
  echo "- Project: \`${UPROJECT:-NOT_SET}\`"
  echo "- Report root: \`$REPORT_ROOT\`"
  echo
  echo "## Checks"
  echo
  echo '```tsv'
  cat "$STATUS_TSV"
  echo '```'
  echo
  echo "## Interpretation"
  echo
  echo "- \`PASS\`: Day-1 server preflight passed."
  echo "- \`PASS_WITH_WARNINGS\`: no hard failure, but every WARN must be reviewed before the 10-node benchmark."
  echo "- \`PARTIAL_ENVIRONMENT_ONLY\`: hardware/UE checks ran, but project/plugin/offscreen checks did not all run."
  echo "- \`FAIL\`: stop; do not start project upload validation or batch rendering until the failing checks are fixed."
  echo
  echo "This preflight does not approve production rendering. It does not replace the later asset gate, local full-chain smoke, or 10-node render benchmark."
} > "$SUMMARY_MD"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$0" > "$REPORT_ROOT/preflight_script.sha256" 2>/dev/null || true
fi

echo
echo "Final verdict: $VERDICT"
echo "Summary: $SUMMARY_MD"
echo "Return the complete report directory for review."
exit "$EXIT_CODE"
