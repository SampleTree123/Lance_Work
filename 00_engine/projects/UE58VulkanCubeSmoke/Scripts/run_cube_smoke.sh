#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"
DATAMAKE_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -P)"

UE_ROOT="${UE_ROOT:-$DATAMAKE_ROOT/00_engine/unreal/UE_5.8}"
UE_EDITOR="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"
RUN_UAT="$UE_ROOT/Engine/Build/BatchFiles/RunUAT.sh"
UPROJECT="$PROJECT_DIR/UE58VulkanCubeSmoke.uproject"
MAP_SCRIPT="$SCRIPT_DIR/create_cube_smoke_map.py"
MAP_PATH="${MAP_PATH:-${DM_CUBE_SMOKE_MAP_PATH:-/Game/Maps/L_UE58_Vulkan_Cube_Smoke}}"
RUNTIME_LIB_DIR="$DATAMAKE_ROOT/00_engine/runtime/ubuntu2204-libs/usr/lib/x86_64-linux-gnu"
VULKANINFO="$DATAMAKE_ROOT/00_engine/runtime/vulkan-tools-1.3.204/usr/bin/vulkaninfo"
NVIDIA_ICD="${NVIDIA_ICD:-/etc/vulkan/icd.d/nvidia_icd.json}"

RUN_ID="${RUN_ID:-job${SLURM_JOB_ID:-noslurm}_$(date +%Y%m%d_%H%M%S)}"
RUN_ROOT="${RUN_ROOT:-$DATAMAKE_ROOT/00_engine/outputs/server_preflight/ue58_vulkan_cube_smoke/$RUN_ID}"
STAGE="${1:-help}"
RENDER_ATTEMPTS="${RENDER_ATTEMPTS:-1}"
RENDER_START_INDEX="${RENDER_START_INDEX:-1}"
RENDER_CAPTURE="${RENDER_CAPTURE:-1}"
RENDER_VALIDATION="${RENDER_VALIDATION:-0}"
RENDER_GPU_CRASH_DEBUGGING="${RENDER_GPU_CRASH_DEBUGGING:-0}"
RENDER_RHI_VALIDATION="${RENDER_RHI_VALIDATION:-0}"
RENDER_VULKAN_STALL_DUMP_SECONDS="${RENDER_VULKAN_STALL_DUMP_SECONDS:-0}"
RENDER_EXEC_COMMANDS="${RENDER_EXEC_COMMANDS:-viewmode unlit}"
RENDER_SHOWFLAG_DIRECT_LIGHTING="${RENDER_SHOWFLAG_DIRECT_LIGHTING:-2}"
RENDER_SHOWFLAG_TRANSLUCENCY="${RENDER_SHOWFLAG_TRANSLUCENCY:-2}"
RENDER_VULKAN_SYNC2="${RENDER_VULKAN_SYNC2:-1}"
RENDER_VULKAN_DYNAMIC_RENDERING="${RENDER_VULKAN_DYNAMIC_RENDERING:-1}"
RENDER_VULKAN_SPLIT_BARRIERS="${RENDER_VULKAN_SPLIT_BARRIERS:-1}"
RENDER_VULKAN_MEMORY_BARRIER_OPT="${RENDER_VULKAN_MEMORY_BARRIER_OPT:-1}"
RENDER_VULKAN_FORCE_PSO_SINGLE_THREADED="${RENDER_VULKAN_FORCE_PSO_SINGLE_THREADED:-0}"
RENDER_TRANSLUCENCY_LIGHTING_VOLUME="${RENDER_TRANSLUCENCY_LIGHTING_VOLUME:-1}"
RENDER_PSO_PRECACHING="${RENDER_PSO_PRECACHING:-1}"
RENDER_POSTPROCESS_PREFER_COMPUTE="${RENDER_POSTPROCESS_PREFER_COMPUTE:-0}"
RENDER_TONEMAP_FORCE_COMPUTE_INTERMEDIATE="${RENDER_TONEMAP_FORCE_COMPUTE_INTERMEDIATE:-0}"
RENDER_TIMEOUT_SECONDS="${RENDER_TIMEOUT_SECONDS:-120}"
PACKAGE_LABEL="${PACKAGE_LABEL:-package_linux_02_legacy_nozen}"

ENV_DIR="$RUN_ROOT/environment"
LOG_DIR="$RUN_ROOT/logs"
PACKAGE_DIR="${PACKAGE_ROOT:-$RUN_ROOT/package}"
RENDER_DIR="$RUN_ROOT/renders"
UE_HOME="${UE_HOME:-$RUN_ROOT/home}"
UE_DDC="${UE_DDC:-$RUN_ROOT/ddc}"
TMP_DIR="$RUN_ROOT/tmp"
STATUS_FILE="$RUN_ROOT/status.tsv"
GPU_MONITOR_PID=""

mkdir -p "$ENV_DIR" "$LOG_DIR" "$PACKAGE_DIR" "$RENDER_DIR" \
  "$UE_HOME" "$UE_DDC" "$TMP_DIR"

if [[ -d "$RUNTIME_LIB_DIR" ]]; then
  export LD_LIBRARY_PATH="$RUNTIME_LIB_DIR:${LD_LIBRARY_PATH:-}"
fi
export HOME="$UE_HOME"
export TMPDIR="$TMP_DIR"
export UE_LocalDataCachePath="$UE_DDC"

stop_gpu_monitor() {
  local pid="${GPU_MONITOR_PID:-}"
  local state=""
  local check
  [[ -z "$pid" ]] && return

  kill "$pid" 2>/dev/null || true
  for check in $(seq 1 30); do
    state="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d '[:space:]')"
    if [[ -z "$state" || "$state" == Z* ]]; then
      wait "$pid" 2>/dev/null || true
      GPU_MONITOR_PID=""
      return
    fi
    sleep 0.1
  done

  kill -KILL "$pid" 2>/dev/null || true
  echo "WARN: GPU monitor $pid did not stop within 3 seconds; continuing without waiting."
  GPU_MONITOR_PID=""
}

cleanup() {
  stop_gpu_monitor
}
trap cleanup EXIT

printf 'RUN_ROOT=%s\n' "$RUN_ROOT"
printf 'STAGE=%s\n' "$STAGE"

usage() {
  cat <<EOF
Usage: RUN_ROOT=/absolute/evidence/path $0 <stage>

Stages:
  environment  Capture GPU, driver, Vulkan ICD, UE and host evidence.
  prepare      Generate and verify the cube map under NullRHI.
  package      Cook and package the minimal Linux Development runtime.
  render       Run packaged HighResShot attempts on NVIDIA Vulkan SM5.
  all          Run all stages in order, stopping on the first failure.

Important environment variables:
  RUN_ROOT, RUN_ID, UE_ROOT, UE_DDC, NVIDIA_ICD, PACKAGE_ROOT,
  PACKAGE_LABEL, RENDER_ATTEMPTS (default 1), RENDER_START_INDEX (default 1),
  RENDER_CAPTURE (0 or 1, default 1), RENDER_VALIDATION (0 or 1, default 0),
  RENDER_GPU_CRASH_DEBUGGING (0 or 1, default 0),
  RENDER_RHI_VALIDATION (0 or 1, default 0),
  RENDER_VULKAN_STALL_DUMP_SECONDS (non-negative number, default 0),
  RENDER_EXEC_COMMANDS (comma-separated UE console commands, default "viewmode unlit"),
  RENDER_SHOWFLAG_DIRECT_LIGHTING (0, 1, or 2 for no override; default 2),
  RENDER_SHOWFLAG_TRANSLUCENCY (0, 1, or 2 for no override; default 2),
  RENDER_VULKAN_SYNC2 (0 or 1, default 1),
  RENDER_VULKAN_DYNAMIC_RENDERING (0 or 1, default 1),
  RENDER_VULKAN_SPLIT_BARRIERS (0 or 1, default 1),
  RENDER_VULKAN_MEMORY_BARRIER_OPT (0 or 1, default 1),
  RENDER_VULKAN_FORCE_PSO_SINGLE_THREADED (0, 1, 2, or 3; default 0),
  RENDER_TRANSLUCENCY_LIGHTING_VOLUME (0 or 1, default 1),
  RENDER_PSO_PRECACHING (0 or 1, default 1),
  RENDER_POSTPROCESS_PREFER_COMPUTE (0 or 1, default 0),
  RENDER_TONEMAP_FORCE_COMPUTE_INTERMEDIATE (0 or 1, default 0),
  RENDER_TIMEOUT_SECONDS (default 120).
EOF
}

record_status() {
  local stage="$1"
  local result="$2"
  local rc="$3"
  printf '%s\t%s\t%s\t%s\n' "$(date --iso-8601=seconds)" "$stage" "$result" "$rc" \
    >>"$STATUS_FILE"
}

print_command() {
  printf 'COMMAND:'
  printf ' %q' "$@"
  printf '\n'
}

run_logged() {
  local label="$1"
  shift
  local log="$LOG_DIR/${label}.log"
  {
    printf 'START=%s\n' "$(date --iso-8601=seconds)"
    print_command "$@"
    "$@"
    local rc=$?
    printf 'EXIT_CODE=%s\n' "$rc"
    printf 'END=%s\n' "$(date --iso-8601=seconds)"
    return "$rc"
  } 2>&1 | tee "$log"
  return "${PIPESTATUS[0]}"
}

environment_stage() {
  local summary="$ENV_DIR/summary.txt"
  local failed=0
  local environment_result="passed"
  local driver_version=""
  local driver_major=""

  {
    printf 'captured_at=%s\n' "$(date --iso-8601=seconds)"
    printf 'hostname=%s\n' "$(hostname)"
    printf 'kernel=%s\n' "$(uname -srmo)"
    printf 'slurm_job_id=%s\n' "${SLURM_JOB_ID:-}"
    printf 'slurm_job_gpus=%s\n' "${SLURM_JOB_GPUS:-}"
    printf 'cuda_visible_devices=%s\n' "${CUDA_VISIBLE_DEVICES:-}"
    printf 'display=%s\n' "${DISPLAY:-}"
    printf 'ue_root=%s\n' "$UE_ROOT"
    printf 'uproject=%s\n' "$UPROJECT"
    printf 'nvidia_icd=%s\n' "$NVIDIA_ICD"
    printf 'vulkaninfo=%s\n' "$VULKANINFO"
    printf 'ld_library_path=%s\n' "${LD_LIBRARY_PATH:-}"
    printf 'disk_root='; df -h "$DATAMAKE_ROOT" | tail -n 1
    printf 'memory='; free -h | awk '/^Mem:/ {print $2 " total, " $7 " available"}'
  } | tee "$summary"

  if [[ ! -c /dev/nvidia0 ]]; then
    echo "FAIL: /dev/nvidia0 is not visible." | tee -a "$summary"
    failed=1
  fi
  for required in "$UE_EDITOR" "$RUN_UAT" "$UPROJECT" "$MAP_SCRIPT" \
    "$VULKANINFO" "$NVIDIA_ICD"; do
    if [[ ! -e "$required" ]]; then
      echo "FAIL: missing $required" | tee -a "$summary"
      failed=1
    fi
  done

  if ! run_logged environment_nvidia_smi nvidia-smi -q; then
    failed=1
  fi
  run_logged environment_nvidia_topology nvidia-smi topo -m || failed=1
  run_logged environment_nvidia_processes \
    nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory \
    --format=csv,noheader || failed=1

  if [[ -x "$VULKANINFO" && -f "$NVIDIA_ICD" ]]; then
    run_logged environment_vulkan_summary \
      env VK_LOADER_LAYERS_DISABLE='*' VK_ICD_FILENAMES="$NVIDIA_ICD" \
      "$VULKANINFO" --summary || failed=1
    run_logged environment_vulkan_full \
      env VK_LOADER_LAYERS_DISABLE='*' VK_ICD_FILENAMES="$NVIDIA_ICD" \
      "$VULKANINFO" --text || failed=1
  fi

  {
    sha256sum "$UE_EDITOR" "$UE_ROOT/Engine/Binaries/ThirdParty/Vulkan/Linux/libvulkan.so" \
      "$UPROJECT" "$PROJECT_DIR/Config/DefaultEngine.ini" "$MAP_SCRIPT" "$NVIDIA_ICD"
    cat "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor.version"
  } >"$ENV_DIR/version_and_hashes.txt" 2>&1

  if ! rg -q 'deviceName[[:space:]]*= NVIDIA H200' "$LOG_DIR/environment_vulkan_full.log"; then
    echo "FAIL: forced NVIDIA ICD did not enumerate NVIDIA H200." | tee -a "$summary"
    failed=1
  fi
  if ! rg -q 'QUEUE_GRAPHICS.*QUEUE_COMPUTE' "$LOG_DIR/environment_vulkan_full.log"; then
    echo "FAIL: no Vulkan graphics+compute queue was reported." | tee -a "$summary"
    failed=1
  fi
  if ! rg -q 'VK_KHR_shader_atomic_int64' "$LOG_DIR/environment_vulkan_full.log"; then
    echo "FAIL: VK_KHR_shader_atomic_int64 was not reported." | tee -a "$summary"
    failed=1
  fi

  driver_version="$(
    nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null \
      | head -n 1 | tr -d '[:space:]'
  )"
  printf 'driver_version=%s\n' "$driver_version" | tee -a "$summary"
  driver_major="${driver_version%%.*}"
  if [[ "$driver_major" =~ ^[0-9]+$ ]] && (( driver_major < 570 )); then
    echo "WARN: driver $driver_version is below the UE 5.8 documented 570+ requirement." \
      | tee -a "$summary"
    environment_result="passed_with_driver_warning"
  fi

  if (( failed )); then
    record_status environment failed 1
    return 1
  fi
  echo "PASS: NVIDIA H200 Vulkan device and required baseline capabilities are visible." \
    | tee -a "$summary"
  record_status environment "$environment_result" 0
}

prepare_stage() {
  run_logged prepare_cube_map \
    timeout --signal=TERM --kill-after=15s 600s \
    "$UE_EDITOR" "$UPROJECT" \
    -run=pythonscript -script="$MAP_SCRIPT" -NullRHI \
    -Unattended -NoSplash -NoSound -NoSourceControl -NoCrashDialog \
    -stdout -FullStdOutLogOutput \
    "-AbsLog=$LOG_DIR/prepare_cube_map_ue.log" -ddc=NoZenLocalFallback
  local rc=$?
  if (( rc != 0 )) || ! rg -q 'DM_UE58_CUBE_MAP=.*"success": true' \
    "$LOG_DIR/prepare_cube_map.log"; then
    local failure_rc="$rc"
    (( failure_rc == 0 )) && failure_rc=1
    record_status prepare failed "$failure_rc"
    return "$failure_rc"
  fi
  local map_file="$PROJECT_DIR/Content/${MAP_PATH#/Game/}.umap"
  if [[ ! -s "$map_file" ]]; then
    echo "FAIL: generated map is missing or empty: $map_file" | tee -a "$LOG_DIR/prepare_cube_map.log"
    record_status prepare failed 1
    return 1
  fi
  sha256sum "$map_file" | tee "$ENV_DIR/generated_map.sha256"
  record_status prepare passed 0
}

package_stage() {
  run_logged "$PACKAGE_LABEL" \
    timeout --signal=TERM --kill-after=30s 1800s \
    "$RUN_UAT" BuildCookRun \
    -project="$UPROJECT" -noP4 -installed -nocompileeditor -utf8output \
    -platform=Linux -clientconfig=Development -build -cook -map="$MAP_PATH" \
    -stage -pak -skipiostore \
    '-AdditionalCookerOptions=-SkipZenStore -ddc=NoZenLocalFallback' \
    -package -archive -archivedirectory="$PACKAGE_DIR"
  local rc=$?
  local launcher="$PACKAGE_DIR/Linux/UE58VulkanCubeSmoke.sh"
  if (( rc != 0 )) || [[ ! -x "$launcher" ]]; then
    local failure_rc="$rc"
    (( failure_rc == 0 )) && failure_rc=1
    record_status package failed "$failure_rc"
    return "$failure_rc"
  fi
  find "$PACKAGE_DIR/Linux" -type f -print0 | sort -z | xargs -0 sha256sum \
    >"$ENV_DIR/package.sha256"
  du -sh "$PACKAGE_DIR/Linux" | tee "$ENV_DIR/package_size.txt"
  record_status package passed 0
}

render_stage() {
  local launcher="$PACKAGE_DIR/Linux/UE58VulkanCubeSmoke.sh"
  local game_binary="$PACKAGE_DIR/Linux/Engine/Binaries/Linux/UnrealGame"
  local packaged_project='"../../../UE58VulkanCubeSmoke/UE58VulkanCubeSmoke.uproject"'
  if [[ ! -x "$launcher" || ! -x "$game_binary" ]]; then
    echo "FAIL: packaged launcher not found: $launcher" >&2
    record_status render failed 2
    return 2
  fi

  if [[ "$RENDER_CAPTURE" != "0" && "$RENDER_CAPTURE" != "1" ]]; then
    echo "FAIL: RENDER_CAPTURE must be 0 or 1." >&2
    return 2
  fi
  if [[ "$RENDER_VALIDATION" != "0" && "$RENDER_VALIDATION" != "1" ]]; then
    echo "FAIL: RENDER_VALIDATION must be 0 or 1." >&2
    return 2
  fi
  if [[ "$RENDER_GPU_CRASH_DEBUGGING" != "0" && "$RENDER_GPU_CRASH_DEBUGGING" != "1" ]]; then
    echo "FAIL: RENDER_GPU_CRASH_DEBUGGING must be 0 or 1." >&2
    return 2
  fi
  if [[ "$RENDER_RHI_VALIDATION" != "0" && "$RENDER_RHI_VALIDATION" != "1" ]]; then
    echo "FAIL: RENDER_RHI_VALIDATION must be 0 or 1." >&2
    return 2
  fi
  if [[ ! "$RENDER_VULKAN_STALL_DUMP_SECONDS" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "FAIL: RENDER_VULKAN_STALL_DUMP_SECONDS must be a non-negative number." >&2
    return 2
  fi
  if [[ ! "$RENDER_SHOWFLAG_DIRECT_LIGHTING" =~ ^[012]$ ]]; then
    echo "FAIL: RENDER_SHOWFLAG_DIRECT_LIGHTING must be 0, 1, or 2." >&2
    return 2
  fi
  if [[ ! "$RENDER_SHOWFLAG_TRANSLUCENCY" =~ ^[012]$ ]]; then
    echo "FAIL: RENDER_SHOWFLAG_TRANSLUCENCY must be 0, 1, or 2." >&2
    return 2
  fi
  if [[ "$RENDER_VULKAN_SYNC2" != "0" && "$RENDER_VULKAN_SYNC2" != "1" ]]; then
    echo "FAIL: RENDER_VULKAN_SYNC2 must be 0 or 1." >&2
    return 2
  fi
  if [[ "$RENDER_VULKAN_DYNAMIC_RENDERING" != "0" && "$RENDER_VULKAN_DYNAMIC_RENDERING" != "1" ]]; then
    echo "FAIL: RENDER_VULKAN_DYNAMIC_RENDERING must be 0 or 1." >&2
    return 2
  fi
  if [[ "$RENDER_VULKAN_SPLIT_BARRIERS" != "0" && "$RENDER_VULKAN_SPLIT_BARRIERS" != "1" ]]; then
    echo "FAIL: RENDER_VULKAN_SPLIT_BARRIERS must be 0 or 1." >&2
    return 2
  fi
  if [[ "$RENDER_VULKAN_MEMORY_BARRIER_OPT" != "0" && "$RENDER_VULKAN_MEMORY_BARRIER_OPT" != "1" ]]; then
    echo "FAIL: RENDER_VULKAN_MEMORY_BARRIER_OPT must be 0 or 1." >&2
    return 2
  fi
  if [[ ! "$RENDER_VULKAN_FORCE_PSO_SINGLE_THREADED" =~ ^[0123]$ ]]; then
    echo "FAIL: RENDER_VULKAN_FORCE_PSO_SINGLE_THREADED must be 0, 1, 2, or 3." >&2
    return 2
  fi
  if [[ "$RENDER_TRANSLUCENCY_LIGHTING_VOLUME" != "0" && "$RENDER_TRANSLUCENCY_LIGHTING_VOLUME" != "1" ]]; then
    echo "FAIL: RENDER_TRANSLUCENCY_LIGHTING_VOLUME must be 0 or 1." >&2
    return 2
  fi
  if [[ "$RENDER_PSO_PRECACHING" != "0" && "$RENDER_PSO_PRECACHING" != "1" ]]; then
    echo "FAIL: RENDER_PSO_PRECACHING must be 0 or 1." >&2
    return 2
  fi
  if [[ "$RENDER_POSTPROCESS_PREFER_COMPUTE" != "0" && "$RENDER_POSTPROCESS_PREFER_COMPUTE" != "1" ]]; then
    echo "FAIL: RENDER_POSTPROCESS_PREFER_COMPUTE must be 0 or 1." >&2
    return 2
  fi
  if [[ "$RENDER_TONEMAP_FORCE_COMPUTE_INTERMEDIATE" != "0" && "$RENDER_TONEMAP_FORCE_COMPUTE_INTERMEDIATE" != "1" ]]; then
    echo "FAIL: RENDER_TONEMAP_FORCE_COMPUTE_INTERMEDIATE must be 0 or 1." >&2
    return 2
  fi

  local overall=0
  local attempt
  local last_attempt=$((RENDER_START_INDEX + RENDER_ATTEMPTS - 1))
  for attempt in $(seq "$RENDER_START_INDEX" "$last_attempt"); do
    local attempt_id
    attempt_id="$(printf '%02d' "$attempt")"
    local image="$RENDER_DIR/cube_smoke_${attempt_id}.png"
    local monitor="$ENV_DIR/gpu_render_${attempt_id}.csv"
    local render_config="$ENV_DIR/render_${attempt_id}_config.txt"
    local -a runtime_env=(env VK_ICD_FILENAMES="$NVIDIA_ICD")
    local -a validation_args=()
    local -a diagnostic_args=()
    local -a showflag_args=()
    local -a exec_args=(-ExecCmds="$RENDER_EXEC_COMMANDS")
    local -a vulkan_compat_args=(
      "-ini:Engine:[ConsoleVariables]:r.Vulkan.AllowSynchronization2=$RENDER_VULKAN_SYNC2"
      "-ini:Engine:[ConsoleVariables]:r.Vulkan.AllowDynamicRendering=$RENDER_VULKAN_DYNAMIC_RENDERING"
      "-ini:Engine:[ConsoleVariables]:r.Vulkan.AllowSplitBarriers=$RENDER_VULKAN_SPLIT_BARRIERS"
      "-ini:Engine:[ConsoleVariables]:r.Vulkan.UseMemoryBarrierOpt=$RENDER_VULKAN_MEMORY_BARRIER_OPT"
      "-ini:Engine:[ConsoleVariables]:r.Vulkan.ForcePSOSingleThreaded=$RENDER_VULKAN_FORCE_PSO_SINGLE_THREADED"
      "-ini:Engine:[ConsoleVariables]:r.TranslucencyLightingVolume=$RENDER_TRANSLUCENCY_LIGHTING_VOLUME"
      "-ini:Engine:[ConsoleVariables]:r.PSOPrecaching=$RENDER_PSO_PRECACHING"
      "-ini:Engine:[ConsoleVariables]:r.PostProcessing.PreferCompute=$RENDER_POSTPROCESS_PREFER_COMPUTE"
      "-ini:Engine:[ConsoleVariables]:r.Tonemapper.ForceComputeIntermediate=$RENDER_TONEMAP_FORCE_COMPUTE_INTERMEDIATE"
      "-ini:Engine:[ConsoleVariables]:r.Vulkan.DumpStalledGPUAfterSeconds=$RENDER_VULKAN_STALL_DUMP_SECONDS"
    )

    {
      printf 'capture=%s\n' "$RENDER_CAPTURE"
      printf 'validation=%s\n' "$RENDER_VALIDATION"
      printf 'gpu_crash_debugging=%s\n' "$RENDER_GPU_CRASH_DEBUGGING"
      printf 'rhi_validation=%s\n' "$RENDER_RHI_VALIDATION"
      printf 'vulkan_stall_dump_seconds=%s\n' "$RENDER_VULKAN_STALL_DUMP_SECONDS"
      printf 'exec_commands=%s\n' "$RENDER_EXEC_COMMANDS"
      printf 'showflag_direct_lighting=%s\n' "$RENDER_SHOWFLAG_DIRECT_LIGHTING"
      printf 'showflag_translucency=%s\n' "$RENDER_SHOWFLAG_TRANSLUCENCY"
      printf 'vulkan_sync2=%s\n' "$RENDER_VULKAN_SYNC2"
      printf 'vulkan_dynamic_rendering=%s\n' "$RENDER_VULKAN_DYNAMIC_RENDERING"
      printf 'vulkan_split_barriers=%s\n' "$RENDER_VULKAN_SPLIT_BARRIERS"
      printf 'vulkan_memory_barrier_opt=%s\n' "$RENDER_VULKAN_MEMORY_BARRIER_OPT"
      printf 'vulkan_force_pso_single_threaded=%s\n' "$RENDER_VULKAN_FORCE_PSO_SINGLE_THREADED"
      printf 'translucency_lighting_volume=%s\n' "$RENDER_TRANSLUCENCY_LIGHTING_VOLUME"
      printf 'pso_precaching=%s\n' "$RENDER_PSO_PRECACHING"
      printf 'postprocess_prefer_compute=%s\n' "$RENDER_POSTPROCESS_PREFER_COMPUTE"
      printf 'tonemap_force_compute_intermediate=%s\n' "$RENDER_TONEMAP_FORCE_COMPUTE_INTERMEDIATE"
      printf 'package_dir=%s\n' "$PACKAGE_DIR"
    } >"$render_config"

    if [[ "$RENDER_VALIDATION" == "1" ]]; then
      runtime_env+=(VK_LAYER_PATH="$PACKAGE_DIR/Linux/Engine/Binaries/ThirdParty/Vulkan/Linux")
      validation_args+=(-vulkanvalidation=2)
    else
      runtime_env+=(VK_LOADER_LAYERS_DISABLE='*')
    fi
    if [[ "$RENDER_GPU_CRASH_DEBUGGING" == "1" ]]; then
      diagnostic_args+=(-gpucrashdebugging -gpubreadcrumbs)
    fi
    if [[ "$RENDER_RHI_VALIDATION" == "1" ]]; then
      diagnostic_args+=(-RHIValidation -RHIValidationBreadcrumbLog)
    fi
    if [[ "$RENDER_SHOWFLAG_DIRECT_LIGHTING" != "2" ]]; then
      showflag_args+=("-ini:Engine:[SystemSettings]:ShowFlag.DirectLighting=$RENDER_SHOWFLAG_DIRECT_LIGHTING")
    fi
    if [[ "$RENDER_SHOWFLAG_TRANSLUCENCY" != "2" ]]; then
      showflag_args+=("-ini:Engine:[SystemSettings]:ShowFlag.Translucency=$RENDER_SHOWFLAG_TRANSLUCENCY")
    fi
    if [[ "$RENDER_CAPTURE" == "1" ]]; then
      exec_args=(-ExecCmds="$RENDER_EXEC_COMMANDS,HighResShot 1 filename=$image")
    fi

    nvidia-smi --query-gpu=timestamp,index,uuid,name,driver_version,utilization.gpu,memory.used,power.draw \
      --format=csv -l 1 >"$monitor" 2>&1 &
    GPU_MONITOR_PID=$!
    echo "GPU monitor for attempt $attempt_id: pid=$GPU_MONITOR_PID log=$monitor"

    run_logged "render_${attempt_id}" \
      timeout --signal=TERM --kill-after=15s "${RENDER_TIMEOUT_SECONDS}s" \
      "${runtime_env[@]}" \
      "$game_binary" "$packaged_project" "$MAP_PATH" \
      -game -RenderOffscreen -vulkan -sm5 -graphicsadapter=0 -BindlessOff \
      "${validation_args[@]}" \
      "${diagnostic_args[@]}" \
      "${showflag_args[@]}" \
      "${vulkan_compat_args[@]}" \
      -Unattended -NoSplash -NoSound -NoLoadingScreen -NoScreenMessages \
      -windowed -ResX=640 -ResY=360 -ForceRes \
      "${exec_args[@]}" \
      -BENCHMARK -FPS=1 -BENCHMARKSECONDS=20 \
      -stdout -FullStdOutLogOutput \
      "-AbsLog=$LOG_DIR/render_${attempt_id}_ue.log" -ddc=NoZenLocalFallback
    local rc=$?

    stop_gpu_monitor

    if (( rc != 0 )) || [[ "$RENDER_CAPTURE" == "1" && ! -s "$image" ]]; then
      echo "FAIL: render attempt $attempt_id exit=$rc image=$image" \
        | tee -a "$LOG_DIR/render_${attempt_id}.log"
      record_status "render_$attempt_id" failed "$rc"
      overall=1
      continue
    fi
    if [[ "$RENDER_CAPTURE" == "1" ]]; then
      file "$image" | tee "$ENV_DIR/image_${attempt_id}.txt"
      sha256sum "$image" | tee -a "$ENV_DIR/image_${attempt_id}.txt"
    else
      echo "PASS: render attempt $attempt_id completed without screenshot capture." \
        | tee "$ENV_DIR/render_${attempt_id}_no_capture.txt"
    fi
    record_status "render_$attempt_id" passed 0
  done

  find "$RENDER_DIR" -maxdepth 1 -type f -printf '%f\t%s bytes\n' | sort \
    | tee "$ENV_DIR/render_outputs.txt"
  return "$overall"
}

case "$STAGE" in
  environment)
    environment_stage
    ;;
  prepare)
    prepare_stage
    ;;
  package)
    package_stage
    ;;
  render)
    render_stage
    ;;
  all)
    environment_stage && prepare_stage && package_stage && render_stage
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown stage: $STAGE" >&2
    usage >&2
    exit 2
    ;;
esac
