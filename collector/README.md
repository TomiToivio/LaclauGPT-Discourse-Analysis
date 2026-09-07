# LaclauGPT Social Media Collector

Collection subsystem for systematic political research on public social media
content. Built for the Brazilian presidential-election study (7 September –
10 October 2026), while keeping the core account/config/store pipeline reusable
for other longitudinal studies.

## Capture paths

There are three capture implementations in the repository, but they do not
have equal status:

1. **Preferred Firefox path:** `collector/firefox/extension/` +
   `collector/firefox/firefox_backend.py`. The extension only captures response
   bodies and navigation; the Python backend runs the shared parsers,
   normalisation and Store. This is the recommended systematic collection path.
2. **CLI Chromium path:** `collector/browser.py`. `CDPCaptureDriver` uses the
   DevTools Network domain and is the CLI default; `AgentBrowserDriver` is a HAR
   fallback. These are useful scripted/manual paths but may miss response bodies
   that Firefox can capture reliably.
3. **Standalone JS extension:** `collector/browser/`. This contains the
   LaclauGPT-native JavaScript parsers and an in-browser buffer. It is useful for
   development/manual capture, but there is currently no repository-side
   automatic drainer from its `get_buffer` message into the Python Store.

Collection produces source material. LaclauGPT discourse analysis consumes it
later. No ideological analysis happens inside the collector.

## Relationship to other projects

- **LaclauGPT-TikTok-Scraper** (historical, CC0,
  github.com/TomiToivio/LaclauGPT-TikTok-Scraper): the 2024 EP-election Firefox
  extension + Node/SQLite backend. Its useful ideas, including explicit request
  routing, provenance, deduplication and researcher-driven browsing, are carried
  forward in modernised form.
- **Zeeschuimer** (MPL-2.0, Digital Methods Initiative): the current Python
  platform parser modules under `collector/modules/` are ports/adaptations of
  its TikTok, Instagram and X/Twitter parsing logic. Those files retain their
  MPL-2.0 attribution. The browser-side LaclauGPT JS parsers under
  `collector/browser/modules/` are a separate LaclauGPT-native implementation.

## Shared Python pipeline

```
capture
  Firefox extension -> firefox_backend.py
  or CDP/HAR -> browser.py
        |
        v
platform parsers       collector/modules/{tiktok,instagram,twitter}.py
        |
        v
normalisation          collector/normalize.py
        |
        v
Store                  collector/store.py
  raw/ + normalized/ + manifests/ + SQLite state
        |
        +--> optional media download: collector/media.py
```

Raw platform payloads and normalized records remain linked through `raw_ref`.
The Store deduplicates by `(platform, document_id)` while raw captures stay
append-only.

## Install

Python 3.12+ is recommended.

```bash
python -m pip install -r collector/requirements.txt
```

`collector/requirements.txt` includes PyYAML, websocket-client and `tzdata`.
`tzdata` is important on Windows so the study timezone
`America/Sao_Paulo` is available to Python's `zoneinfo` implementation.

For tests:

```bash
python -m pip install pytest
python -m pytest -q tests/collectors
```

## Configure accounts

`config/brazil-election-2026.yaml` is the single source of truth for the study
window, timezone, enabled platforms, target accounts and page URL templates.
Handles are kept exactly as configured. The file currently flags that seven
main candidates were expected while six are configured; the collector reports
that gap instead of inventing an account.

## Preferred run: Firefox

Start the local backend:

```bash
python -m collector.firefox.firefox_backend \
    --config collector/config/brazil-election-2026.yaml \
    --data-root ~/laclaugpt-brasil-data
```

Then load `collector/firefox/extension/manifest.json` from
`about:debugging#/runtime/this-firefox` in a logged-in Firefox session.

Useful health endpoint:

```text
http://127.0.0.1:8765/status
```

The automatic tour is supplied by the backend from the YAML config. Each
configured page URL is a separate tour stop, so X profile + `/with_replies` and
Instagram profile + `/reels/` are both visited. The backend and tour stop
collecting outside the configured study window, using the study timezone.

## CLI run

Plan without browsing:

```bash
python -m collector.run \
    --config collector/config/brazil-election-2026.yaml \
    --data-root ~/laclaugpt-brasil-data \
    --dry-run
```

One Chromium/CDP pass:

```bash
python -m collector.run \
    --config collector/config/brazil-election-2026.yaml \
    --data-root ~/laclaugpt-brasil-data
```

HAR fallback:

```bash
python -m collector.run \
    --config collector/config/brazil-election-2026.yaml \
    --data-root ~/laclaugpt-brasil-data \
    --driver har
```

With media:

```bash
python -m collector.run \
    --config collector/config/brazil-election-2026.yaml \
    --data-root ~/laclaugpt-brasil-data \
    --download-media
```

The CLI uses one stable `run_id` per pass. Per-account failures are recorded and
do not abort the whole run. Store checkpoints capture last status; deduplication
prevents repeated normalized rows across passes.

## Output layout

```text
<data-root>/
  raw/<platform>/<YYYYMMDD>/capture-....ndjson
  normalized/<platform>.jsonl
  manifests/run-....json
  media/
  state.sqlite3
```

A normalized record contains fields such as:

```json
{
  "document_id": "7400000000000000001",
  "platform": "tiktok",
  "author": "lulaoficial",
  "timestamp": "2026-09-07T12:00:00Z",
  "source_url": "https://www.tiktok.com/@lulaoficial/video/...",
  "text": "caption…",
  "parent_document_id": null,
  "hashtags": ["..."],
  "mentions": ["..."],
  "engagement": {"likes": 1234, "comments": 56, "plays": 90000},
  "media_references": [
    {"kind": "video", "url": "...", "media_index": 0}
  ],
  "raw_ref": "raw/tiktok/20260907/capture-....ndjson",
  "collection_provenance": {
    "captured_at": "...",
    "collector_version": "0.1.0",
    "module": "zeeschuimer-tiktok-2026-09",
    "git_commit": "abc1234",
    "visited_url": "https://www.tiktok.com/@lulaoficial",
    "api_url": "https://www.tiktok.com/api/post/item_list/...",
    "run_id": "...",
    "account": "Lula:lulaoficial",
    "transformations": ["laclaugpt-network-capture", "map_item-normalise"],
    "media_downloaded": null
  }
}
```

The parser `module` value records the Python parser implementation lineage;
`transformations` records the actual LaclauGPT capture/normalisation pipeline.
These are intentionally different provenance facts.

X post IDs remain strings because they exceed JavaScript's exact integer range.

## Media

`--download-media` collects public media referenced by normalized records after
capture. Media jobs are deterministic by `platform_documentID_mediaIndex`, use
SHA-256 checksums, record failures without damaging post metadata, and write
through the `MediaBackend` interface. The default backend is filesystem storage;
Allas/S3 can implement the same interface later.

Signed CDN URLs can expire, so media should be downloaded close to collection
time. Media belongs outside Git.

## Import into LaclauGPT analysis

The normalized records map onto the LaclauGPT source-document conventions.
`document_id`, `platform`, `author`, `timestamp`, `source_url` and `text` remain
available for legacy/interchange adapters, while provenance and media fields
keep the richer collector context.

## Known platform fragility

Social-media interfaces change constantly. When collection returns nothing,
check these layers in order:

1. **Authentication / consent / rate limits.** Normal logged-in browsing may be
   required. The collector does not bypass private accounts, CAPTCHAs or access
   controls.
2. **Firefox stream capture.** `filterResponseData` must forward every original
   response chunk back to the page while keeping a private decoded copy. The
   preferred Firefox extension does this explicitly.
3. **Chromium body availability.** The current CDP driver waits for matching
   requests to reach `Network.loadingFinished` and then calls
   `Network.getResponseBody`. Some platform/browser combinations can still
   return empty bodies after the page consumes the stream. Full Fetch-domain
   interception/replay is **not currently implemented**. Use the Firefox path
   when this happens. HAR may omit bodies as well.
4. **Parser drift.** Inspect the current platform payload and update the
   affected parser. Python ports retain upstream attribution where applicable.
5. **Handle changes.** Edit the YAML config; the collector follows it.

## Legacy helpers

`collector/backend/` contains some older implementation modules. The scheduled
entry point `collector.backend.scheduler` now delegates to the canonical
`collector.run` pipeline instead of invoking removed `autoscraper.py` /
`clean_captures.py` files. New development should target the shared root
collector modules and the preferred Firefox path.

## Research requirements

Only public political content is collected. The collector does not bypass
private accounts, authentication barriers, CAPTCHAs or platform access
controls. Private messages are out of scope. Collection code should avoid
persisting unrelated prefetched content whenever the active platform view can be
identified reliably.
