# DAIR / AI26 public collection profile

This document describes the public, reproducible part of the DAIR source profile for the AI26 project. It is a source-acquisition profile, not an ideological classifier.

`AI Critical` is used only as a provisional source-selection/sensitising category. Inclusion in this profile does **not** assign an ideology to DAIR, Emily M. Bender, Alex Hanna, or any collected document. Interpretation happens later in the human-in-the-loop discourse-analysis pipeline.

The reviewed public identifiers live in:

`collector/config/dair-critical-ai.reviewed.yaml`

## Source matrix

| Source | Method | Default content | Status |
| --- | --- | --- | --- |
| DAIR publications | RSS/Atom where available, otherwise conservative web collection | Metadata and permitted text | Enabled |
| DAIR blog | RSS/Atom where available, otherwise conservative web collection | Article text where permitted | Enabled |
| Mastodon | Public REST API | Public statuses | Enabled |
| Bluesky | Public AT Protocol AppView | Public author-feed records | Enabled |
| PeerTube | Public REST API | Metadata and existing captions first | Enabled |
| X / Twitter | Existing repository collector | Public Alex Hanna posts | Configured |
| Twitch | Captions or separately reviewed audio-only VOD path | Transcript and metadata | Optional / disabled |
| LinkedIn | Authorized/manual browser capture only | Public company posts | Optional / disabled |

The public API adapters for Mastodon, Bluesky and PeerTube are implemented in `laclaugpt.collect.public_platforms` and feed the same canonical `CollectRecord -> SourceItem/IngestionRecord` path as the existing RSS and web collectors.

## Transcript-first policy

The modality policy is deliberately conservative:

1. Text-native sources: collect the source text.
2. Captioned video: use existing captions/subtitles and metadata.
3. Uncaptioned video: mark it for a separate local audio-only ASR workflow when collection and platform terms permit.
4. Multimodal processing: disabled by default. Enable it only when visual rhetoric, slides, editing, imagery, or embodied performance is part of the research question.

PeerTube records store `source_modality`, `text_origin`, caption provenance, transcript availability, and verification state in source metadata. Platform-generated captions are explicitly marked machine-generated/unverified. Exact quotations from ASR or automatically generated captions require human verification.

The public PeerTube collector does **not** automatically download audio or run ASR. That keeps the API acquisition layer small and leaves transcription in the repository's dedicated local media/transcription workflow.

## Canonical field mapping

The adapters intentionally reuse the canonical model rather than adding DAIR-specific document classes.

| Source fact | Canonical location |
| --- | --- |
| Platform-native stable ID | `SourceItem.native_id` |
| Canonical/public URL | `SourceItem.source_url` |
| Platform | `SourceItem.platform` |
| Source type | `SourceItem.source_type` |
| Public actor/account label | `SourceItem.author_text` |
| Publication time | `SourceItem.published_at` |
| Collection time | `SourceItem.collected_at` / `IngestionRecord.collected_at` |
| Original language | `SourceItem.language` |
| Text or selected transcript | `SourceItem.raw_text` |
| Relation type, thread/root IDs, DID/CID, caption details | `SourceItem.metadata` / ingestion metadata |
| Collector name/version | `IngestionRecord.collector` / `collector_version` |
| Raw capture reference when supported | `IngestionRecord.raw_payload_ref` |
| Derived transcript representation | canonical `Representation` model in later processing |

Cross-platform provenance must be retained. Similar or cross-posted text may be detected later, but platform-specific source records must not be collapsed into a single provenance-less item.

## Mastodon

The collector accepts profile URLs and common ActivityPub-style references such as:

```bash
python -m laclaugpt collect mastodon 'dair-community.social/@alex'
python -m laclaugpt collect mastodon 'dair-community.social/@EmilyMBender'
```

The adapter uses account lookup and public account-status endpoints. It records originals, replies and boosts as distinct relation types; keeps content warnings; normalizes HTML to text while retaining source HTML in metadata; and preserves hashtags, mentions, media metadata, language, edit time, reply IDs and public engagement counts.

Use `--since-id` as the incremental checkpoint. The collector never requests followers, private statuses or direct messages.

The DAIR institutional Mastodon account is intentionally left as `discovery_required` in the profile until its canonical public account identifier is positively verified. Do not guess it from the instance domain.

## Bluesky

The Bluesky collector resolves the human-readable handle through the public AppView and stores the stable DID in metadata. The stable AT URI and CID are preserved for each post.

```bash
python -m laclaugpt collect bluesky dairinstitute.bsky.social
python -m laclaugpt collect bluesky emilymbender.bsky.social
python -m laclaugpt collect bluesky alexhanna.bsky.social
```

Posts, replies, quotes and reposts are recorded as different relation types. Parent/root AT URIs, facets, links, hashtags, mention DIDs, language labels and public engagement counts are retained.

Handle resolution must succeed. The handle alone is not treated as a permanent actor identifier.

## PeerTube

Use channel discovery before selecting channels from the DAIR instance. Do not assume that every video visible on an instance is institution-authored.

The API layer supports public channel discovery and channel video collection. A selected video's captions are ranked as follows:

1. creator-supplied caption;
2. platform-generated caption;
3. no transcript, with the item marked for a separately reviewed local audio-ASR workflow.

Example Python discovery:

```python
from laclaugpt.collect.public_platforms import discover_peertube_channels

channels = discover_peertube_channels('https://peertube.dair-institute.org/')
for channel in channels:
    print(channel.get('name'), channel.get('displayName'))
```

After human selection, collect one public channel:

```bash
python -m laclaugpt collect peertube \
  https://peertube.dair-institute.org/ \
  --channel <reviewed-channel-handle>
```

The collector retrieves caption tracks when available. It does not interpret video frames, download chat, or start multimodal analysis.

## DAIR website, publications and blog

The existing canonical commands remain the preferred first step:

```bash
python -m laclaugpt collect web https://dair-institute.org/publications/
python -m laclaugpt collect web https://dair-institute.org/blog/
```

When a stable RSS/Atom feed is discovered, prefer:

```bash
python -m laclaugpt collect rss <feed-url> --fetch-article
```

Do not copy or republish third-party full-text papers merely because the DAIR publications index links to them. Preserve metadata, abstracts/descriptions where permitted, canonical URLs and authorship provenance.

## X / Twitter

Alex Hanna's public X account is listed in the reviewed profile for use through the repository's existing X collector rather than a parallel implementation. The profile stores the factual handle only and does not assign any ideological attribute to the person.

## Twitch

Twitch is intentionally optional and disabled in the public profile. Enable it only if a stable authorized public caption/transcript path is available, or after a separate review permits audio-only processing of archived public VODs.

Do not capture live video by default and do not collect Twitch chat participants as part of this profile.

## LinkedIn

No brittle or unauthorized LinkedIn scraper is included. The profile remains disabled unless a separately reviewed authorized/manual browser-capture workflow is available. Such a workflow must not store credentials, automate login, or bypass access controls.

## Public/private boundary

This profile is a narrow reproducibility exception for factual identifiers of a public institution and public researchers. It contains no collected posts, transcripts, inferred political attributes, credentials, cookies, private paths, schedules or controlled-storage information.

Runtime research data remains outside Git. The repository publication and data-collection policies remain authoritative.

## Failure handling and incremental collection

Collectors should fail visibly when account resolution fails or an API payload has the wrong shape. Incremental checkpoints are platform-native where practical (`since_id` for Mastodon, AppView cursor for Bluesky, offset/time ordering for PeerTube) and deduplication still occurs in the canonical `CollectionStore`.

An unexpectedly empty first collection should be investigated rather than silently accepted. A later run that yields zero *new* records after canonical deduplication may be normal.

## Tests

All tests for these adapters are offline and use small synthetic platform-shaped fixtures. CI must not call live DAIR, Mastodon, Bluesky or PeerTube services.

Run:

```bash
python -m pytest -q tests/test_dair_collectors.py tests/test_collect.py
```

The public tests also verify that the reviewed profile contains no credential-like fields and that collection-time ideology assignment remains disabled.
