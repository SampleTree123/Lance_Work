#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: run_datamake_training.sh --dataset-config PATH --run-name NAME [options]

Required:
  --dataset-config PATH       Lance YAML produced by the DataMake builder
  --run-name NAME             Unique output directory / W&B display name

Options:
  --mode smoke|resume         Legacy full-parameter smoke preset (default: smoke)
  --total-steps N             Exclusive training-loop upper bound
  --checkpoint-step N         Step at which to save the audit checkpoint
  --resume-from PATH          Full Lance checkpoint directory to resume
  --output-root PATH          Parent directory for run outputs
  --num-workers N             DataLoader workers (default: 2)
  --master-port N             Single-node torchrun rendezvous port
  --wandb-mode MODE           offline or online (default: offline)
  --wandb-project NAME        W&B project (default: datamake_lance)
  --wandb-entity NAME         Optional W&B user/team entity
  --wandb-run-id ID           Stable ID used across checkpoint resumes
  --wandb-group NAME          Optional W&B run group
  --wandb-job-type NAME       Optional W&B job type
  --wandb-tags CSV            Optional comma-separated W&B tags
  --log-every N               Training/W&B metric interval (default: 1 step)

This launcher intentionally implements only full-parameter Lance fine-tuning.
It does not expose LoRA or freeze_und_params fallbacks.
EOF
}

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
OUTER_ROOT=$(cd -- "$SCRIPT_DIR/../../../.." && pwd)
LANCE_ROOT="$OUTER_ROOT/10_research/model_experiments/lance/lance"
CONDA_ENV=${DATAMAKE_LANCE_ENV:-/scratch/prj0000000275/jcy/.conda/envs/xks_lance}
TORCHRUN="$CONDA_ENV/bin/torchrun"
MODEL_PATH="$LANCE_ROOT/downloads/Lance_3B_Video"
VIT_PATH="$LANCE_ROOT/downloads/Qwen2.5-VL-ViT"
OUTPUT_ROOT="$OUTER_ROOT/10_research/model_experiments/lance/outputs/training_runs"

MODE=smoke
DATASET_CONFIG=
RUN_NAME=
TOTAL_STEPS=
CHECKPOINT_STEP=
RESUME_FROM=
NUM_WORKERS=2
MASTER_PORT=${MASTER_PORT:-29531}
WANDB_MODE_SETTING=offline
WANDB_PROJECT_SETTING=datamake_lance
WANDB_ENTITY_SETTING=${WANDB_ENTITY:-}
WANDB_RUN_ID_SETTING=
WANDB_GROUP_SETTING=
WANDB_JOB_TYPE_SETTING=
WANDB_TAGS_SETTING=
LOG_EVERY=1

while (($#)); do
    case "$1" in
        --mode) MODE=$2; shift 2 ;;
        --dataset-config) DATASET_CONFIG=$2; shift 2 ;;
        --run-name) RUN_NAME=$2; shift 2 ;;
        --total-steps) TOTAL_STEPS=$2; shift 2 ;;
        --checkpoint-step) CHECKPOINT_STEP=$2; shift 2 ;;
        --resume-from) RESUME_FROM=$2; shift 2 ;;
        --output-root) OUTPUT_ROOT=$2; shift 2 ;;
        --num-workers) NUM_WORKERS=$2; shift 2 ;;
        --master-port) MASTER_PORT=$2; shift 2 ;;
        --wandb-mode) WANDB_MODE_SETTING=$2; shift 2 ;;
        --wandb-project) WANDB_PROJECT_SETTING=$2; shift 2 ;;
        --wandb-entity) WANDB_ENTITY_SETTING=$2; shift 2 ;;
        --wandb-run-id) WANDB_RUN_ID_SETTING=$2; shift 2 ;;
        --wandb-group) WANDB_GROUP_SETTING=$2; shift 2 ;;
        --wandb-job-type) WANDB_JOB_TYPE_SETTING=$2; shift 2 ;;
        --wandb-tags) WANDB_TAGS_SETTING=$2; shift 2 ;;
        --log-every) LOG_EVERY=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

case "$MODE" in
    smoke)
        TOTAL_STEPS=${TOTAL_STEPS:-2}
        CHECKPOINT_STEP=${CHECKPOINT_STEP:-$((TOTAL_STEPS - 1))}
        TEXT_DROPOUT=0.1
        VIT_DROPOUT=0.1
        WARMUP_STEPS=1
        LR=0.00001
        ;;
    resume)
        TOTAL_STEPS=${TOTAL_STEPS:-3}
        CHECKPOINT_STEP=${CHECKPOINT_STEP:-$((TOTAL_STEPS - 1))}
        TEXT_DROPOUT=0.1
        VIT_DROPOUT=0.1
        WARMUP_STEPS=1
        LR=0.00001
        ;;
    *) echo "--mode must be smoke or resume" >&2; exit 2 ;;
esac

if [[ -z "$DATASET_CONFIG" || -z "$RUN_NAME" ]]; then
    usage >&2
    exit 2
fi
if [[ "$WANDB_MODE_SETTING" != offline && "$WANDB_MODE_SETTING" != online ]]; then
    echo "--wandb-mode must be offline or online" >&2
    exit 2
fi
if [[ "$WANDB_MODE_SETTING" == offline ]]; then
    WANDB_OFFLINE_FLAG=True
else
    WANDB_OFFLINE_FLAG=False
fi
if [[ -z "$WANDB_PROJECT_SETTING" ]]; then
    echo "--wandb-project must not be empty" >&2
    exit 2
fi
WANDB_RUN_ID_SETTING=${WANDB_RUN_ID_SETTING:-$RUN_NAME}
if ! [[ "$WANDB_RUN_ID_SETTING" =~ ^[A-Za-z0-9._-]{1,64}$ ]]; then
    echo "--wandb-run-id must contain 1..64 letters, digits, dots, underscores, or hyphens" >&2
    exit 2
fi
if [[ ! -f "$DATASET_CONFIG" ]]; then
    echo "Dataset config does not exist: $DATASET_CONFIG" >&2
    exit 2
fi
if [[ ! -x "$TORCHRUN" ]]; then
    echo "torchrun executable does not exist: $TORCHRUN" >&2
    exit 2
fi
if [[ ! -d "$MODEL_PATH" || ! -d "$VIT_PATH" ]]; then
    echo "Lance model or ViT path is missing under $LANCE_ROOT/downloads" >&2
    exit 2
fi
if [[ "$MODE" == resume && -z "$RESUME_FROM" ]]; then
    echo "--mode resume requires --resume-from" >&2
    exit 2
fi
if [[ -n "$RESUME_FROM" && ! -d "$RESUME_FROM" ]]; then
    echo "Resume checkpoint does not exist: $RESUME_FROM" >&2
    exit 2
fi
if ! [[ "$TOTAL_STEPS" =~ ^[1-9][0-9]*$ && "$CHECKPOINT_STEP" =~ ^[0-9]+$ ]]; then
    echo "step values must be non-negative integers and total steps must be positive" >&2
    exit 2
fi
if ((CHECKPOINT_STEP >= TOTAL_STEPS)); then
    echo "checkpoint step must be lower than total steps" >&2
    exit 2
fi
if ! [[ "$NUM_WORKERS" =~ ^[0-9]+$ && "$MASTER_PORT" =~ ^[0-9]+$ && "$LOG_EVERY" =~ ^[1-9][0-9]*$ ]]; then
    echo "worker count and master port must be non-negative integers; log interval must be positive" >&2
    exit 2
fi
if [[ "$WANDB_MODE_SETTING" == online && -z "${WANDB_API_KEY:-}" ]]; then
    WANDB_NETRC=${NETRC:-${HOME}/.netrc}
    if [[ ! -f "$WANDB_NETRC" ]] || ! rg -q 'machine[[:space:]]+api\.wandb\.ai' "$WANDB_NETRC"; then
        echo "W&B online mode requires WANDB_API_KEY or a prior 'wandb login' on this node" >&2
        exit 2
    fi
fi

DATASET_CONFIG=$(realpath "$DATASET_CONFIG")
OUTPUT_ROOT=$(realpath -m "$OUTPUT_ROOT")
if [[ -n "$RESUME_FROM" ]]; then
    RESUME_FROM=$(realpath "$RESUME_FROM")
fi
RUN_DIR="$OUTPUT_ROOT/$RUN_NAME"
if [[ -e "$RUN_DIR" ]]; then
    echo "Refusing to reuse existing run directory: $RUN_DIR" >&2
    exit 2
fi
mkdir -p "$RUN_DIR"
LOG_FILE="$RUN_DIR/launcher.log"

export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
export NCCL_DEBUG=${NCCL_DEBUG:-WARN}
export PYTHONWARNINGS="${PYTHONWARNINGS:+$PYTHONWARNINGS,}ignore::FutureWarning:deepspeed.runtime.zero.linear"
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}
export WANDB_MODE="$WANDB_MODE_SETTING"
export WANDB_PROJECT="$WANDB_PROJECT_SETTING"
export WANDB_RUN_ID="$WANDB_RUN_ID_SETTING"
export WANDB_RESUME=allow
export WANDB_DISABLE_CODE=true
export WANDB_CONSOLE=off
export WANDB_LOG_MODEL=false
if [[ -n "$WANDB_ENTITY_SETTING" ]]; then
    export WANDB_ENTITY="$WANDB_ENTITY_SETTING"
fi
if [[ -n "$WANDB_GROUP_SETTING" ]]; then
    export WANDB_RUN_GROUP="$WANDB_GROUP_SETTING"
fi
if [[ -n "$WANDB_JOB_TYPE_SETTING" ]]; then
    export WANDB_JOB_TYPE="$WANDB_JOB_TYPE_SETTING"
fi
if [[ -n "$WANDB_TAGS_SETTING" ]]; then
    export WANDB_TAGS="$WANDB_TAGS_SETTING"
fi
export HF_HOME=${HF_HOME:-/scratch/prj0000000275/jcy/.cache/huggingface}
export PYTHONPATH="$LANCE_ROOT${PYTHONPATH:+:$PYTHONPATH}"

RESUME_ARGS=(--auto_resume False --resume_model_only False --load_data_status False)
if [[ -n "$RESUME_FROM" ]]; then
    RESUME_ARGS+=(--resume_from "$RESUME_FROM" --load_data_status True)
fi

COMMAND=(
    "$TORCHRUN"
    --nnodes 1
    --nproc-per-node 1
    --node-rank 0
    --master-addr 127.0.0.1
    --master-port "$MASTER_PORT"
    train/unified_train.py
    --model_path "$MODEL_PATH"
    --vit_path "$VIT_PATH"
    --vit_type qwen_2_5_vl_original
    --llm_qk_norm True
    --llm_qk_norm_und True
    --llm_qk_norm_gen True
    --tie_word_embeddings False
    --max_num_frames 121
    --max_latent_size 64
    --latent_patch_size 1 1 1
    --load_from_lance_checkpoint True
    --init_from_vlm_checkpoint False
    --copy_init_moe True
    --visual_und True
    --visual_gen True
    --vae_model_type wan
    --freeze_llm False
    --freeze_llm_embed_tokens True
    --freeze_vit True
    --freeze_vae True
    --freeze_und_params False
    --freeze_und False
    --dataset_config_file "$DATASET_CONFIG"
    --val_dataset_config_file "$DATASET_CONFIG"
    --num_workers "$NUM_WORKERS"
    --prefetch_factor 2
    --expected_num_tokens 65536
    --max_num_tokens 65536
    --max_num_tokens_per_sample 65536
    --prefer_buffer_before 65536
    # Every DataMake prefix is > half of the 65,536-token pack, so no two rows
    # can share a pack. Disable the 50-row fit-search buffer to avoid decoding
    # dozens of 1440p videos before the first optimization step.
    --max_buffer_size 0
    --require_und_gen True
    --data_seed 2026
    --global_seed 2026
    --text_cond_dropout_prob "$TEXT_DROPOUT"
    --vae_cond_dropout_prob 0
    --vit_cond_dropout_prob "$VIT_DROPOUT"
    --warmup_steps "$WARMUP_STEPS"
    --lr_scheduler constant
    --lr "$LR"
    --min_lr 0.000001
    --beta1 0.9
    --beta2 0.95
    --eps 0.000000000000001
    --max_grad_norm 1.0
    --ce_weight 0.25
    --mse_weight 1.0
    --timestep_shift 4.0
    --use_flex True
    --num_replicate 1
    --num_shard 1
    --use_ema False
    "${RESUME_ARGS[@]}"
    --outputs_dir "$OUTPUT_ROOT"
    --total_steps "$TOTAL_STEPS"
    --save_every 1000000
    --log_every "$LOG_EVERY"
    --ckpt_debug_steps "$CHECKPOINT_STEP"
    --wandb_project "$WANDB_PROJECT_SETTING"
    --wandb_name "$RUN_NAME"
    --wandb_runid "$WANDB_RUN_ID_SETTING"
    --wandb_resume allow
    --wandb_offline "$WANDB_OFFLINE_FLAG"
    --validation_step -1
    --validation_type und_gen
    --validation_num_timesteps 10
    --validation_timestep_shift 3.0
    --validation_max_samples 1
    --validation_log_type direct
    --apply_qwen_2_5_vl_pos_emb True
    --apply_chat_template False
)

{
    echo "started_at=$(date --iso-8601=seconds)"
    echo "host=$(hostname)"
    echo "mode=$MODE"
    echo "dataset_config=$DATASET_CONFIG"
    echo "output_root=$OUTPUT_ROOT"
    echo "run_name=$RUN_NAME"
    echo "total_steps=$TOTAL_STEPS"
    echo "checkpoint_step=$CHECKPOINT_STEP"
    echo "resume_from=${RESUME_FROM:-none}"
    echo "wandb_mode=$WANDB_MODE_SETTING"
    echo "wandb_project=$WANDB_PROJECT_SETTING"
    echo "wandb_entity=${WANDB_ENTITY_SETTING:-default}"
    echo "wandb_run_id=$WANDB_RUN_ID_SETTING"
    echo "wandb_group=${WANDB_GROUP_SETTING:-none}"
    echo "wandb_job_type=${WANDB_JOB_TYPE_SETTING:-none}"
    echo "wandb_tags=${WANDB_TAGS_SETTING:-none}"
    echo "log_every=$LOG_EVERY"
    echo "full_parameter_route=True"
    echo "lora=False"
    nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.free,driver_version --format=csv,noheader
    printf 'command='
    printf '%q ' "${COMMAND[@]}"
    printf '\n'
} | tee "$RUN_DIR/launch_metadata.txt"

set +e
(
    cd "$LANCE_ROOT"
    "${COMMAND[@]}"
) 2>&1 | tee "$LOG_FILE"
TRAIN_EXIT=${PIPESTATUS[0]}
set -e

if ((TRAIN_EXIT != 0)); then
    echo "Training process exited with status $TRAIN_EXIT" >&2
    exit "$TRAIN_EXIT"
fi
if rg -q '\[TRAINING EXCEPTION\]|Non-finite loss|bad data at step' "$LOG_FILE"; then
    echo "Training loop logged a skipped/invalid step; see $LOG_FILE" >&2
    exit 3
fi
if ! rg -q 'Done!' "$LOG_FILE"; then
    echo "Training process did not log normal completion" >&2
    exit 3
fi
printf -v CHECKPOINT_BASENAME '%07d' "$CHECKPOINT_STEP"
CHECKPOINT_DIR="$RUN_DIR/checkpoints/$CHECKPOINT_BASENAME"
for artifact in model.safetensors optimizer.00000-of-00001.pt scheduler.pt data_status.pt; do
    if [[ ! -f "$CHECKPOINT_DIR/$artifact" ]]; then
        echo "Expected checkpoint artifact is missing: $CHECKPOINT_DIR/$artifact" >&2
        exit 3
    fi
done

{
    echo "finished_at=$(date --iso-8601=seconds)"
    echo "status=passed"
    echo "checkpoint=$CHECKPOINT_DIR"
    du -sh "$CHECKPOINT_DIR"
} | tee "$RUN_DIR/result.txt"
