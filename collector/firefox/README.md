# Firefox capture layer

Firefox extension + local backend for the Brazil 2026 study. This is
the **preferred capture path** for the collector.

## Why Firefox

`browser.webRequest.filterResponseData` is a Firefox-only API that
reliably delivers API response bodies. Chromium (CDP/HAR) returns
empty bodies for TikTok's main `post/item_list` feed — verified
2026-09-07 — because the page consumes the response stream itself.
Zeeschuimer and the historical LaclauGPT TikTok Scraper are
Firefox-based for exactly this reason.

## Architecture

```
Firefox (your normal browser, logged in)
  extension: capture.js     webRequest.filterResponseData -> POST /capture
             navigation.js  tour loop: visits each account, scrolls
             content.js     scroll helper on account pages
        |  HTTP 127.0.0.1:8765
        v
  firefox_backend.py        SAME tested pipeline as the CDP driver:
                            collector/modules parsers -> normalize ->
                            store (raw/, normalized/, manifests/, SQLite)
```

The extension is a thin capture + navigation layer; all parsing and
storage live in the Python backend, so every capture path (CDP, HAR,
Firefox) converges on one tested pipeline and one data layout.

Attribution: adapted from the historical LaclauGPT TikTok Scraper
Firefox extension (CC0) and Zeeschuimer's capture architecture
(MPL-2.0). Academic research use only.

## Install (one-time, your Windows Firefox)

1. Start the backend:
   ```bash
   python -m collector.firefox.firefox_backend \
       --config collector/config/study.private.yaml \
       --data-root ~/laclaugpt-brasil-data
   ```
2. Open Firefox -> `about:debugging#/runtime/this-firefox`
3. "Load Temporary Add-on..." -> select `collector/firefox/extension/manifest.json`
4. Keep the backend running while you browse. The extension captures
   API responses from every TikTok/Instagram/X page you visit and the
   tour loop visits the configured accounts automatically every 5 min.

## Notes

- The tour loop asks the backend for the account list (`/tour`) built
  from the study YAML — same single source of truth as the CLI runner.
- `GET /status` on the backend shows live counters (captures, posts,
  seen_total, git commit).
- Captures from pages you browse personally are filtered by the same
  view-allowlist logic as the CDP path (Instagram prefetch, X
  non-post-bearing operations, TikTok preload) — your own feed is not
  silently collected.
- The extension is temporary (about:debugging): reload it after
  Firefox restarts. For the study period that is the honest tradeoff
  for no signed distribution.