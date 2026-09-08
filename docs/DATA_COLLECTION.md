# Data collection — one canonical corpus, many input channels

LaclauGPT ingests material through several collection channels. All of
them converge into the same canonical model
(`laclaugpt.model`: `SourceItem` → `IngestionRecord` → `Provenance`,
with `Representation` for text variants) and the same analysis pipeline.
There is no per-channel document ontology: an RSS entry, a fetched web
page, a Hermes submission, a manual researcher submission and a Telegram
message all become `SourceItem`s whose collection source is metadata.

> Design principle: **many sources, one canonical corpus.** Collection
> source is explicit metadata, never an analytical category.

## Common ingestion architecture

```
source adapter (rss | web | hermes | manual | telegram)
   → CollectRecord        (laclaugpt/collect: edge-neutral shape)
   → SourceItem           (canonical, laclaugpt.model)
   → IngestionRecord      (collector name, version, timestamps)
   → Provenance           (method=collect:<channel>, imported_from)
   → collection-data/normalized/<channel>.jsonl   (gitignored)
   → analysis pipeline (pipeline.run_pipeline) → interchange/graph
```

Module: `laclaugpt/collect/` (spine) + `laclaugpt/collect/cli.py`
(CLI). Runtime data lives under `collection-data/` (gitignored —
never commit feeds, channel lists or credentials).

## Canonical fields

Every collected item carries:

| Field | Where | Notes |
|---|---|---|
| source type | `SourceItem.source_type` | `rss`/`web`/`hermes`/`manual`/`telegram` |
| source URL | `SourceItem.source_url` + `normalized_source_url` | normalized = lowercase host, tracking params stripped |
| native ID | `SourceItem.native_id` | RSS guid, Telegram message id, … |
| published at | `SourceItem.published_at` | when the source supplies it |
| collected at | `SourceItem.collected_at` | always (UTC ISO) |
| author | `SourceItem.author_text` | when available |
| text | `SourceItem.raw_text` | raw or main-text extraction |
| collection method | `IngestionRecord.collector` | `rss`/`web`/`hermes`/`manual`/`telegram` |
| collector version | `IngestionRecord.collector_version` | `laclaugpt-collect-1.0` |
| provenance | `Provenance(method=collect:<channel>)` | `imported_from` = feed URL / hermes / vasama-osint |
| project/arena | only when explicitly configured | collection is project-independent |

## Deduplication

Stable identity, checked in order:

1. `native_id` when the source provides one (`<source_type>:<id>`);
2. normalized URL (`<source_type>:url:<canonical-url>`);
3. content hash only as last fallback.

Different sources with identical text are **not** merged: the source
type is part of the dedup key (an RSS post and a fetched page are
different items). Dedup ledger: `collection-data/seen.jsonl`.

## CLI

```bash
# RSS/Atom: one or more feeds, or a config file with one URL per line
python -m laclaugpt collect rss https://example.org/feed.xml
python -m laclaugpt collect rss collection-data/feeds.txt

# Web pages (also: --urls-file urls.txt)
python -m laclaugpt collect web https://example.org/article

# Manual researcher submission
python -m laclaugpt collect manual --url https://example.org/src --title "Source"
python -m laclaugpt collect manual --text "field note" --title "Note" --author "Tomi"
python -m laclaugpt collect manual --file notes.md --title "Notes"

# Hermes Agent submission (JSON file or '-' for stdin)
python -m laclaugpt collect hermes hermes_payload.json

# Telegram (adapter: one Vasama-OSINT event as JSON)
python -m laclaugpt collect telegram telegram_event.json
```

Output per call: `{"collector_version": "...", "saved": N,
"skipped_duplicates": M}`.

## RSS

- deps: `feedparser` (parsing), optional `trafilatura` (web main text);
- fields: feed URL/name, entry guid/link, title, author, published,
  summary (HTML-stripped); `fetch_article` is a documented extension
  point (fetch linked page, reuse the web adapter);
- incremental: dedup ledger means old entries are never re-ingested;
- cron-friendly — one process, no daemon state:

```cron
# every 30 minutes, AI-corpus feeds
*/30 * * * * cd /home/tomi/LaclauGPT-Discourse-Analysis && python -m laclaugpt collect rss collection-data/feeds.txt >> collection-data/rss.log 2>&1
```

## Web fetch

- input: one URL, several URLs, or `--urls-file`;
- extraction: `trafilatura` main text when available, HTML-strip
  fallback; keeps title + HTTP status for verification;
- fetch failures are recorded and skipped, never fatal to the batch;
- not a crawler: exactly the requested URLs, no link following.

## Hermes Agent submissions

Hermes submits JSON to the collection API (or shells to the CLI):

```json
{"items": [{
    "source_type": "web",
    "url": "https://example.org/news",
    "title": "News",
    "text": "SOURCE CONTENT ONLY",
    "author": "…", "published_at": "…",
    "tags": ["ai26"],
    "hermes_metadata": {"fetched_by": "hermes", "tool": "web"},
    "hermes_commentary": "agent analytical note"
}]}
```

**Boundary rule:** only source content (`text`) enters the research
corpus. `hermes_metadata` and `hermes_commentary` are preserved inside
`SourceItem.metadata` for audit, never merged into the source text —
Hermes interpretation is not source truth.

## Manual researcher workflow

Deliberately boring and reliable: `--url`, `--text`, `--file`, plus
`--title/--author/--notes`. Manual submissions use the same provenance
path as every other channel (`method=collect:manual`) — a human
submission never bypasses data-boundary rules.

## Telegram integration

**Existing collector is reused, not duplicated.** The Vasama-OSINT
Telegram collector (`vasama_collect_telegram.py` on DEPLOYMENT_HOST: telethon
sessions → `laclaugpt_ai26.events` in MongoDB) keeps running as the
collection edge. The LaclauGPT side provides an adapter boundary:

```python
from laclaugpt.collect import collect_telegram_message, CollectionStore
record = collect_telegram_message(event_document)   # one laclaugpt_ai26 event
store.save(record)                                   # canonical SourceItem
```

CLI equivalent: `python -m laclaugpt collect telegram event.json`.
Provenance records `imported_from="vasama-osint:vasama_collect_telegram"`,
so the message remains traceable to the original collector. No second
telethon implementation exists or is planned inside LaclauGPT.

## Minet

[Minet](https://github.com/medialab/minet) is the upstream web-mining
layer (see also `docs/INTEROPERABILITY_SPEC.md` §12 and the existing
`minet_adapter`). Its CSV output joins the same spine:

```bash
# minet extract output (trafilatura-backed full text)
python -m laclaugpt collect minet extract.csv

# minet platform-collector output (twitter/youtube/telegram/...)
python -m laclaugpt collect minet collector.csv --kind collector --platform twitter

# column overrides per the interoperability spec
python -m laclaugpt collect minet extract.csv \
    --text-column text --url-column url --author-column author \
    --timestamp-column timestamp
```

Source type: `minet`, platform `minet-extract` / `minet-<platform>`;
all unmapped minet fields are preserved under
`metadata["minet"]` (spec §12 contract); provenance
`imported_from=<csv path>`. The adapter works from minet-produced
CSVs — minet itself is an optional external tool, not a LaclauGPT
dependency.

## Zeeschuimer

[Zeeschuimer](https://github.com/digitalmethodsinitiative/zeeschuimer)
captures social-platform traffic as a browser extension and exports
NDJSON. The importer reads the documented export wrapper (`data`,
`timestamp`, `platform`, `source`, `search`, `complete`, `item_index`)
and is platform-agnostic:

```bash
# default text probe: desc, caption, text, content, title, body, full_text
python -m laclaugpt collect zeeschuimer export.ndjson

# per-platform text field override
python -m laclaugpt collect zeeschuimer export.ndjson --text-fields desc,body
```

- `native_id`: Zeeschuimer item id or the platform payload's own id
  (`id`/`aweme_id`/`pk`/`code`/`rest_id`);
- author resolved from common payload shapes (`author.user.*`,
  `user.username`, `creator.nickname`, …);
- the full platform payload is preserved under
  `metadata["platform_payload"]` (lossless — payload fields are not
  flattened into the source text);
- `complete=false` items are kept but flagged (`zeeschuimer.complete`
  in metadata) — human review decides whether to use them;
- provenance: `imported_from=<ndjson path>`,
  `method=collect:zeeschuimer`.

JSON-array exports are accepted as well as line-delimited NDJSON.

## Storage

`CollectionStore` writes JSONL (`collection-data/normalized/<channel>.jsonl`)
with a dedup ledger — the same normalized-JSONL shape the existing
browser collector already produces, readable with pandas and swappable
for MongoDB/S3 later without touching the collectors.

## Configuration

- `collection-data/` — feeds, URL lists, channel lists, credentials
  (gitignored; contains per-deployment private endpoints);
- `config/` + `run_configs/` — research semantics (projects/arenas),
  unchanged by this work;
- machine/execution profiles — unchanged.

## Current limitations & extension points

- RSS `fetch_article` is a flag, article fetching reuses the web
  adapter (to be wired through the CLI in a follow-up);
- web fetch has no JS rendering (deliberate — the browser collector
  covers JS-heavy sources; Zeeschuimer covers platform-captured feeds);
- Telegram relies on the Vasama-OSINT collector being reachable (it
  reads `laclaugpt_ai26.events`); a file-export path works without Mongo;
- Zeeschuimer text extraction probes common field names; new platform
  payloads may need a `--text-fields` override until upstream field
  naming is checked;
- new channels: implement a function returning `CollectRecord`s and one
  CLI subcommand — the spine, dedup and storage are shared.

## Tests

`tests/test_collect.py` (RSS/Atom, normalization, dedup, mocked web,
Hermes contract, manual, Telegram adapter, CLI) and
`tests/test_collect_minet_zeeschuimer.py` (minet extract/collector CSVs,
Zeeschuimer NDJSON + array exports, dedup, platform text overrides) —
fully offline/synthetic; no live feeds, channels or websites.
