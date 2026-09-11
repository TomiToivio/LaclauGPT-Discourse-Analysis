# DAIR critical-AI public-source collection

This is the canonical public collection profile for DAIR material in AI26. `dair-critical-ai` is a provisional sampling/source-selection rationale, **not** an ideological classification. Every collected item enters the canonical corpus with `classification_state: unjudged`; discourse and ideology interpretation happens later under `THEORY.md` with human review.

The source configuration is `config/sources/dair-critical-ai.yaml`. It contains only reviewed factual identifiers for a public institution and public researchers. Runtime data, credentials, cookies, private paths and operational secrets stay outside Git.

## Source matrix

| Source | Method | Default content | Status |
| --- | --- | --- | --- |
| DAIR website | direct public page | permitted page text/metadata | Enabled |
| DAIR publications | RSS/Atom if a suitable feed is verified, otherwise conservative same-site index | metadata and permitted text | Enabled |
| DAIR blog | RSS/Atom if a suitable feed is verified, otherwise conservative same-site index | article text | Enabled |
| Mastodon (DAIR, Bender, Hanna) | public REST API | public statuses | Enabled |
| Bluesky (DAIR, Bender, Hanna) | public AT Protocol AppView | public author feeds | Enabled |
| DAIR PeerTube | public REST API, DAIR-owned channels only | metadata and existing captions first | Enabled |
| Mystery AI Hype Theater 3000 | Buzzsprout RSS + publisher transcript | audio metadata and creator transcript | Enabled |
| X (`alexhanna`) | existing researcher-operated browser collector | public posts | Configured separately |
| Twitch | authorized captions or separately reviewed audio-only VOD path | transcript + metadata | Optional/disabled |
| LinkedIn | authorized/manual browser capture only | public company posts | Optional/disabled |

DAIR's public PeerTube material identifies the account as `dair`, and DAIR's own PeerTube description links to `dair-community.social/@DAIR`; these factual identifiers are used only for source resolution, not interpretation.

## Run

Install the collection extras, then validate the plan without network collection or writes:

```bash
laclaugpt collect dair --project ai26 --source-group dair-critical-ai --dry-run
```

Run all enabled sources:

```bash
laclaugpt collect dair --project ai26 --source-group dair-critical-ai
```

Select individual configured sources when needed:

```bash
laclaugpt collect dair --source mastodon-alex
laclaugpt collect dair --source bluesky-alex
laclaugpt collect dair --source peertube-dair
laclaugpt collect dair --source maiht3k-podcast
```

Use `--data-root` for a controlled runtime location. The default `collection-data/` is ignored by Git.

## Transcript-first modality policy

The acquisition order is explicit:

1. text-native source -> collect source text;
2. creator/publisher captions or transcripts -> collect those first;
3. platform-generated captions -> collect with `machine_generated_unverified` provenance;
4. uncaptioned audio/video -> leave `asr_required=true` for a separate local ASR workflow where permitted;
5. multimodal interpretation -> disabled by default and enabled only for a research question that requires visual evidence.

The DAIR source-group collector does **not** automatically run ASR or image/video interpretation. If local ASR is later run, retain timestamps, model/version, language detection, parameters and machine-generated status. Do not use an ASR passage as an exact quotation before human verification.

For PeerTube, the collector first discovers channels owned by the configured `dair` account. It does not assume that every video visible on the instance is DAIR-authored. For each selected video it retrieves metadata and checks the public caption endpoint, preferring creator captions over automatically generated captions.

## Canonical mapping and provenance

All inputs converge on the existing `CollectRecord -> SourceItem / IngestionRecord` model. No DAIR-specific document ontology is added.

| Source fact | Canonical destination |
| --- | --- |
| platform-native stable identifier | `SourceItem.native_id` |
| canonical/public URL | `SourceItem.source_url` |
| platform and source type | `SourceItem.platform`, `SourceItem.source_type` |
| actor/account label | `SourceItem.author_text` |
| publication and collection time | `SourceItem.published_at`, `IngestionRecord.collected_at` |
| original language | `SourceItem.language` |
| source text / selected transcript | `SourceItem.raw_text` |
| DID / ActivityPub identity / relation / thread IDs / captions / media metadata | `SourceItem.metadata` and ingestion metadata |
| project | `IngestionRecord.dataset_id = ai26` |
| raw capture | `IngestionRecord.raw_payload_ref` |
| collector/version | `IngestionRecord.collector`, `collector_version` |

Permitted raw API/page payloads are written under `raw/<platform>/` before normalized records are saved. Each record carries a safe configuration fingerprint, project, arena, source group and source key. Cross-posted material remains separate by platform so provenance is not collapsed.

## Incremental behaviour

Mastodon resolves each configured public account and starts from the newest feed. Its persistent checkpoint is the newest status ID from the previous run (`since_id`); `max_id` is used only for bounded pagination inside one run.

Bluesky resolves the handle to a stable DID on every run. The checkpoint is the newest AT URI previously seen, and the collector walks the newest-first author feed until it encounters that URI. Handles therefore remain human-readable labels while the DID and AT URI provide stable identity.

PeerTube uses the newest collected publication timestamp as its source checkpoint. Each run discovers DAIR-owned channels from the `dair` account and retrieves only newer videos within bounded pagination.

A valid incremental run with no new records is normal. A first run that resolves an enabled source but unexpectedly yields zero records fails visibly rather than silently reporting success.

## Ethical boundaries

Only public material is collected. The profile does not collect followers, private posts, direct messages, Twitch chat participants or unrelated prefetched user content. It does not bypass CAPTCHAs, authentication barriers or access controls.

LinkedIn stays disabled unless a separately reviewed authorized/manual workflow is used. Twitch stays disabled until a reliable authorized transcript/caption route, or an approved audio-only VOD workflow, exists. The rest of the source group works without either platform.

Website collection does not treat third-party papers linked from the publications index as DAIR-authored material and does not republish copyrighted full text when only metadata, abstracts or links are supplied.

## Tests

The DAIR tests are offline and use synthetic platform-shaped payloads. CI must not call live DAIR, Mastodon, Bluesky or PeerTube services.

```bash
python -m pytest -q tests/test_collect_dair.py tests/test_collect.py
```

The tests cover account resolution, relation mapping, stable Bluesky identity, incremental checkpoints, PeerTube channel discovery and caption priority, transcript provenance, raw-capture linkage, deduplication, configuration switches, malformed configuration and public-config hygiene.
