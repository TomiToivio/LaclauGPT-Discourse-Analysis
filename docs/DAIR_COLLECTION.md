# DAIR critical-AI public-source collection

This profile collects public source material for AI26. `dair-critical-ai` is a provisional sampling rationale, not an ideological classification. Collection remains separate from human-reviewed discourse analysis under `THEORY.md`.

| Source | Method | Default content | Status |
| --- | --- | --- | --- |
| DAIR publications | conservative same-site HTML index | metadata and permitted page text | Enabled |
| DAIR blog | conservative same-site HTML index | article text | Enabled |
| Mastodon (DAIR, Bender, Hanna) | public REST API | public statuses | Enabled |
| Bluesky (DAIR, Bender, Hanna) | public AT Protocol AppView | public author feeds | Enabled |
| Mystery AI Hype Theater 3000 | Buzzsprout RSS plus publisher episode transcript | audio metadata and creator transcript | Enabled |
| X (`alexhanna`) | existing researcher-operated browser collector | public posts | Configured, disabled here |
| PeerTube | public instance | none | Disabled; podcast transcript feed replaces it |
| Twitch | authorized captions only | none | Optional/disabled |
| LinkedIn | authorized manual browser capture only | none | Optional/disabled |

## Run

Install `.[collect]`, then run all enabled sources:

```bash
laclaugpt collect dair --project ai26 --source-group dair-critical-ai
```

Select one or more configured source keys:

```bash
laclaugpt collect dair --source mastodon-alex --source bluesky-alex
laclaugpt collect dair --source maiht3k-podcast --dry-run
```

Use `--config` to point to a local copy when adding accounts; each entry needs a unique `key`, `kind`, and explicit `enabled`. No credentials belong in this file. Public Mastodon and Bluesky endpoints need no token. X requires the repository's existing explicitly operated browser collector. LinkedIn must not be scraped or automatically logged into.

Outputs default to `collection-data/`: permitted API/page captures are written under `raw/<platform>/` before normalized canonical records under `normalized/`; deduplication uses platform-native IDs or normalized canonical URLs; cursors are stored in `checkpoints.json`. `collection-data/` is ignored. Use `--data-root` to select another local runtime directory.

## Canonical mapping and provenance

Platform IDs map to `native_id`; DID/ActivityPub identity, relations, thread/root/parent IDs, facets, media, and public engagement remain metadata; canonical URL maps to `source_url`; original-language text maps to `raw_text`; project maps to ingestion `dataset_id`. Every item records collector/version, collection time, raw-capture reference, project `ai26`, arena `elites`, source group, source key, and `classification_state: unjudged`. Cross-posts remain distinct records so platform provenance is not collapsed.

Podcast records use `source_modality: audio`, `text_origin: creator_transcript`, `transcription_method: publisher_supplied`, and `verification_state: creator_published`. This is not ASR. Multimodal processing is disabled. If a future item lacks creator captions, local ASR may be added only where permitted, retaining timestamps, model/version, parameters, detected language, and a machine-generated/unverified label.

## Ethics, recovery, and limitations

Only public posts and public publisher transcripts are requested. Followers, private posts, direct messages, Twitch chat, credentials, and automated LinkedIn login are out of scope. Original HTML is retained for Mastodon context; quoted/reported material must not be attributed as the author's own position without human review. Rate limiting and `Retry-After` are respected. Resolution errors, malformed responses, and unexpectedly empty enabled sources fail visibly. Re-run after transient failures: the dedup ledger and per-source checkpoint prevent ordinary duplication. Website selectors are deliberately isolated because the DAIR site exposes no suitable conventional RSS/Atom feed at the checked endpoints.