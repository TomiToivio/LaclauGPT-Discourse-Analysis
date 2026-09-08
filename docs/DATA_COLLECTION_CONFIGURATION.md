# Data collection configuration and privacy

LaclauGPT keeps **collection software and configuration schemas public, but operational collection settings private by default**.

This boundary applies to browser/social-media collection and to future source adapters such as RSS, Telegram, web fetch, agent submissions and researcher-managed source lists.

## Default rule

> **Public repository: collection machinery and safe templates. Private environment: live source selection and operational settings.**

The public repository may contain:

- collector source code;
- configuration schemas and documented field names;
- `.example.yaml`, template or synthetic configuration files;
- clearly fictional source identifiers used in tests;
- generic scheduling examples such as cron syntax;
- descriptions of collection strategies and provenance fields;
- narrowly reviewed factual public-source metadata when publication is necessary for reproducibility and allowed by the research-data publication policy.

The public repository should **not** contain live operational collection settings by default, including:

- Telegram channel/group IDs, invite links, usernames or monitored-channel lists;
- RSS feed lists that reveal a live research watch list or sampling strategy;
- private or study-specific web target lists;
- social-media account watch lists for ordinary research subjects;
- API keys, tokens, cookies, session files, phone numbers or authentication material;
- private endpoints, database credentials or controlled-storage locations;
- operational schedules whose combination with source lists exposes active monitoring;
- researcher-maintained source-selection notes;
- source lists that contain or imply sensitive attributes about identifiable people.

## Public templates vs private operational files

Use a split such as:

```text
collector/config/
  telegram.example.yaml       # PUBLIC: schema + fictional placeholders
  rss.example.yaml            # PUBLIC: schema + example.org feeds
  STUDY_TEMPLATE.yaml         # PUBLIC: safe reusable template

<private config directory>/
  telegram.private.yaml       # RESTRICTED: actual channels and credentials
  rss.private.yaml            # RESTRICTED: actual feed/watch list
  study.private.yaml          # RESTRICTED: live source selection
```

Private files may live in a researcher-controlled directory outside the repository, an approved secret/configuration service, or controlled research infrastructure. Environment variables should be used for credentials and secrets.

## Telegram

Telegram deserves an especially conservative default because an operational configuration can reveal:

- monitored channels and communities;
- private or semi-private invite links;
- researcher accounts or phone-number-linked credentials;
- an active intelligence/research watch list;
- source combinations that may expose the study design before publication.

Therefore real Telegram configuration is **RESTRICTED by default**. Public GitHub files should contain only schemas, documentation and synthetic/example values unless a specific configuration has passed explicit publication review.

The same rule applies even when all monitored Telegram channels are themselves publicly visible. Public visibility of a source does not automatically make the researcher's operational watch list a public artifact.

## RSS and web source lists

Individual well-known public RSS feeds or URLs may be harmless in documentation, but a complete operational feed/watch list can reveal sampling strategy, hypotheses, targets or unpublished research direction. Treat live lists as private by default.

If reproducibility later requires publication of a source list, review it separately under `docs/DATA_PUBLICATION_POLICY.md` and publish only the minimum necessary metadata.

## Public-figure exception

A narrowly reviewed study configuration containing factual public-figure or institutional source identifiers may be publishable when it is genuinely needed for reproducibility. This is an exception, not the default.

Such a file must:

- contain factual public-source identifiers only;
- contain no inferred ideological, political or sensitive attributes about individuals;
- contain no credentials, private links or operational secrets;
- be explicitly marked as an operational configuration released after review;
- remain subject to platform terms, copyright/database rights, research ethics and data-protection review.

The existing research-data publication policy remains authoritative for deciding whether such a configuration may be public.

## Git conventions

Private collection files should use names that are ignored by Git, for example:

```text
*.private.yaml
*.local.yaml
telegram.yaml
rss.yaml
collection-sources.yaml
```

where the unsuffixed names are reserved for local/private operational files and public versions use `.example.yaml` or clearly synthetic/test names.

Do not rely on `.gitignore` as the only protection. Before committing or opening a pull request, inspect the staged diff for source lists, credentials, identifiers, private endpoints and research-subject information.

## Provenance without publication

Operational configuration should still be reproducible inside controlled research infrastructure. Record a safe configuration identity in outputs, for example:

- configuration version or hash;
- collector version;
- run ID;
- collection time;
- source type;
- project/arena identity where appropriate.

Do not embed the entire private source list or credentials into public provenance records merely to make the run traceable.

## Relationship to other policies

This document complements:

- [`DATA_PUBLICATION_POLICY.md`](DATA_PUBLICATION_POLICY.md)
- [`DATA_LIFECYCLE.md`](DATA_LIFECYCLE.md)
- [`../collector/README.md`](../collector/README.md)

The governing principle is the same throughout LaclauGPT:

**Open machinery, private live collection configuration, controlled research data.**
