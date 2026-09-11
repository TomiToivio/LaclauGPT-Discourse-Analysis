# Running multiple studies with the shared Firefox collector

One collector codebase can serve multiple studies while keeping their operational environments physically separated. Studies must not share data roots, SQLite state, dedup keys, checkpoints, raw captures, normalized output, media stores, manifests or run IDs.

```text
                    shared collector/firefox code
                              |
                  +-----------+-----------+
                  |                       |
              study A                 study B
                  |                       |
            private config           private config
                  |                       |
          browser profile A        browser profile B
                  |                       |
           private backend          private backend
                  |                       |
          controlled data root     controlled data root
```

Study identity is explicit and recorded in collection provenance. It must never be inferred from content.

## Backends

Operational backend commands belong in private deployment documentation. The public repository intentionally omits real host addresses, ports, checkout paths, data-root paths and service definitions.

A generic invocation is:

```bash
python -m collector.firefox.firefox_backend \
    --config /path/to/private/study.yaml \
    --host 127.0.0.1 \
    --port <port> \
    --data-root /path/to/controlled/data
```

If the browser and backend run on different machines, configure the address privately on those machines. Do not commit LAN, VPN, Tailscale/CGNAT or other deployment addresses to this repository.

## Service management

Systemd units and timers are private operational deployment configuration. They belong in the operator's user/system configuration, for example under a controlled `~/.config/systemd/user/` location, not under the public repository.

The public tree intentionally does not contain `deploy/systemd/`. Git ignore rules and the publication-safety guard reject that path.

## Firefox profiles

Use a separate browser profile for each study. Each profile may store its backend address in extension-local storage, allowing the same extension code to talk to separate backends without code duplication.

The exact backend URL is deployment-specific and must remain outside Git. Reload the extension after changing local settings and verify the capture flow from the controlled runtime environment rather than from public deployment documentation.

## Data roots

Each backend writes only inside its own controlled data root. The expected logical structure is:

```text
<private-data-root>/
  raw/
  normalized/
  media/
  manifests/
  state.sqlite3
```

The same platform document may exist in more than one study when separate sampling designs legitimately capture it; deduplication is scoped to the study.

## Privacy boundary

Live account lists, operational study configs, service units, concrete host addresses, private ports, checkout paths and data locations stay outside the public repository.

The public repository carries reusable collector code, schemas, synthetic fixtures and privacy-safe documentation only.
