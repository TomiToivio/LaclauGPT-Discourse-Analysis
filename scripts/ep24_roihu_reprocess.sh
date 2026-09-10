#!/bin/bash
#SBATCH --job-name=ep24-reprocess
#SBATCH --partition=gpumedium
#SBATCH --time=1-12:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=120G
#SBATCH --gres=gpu:gh200:1
#SBATCH --array=0-1
#SBATCH --output=ep24_reprocess_%A_%a.out
#SBATCH --error=ep24_reprocess_%A_%a.err

set -euo pipefail
REPO_ROOT=${REPO_ROOT:-LACLAUGPT_REPO_ROOT}
DATA_ROOT=${LACLAUGPT_DATA_DIR:-LACLAUGPT_DATA_DIR}
SOURCE_CSV=${EP24_SOURCE_CSV:-$DATA_ROOT/ep24/source/dashboard_9_1_2026.csv}
SAMPLE_SIZE=${EP24_SAMPLE_SIZE:-0}
countries=(finland poland)
country=${countries[$SLURM_ARRAY_TASK_ID]}
run_root=$DATA_ROOT/ep24/reprocess/$country
mkdir -p "$run_root" "$DATA_ROOT/ep24/videos"
cd "$REPO_ROOT"

module purge
module load pytorch
module load ffmpeg
source .venv-roihu/bin/activate
export LLM_MODE=local
export OLLAMA_HOST=http://127.0.0.1:11434
export LACLAUGPT_DATA_DIR=$DATA_ROOT
export TMPDIR=${TMPDIR:-/tmp}

command -v ollama >/dev/null || { echo "ollama is not on PATH" >&2; exit 2; }
ollama serve >"$run_root/ollama.log" 2>&1 &
ollama_pid=$!
trap 'kill "$ollama_pid" 2>/dev/null || true' EXIT
for _ in {1..60}; do
  curl --fail --silent "$OLLAMA_HOST/api/tags" >/dev/null 2>&1 && break
  sleep 1
done
curl --fail --silent --show-error "$OLLAMA_HOST/api/tags" >/dev/null
ollama pull gemma4:26b

python -m scripts.ep24_roihu_reprocess \
  --country "$country" \
  --source-csv "$SOURCE_CSV" \
  --data-root "$DATA_ROOT" \
  --sample-size "$SAMPLE_SIZE"
