#!/bin/bash
#SBATCH -J dm_cfg4_gt1650
#SBATCH -A prj0000000275
#SBATCH --partition=testqueue
#SBATCH --qos=highpriority
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --gres=gpu:h200:4
#SBATCH --cpus-per-task=14
#SBATCH --mem=512G
#SBATCH --time=06:00:00
#SBATCH --output=/scratch/prj0000000275/jcy/xks/DataMake/10_research/model_experiments/lance/outputs/slurm_logs/cfg4_%j.out
#SBATCH --error=/scratch/prj0000000275/jcy/xks/DataMake/10_research/model_experiments/lance/outputs/slurm_logs/cfg4_%j.err
set -euo pipefail
source /home/users/astar/cfar/stuchengyou/.init.sh
source /apps/miniforge/24.11.3/etc/profile.d/conda.sh
conda activate /scratch/prj0000000275/jcy/.conda/envs/xks_lance
cd /scratch/prj0000000275/jcy/xks/DataMake/10_research/model_experiments/lance
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy
export OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export HF_HOME=/scratch/prj0000000275/jcy/.cache/huggingface
RUN_ROOT="$PWD/outputs/multiturn_chat/mixed_cfg_gt1650_job${SLURM_JOB_ID}"
CHECKPOINT="$PWD/outputs/optimization_diagnostics/cfg_gt1650_shared_snapshot"
mkdir -p "$RUN_ROOT"
python scripts/run_datamake_cfg4.py --plan-only --root "$RUN_ROOT" --checkpoint "$CHECKPOINT" > "$RUN_ROOT/plan.json"
srun --kill-on-bad-exit=1 --gpu-bind=single:1 python scripts/run_datamake_cfg4.py --root "$RUN_ROOT" --checkpoint "$CHECKPOINT"
python scripts/build_datamake_cfg4_review.py --root "$RUN_ROOT"
