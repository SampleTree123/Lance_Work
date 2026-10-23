#!/usr/bin/env bash
#SBATCH --job-name=dm-first-batch-production
#SBATCH --partition=testqueue
#SBATCH --account=prj0000000275
#SBATCH --qos=highpriority
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=14
#SBATCH --gres=gpu:h200:1
#SBATCH --mem=250G
#SBATCH --time=18:00:00

set -euo pipefail

ROOT="${DM_ROOT:-/scratch/prj0000000275/jcy/xks/DataMake}"
: "${DM_PRODUCTION_RUN_ROOT:?Set DM_PRODUCTION_RUN_ROOT to a new versioned Run Root}"
: "${DM_DELIVERY_ROOT:?Set DM_DELIVERY_ROOT to a new versioned dataset_v1 directory}"
RUN_ROOT="${DM_PRODUCTION_RUN_ROOT}"
DELIVERY_ROOT="${DM_DELIVERY_ROOT}"
ENGINE_ROOT="${DM_ENGINE_ROOT:-/scratch/prj0000000275/jcy/sx/UnrealEngine}"
UPROJECT="${DM_UPROJECT:-${ROOT}/00_engine/projects/datatry_02/datatry_02.uproject}"
GRAPH_ROOT="${DM_GRAPH_ROOT:-${ROOT}/00_engine/outputs/first_batch_dataset/graph_20260824_v1}"
PROMPT_ROOT="${DM_PROMPT_ROOT:-${GRAPH_ROOT}/text_first_batch_20260824_v2}"
FFMPEG_EXE="${DM_FFMPEG_EXE:-/scratch/prj0000000275/jcy/.conda/envs/Univid/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2}"

export DM_FFMPEG_EXE="${FFMPEG_EXE}"

cd "${ROOT}"

exec python "${ROOT}/00_engine/scripts/unreal/run_first_batch_server_production.py" \
  --run-root "${RUN_ROOT}" \
  --delivery-root "${DELIVERY_ROOT}" \
  --engine-root "${ENGINE_ROOT}" \
  --uproject "${UPROJECT}" \
  --graph-root "${GRAPH_ROOT}" \
  --prompt-root "${PROMPT_ROOT}" \
  --batch-size 50 \
  --max-invocations-per-batch 2 \
  --confirm-full-run
