#!/bin/bash
#SBATCH -J dm_mix8_chain
#SBATCH -A prj0000000275
#SBATCH --partition=testqueue
#SBATCH --qos=highpriority
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:h200:8
#SBATCH --cpus-per-task=112
#SBATCH --mem=1024G
#SBATCH --time=18:00:00
#SBATCH --output=/scratch/prj0000000275/jcy/xks/DataMake/10_research/model_experiments/lance/outputs/slurm_logs/coinve_mixed_chain_predx0_ddp8_%j.out
#SBATCH --error=/scratch/prj0000000275/jcy/xks/DataMake/10_research/model_experiments/lance/outputs/slurm_logs/coinve_mixed_chain_predx0_ddp8_%j.err

set -euo pipefail
source /home/users/astar/cfar/stuchengyou/.init.sh
source /apps/miniforge/24.11.3/etc/profile.d/conda.sh
LANCE_ENV=${DATAMAKE_LANCE_ENV:-/scratch/prj0000000275/jcy/.conda/envs/xks_lance}
conda activate "$LANCE_ENV"
cd /scratch/prj0000000275/jcy/xks/DataMake/10_research/model_experiments/lance
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy
export OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
"$LANCE_ENV/bin/python" scripts/run_datamake_chain_pred_x0_ddp_training.py \
  --profile configs/datamake_coinve_mixed_ddp8_lora64_both_chain_pred_x0_no_region_v2.json \
  --resume-from "${RESUME_FROM:-none}" \
  --mode "${DDP_MODE:-validate}"
