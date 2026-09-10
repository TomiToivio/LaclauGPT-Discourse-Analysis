# Laskin AI26 realtime deployment (operational notes)

Machine: `laskin01` (Linux GPU web server, 3x Tesla V100-32GB, MongoDB 8.0,
Ollama). Repo at `/mnt/workspace/LaclauGPT-Discourse-Analysis` (git, tracks
origin/main). Private runtime settings at `~/.config/laclaugpt/ai26/`
(chmod 700 dir, chmod 600 credential files) — **never committed**.

This is the concrete `linux-gpu-realtime` + `realtime-fullstack` deployment
(docs/DEPLOYMENT_PROFILES.md §4), machine-local and uncommitted:
`~/.config/laclaugpt/ai26/machine_override.yaml`.

## Implemented (2026-09-08)

### Canonical spine
One corpus, one ontology. Every channel writes `CollectRecord →
SourceItem/IngestionRecord/Provenance` through the repo's `laclaugpt collect`
CLI, then an ai26_runtime writer upserts into MongoDB `vasama_ai.ai26_*`
collections (`ai26_sources`, `ai26_ingestion`, `ai26_annotations`,
`ai26_graph_nodes/edges`, `ai26_runs`, `ai26_review`, `ai26_registry`).
Dedup: repo-level CollectionStore ledger + unique Mongo indexes; acquisition
provenance preserved (RSS→article, YouTube, Telegram, Hermes, manual, minet
resolve to the same document without merging distinct provenance records).

### Collection (systemd user timers)
| Unit | Cadence | Function |
|---|---|---|
| `ai26-rss.timer/.service` | 30 min | feeds.txt → `collect rss --fetch-article` → Mongo |
| `ai26-youtube.timer/.service` | hourly | channel RSS (youtube.txt) → Mongo |
| `ai26-telegram.timer/.service` | 15 min | vasama_ai.events bridge → Mongo (adapter boundary to the external Telegram collector; no telethon here) |
| `ai26-analysis.timer/.service` | 10 min | incremental analysis worker (batch 6) |
| `ai26-export.timer/.service` | 10 min | Mongo → canonical annotation JSONL for the dashboard |
| `ai26-backup.timer` (system) | nightly 02:45 | mongodump gzip archives, 7d/4w/6m retention |

Logs: `~/.config/laclaugpt/ai26/{rss,youtube,telegram,analysis,dashboard,export}.log`.
Source lists (`feeds.txt`, `youtube.txt`, `telegram.txt`) are research
sampling metadata and stay private.

### Analysis: stage-aware local gemma4 routing
`laclaugpt/model_routing.py` (Tomi's rule, 2026-09-08): pick the Gemma 4 tier
by pipeline stage, never cloud. `pipeline.Stage.call` resolves the model per
stage via `pick_model(stage, text_len)` when the configured model is a local
gemma4 tag (non-gemma4 configs are untouched; router failure falls back to the
configured model):

| Stage | Default tier | Notes |
|---|---|---|
| summary | gemma4:e4b | dense summary |
| discourse | gemma4:31b | Laclau/Palonen coding + verbatim evidence |
| postprocess | gemma4:e2b | structured extraction |
| populism | gemma4:26b | Us/Frontier judgement |

Long texts (>8000 chars) escalate one tier; `_loaded_models`/`_free_vram_gb`
guard against VRAM exhaustion (V100-32GB per GPU). Actual served model,
digest, mode and fallback reason are recorded in stage provenance and the
SQLite stage cache keys (per-stage DBs under `data/<arena>/database/`).

Throughput on Laskin: `OLLAMA_KEEP_ALIVE=24h` keeps all tiers resident across
stage rotation (3x V100 = 96 GB; ~37 s per cold load otherwise). With warm
tiers: ~24 docs/hour sustained (batch 6, long institutional posts; short items
peaked ~80/h). No cloud fallback anywhere (`allow_cloud_fallback: false`,
`LLM_ALLOW_CLOUD_FALLBACK` unset).

Worker failure semantics: pipeline subprocess failure marks sources
`analysis_status=error` with the stderr tail (retryable on later ticks);
`done` is set only after annotations were actually written; every tick
appends an observability record to `ai26_runs`.

Annotation → source join: annotation `document_id` is `{platform}::{url}`;
the worker resolves both spellings against `native_id`/`source_url`/
`normalized_source_url`.

### Dashboard
Streamlit via `python3 -m laclaugpt.cli dashboard <jsonl> --project ai26
--arena elites --host 127.0.0.1 --port 8502` (systemd `ai26-dashboard.service`).
Input is canonical annotation JSONL exported from Mongo by
`ai26_runtime/export_dashboard_jsonl.py` (timer `ai26-export.timer`).
MongoDB is storage, not ontology — the dashboard consumes canonical
interchange, so the graph schema is unchanged.

### minet
`~/.local/bin/minet` 4.2.1. Batch chain in `ai26_runtime/minet_job.sh`:
`minet fetch url -i urls.csv` → `minet extract path --body-column body_text`
→ `collect minet --kind extract --text-column content` (adapter default text
field is `content`) → Mongo. Only explicitly selected URLs; no crawlers, no
X/Instagram/TikTok collectors (researcher adds the browser collector later).

### MongoDB
`mongod.conf`: `bindIp: 127.0.0.1,<TAILSCALE-IP>` (Tailscale; see private config), `authorization:
enabled`. Accounts: `vasama` (app/admin), `ai26_backup` (backup@admin —
mongodump/restore + read access, interim Vasama-OSINT read role), and
`vasama_osint` (created on admin, roles PENDING — granting `read@vasama_ai`
needs `userAdmin@vasama_ai` or root credentials, Tomi-only).
Credentials live in `~/.config/laclaugpt/ai26/mongo_users.json` (chmod 600).
Backups: `~/.config/laclaugpt/ai26/ai26_backup.sh` →
`~/ai26-backups/{archives,daily,weekly,monthly}` (system unit
`ai26-backup.timer` at 02:45; note `authSource=admin` in the dump URI).
**Restore test: NOT yet run** — blocked pending Tomi's decision/credentials;
do not claim backup safety until it succeeds.

### Benchmarks done so far
- gemma4:26b responds ~30 tok/s cold, ~71 tok/s warm; 31b similar (MoE).
- Cold model load ≈ 37 s → keep_alive is the dominant throughput lever.
- Stage routing verified serving e4b/31b/e2b/26b on real runs.

## Scaffolded / pending
- Restore test (Stage 8 acceptance) — awaiting Tomi.
- `vasama_osint` role grant — awaiting root Mongo credentials.
- Benchmark suite for gemma4:12b/31b variants on AI26 samples (structured-output
  validity + evidence fidelity on a reviewed sample).
- Temporal views (hourly/daily/weekly rollups, signifier trends) — planned as
  derived views over `ai26_annotations`, not a new store.
- Telegram source list growth; Hermes discovery submissions into ai26_registry.

## Operating notes
- User-mode systemd units must NOT set `User=` (status 216/GROUP failure).
- `ssh Laskin` non-interactive shells can't read protected journal logs; use
  script files for any Mongo `$`-prefixed operators (`\$` breaks over ssh).
- `minet fetch` requires `-i <csv>` (4.x CLI), positional bare-file input was
  removed; fetch stores contents under `<run_dir>/contents/`.
- Mongo user creation: `userAdmin@admin` may create users with roles on
  `admin` only; `read@vasama_ai` needs `userAdmin@vasama_ai`/root.
- Reanalysis reset: set `analysis_status: pending` (never re-mark `done`
  without annotations in `ai26_annotations`).