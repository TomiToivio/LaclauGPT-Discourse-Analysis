# Collector configuration policy

This directory contains **public configuration templates and only specifically reviewed public study configurations**.

The default rule for LaclauGPT is:

> **Collection code and configuration schemas are public. Live operational collection settings are private.**

Do not commit real operational source-selection files here by default. Keep actual Telegram channel lists, RSS feed/watch lists, study-specific web targets, ordinary-user social-media watch lists, credentials, cookies, API tokens, session material, private endpoints and controlled-storage settings outside Git.

Use public templates with fictional/example values for documentation and tests. Private operational files should use ignored names such as `*.private.yaml` or `*.local.yaml`, or live in a controlled configuration directory outside the repository.

A study configuration containing factual identifiers for public figures or public institutions may be published only as a narrow reproducibility exception after explicit review. Such files must not contain inferred sensitive attributes, credentials, private links or unrelated research-subject information.

The existing `brazil-election-2026.yaml` is an example of that reviewed exception and must not be treated as precedent for publishing all future watch lists.

For the complete rule, including Telegram, RSS and web-source lists, see [`../../docs/DATA_COLLECTION_CONFIGURATION.md`](../../docs/DATA_COLLECTION_CONFIGURATION.md) and [`../../docs/DATA_PUBLICATION_POLICY.md`](../../docs/DATA_PUBLICATION_POLICY.md).
