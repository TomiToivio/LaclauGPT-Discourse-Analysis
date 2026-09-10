#!/bin/bash
#SBATCH --job-name=ep24_full_poland
#SBATCH --partition=gpumedium
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gpus=1
#SBATCH --output=ep24_full_poland_%j.out

set -euo pipefail
REPO_ROOT=/users/totoivio/LaclauGPT-Discourse-Analysis
DATA_ROOT=/scratch/project_2009497/laclaugpt2
cd "$REPO_ROOT"

module load python-pytorch/2.10
module load ffmpeg

export LACLAUGPT_MEMORY_DIR=$DATA_ROOT/memory
export LACLAUGPT_DATA_DIR=$DATA_ROOT
export TMPDIR=${TMPDIR:-/tmp}

# faster-whisper is local (GPU); LLM stages talk to Ollama Cloud
python ep24_full_pipeline.py --country poland \
    --data-root "$DATA_ROOT" --repo-root "$REPO_ROOT"
