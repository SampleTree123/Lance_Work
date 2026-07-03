#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_video_edit.sh --video VIDEO --prompt "PROMPT" [options]
  run_video_edit.sh --video VIDEO --prompts-file FILE [options]

Required:
  --video VIDEO          Input video path for the first turn.
  --prompt PROMPT        Single-turn edit prompt.
  --prompts-file FILE    Multi-turn prompt file; each non-empty non-comment line is one turn.

Options:
  --name NAME            Run name. Default: timestamped name.
  --steps N              Validation diffusion steps. Default: 30.
  --frames N             Output/input frame count Lance samples. Default: 50.
  --seed N               Validation seed. Default: 42.
  --cfg SCALE            CFG text scale. Default: 4.0.
  --resolution NAME      Lance resolution flag. Default: video_480p.
  --height N             Passed through to Lance. Editing uses input size when applicable. Default: 480.
  --width N              Passed through to Lance. Editing uses input size when applicable. Default: 480.
  --output-root DIR      Output root. Default: <repo>/10_research/model_experiments/lance/outputs/video_edit.
  --job-id ID            Optional SLURM allocation job id. If set, run the script inside that job via srun.
  --no-srun              Internal flag; prevents recursive srun wrapping.
  -h, --help             Show this help.

Examples:
  10_research/model_experiments/lance/scripts/run_video_edit.sh --video 10_research/model_experiments/lance/inputs/video_edit/videos/a.mp4 --prompt "Make the sky cloudy." --name cloudy
  10_research/model_experiments/lance/scripts/run_video_edit.sh --video 10_research/model_experiments/lance/inputs/video_edit/videos/a.mp4 --prompts-file 10_research/model_experiments/lance/inputs/video_edit/prompts/turns.txt --name chain_test
EOF
}

die() {
  echo "Error: $*" >&2
  exit 1
}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DATAMAKE_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd -P)

VIDEO=""
PROMPT=""
PROMPTS_FILE=""
RUN_NAME=""
STEPS=30
FRAMES=50
SEED=42
CFG_SCALE=4.0
RESOLUTION="video_480p"
HEIGHT=480
WIDTH=480
OUTPUT_ROOT="$DATAMAKE_ROOT/10_research/model_experiments/lance/outputs/video_edit"
JOB_ID=""
NO_SRUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --video) VIDEO="$2"; shift 2 ;;
    --prompt) PROMPT="$2"; shift 2 ;;
    --prompts-file) PROMPTS_FILE="$2"; shift 2 ;;
    --name) RUN_NAME="$2"; shift 2 ;;
    --steps) STEPS="$2"; shift 2 ;;
    --frames) FRAMES="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --cfg) CFG_SCALE="$2"; shift 2 ;;
    --resolution) RESOLUTION="$2"; shift 2 ;;
    --height) HEIGHT="$2"; shift 2 ;;
    --width) WIDTH="$2"; shift 2 ;;
    --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
    --job-id) JOB_ID="$2"; shift 2 ;;
    --no-srun) NO_SRUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ -n "$VIDEO" ]] || die "--video is required"
[[ -n "$PROMPT" || -n "$PROMPTS_FILE" ]] || die "provide --prompt or --prompts-file"
[[ -z "$PROMPT" || -z "$PROMPTS_FILE" ]] || die "use only one of --prompt or --prompts-file"

if [[ -n "$JOB_ID" && "$NO_SRUN" -eq 0 ]]; then
  rerun_args=("$0" "--no-srun" "--video" "$VIDEO")
  [[ -n "$PROMPT" ]] && rerun_args+=("--prompt" "$PROMPT")
  [[ -n "$PROMPTS_FILE" ]] && rerun_args+=("--prompts-file" "$PROMPTS_FILE")
  [[ -n "$RUN_NAME" ]] && rerun_args+=("--name" "$RUN_NAME")
  rerun_args+=(
    "--steps" "$STEPS"
    "--frames" "$FRAMES"
    "--seed" "$SEED"
    "--cfg" "$CFG_SCALE"
    "--resolution" "$RESOLUTION"
    "--height" "$HEIGHT"
    "--width" "$WIDTH"
    "--output-root" "$OUTPUT_ROOT"
  )
  exec srun --jobid="$JOB_ID" --overlap -N1 -n1 --gres=gpu:1 bash "${rerun_args[@]}"
fi

abs_path() {
  local path="$1"
  if [[ "$path" = /* ]]; then
    printf '%s\n' "$path"
  else
    printf '%s\n' "$(cd "$(dirname "$path")" && pwd -P)/$(basename "$path")"
  fi
}

VIDEO=$(abs_path "$VIDEO")
[[ -f "$VIDEO" ]] || die "video not found: $VIDEO"

if [[ -n "$PROMPTS_FILE" ]]; then
  PROMPTS_FILE=$(abs_path "$PROMPTS_FILE")
  [[ -f "$PROMPTS_FILE" ]] || die "prompts file not found: $PROMPTS_FILE"
fi

if [[ -z "$RUN_NAME" ]]; then
  RUN_NAME="video_edit_$(date +%Y%m%d_%H%M%S)"
fi

LANCE_REPO="$DATAMAKE_ROOT/10_research/model_experiments/lance/lance"
MODEL_PATH="downloads/Lance_3B_Video"
CONFIG_ROOT="$DATAMAKE_ROOT/10_research/model_experiments/lance/logs/generated_configs/$RUN_NAME"
RUN_DIR="$OUTPUT_ROOT/$RUN_NAME"

[[ -d "$LANCE_REPO" ]] || die "Lance repo not found: $LANCE_REPO"
[[ -d "$LANCE_REPO/$MODEL_PATH" ]] || die "Lance model path not found: $LANCE_REPO/$MODEL_PATH"

mkdir -p "$CONFIG_ROOT" "$RUN_DIR"

if command -v conda >/dev/null 2>&1; then
  CONDA_BASE=$(conda info --base)
  if [[ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]]; then
    # shellcheck disable=SC1090
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate xks_lance
  fi
fi

HF_HOME="${HF_HOME:-/scratch/prj0000000275/jcy/.cache/huggingface}"
HF_HOME=$(readlink -f "$HF_HOME")
export HF_HOME
export HF_HUB_CACHE="${HF_HUB_CACHE:-$HF_HOME/hub}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-$HF_HOME/hub}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export PYTHONUNBUFFERED=1

mapfile -t PROMPTS < <(
  if [[ -n "$PROMPTS_FILE" ]]; then
    python - "$PROMPTS_FILE" <<'PY'
from pathlib import Path
import sys

for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#"):
        print(line)
PY
  else
    printf '%s\n' "$PROMPT"
  fi
)

[[ "${#PROMPTS[@]}" -gt 0 ]] || die "no prompts found"

echo "DataMake root: $DATAMAKE_ROOT"
echo "Lance repo:    $LANCE_REPO"
echo "Input video:   $VIDEO"
echo "Run dir:       $RUN_DIR"
echo "Turns:         ${#PROMPTS[@]}"
echo "Steps:         $STEPS"
echo "Frames:        $FRAMES"
echo "HF_HOME:       $HF_HOME"
echo

cd "$LANCE_REPO"
CURRENT_VIDEO="$VIDEO"

for i in "${!PROMPTS[@]}"; do
  TURN_NUM=$((i + 1))
  TURN_LABEL=$(printf "%02d" "$TURN_NUM")
  TURN_DIR="$RUN_DIR/turn_$TURN_LABEL"
  CONFIG_PATH="$CONFIG_ROOT/turn_$TURN_LABEL.json"
  TURN_PROMPT="${PROMPTS[$i]}"

  mkdir -p "$TURN_DIR"

  python - "$CONFIG_PATH" "$TURN_PROMPT" "$CURRENT_VIDEO" <<'PY'
import json
from pathlib import Path
import sys

config_path = Path(sys.argv[1])
prompt = sys.argv[2]
video = sys.argv[3]

payload = {
    "0001": {
        "interleave_array": [prompt, video],
        "element_dtype_array": ["text", "video"],
        "istarget_in_interleave": [0, 0],
    }
}
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

  echo "================================================"
  echo "Turn $TURN_LABEL"
  echo "Input:  $CURRENT_VIDEO"
  echo "Prompt: $TURN_PROMPT"
  echo "Output: $TURN_DIR"
  echo "================================================"

  bash inference_lance.sh \
    --TASK_NAME video_edit \
    --MODEL_PATH "$MODEL_PATH" \
    --CONFIG_PATH "$CONFIG_PATH" \
    --SAVE_PATH_GEN "$TURN_DIR" \
    --VALIDATION_NUM_TIMESTEPS "$STEPS" \
    --VALIDATION_TIMESTEP_SHIFT 3.5 \
    --VALIDATION_DATA_SEED "$SEED" \
    --CFG_TEXT_SCALE "$CFG_SCALE" \
    --NUM_FRAMES "$FRAMES" \
    --VIDEO_HEIGHT "$HEIGHT" \
    --VIDEO_WIDTH "$WIDTH" \
    --RESOLUTION "$RESOLUTION" \
    --USE_KVCACHE true \
    --ENHANCE_PROMPT false

  NEXT_VIDEO=$(find "$TURN_DIR" -maxdepth 1 -type f -name '*.mp4' | sort | head -n 1)
  [[ -n "$NEXT_VIDEO" ]] || die "no mp4 generated in $TURN_DIR"
  CURRENT_VIDEO="$NEXT_VIDEO"
done

echo
echo "Done."
echo "Final video: $CURRENT_VIDEO"
echo "Run dir:     $RUN_DIR"
