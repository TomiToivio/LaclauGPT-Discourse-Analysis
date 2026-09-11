# Data collection configuration and privacy

LaclauGPT keeps **collection software and schemas public, but live source selection and deployment configuration private**.

This boundary applies to RSS, Telegram, web collection, social-media adapters, browser capture, researcher-managed source lists, service units, schedules and host-specific deployment settings.

## Default rule

> **Public repository: reusable machinery, schemas and synthetic examples. Private environment: live source selection, schedules and deployment configuration.**

The public repository may contain:

- collector source code;
- configuration schemas and documented field names;
- `.example.yaml`, template or synthetic configuration files;
- clearly fictional source identifiers used in tests;
- generic scheduling or deployment examples with placeholders only;
- descriptions of collection strategies and provenance fields.

The public repository must not contain:

- live Telegram channel/group IDs, invite links or monitored-channel lists;
- operational RSS/feed lists or web watch lists;
- social-media account watch lists;
- researcher-maintained source-selection registries;
- enabled/disabled source combinations that reveal a current sampling strategy;
- API keys, tokens, cookies, session files, phone numbers or authentication material;
- private endpoints, database credentials or controlled-storage locations;
- user-specific checkout paths, allocation/storage-project identifiers or internal hostnames;
- LAN, VPN, Tailscale/CGNAT or other deployment addresses;
- systemd units, timers or other live service definitions;
- operational schedules tied to a live source profile.

## Repository-level private paths

Two paths are explicitly reserved for private local use and are forbidden in the public Git tree:

```text
config/sources/
deploy/systemd/
```

Both paths are ignored by Git and rejected by the publication-safety guard if tracked.

Public schemas and examples should live in clearly safe locations such as `collector/config/*.example.yaml` or synthetic test fixtures. Live operational files should live outside the repository entirely.

## Recommended private layout

A local/operator-controlled layout may look like:

```text
~/.config/laclaugpt/
  sources/
    study-a.yaml
    study-b.yaml

~/.config/systemd/user/
  <private service units and timers>
```

Credentials should use environment variables, an approved secret store or other controlled infrastructure rather than source files where possible.

## Public sources are not automatically public configuration

A source being publicly accessible does not make the researcher's watch list, sampling frame or operational monitoring setup a public artifact. A complete source list can reveal hypotheses, unpublished research direction, active monitoring and study design.

If reproducibility later requires publication of a sampling frame, publish a separately reviewed research artifact or paper supplement rather than restoring the live operational configuration tree.

## Telegram, RSS and social sources

Treat all live source profiles as private by default, even when every underlying channel, account or URL is public. The same principle applies across Telegram, RSS, Mastodon, Bluesky, X, PeerTube, Twitch, LinkedIn, websites and future adapters.

## Deployment configuration

Host-specific service definitions, ports, paths, environment blocks, service schedules and network addresses are private operational material. Generic instructions may be documented publicly using placeholders, but deployable unit files belong outside the public repository.

## Provenance without publication

Operational configuration should remain reproducible inside controlled research infrastructure. Record safe provenance such as:

- configuration version or hash;
- collector version;
- run ID;
- collection time;
- source type;
- project/arena identity where appropriate.

Do not embed the full private source list, service configuration or credentials into public provenance merely to make a run traceable.

## Git and CI controls

Do not rely on `.gitignore` alone. The repository publication-safety check also rejects restricted roots, credential/session artifacts, machine-specific paths, private network addresses and other high-signal operational material.

Before committing or opening a pull request, inspect the staged diff for source lists, credentials, identifiers, private endpoints and deployment information.

## Relationship to other policies

This document complements:

- [`DATA_PUBLICATION_POLICY.md`](DATA_PUBLICATION_POLICY.md)
- [`DATA_LIFECYCLE.md`](DATA_LIFECYCLE.md)
- [`../collector/README.md`](../collector/README.md)
