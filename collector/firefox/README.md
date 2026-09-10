# Running two studies with the shared Firefox collector

One collector codebase, two physically separated datasets. Brazil26 and
AI26 never share a data root, SQLite state, dedup keys, checkpoints,
raw captures, normalized output, media store, manifests, or run ids.

```text
                    shared collector/firefox code
                              |
                  +-----------+-----------+
                  |                       |
             Brazil26                  AI26
                  |                       |
        private election config   private ai26 config
                  |                       |
          Firefox profile A        Firefox profile B
                  |                       |
            backend :8765           backend :8766
                  |                       |
 ~/laclaugpt-brasil-data      ~/laclaugpt-ai26-data
```

Study identity is always explicit, never inferred from content:

- the config's `study:` field;
- reported by `/status` and `/tour`;
- recorded in every normalized record under `collection_provenance.study`.

## Backends

```bash
# Brazil26 (existing deployment; keep host/port/data-root as configured)
python -m collector.firefox.firefox_backend \
    --config collector/config/brazil-election-2026.yaml \
    --host 100.115.95.109 --port 8765 \
    --data-root ~/laclaugpt-brasil-data

# AI26 (separate checkout dir on the deployment host, private config)
python -m collector.firefox.firefox_backend \
    --config collector/config/ai26.private.yaml \
    --host 127.0.0.1 --port 8766 \
    --data-root ~/laclaugpt-ai26-data
```

Systemd user services:

```bash
systemctl --user start brazil-capture.service   # :8765 (existing)
systemctl --user start ai26-capture.service     # :8766 (new, deploy/systemd/ai26/)
```

`ai26-capture.service` reads `AI26_CONFIG`, `AI26_BIND_HOST`,
`AI26_PORT`, `AI26_DATA_ROOT` from its environment block.

## Firefox profiles

The extension ships with `http://127.0.0.1:8765` as the
backwards-compatible default. Each Firefox profile stores its own
backend address in extension local storage under `backend_url`, so the
SAME extension code runs against different backends without code
duplication.

The backend may also listen on a non-localhost address (e.g. the
deployment host's Tailscale IP) when the browser runs on a different
machine than the backend. Per-deployment addresses live ONLY in the
extension storage of that machine's profile — never in the public
sources.

Create one profile per study and set the backend once per profile:

```bash
# Brazil26 profile (default endpoint, nothing to set)
firefox --createProfile laclaugpt-brazil26
firefox --profile laclaugpt-brazil26 -url about:debugging # install the extension, done

# AI26 profile: point the extension at :8766
firefox --createProfile laclaugpt-ai26
firefox --profile laclaugpt-ai26
# then in the extension's background context (about:debugging -> Inspect):
#   browser.storage.local.set({ backend_url: "http://127.0.0.1:8766" })
```

The value must match the backend's actual `--host`/port. When the
backend binds a Tailscale/deployment IP instead of localhost, set that
same IP in `backend_url`, e.g.
`browser.storage.local.set({ backend_url: "http://<tailscale-ip>:8766" })`
for the AI26 profile and `:8765` for the Brazil26 profile. A profile
still pointing at a stale default shows up as a healthy `/tour` and
`/status` on the backend with `firefox bridge: saved=0` and no new
`raw/` files — the fix is the storage edit above, not a backend
restart.

`navigation.js` awaits the stored value before its first tour tick;
`capture.js` resolves it before the first capture POST. Invalid or
absent values fall back to `127.0.0.1:8765`.

After editing `backend_url` (or after a browser restart), reload the
temporary add-on via about:debugging so both background scripts pick up
the stored value. Verify capture flow, not unit state: newest
`raw/<platform>/<date>/capture-*.ndjson` mtimes minutes old = alive.

## Data roots

Each backend writes only inside its own data root:

```text
~/laclaugpt-brasil-data/    raw/ normalized/ media/ manifests/ state.sqlite3
~/laclaugpt-ai26-data/      raw/ normalized/ media/ manifests/ state.sqlite3
```

The same platform document may exist once in EACH dataset when both
sampling designs legitimately capture it; dedup is per study. Tests:
`tests/collectors/test_dual_study_isolation.py`.

## Privacy boundary

Live account lists (`ai26.private.yaml`, the Brazil26 operational
config) stay in the private deployment checkout and are never
committed. The public repository carries only the schema, the
synthetic test fixtures, and this documentation.