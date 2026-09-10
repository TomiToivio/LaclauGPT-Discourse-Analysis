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

# LLM stages run on the LOCAL Ollama server (gemma4:26b) inside this job:
# auto mode would route a weak-GPU login node to cloud; force local + model.
export LLM_MODE=local
export LACLAUGPT_OLLAMA_MODEL=gemma4:26b
export OLLAMA_HOST=http://127.0.0.1:11434
export OLLAMA_KEEP_ALIVE=24h

# one ollama serve per job (ephemeral, on the allocated node)
mkdir -p "$DATA_ROOT/ollama"
export OLLAMA_MODELS="$DATA_ROOT/ollama/models"
if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  "$DATA_ROOT/ollama/bin/ollama" serve >"$DATA_ROOT/ollama/serve.log" 2>&1 &
  for i in $(seq 1 30); do
    curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    sleep 2
  done
fi
ollama pull gemma4:26b

# faster-whisper is local (GPU); LLM stages talk to the local Ollama
python ep24_full_pipeline.py --country poland \
    --data-root "$DATA_ROOT" --repo-root "$REPO_ROOT"
