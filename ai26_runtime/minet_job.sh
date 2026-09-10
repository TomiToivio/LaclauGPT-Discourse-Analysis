#!/usr/bin/env bash
# AI26 minet batch: URL-list -> minet fetch+extract -> laclaugpt collect minet -> canonical sources
# Usage: minet_job.sh <urls.txt> <arena>
set -euo pipefail
URLS="$1"
ARENA="${2:-elites}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="${LACLAUGPT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
RUN_DIR="${TMPDIR:-/tmp}/ai26-minet-$(date +%s)"
MINET_BIN="${MINET_BIN:-$HOME/.local/bin/minet}"
mkdir -p "$RUN_DIR"
cd "$REPO"

printf 'url\n' > "$RUN_DIR/urls.csv"
grep -vE '^\s*(#|$)' "$URLS" >> "$RUN_DIR/urls.csv"

"$MINET_BIN" fetch url -i "$RUN_DIR/urls.csv" -o "$RUN_DIR/fetched.csv" \
    2>"$RUN_DIR/fetch.err"

"$MINET_BIN" extract path -i "$RUN_DIR/fetched.csv" \
    --body-column body_text -o "$RUN_DIR/extracted.csv" \
    2>"$RUN_DIR/extract.err" || true

python3 -m laclaugpt.cli collect minet "$RUN_DIR/extracted.csv" \
    --kind extract --text-column content || true

ARENA="$ARENA" python3 - << 'PEOF'
import os, sys
from pathlib import Path
repo = Path.cwd()
sys.path.insert(0, str(repo / "ai26_runtime"))
from mongo_writer import ingest_jsonl
minet = repo / "collection-data" / "normalized" / "minet.jsonl"
if minet.exists():
    stats = ingest_jsonl(str(minet), arena=os.environ.get("ARENA", "elites"))
    print("minet -> mongo:", stats)
else:
    print("no minet.jsonl produced")
PEOF
echo "minet job done: $RUN_DIR"
