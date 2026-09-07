# LaclauGPT Social Media Collector

Collection subsystem for systematic political research on public social
media content. Built for the Brazilian presidential-election study
(7 September – 10 October 2026), general enough for any account-based
longitudinal study.

**Relationship to other projects**

- **LaclauGPT-TikTok-Scraper** (historical, CC0,
  github.com/TomiToivio/LaclauGPT-TikTok-Scraper): the 2024 EP-election
  Firefox extension + Node/SQLite backend. Its useful ideas — provenance
  fields on every record, hashtag/challenge side tables,
  INSERT-OR-IGNORE-style dedup, random-walk browsing discipline — are
  carried forward here in modernised form. The old repository is
  historical and remains untouched.
- **Zeeschuimer** (MPL-2.0, digitalmethodsinitiative): the platform
  parsing logic (endpoint detection, embedded-JSON extraction, ad
  filtering, partial-item handling) is ported from its TikTok,
  Instagram and X/Twitter modules. See `modules/README.md` for the
  required attribution. LaclauGPT is NOT a Zeeschuimer fork: capture is
  CDP-based rather than an extension, and parsing outputs feed the
  LaclauGPT interchange instead of 4CAT (4CAT remains importable via
  the existing adapters).

## Architecture (four layers)

```
1. browser/network capture     collector/browser.py
      CDP Network-domain capture against a persistent logged-in
      Chromium profile (agent-browser CLI drives navigation),
      plus a HAR-export fallback driver
2. platform-specific parsing   collector/modules/{tiktok,instagram,x}.py
      Zeeschuimer-derived capture()/map_item() ports
3. normalisation + provenance  collector/normalize.py
      raw platform item -> stable record with full provenance;
      raw and normalised representations stay linked via raw_ref
4. durable metadata + media    collector/store.py, collector/media.py
      raw/ + normalized/ + manifests/ + SQLite state (seen posts,
      checkpoints, media index), queued sha256-checked downloads,
      S3-swappable backend interface
```

Collection produces source material. LaclauGPT discourse analysis
consumes it later — no ideological analysis happens inside the
collector.

## Install

No packaging yet (repo has no packaging manifest); the collector runs
from the repository root with Python 3.12+ and:

```
pyyaml        # config
websocket-client, requests   # CDP driver / media fetch
pytest        # tests
```

## Configure accounts

`config/brazil-election-2026.yaml` holds the study: window, timezone,
enabled platforms, candidate handles (Lula has two per platform) and
party accounts (PT, PL). Handles are stored exactly as supplied by the
researchers; nothing is silently corrected. The configuration flags a
gap: the researcher described SEVEN main presidential candidates but
supplied SIX — the seventh is not invented; `expected_candidates` keeps
the manifest flagging it.

Add accounts by editing the YAML; the runner follows it.

## Run

```bash
# plan + config check (no browsing)
python -m collector.run \
    --config collector/config/brazil-election-2026.yaml \
    --data-root ~/laclaugpt-brasil-data --dry-run

# one collection pass (browser capture + store)
python -m collector.run \
    --config collector/config/brazil-election-2026.yaml \
    --data-root ~/laclaugpt-brasil-data

# with media download (videos/thumbnails/images, checksummed)
python -m collector.run --config ... --data-root ... --download-media
```

One pass visits every configured account/page (profile + /with_replies
for X, profile + /reels for Instagram), captures platform API
responses, normalises, deduplicates (platform + document_id), writes
raw NDJSON + normalised JSONL + a per-run manifest, and records
per-account success/failure. One account failing never aborts the run;
checkpoints let the next pass resume. The study window (start/end in
the config) gates execution.

Data root must live OUTSIDE the repository (`.gitignore` covers
`laclaugpt-brasil-data/`, `collection-data/`, `*.har`).

## Login state (one-time setup)

The CDP driver attaches to a persistent Chromium profile. Create it
once, logged in, headed:

```bash
~/.hermes/hermes-agent/node_modules/.bin/agent-browser \
    --profile ~/.hermes/chromium-laclaugpt-profile --headed \
    open https://www.tiktok.com
# log in to TikTok / Instagram / X once in that window; cookies persist
```

Normal authenticated browsing is how the public web interface exposes
this content; the collector does not bypass authentication barriers,
private accounts, or CAPTCHAs (see Research requirements below).

## Output schema (normalised record, one JSON object per line)

```json
{
  "document_id": "7400000000000000001",
  "platform": "tiktok",
  "author": "lulaoficial",
  "author_fullname": "Presidente Lula",
  "timestamp": "2026-09-07T12:00:00Z",
  "source_url": "https://www.tiktok.com/@lulaoficial/video/...",
  "text": "caption…",
  "language": "",
  "parent_document_id": null,
  "hashtags": ["..."], "mentions": ["..."],
  "engagement": {"likes": 1234, "comments": 56, "plays": 90000},
  "media_references": [{"kind": "video", "url": "...", "media_index": 0}],
  "raw_ref": "raw/tiktok/20260907/capture-…ndjson",
  "collection_provenance": {
    "captured_at": "…", "collector_version": "0.1.0",
    "module": "zeeschuimer-tiktok-2026-09", "git_commit": "abc1234",
    "visited_url": "https://www.tiktok.com/@lulaoficial",
    "api_url": "https://www.tiktok.com/api/post/item_list/…",
    "run_id": "…", "account": "Lula:lulaoficial",
    "transformations": ["zeeschuimer-capture", "map_item-normalise"],
    "media_downloaded": null
  }
}
```

X/Twitter post IDs remain exact strings (they exceed 2^53; JS Number
would silently round them). Raw payloads are append-only NDJSON under
`raw/` — every normalised field is re-derivable from its raw_ref.

## Media

`--download-media` enqueues every referenced public media object
(TikTok video+thumbnail, Instagram images/carousel/reels, X images/
videos, clearly-attributable quote media). Deterministic names:
`platform_postID_mediaIndex.ext`. sha256 + byte size + MIME + status
per object in the media index; verified copies are never re-downloaded;
failures are recorded per object and the post metadata stays intact.
Signed CDN URLs expire — download near capture time. Media never gets
committed to Git; the backend interface (`MediaBackend`) takes a CSC
Allas/S3 implementation later without touching the pipeline.

## Import into LaclauGPT analysis

The normalised records map onto the LaclauGPT document model:
`document_id`/`platform`/`author`/`timestamp`/`source_url`/`text` are
the legacy CSV schema fields; `laclaugpt/adapters/legacy.py` converts
rows with these fields, and `collector/normalize.py` keeps the raw↔
normalised linkage required for provenance-preserving imports. A run
manifest (collector version, git SHA, per-account results, media
counts) is written per pass for the analysis pipeline's dataset
registration.

## Known platform fragility and maintenance expectations

Social-media interfaces change constantly. These parsers require
maintenance; when a capture returns nothing, suspect (in order):

1. **Unauthenticated browsing walls.** Verified 2026-09-07 on TikTok:
   logged-out headless visits get a cookie-consent modal (shadow-DOM
   buttons "Decline optional cookies"/"Allow all" — the driver clicks
   through) and, after some navigation, a "Something went wrong"
   feed error plus empty `item_list` bodies. Login in the persistent
   profile restores reliability. Instagram is the most aggressive
   about login walls; X applies aggressive rate limiting.
2. **Response-body capture mechanics.** The CDP driver must hold the
   response while reading it (Fetch interception); naive
   `Network.getResponseBody` after the page consumed the stream can
   return an empty body. This build of Chromium also lacks
   `Fetch.takeResponseBodyForInterceptionAsStream` (-32601), so the
   driver uses the request-stage pause + replay path with browser
   cookies, or falls back to the HAR driver (no bodies).
3. **Upstream parser drift.** The modules are line-comparable ports of
   Zeeschuimer's; diff against upstream when behaviour diverges.
4. Handle renames/deletions: edit the config, the collector follows.

## Research requirements

Only public political content is collected. The collector does not
bypass private accounts, authentication barriers, CAPTCHAs, or platform
access controls; normal authenticated browsing by a researcher is the
accepted access mode. Private messages are never touched. Prefetched
content that the visitor never saw is dropped (TikTok /api/preload/,
Instagram graphql prefetch allowlist) so the researcher's personal feed
is not accidentally collected — particularly important for Instagram
and X.