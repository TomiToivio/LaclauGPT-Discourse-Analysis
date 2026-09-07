# LaclauGPT Collector — Firefox extension

The browser-capture layer of the LaclauGPT Social Media Collector
(issue #20): a Manifest V2 Firefox add-on that captures public TikTok,
Instagram and X/Twitter content **from the network layer** while the
researcher browses normally.

## Origin

This extension follows the architecture of the original 2024
[LaclauGPT-TikTok-Scraper](https://github.com/TomiToivio/LaclauGPT-TikTok-Scraper)
(CC0, Tomi Toivio): explicit request routing, small platform-specific parsers,
and a LaclauGPT-owned record shape. The interception technique
(`webRequest.filterResponseData`) is Firefox-standard webRequest plumbing.
The historical repository is untouched; this is its generalisation to
TikTok + Instagram + X under the current collector architecture (issue #20).

## Install (temporary, Firefox)

1. `about:debugging#/runtime/this-firefox`
2. *Load Temporary Add-on…* → select `collector/browser/manifest.json`
3. Browse the target accounts normally — capture is automatic.

## Architecture

```
browser/
  manifest.json     MV2 (Firefox) — storage, webRequest, 3 platform hosts
  background.js     network interception → platform parsers → buffer
  content.js        embedded-JSON extraction (SIGI_STATE, UDR, IG inline)
  modules/
    tiktok.js       item_list + embedded payloads → records
    instagram.js    xdt GraphQL connections, visited-account filter
    twitter.js      GraphQL timeline, rest_id STRING ids, quote/reply links
```

Records buffer in `browser.storage.local` (per platform, capped 5000) and
are drained by the scheduler via the `get_buffer` message → NDJSON on disk
(`raw/`), then normalised into interchange records (`normalized/`).

## Research-ethics rules (enforced)

- Only **public** content, only what the platform serves during normal
  authenticated browsing — no private accounts, no CAPTCHA circumvention.
- Instagram: the ownership filter drops background/preloaded
  posts so the researcher's own feed never leaks into the corpus.
- X capture is operation-shape based, never hard-coded query IDs.

## Known fragility

Platform APIs change constantly. These parsers require maintenance after
platform updates. When one breaks, first re-verify the platform's current
API response shapes, then update the affected parser module.