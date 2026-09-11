# DAIR collection adapter

LaclauGPT contains public collector code for DAIR-related research material, but the **live source profile is private operational configuration**. The repository documents the collection mechanics without publishing the current watch list, account identifiers, enabled/disabled source set, schedules, credentials, or deployment details.

Collected items enter the canonical corpus with `classification_state: unjudged`. Source selection is not itself an ideological classification; discourse and ideology interpretation happen later under `THEORY.md` with human review.

## Private configuration

The collector expects its source profile outside the public repository. By default it resolves:

```text
~/.config/laclaugpt/sources/dair-critical-ai.yaml
```

or the path supplied through:

```bash
export LACLAUGPT_DAIR_CONFIG=/path/to/private/dair-critical-ai.yaml
```

An explicit path may also be supplied with `--config`.

The public repository intentionally does not contain `config/sources/`. That path is ignored by Git and rejected by the publication-safety guard.

## Supported collection mechanisms

The DAIR collector can work with text-native websites, RSS/Atom feeds, public social APIs, public video-platform metadata/captions, podcast feeds and researcher-operated browser capture. Which concrete sources are enabled belongs to the private profile.

The modality order is transcript-first:

1. collect text-native source text where permitted;
2. prefer creator/publisher captions or transcripts;
3. retain machine-generated captions with explicit provenance;
4. mark uncaptioned audio/video as requiring a separate local ASR workflow where permitted;
5. use multimodal interpretation only when a research question requires visual evidence.

The collector does not automatically treat media appearance as authorship and does not infer ideology from source identity.

## Running

Validate a private configuration without collecting:

```bash
laclaugpt collect dair --dry-run
```

Run the configured source profile:

```bash
laclaugpt collect dair
```

Use `--config` to override the private config path and `--data-root` for a controlled runtime collection directory.

## Canonical mapping and provenance

All inputs converge on the existing `CollectRecord -> SourceItem / IngestionRecord` model. Platform-native identifiers, canonical URLs, publication times, source text, transcript provenance and collection metadata are retained in the canonical model.

Runtime raw payloads and normalized records remain outside Git. Public outputs should contain only reviewed provenance fields and safe configuration fingerprints, never the private source list itself.

## Incremental behaviour

Platform adapters use stable native identifiers and persistent checkpoints where available. A valid incremental run with no new records is normal. Unexpected zero-result first runs should fail visibly rather than silently report success.

## Ethical boundaries

Collection is limited to material accessible through the configured, permitted collection route. The collector does not bypass authentication barriers, CAPTCHAs or access controls, and it does not treat private messages, follower lists or unrelated user data as default research inputs.

Copyright, platform terms, research ethics and data-protection requirements apply independently of technical accessibility.

## Tests

DAIR collector tests are offline and use synthetic platform-shaped payloads. CI must not call live source services.

```bash
python -m pytest -q tests/test_collect_dair.py tests/test_collect.py
```

The tests cover adapter behaviour, incremental checkpoints, transcript provenance, raw-capture linkage, deduplication, configuration validation and privacy-safe operation without requiring the private source profile.
