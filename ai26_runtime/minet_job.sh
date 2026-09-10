#!/usr/bin/env bash
# AI26 minet batch: URL-list -> minet fetch+extract -> laclaugpt collect minet -> ai26_sources
# Usage: minet_job.sh <urls.txt> <arena>
# minet 4.2.1: fetch needs -i csv; extract reads the fetch report with
# --body-column pointing at the column that holds the HTML bodies. Fetch stores
# contents on disk next to the report (folder next to -o output).
set -euo pipefail
URLS="$1"
ARENA="${2:-elites}"
RUN_DIR=/tmp/ai26-minet-$(date +%s)
mkdir -p "$RUN_DIR"
cd LACLAUGPT_REPO_ROOT

printf 'url\n' > "$RUN_DIR/urls.csv"
grep -vE '^\s*(#|$)' "$URLS" >> "$RUN_DIR/urls.csv"

# 1. fetch (HTTP); contents land in $RUN_DIR/contents, report in fetched.csv
~/.local/bin/minet fetch url -i "$RUN_DIR/urls.csv" -o "$RUN_DIR/fetched.csv" \
    2>"$RUN_DIR/fetch.err"

# 2. extract main text (trafilatura) from the fetch report
~/.local/bin/minet extract path -i "$RUN_DIR/fetched.csv" \
    --body-column body_text -o "$RUN_DIR/extracted.csv" \
    2>"$RUN_DIR/extract.err" || true

# 3. import through the existing adapter into the canonical spine
python3 -m laclaugpt.cli collect minet "$RUN_DIR/extracted.csv" \
    --kind extract --text-column content || true

# 4. push the fresh JSONL into ai26_sources
ARENA="$ARENA" python3 - << 'PEOF'
import os, sys
from pathlib import Path
sys.path.insert(0, "LACLAUGPT_REPO_ROOT/ai26_runtime")
from mongo_writer import ingest_jsonl, get_db
db = get_db()
minet = Path("collection-data/normalized/minet.jsonl")
if minet.exists():
    stats = ingest_jsonl(str(minet), arena=os.environ.get("ARENA", "elites"))
    print("minet -> mongo:", stats)
else:
    print("no minet.jsonl produced")
PEOF
echo "minet job done: $RUN_DIR"