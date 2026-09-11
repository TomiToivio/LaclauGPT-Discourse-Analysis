# LaclauGPT Social Media Collector

Collection subsystem for systematic political research on public social-media
content. The current Brazil 2026 study is one deployment profile; the collector
core is intended to be reusable across projects.

## Architecture

The collector has four layers:

1. browser/network capture;
2. LaclauGPT-native platform parsing;
3. normalisation and provenance;
4. durable metadata/media storage.

The preferred systematic path is:

```text
Firefox extension
      |
      v
collector/firefox/firefox_backend.py
      |
      v
collector/modules/{tiktok,instagram,twitter}.py
      |
      v
collector/normalize.py
      |
      v
collector/store.py
```

Chromium/CDP and HAR remain alternative capture paths. The standalone browser
extension under `collector/browser/` contains a JavaScript implementation of the
same LaclauGPT parser design.

Collection produces source material. Discourse analysis happens later.

## Parser lineage

The platform parsers follow the architecture of the historical
[LaclauGPT-TikTok-Scraper](https://github.com/TomiToivio/LaclauGPT-TikTok-Scraper):
explicit request routing, small native-platform parsers, provenance, stable post
IDs and a LaclauGPT-owned record shape.

Zeeschuimer is a **design inspiration** for browser/API-response interception and
remains supported as an interoperability/import format elsewhere in LaclauGPT.
The current Python parsers under `collector/modules/` are independent LaclauGPT
implementations, not Zeeschuimer ports or line-comparable adaptations.

See `collector/modules/README.md` for parser design rules.

## Capture paths

### Preferred: Firefox

The Firefox extension captures response bodies and navigation while the Python
backend performs parsing, normalisation and storage.

```bash
python -m collector.firefox.firefox_backend \
    --config collector/config/study.private.yaml \
    --data-root ~/laclaugpt-brasil-data
```

Load `collector/firefox/extension/manifest.json` with Firefox
`about:debugging#/runtime/this-firefox` in a logged-in research session.

Health endpoint:

```text
http://127.0.0.1:8765/status
```

### Chromium/CDP

```bash
python -m collector.run \
    --config collector/config/study.private.yaml \
    --data-root ~/laclaugpt-brasil-data
```

### HAR fallback

```bash
python -m collector.run \
    --config collector/config/study.private.yaml \
    --data-root ~/laclaugpt-brasil-data \
    --driver har
```

### Dry run

```bash
python -m collector.run \
    --config collector/config/study.private.yaml \
    --data-root ~/laclaugpt-brasil-data \
    --dry-run
```

## Configuration

`collector/config/study.private.yaml` is the local/private source of truth for
study windows, timezones, target accounts and platform URL templates. Real
account lists and operational configuration do not belong in the public repo.

## Output

```text
<data-root>/
  raw/<platform>/<YYYYMMDD>/capture-....ndjson
  normalized/<platform>.jsonl
  manifests/run-....json
  media/
  state.sqlite3
```

Raw platform payloads and normalized records remain linked through `raw_ref`.
The Store deduplicates by `(platform, document_id)`.

A normalized record contains a stable research-facing subset such as:

```json
{
  "document_id": "7400000000000000001",
  "platform": "tiktok",
  "author": "synthetic_user",
  "timestamp": "2026-09-07T12:00:00Z",
  "source_url": "https://www.tiktok.com/@synthetic_user/video/7400000000000000001",
  "text": "Synthetic caption for collector documentation.",
  "hashtags": ["synthetic"],
  "engagement": {"likes": 1234, "comments": 56, "plays": 90000},
  "collection_provenance": {
    "collector_version": "0.1.0",
    "module": "laclaugpt-native-tiktok-2026-09",
    "transformations": ["laclaugpt-network-capture", "map_item-normalise"]
  }
}
```

The example is synthetic and does not represent a research participant.

X/Twitter post IDs remain strings because they exceed JavaScript's exact integer
range.

## Zero-run observability

A capture pass that parses zero items is not silently treated as success.
Collector results expose request/body counters and a warning when the likely
cause is authentication, empty response bodies or parser drift. Zero *new* posts
on a repeated run remains normal deduplication.

## Media

Use `--download-media` to download public media referenced by normalized
records. Media uses deterministic identifiers and checksums and remains outside
Git.

```bash
python -m collector.run \
    --config collector/config/study.private.yaml \
    --data-root ~/laclaugpt-brasil-data \
    --download-media
```

Signed CDN URLs can expire, so media retrieval should happen close to collection
time.

## Tests

```bash
python -m pip install pytest
python -m pytest -q tests/collectors
```

Public tests use synthetic fixtures only.

## Platform fragility

Social-media interfaces change frequently. When collection returns nothing,
check in this order:

1. authentication, consent and rate limits;
2. whether Firefox/CDP/HAR actually captured response bodies;
3. endpoint/view routing in the platform parser;
4. payload-shape changes;
5. configured handle or account changes.

The collector does not bypass private accounts, CAPTCHAs or platform access
controls.

## Legacy helpers

`collector/backend/` contains older operational helpers. New development should
target the shared root collector modules and the preferred Firefox path.

## Research boundary

Only material allowed by the study's research protocol should be collected.
Private messages and unrelated prefetched user material are out of scope.
Collected research data, browser/session state, credentials, operational
configuration and generated outputs remain outside Git.
