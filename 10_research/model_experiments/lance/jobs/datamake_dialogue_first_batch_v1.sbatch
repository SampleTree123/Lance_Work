#!/bin/bash

#SBATCH -A prj0000000275
#SBATCH --job-name=dm_lance_dialogue_v1
#SBATCH --partition=testqueue
#SBATCH --qos=highpriority
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:h200:4
#SBATCH --cpus-per-task=56
#SBATCH --mem=1024G
#SBATCH --time=18:00:00
#SBATCH --output=/home/users/astar/cfar/stuchengyou/jcy/xks/DataMake/10_research/model_experiments/lance/outputs/slurm_logs/dm_lance_dialogue_v1_%j.out
#SBATCH --error=/home/users/astar/cfar/stuchengyou/jcy/xks/DataMake/10_research/model_experiments/lance/outputs/slurm_logs/dm_lance_dialogue_v1_%j.err

set -euo pipefail

source ~/.init.sh
source /apps/miniforge/24.11.3/etc/profile.d/conda.sh

WORK_DIR=/home/users/astar/cfar/stuchengyou/jcy/xks/DataMake
LANCE_DIR="$WORK_DIR/10_research/model_experiments/lance"
LANCE_ENV=${DATAMAKE_LANCE_ENV:-/scratch/prj0000000275/jcy/.conda/envs/xks_lance}
PROFILE=${DATAMAKE_FORMAL_PROFILE:-$LANCE_DIR/configs/datamake_dialogue_first_batch_v1.json}
RESUME_VALUE=${RESUME_FROM:-none}

cd "$LANCE_DIR"
conda activate "$LANCE_ENV"

# ~/.init.sh carries a localhost proxy that is valid only on the submit host.
# Compute nodes have direct W&B access, so inherited proxy variables must not
# be passed to the preflight or training process.
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY
unset http_proxy https_proxy all_proxy no_proxy

export DATAMAKE_LANCE_ENV="$LANCE_ENV"
export OMP_NUM_THREADS=1
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

report_exit() {
  exit_status=$?
  echo "finished_at=$(date --iso-8601=seconds)"
  echo "exit_status=$exit_status"
}
trap report_exit EXIT

echo "started_at=$(date --iso-8601=seconds)"
echo "slurm_job_id=${SLURM_JOB_ID:?SLURM_JOB_ID is required}"
echo "host=$(hostname)"
echo "work_dir=$WORK_DIR"
echo "python=$(command -v python)"
echo "profile=$PROFILE"
echo "resume_from=$RESUME_VALUE"
echo "stdout_log=$LANCE_DIR/outputs/slurm_logs/dm_lance_dialogue_v1_${SLURM_JOB_ID}.out"
echo "stderr_log=$LANCE_DIR/outputs/slurm_logs/dm_lance_dialogue_v1_${SLURM_JOB_ID}.err"
nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.free,driver_version --format=csv,noheader

python "$LANCE_DIR/scripts/run_datamake_formal_training.py" \
  --profile "$PROFILE" \
  --resume-from "$RESUME_VALUE"
