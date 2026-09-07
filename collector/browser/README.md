# LaclauGPT Collector — Firefox extension

The browser-capture layer of the LaclauGPT Social Media Collector
(issue #20): a Manifest V2 Firefox add-on that captures public TikTok,
Instagram and X/Twitter content **from the network layer** while the
researcher browses normally — the Zeeschuimer approach.

## Origin & attribution

- **[Zeeschuimer](https://github.com/digitalmethodsinitiative/zeeschuimer)**
  (Digital Methods Initiative, **MIT**): the interception technique
  (`webRequest.filterResponseData`), per-platform endpoint knowledge
  (TikTok item_list / SIGI_STATE / __UNIVERSAL_DATA_FOR_REHYDRATION__;
  Instagram xdt GraphQL connections and the visited-account ownership
  filter; X GraphQL tweet_results walking), and the rule that X IDs stay
  strings. Parser modules are re-implementations of that knowledge for
  LaclauGPT's record shape — no verbatim upstream code.
- **[LaclauGPT-TikTok-Scraper](https://github.com/TomiToivio/LaclauGPT-TikTok-Scraper)**
  (CC0, 2024): the original background/content split and the
  filterResponseData plumbing, extended from TikTok-only to three platforms.
  The historical repo is untouched.

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
- Instagram: the Zeeschuimer ownership filter drops background/preloaded
  posts so the researcher's own feed never leaks into the corpus.
- X capture is operation-shape based, never hard-coded query IDs.

## Known fragility

Platform APIs change constantly. These parsers require maintenance after
platform updates — the same maintenance expectation as Zeeschuimer itself.
When a platform breaks, check the upstream Zeeschuimer module first: their
fix usually ports directly.