# LaclauGPT Collector — standalone Firefox extension

This is a LaclauGPT-native browser-capture prototype: a Manifest V2 Firefox
add-on that captures public TikTok, Instagram and X/Twitter content from the
network layer while the researcher browses normally.

**Status:** this directory is not the preferred automated collection path.
`collector/firefox/extension/` + `collector/firefox/firefox_backend.py` is the
current end-to-end Firefox collector because it sends captures directly into
the shared Python parser/normalise/store pipeline. This standalone extension
instead parses in JavaScript and buffers records in `browser.storage.local`.
There is currently no repository-side process that automatically drains its
`get_buffer` message into the Python Store.

## Origin

This extension follows the architecture of the original 2024
[LaclauGPT-TikTok-Scraper](https://github.com/TomiToivio/LaclauGPT-TikTok-Scraper)
(CC0, Tomi Toivio): explicit request routing, small platform-specific parsers,
and a LaclauGPT-owned record shape. The interception technique
(`webRequest.filterResponseData`) is Firefox webRequest plumbing. The
historical repository is untouched; this is its generalisation to TikTok +
Instagram + X.

## Install for manual/development use

1. Open `about:debugging#/runtime/this-firefox`
2. *Load Temporary Add-on…* and select `collector/browser/manifest.json`
3. Browse target accounts normally; capture is automatic

For systematic study collection use the preferred
`collector/firefox/extension/` path documented in `collector/firefox/README.md`.

## Architecture

```
browser/
  manifest.json     MV2 Firefox extension
  background.js     network interception -> JS platform parsers -> local buffer
  content.js        embedded-JSON extraction (SIGI_STATE, UDR, IG inline)
  modules/
    tiktok.js       LaclauGPT TikTok response routing -> records
    instagram.js    GraphQL/API parsing + visited-account filter
    twitter.js      GraphQL timeline parsing, exact string IDs, quote/reply links
```

Records are deduplicated in `browser.storage.local`, per platform, capped at
5000 records. The background message API supports `get_buffer`,
`buffer_status`, and `clear_buffer`. Automatic persistence from this buffer to
`collector/store.py` is intentionally **not claimed here** because it is not
currently wired in the repository.

## Research-ethics rules

- Only public content served during normal authenticated browsing.
- No private-account, CAPTCHA or access-control circumvention.
- Instagram parsing guards against unrelated prefetched profile content.
- X capture is operation-shape based rather than tied to rotating GraphQL IDs.

## Known fragility

Platform APIs change constantly. When one platform stops producing records,
first inspect a current response payload and update only the affected parser.
The preferred Firefox/Python path has the stronger automated test coverage and
should be used for research collection runs.
