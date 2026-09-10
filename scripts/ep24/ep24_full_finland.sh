#!/bin/bash
#SBATCH --job-name=ep24_full_finland
#SBATCH --partition=gpumedium
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gpus=1
#SBATCH --output=ep24_full_finland_%j.out

set -euo pipefail
REPO_ROOT=LACLAUGPT_REPO_ROOT
DATA_ROOT=LACLAUGPT_DATA_DIR
cd "$REPO_ROOT"

module load python-pytorch/2.10
module load ffmpeg

export LACLAUGPT_MEMORY_DIR=$DATA_ROOT/memory
export LACLAUGPT_DATA_DIR=$DATA_ROOT
export TMPDIR=${TMPDIR:-/tmp}

# faster-whisper is local (GPU); LLM stages talk to Ollama Cloud
python ep24_full_pipeline.py --country finland \
    --data-root "$DATA_ROOT" --repo-root "$REPO_ROOT"
