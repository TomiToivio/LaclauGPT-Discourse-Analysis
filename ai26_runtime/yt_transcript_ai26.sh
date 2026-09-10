#!/usr/bin/env bash
# yt_transcript_ai26.sh <youtube_url> <arena> [label]
# Fetch a YouTube video's auto-captions (transcript only, no video download),
# build a canonical manual record, ingest via `laclaugpt collect manual`,
# and push into ai26_sources (Mongo).
set -uo pipefail
URL="$1"
ARENA="${2:-elites}"
REPO=LACLAUGPT_REPO_ROOT
RUN_DIR=/tmp/ai26-yt-$(date +%s)
mkdir -p "$RUN_DIR"
cd "$REPO"

# 1. video id from URL
YTID=$(echo "$URL" | grep -oE 'v=[A-Za-z0-9_-]{11}' | cut -d= -f2)
[ -z "$YTID" ] && YTID=$(basename "$URL")

# 2. captions only — json3 format sidesteps the vtt 429; two attempts
for i in 1 2; do
    python3 -m yt_dlp --skip-download --write-auto-subs \
        --sub-langs 'en-orig,en' --sub-format json3 --sleep-requests 4 \
        -o "$RUN_DIR/%(id)s" "$URL" >> "$RUN_DIR/yt.log" 2>&1
    ls "$RUN_DIR"/*json3* >/dev/null 2>&1 && break
    sleep 45
done
ls "$RUN_DIR"/*json3* >/dev/null 2>&1 || { echo "yt-dlp failed: see $RUN_DIR/yt.log"; exit 1; }

# 3. transcript -> plain text
python3 - "$YTID" "$RUN_DIR" <<'PEOF'
import glob, json, sys

ytid, run_dir = sys.argv[1], sys.argv[2]
cands = sorted(glob.glob(f"{run_dir}/{ytid}*.json3")) or sorted(
    glob.glob(f"{run_dir}/{ytid}*.vtt"))
if not cands:
    print("NO_CAPTIONS"); sys.exit(1)
d = json.load(open(cands[0], encoding="utf-8"))
lines = []
for e in d.get("events", []):
    segs = e.get("segs") or []
    lines.append("".join(s.get("utf8", "") for s in segs))
text = " ".join(" ".join(lines).split())
open(f"{run_dir}/transcript.txt", "w", encoding="utf-8").write(text)
print(f"TRANSCRIPT {len(text)} chars from {cands[0]}")
PEOF

# 4. metadata via oEmbed (keyless, no yt-dlp rate pressure)
META=$(curl -s "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=$YTID&format=json")
TITLE=$(echo "$META" | python3 -c "import json,sys;print(json.load(sys.stdin)['title'])")
AUTHOR=$(echo "$META" | python3 -c "import json,sys;print(json.load(sys.stdin)['author_name'])")

# 5. canonical manual ingest (transcript = SOURCE TEXT; note = collector comment)
python3 -m laclaugpt.cli collect manual \
    --file "$RUN_DIR/transcript.txt" \
    --url "https://www.youtube.com/watch?v=$YTID" \
    --title "$TITLE" \
    --author "$AUTHOR" \
    --notes "YouTube auto-caption transcript (en), video https://www.youtube.com/watch?v=$YTID; collector note is NOT source text. AI26 sampling metadata." \
    2>&1 | tail -1

# 6. push NEW rows into ai26_sources
ARENA="$ARENA" python3 - "$RUN_DIR" <<'PEOF2'
import glob, json, os, sys
sys.path.insert(0, "LACLAUGPT_REPO_ROOT/ai26_runtime")
sys.path.insert(0, "LACLAUGPT_REPO_ROOT")
from mongo_writer import get_db
db = get_db()
existing = {r["ingestion_id"] for r in db["ai26_ingestion"].find({}, {"ingestion_id": 1})}
saved = 0
with open("LACLAUGPT_REPO_ROOT/collection-data/normalized/manual.jsonl",
          encoding="utf-8") as fh:
    for line in fh:
        payload = json.loads(line)
        src, ing = payload["source"], payload["ingestion"]
        if ing["ingestion_id"] in existing:
            continue
        src["metadata"]["arena"] = os.environ["ARENA"]
        src["metadata"]["ingestion_id"] = ing["ingestion_id"]
        r = db["ai26_sources"].update_one(
            {"source_type": src["source_type"],
             "normalized_source_url": src.get("normalized_source_url")},
            {"$setOnInsert": src}, upsert=True)
        if r.upserted_id:
            saved += 1
            db["ai26_ingestion"].insert_one(ing)
print(f"manual -> mongo: saved {saved}")
PEOF2
echo "done: $RUN_DIR"