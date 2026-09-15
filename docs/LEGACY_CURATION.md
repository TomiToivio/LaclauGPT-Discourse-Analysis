# Legacy LaclauGPT curation and provenance

Status: maintained curation record for issue #143.  
Date: 2026-09-15.

This document records the deliberate recovery of useful knowledge and implementation patterns from older LaclauGPT repositories. The current public repository, its canonical pipeline, and `paper/PAPER.md` remain authoritative. Legacy repositories are source material, not architecture templates.

## Decision vocabulary

- `PROMOTE` — refactor into maintained public code/docs/tests.
- `EXTRACT_THEN_DELETE` — salvage a small useful idea/helper from an obsolete larger component.
- `ARCHIVE_REFERENCE` — keep only a concise provenance/reference note.
- `PRIVATE_ONLY` — useful, but not suitable for the public repository.
- `DELETE/IGNORE` — obsolete, duplicated, unsafe, irrelevant, or generated debris.
- `NEEDS_REVIEW` — licensing, privacy, scientific value, or maintenance status is uncertain.

Maturity labels used below are `CORE`, `OPTIONAL-INFRASTRUCTURE`, `EXPERIMENTAL`, `LATER-PAPER-CANDIDATE`, and `ARCHIVAL/COMPARISON-ONLY`.

## Architecture mapping

Legacy material is mapped into the maintained architecture rather than revived as separate top-level applications:

1. **LaclauGPT Data Collection** — `collector/` and collection documentation.
2. **LaclauGPT Data Storage** — canonical record/provenance/store layers and storage adapters.
3. **LaclauGPT Data Analysis** — canonical analysis pipeline, post-processing, normalization, baselines.
4. **LaclauGPT Data Visualization** — researcher-facing exports, dashboards, visualizations.
5. **LaclauGPT Research Assistant** — optional human-in-the-loop agent/research tooling.
6. **LaclauGPT Simulation Laboratory** — optional Mesa/Concordia-style simulation work.
7. **LaclauGPT Experimental Laboratory** — comparison methods and other experiments that are not part of the canonical paper pipeline.

The first four are the maintained functional architecture. The last three are explicitly optional/experimental and must not silently alter the paper or default pipeline.

## Audited legacy sources and decisions

| Legacy source | Purpose/type | Public safety / provenance | Overlap and value | Decision | Destination / rationale |
|---|---|---|---|---|---|
| `TomiToivio/LaclauGPT-TikTok-Scraper` | Firefox network capture + Node/SQLite backend | Public, CC0; research data excluded | High historical value. Request routing, small parsers, deduplication and localhost handoff are already generalized by current collectors. The old 2024 endpoint mappings are fragile. | `ARCHIVE_REFERENCE` / already promoted | **Data Collection**. Keep current `collector/firefox/` as preferred path and `collector/browser/` as a secondary/manual prototype. Do not re-import the Node/SQLite stack. |
| `TomiToivio/LaclauGPT-Multimodal-Analysis` | Puhti batch sequence: frame extraction/OCR/transcription, multimodal frame analysis, summary, structured post-processing, Laclau/Palonen analysis | Public research-software documentation; dummy/public-safe material only | Strong provenance for the multimodal pipeline and HPC sequencing, but implementation is tied to the EP2024/Puhti-era workflow and has been superseded by the current canonical pipeline. | `EXTRACT_THEN_DELETE` conceptually; `ARCHIVE_REFERENCE` for old scripts | **Data Analysis**. Retain the useful staged pattern and resumable/HPC concepts in maintained implementations; do not copy old project-specific batch scripts wholesale. |
| `TomiToivio/LaclauGPT-Data-Collection` | RSS/API/scraper collection; distributed-services architecture | Private; may contain operational targets/config/data; repo-level license exists but file-level safety must be checked before promotion | The collector capability family remains valuable, but the old Celery/Redis/NATS/Mongo/S3 service topology is much heavier than the current repository needs. | `PRIVATE_ONLY` by default; `NEEDS_REVIEW` file-by-file | **Data Collection**. Extract only provider-agnostic parsers, retry/checkpoint patterns, or synthetic tests after explicit privacy/licensing review. Never copy target lists or operational config. |
| `TomiToivio/LaclauGPT-Web-Scraper` | Generic web-ingestion experiment | Private | Potential parser/normalization ideas; operational assumptions unknown. | `NEEDS_REVIEW` | **Data Collection / Experimental Laboratory**. Promote only small provider-agnostic helpers after inspection. |
| `TomiToivio/LaclauGPT-Data-Storage` (`splitting`) | MongoDB, DuckDB, object storage, Redis, vector/graph memory, messaging ideas | Private; architecture notes are generic but repository content may include private operational assumptions | Useful as a catalogue of storage experiments. The old "one service per concern" distributed architecture is not a requirement for current LaclauGPT. | `ARCHIVE_REFERENCE` for topology; `NEEDS_REVIEW` for reusable helpers | **Data Storage** or **Experimental Laboratory**. Prefer narrow adapters behind current canonical interfaces. Vector/graph memory belongs behind optional context-memory interfaces rather than becoming a second canonical store. |
| `TomiToivio/LaclauGPT-Data-Analysis` | Legacy analysis-module shell/documentation | Private; repository is essentially documentation in the audited default branch | Little unique executable value relative to current analysis pipeline. | `DELETE/IGNORE` | Current **Data Analysis** is authoritative. Do not recreate a historical module boundary just because the old repository existed. |
| `TomiToivio/LaclauGPT-Data-Visualization` | Streamlit dashboard/UI concept | Private; documentation is generic | The idea of a researcher-facing dashboard is useful, but the old distributed-service coupling is obsolete. | `EXTRACT_THEN_DELETE` conceptually | **Data Visualization**. Retain researcher-readable exports and dashboard concepts, not the old service topology. |
| `TomiToivio/laclaugpt-dashboard` | Historical dashboard implementation | Private; may contain generated/research-facing data assumptions | Potential UI patterns, but high risk of duplicating current dashboard/export code. | `NEEDS_REVIEW` | **Data Visualization**. Only extract presentation patterns or generic widgets that are not already implemented. |
| `TomiToivio/LaclauAgent` | Legacy agent/research-assistant experiment | Private | Potentially useful workflow/tooling patterns, but agent autonomy and hidden state would violate the current human-in-the-loop boundary if copied blindly. | `PRIVATE_ONLY` / `NEEDS_REVIEW` | **Research Assistant**. Only promote explicit, inspectable, human-triggered tools with structured outputs. |
| `TomiToivio/LaclauGPT-Deep-Research-Agent` | Research-agent experiment | Private | Similar value/risk to `LaclauAgent`; not part of the canonical analytical pipeline. | `PRIVATE_ONLY` / `NEEDS_REVIEW` | **Research Assistant**, `EXPERIMENTAL`. |
| `TomiToivio/LaclauGPT-Data-Collection-Agent` | Collection-agent experiment | Private | May contain useful orchestration patterns, but collection targets and operational state belong in private configuration. | `PRIVATE_ONLY` / `NEEDS_REVIEW` | **Research Assistant / Data Collection**, experimental only. |
| `TomiToivio/LaclauGPT-Social-Simulation-Laboratory` | Social simulation experiments | Private and very large; likely contains generated/model artifacts and environment-specific material | Useful as a separate research track, not as canonical discourse analysis. | `PRIVATE_ONLY` / `ARCHIVE_REFERENCE` | **Simulation Laboratory**. Do not merge large historical subtree or outputs into the public repository. |
| `TomiToivio/LaclauGPT` | Historical monorepo lineage | Public; currently substantially overlaps the maintained public repository | Useful mainly as provenance/history. Maintaining two public implementations would create drift. | `ARCHIVE_REFERENCE` | Current public `LaclauGPT-Discourse-Analysis` remains authoritative. |
| `TomiToivio/LaclauGPT-Discourse-Analysis-Private` | Operational/private companion | Private by design | Contains project-specific operational material, EP24/AI26/Brazil26 data/configuration and implementation work that must cross the boundary only deliberately. | `PRIVATE_ONLY` except explicitly reviewed reusable code | Any promotion requires a separate privacy/secrets/data review and synthetic fixtures. No bulk copying. |

## What has already been successfully recycled

### 2024 TikTok collector → current browser collectors

The clearest successful legacy migration is the 2024 TikTok scraper. The old repository used a Firefox extension to observe TikTok JSON responses and a localhost Node/SQLite backend. The maintained repository now generalizes the useful interception/parser pattern to multiple platforms and documents the legacy scraper as its provenance.

The current preferred systematic path is the Store-backed Firefox/Python collector (`collector/firefox/extension/` plus `collector/firefox/firefox_backend.py`). `collector/browser/` is retained only as a secondary/manual LaclauGPT-native JavaScript prototype. This consolidation is intentional: the old Node/SQLite backend is not revived as a second storage pipeline.

Decision: **PROMOTED previously, audited and retained**. Maturity: `CORE` for the Store-backed path, `OPTIONAL-INFRASTRUCTURE` for the standalone browser prototype.

### Multimodal/HPC staged-processing pattern

The old multimodal repository documents a useful sequence: preprocessing (frames/OCR/transcript) → multimodal frame analysis → summary → structured post-processing → discourse-theoretical analysis. The durable insight is the staged, restartable pipeline, not the exact Puhti-era scripts or project-specific settings.

Decision: **EXTRACT_THEN_DELETE** as an architectural pattern. Maturity: `CORE` where equivalent current stages exist; old scripts remain `ARCHIVAL/COMPARISON-ONLY`.

### Researcher-readable outputs

Legacy dashboard repositories reinforce a durable requirement: machine-readable JSON is not enough. Researchers need human-readable per-item summaries and corpus-level views. That requirement belongs in **Data Visualization** and export/report generation, while old Streamlit/service coupling does not.

Decision: **PROMOTE the requirement/pattern, not the old deployment topology**. Maturity: `CORE` for researcher-readable exports; dashboards remain `OPTIONAL-INFRASTRUCTURE` unless required by a study.

## Explicitly rejected legacy architecture

The following historical patterns are not revived as defaults:

- a mandatory Celery + Redis + NATS + MongoDB + S3 + DuckDB + ChromaDB + ArangoDB + MQTT distributed stack;
- a second storage pipeline just to preserve the old TikTok Node/SQLite backend;
- project-specific target lists, private endpoints, object-store paths, account names, or operational configuration;
- old EP24/AI26/Brazil26 data or row-level derived research outputs;
- duplicate Ollama wrappers, configuration loaders, normalizers, dashboards, or context-memory implementations when current equivalents exist;
- SNA/network-analysis code as a silent expansion of the current paper;
- autonomous research/collection agents outside the human-in-the-loop boundary;
- generated media, caches, databases, model artifacts, or giant simulation outputs.

## Promotion gate for future archaeology

A legacy file may enter the public repository only when all of the following are true:

1. It adds a capability or tested pattern not already better represented.
2. Its license/provenance permits reuse and attribution is retained where needed.
3. It contains no credentials, tokens, private hosts, private object-store locations, target lists, or row-level research data.
4. Any fixture is synthetic or demonstrably public/non-sensitive.
5. It is refactored behind current interfaces instead of recreating a historical subsystem.
6. Runtime code receives targeted regression tests.
7. Optional dependencies fail gracefully.
8. The canonical default pipeline and paper scope do not change silently.

When only a small algorithm or schema is valuable, extract that unit and leave the rest behind.

## Deduplication map

Use one maintained implementation per concern:

- browser/systematic collection → current `collector/` paths;
- canonical record/provenance semantics → current shared record/store interfaces;
- Context Memory/RAG → current documented context-memory architecture, optional behind a common interface;
- model access → current model/provider wrapper(s), not repository-specific Ollama clients;
- entity/topic/codebook normalization → current canonical codebook/normalization layer;
- preprocessing → current canonical media/text preprocessing path;
- researcher-readable outputs → current export/report layer;
- dashboards → one maintained visualization surface per active use case;
- theory/paper → `paper/PAPER.md` is source of truth for paper scope; repository experiments do not become paper claims automatically.

## Public/private boundary

The private repositories are inventories of possible ideas, not source trees to synchronize into public Git. Their presence in this audit does **not** approve their contents for publication.

A future promotion from a private repository should be a small, reviewable commit that names the source repository/path in the commit or documentation, removes operational assumptions, replaces real examples with synthetic fixtures, and passes the public test suite.

## Outcome of this audit

This audit deliberately produces no bulk legacy merge. The highest-value legacy collector pattern is already represented in the maintained repository, the old multimodal/HPC workflow contributes a staged-processing provenance pattern, and the old module repositories mostly provide architectural experiments or private operational material rather than unique public-safe code that should be copied wholesale.

That is the intended result: keep the useful knowledge and provenance while making the maintained public repository clearer than a naive union of its ancestors.