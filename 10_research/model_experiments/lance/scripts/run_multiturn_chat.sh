#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_multiturn_chat.sh --conversation CONVERSATION_JSON [options]
  run_multiturn_chat.sh --video VIDEO --prompts-file FILE [options]
  run_multiturn_chat.sh --video VIDEO --prompt "PROMPT" [--prompt "PROMPT2" ...] [options]

Modes:
  --conversation JSON    Full Lance multi-turn conversation JSON. Supports mixed actions.
  --video VIDEO          Initial source video; used with --prompt/--prompts-file to build edit_video turns.
  --prompt PROMPT        One edit_video prompt. Repeat for multiple turns.
  --prompts-file FILE    One edit_video prompt per non-empty non-comment line.

Options:
  --name NAME            Run name. Default: timestamped name.
  --steps N              Validation diffusion steps. Default: 30.
  --frames N             Default video frame count for generation. Default: 50.
  --seed N               Validation seed. Default: 42.
  --cfg SCALE            CFG text scale. Default: 4.0.
  --resolution NAME      Lance resolution flag. Default: video_480p.
  --height N             Default video height. Editing uses source size when applicable. Default: 480.
  --width N              Default video width. Editing uses source size when applicable. Default: 480.
  --model-path PATH      Lance model path relative to Lance repo or absolute. Default: downloads/Lance_3B_Video.
  --output-root DIR      Output root. Default: <repo>/10_research/model_experiments/lance/outputs/multiturn_chat.
  --job-id ID            Optional SLURM allocation job id. If set, run inside that job via srun.
  --no-srun              Internal flag; prevents recursive srun wrapping.
  -h, --help             Show this help.

Notes:
  This uses full conversation context: previous user text remains as previous turns,
  not as text appended into the latest prompt.
EOF
}

die() {
  echo "Error: $*" >&2
  exit 1
}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DATAMAKE_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd -P)

CONVERSATION=""
VIDEO=""
PROMPTS_FILE=""
PROMPTS=()
RUN_NAME=""
STEPS=30
FRAMES=50
SEED=42
CFG_SCALE=4.0
RESOLUTION="video_480p"
HEIGHT=480
WIDTH=480
MODEL_PATH="downloads/Lance_3B_Video"
OUTPUT_ROOT="$DATAMAKE_ROOT/10_research/model_experiments/lance/outputs/multiturn_chat"
JOB_ID=""
NO_SRUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --conversation) CONVERSATION="$2"; shift 2 ;;
    --video) VIDEO="$2"; shift 2 ;;
    --prompt) PROMPTS+=("$2"); shift 2 ;;
    --prompts-file) PROMPTS_FILE="$2"; shift 2 ;;
    --name) RUN_NAME="$2"; shift 2 ;;
    --steps) STEPS="$2"; shift 2 ;;
    --frames) FRAMES="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --cfg) CFG_SCALE="$2"; shift 2 ;;
    --resolution) RESOLUTION="$2"; shift 2 ;;
    --height) HEIGHT="$2"; shift 2 ;;
    --width) WIDTH="$2"; shift 2 ;;
    --model-path) MODEL_PATH="$2"; shift 2 ;;
    --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
    --job-id) JOB_ID="$2"; shift 2 ;;
    --no-srun) NO_SRUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

if [[ -n "$JOB_ID" && "$NO_SRUN" -eq 0 ]]; then
  rerun_args=("$0" "--no-srun")
  [[ -n "$CONVERSATION" ]] && rerun_args+=("--conversation" "$CONVERSATION")
  [[ -n "$VIDEO" ]] && rerun_args+=("--video" "$VIDEO")
  [[ -n "$PROMPTS_FILE" ]] && rerun_args+=("--prompts-file" "$PROMPTS_FILE")
  for prompt in "${PROMPTS[@]}"; do
    rerun_args+=("--prompt" "$prompt")
  done
  [[ -n "$RUN_NAME" ]] && rerun_args+=("--name" "$RUN_NAME")
  rerun_args+=(
    "--steps" "$STEPS"
    "--frames" "$FRAMES"
    "--seed" "$SEED"
    "--cfg" "$CFG_SCALE"
    "--resolution" "$RESOLUTION"
    "--height" "$HEIGHT"
    "--width" "$WIDTH"
    "--model-path" "$MODEL_PATH"
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

if [[ -z "$RUN_NAME" ]]; then
  RUN_NAME="multiturn_chat_$(date +%Y%m%d_%H%M%S)"
fi

LANCE_REPO="$DATAMAKE_ROOT/10_research/model_experiments/lance/lance"
CONFIG_ROOT="$DATAMAKE_ROOT/10_research/model_experiments/lance/logs/generated_configs/$RUN_NAME"
RUN_DIR="$OUTPUT_ROOT/$RUN_NAME"

[[ -d "$LANCE_REPO" ]] || die "Lance repo not found: $LANCE_REPO"

if [[ "$MODEL_PATH" = /* ]]; then
  [[ -d "$MODEL_PATH" ]] || die "Lance model path not found: $MODEL_PATH"
else
  [[ -d "$LANCE_REPO/$MODEL_PATH" ]] || die "Lance model path not found: $LANCE_REPO/$MODEL_PATH"
fi

mkdir -p "$CONFIG_ROOT" "$RUN_DIR"

if [[ -n "$CONVERSATION" ]]; then
  CONVERSATION=$(abs_path "$CONVERSATION")
  [[ -f "$CONVERSATION" ]] || die "conversation not found: $CONVERSATION"
else
  [[ -n "$VIDEO" ]] || die "provide --conversation, or --video with --prompt/--prompts-file"
  [[ "${#PROMPTS[@]}" -gt 0 || -n "$PROMPTS_FILE" ]] || die "provide --prompt or --prompts-file"
  [[ "${#PROMPTS[@]}" -eq 0 || -z "$PROMPTS_FILE" ]] || die "use --prompt or --prompts-file, not both"
  VIDEO=$(abs_path "$VIDEO")
  [[ -f "$VIDEO" ]] || die "video not found: $VIDEO"
  CONVERSATION="$CONFIG_ROOT/conversation.json"
  build_args=("$SCRIPT_DIR/build_multiturn_conversation.py" "--video" "$VIDEO" "--output" "$CONVERSATION")
  if [[ -n "$PROMPTS_FILE" ]]; then
    PROMPTS_FILE=$(abs_path "$PROMPTS_FILE")
    [[ -f "$PROMPTS_FILE" ]] || die "prompts file not found: $PROMPTS_FILE"
    build_args+=("--prompts-file" "$PROMPTS_FILE")
  else
    for prompt in "${PROMPTS[@]}"; do
      build_args+=("--prompt" "$prompt")
    done
  fi
  python "${build_args[@]}" >/dev/null
fi

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

echo "DataMake root: $DATAMAKE_ROOT"
echo "Lance repo:    $LANCE_REPO"
echo "Conversation:  $CONVERSATION"
echo "Run dir:       $RUN_DIR"
echo "Steps:         $STEPS"
echo "Frames:        $FRAMES"
echo "HF_HOME:       $HF_HOME"
echo

cd "$LANCE_REPO"
python multiturn_chat.py \
  --model_path "$MODEL_PATH" \
  --vit_type qwen_2_5_vl_original \
  --llm_qk_norm true \
  --llm_qk_norm_und true \
  --llm_qk_norm_gen true \
  --tie_word_embeddings false \
  --validation_num_timesteps "$STEPS" \
  --validation_timestep_shift 3.5 \
  --copy_init_moe true \
  --max_num_frames 121 \
  --max_latent_size 64 \
  --latent_patch_size 1 1 1 \
  --visual_und true \
  --visual_gen true \
  --vae_model_type wan \
  --apply_qwen_2_5_vl_pos_emb true \
  --apply_chat_template false \
  --cfg_type 0 \
  --validation_data_seed "$SEED" \
  --video_height "$HEIGHT" \
  --video_width "$WIDTH" \
  --num_frames "$FRAMES" \
  --resolution "$RESOLUTION" \
  --text_template true \
  --cfg_text_scale "$CFG_SCALE" \
  --use_KVcache true \
  --conversation_path "$CONVERSATION" \
  --save_path "$RUN_DIR" \
  --transcript_name transcript.json
