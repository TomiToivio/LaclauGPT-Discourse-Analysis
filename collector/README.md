# LaclauGPT Social Media Collector

Issue-driven build: [vasama-osint lineage → LaclauGPT-Discourse-Analysis #20](https://github.com/TomiToivio/LaclauGPT-Discourse-Analysis/issues/20)
— a general-purpose social-media collection system for systematic political
research, first use case: the **2026 Brazilian presidential-election study**
(2026-09-07 → 2026-10-10, America/Sao_Paulo; six named candidates + PT/PL
party accounts on Instagram, TikTok, X).

## Design (issue #20 four layers)

```
collector/
  config/   brazil-election-2026.yaml (accounts, window, media policy)
  modules/  platform parsers (TikTok / Instagram / X)
  backend/  capture + normalisation + media queue + scheduler
  media/    downloaded objects (checksummed, never committed to Git)
  schemas/  NormalizedPost + MediaRef + interchange mapping
  tests/    synthetic offline fixtures only
```

**Origin & attribution:** the capture approach adapts
[Zeeschuimer](https://github.com/digitalmethodsinitiative/zeeschuimer)
(Digital Methods Initiative, MIT) — network-interception of platform APIs
rather than DOM scraping — and ports the working pieces of the historical
[TomiToivio/LaclauGPT-TikTok-Scraper](https://github.com/TomiToivio/LaclauGPT-TikTok-Scraper)
(Firefox extension + Node backend, 2024). The historical repository is left
untouched. Zeeschuimer-derived parser knowledge is re-implemented in
LaclauGPT's own collector code with attribution; no verbatim module copies.

## Key rules (from the issue)

- Collection is **separate from discourse analysis** — the collector feeds
  LaclauGPT, never analyses.
- `raw/`, `normalized/`, `media/`, `manifests/` stay **logically separate**;
  provenance answers when/by-which-version/from-which-URL/what-transforms.
- X post IDs remain **exact strings** (beyond JS safe-integer range).
- Handles stored **exactly as supplied** — no silent corrections; the
  missing **seventh candidate** is flagged as TODO, never invented.
- **No bypassing** of private accounts/auth barriers/CAPTCHAs; public
  political content only.
- Media: queued (never blocks capture), dedupe by checksum,
  deterministic names `platform_postid_index`, failures recorded —
  metadata stays usable when a signed URL expires.
- Storage: filesystem + JSONL/SQLite now; interface ready for
  CSC Allas/S3 later. No MongoDB/Kafka fashion requirements.

## Status

Work in progress on branch `feature/issue-20-social-media-collector`:
configuration + records/media/scheduler skeleton landed; platform parsers
and offline test fixtures are the next commits (see issue #20 checklist).
Not merged to main until tests pass and platform behaviour is verified.