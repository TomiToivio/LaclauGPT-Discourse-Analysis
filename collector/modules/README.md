# Platform parsing modules

These are **LaclauGPT-native platform parsers** for TikTok, Instagram and
X/Twitter.

Their architecture follows the historical
[LaclauGPT-TikTok-Scraper](https://github.com/TomiToivio/LaclauGPT-TikTok-Scraper):
capture a platform response, route it by request/view, parse native platform
objects in small helpers, and map them into a LaclauGPT-owned record shape.

Zeeschuimer remains an important **design inspiration** for browser/API-response
capture and a useful interoperability target, but these Python modules are not
ports or line-comparable adaptations of Zeeschuimer source code. They do not
reuse Zeeschuimer's parser source structure, 4CAT mapping sentinel, `_zs_*`
internal fields, or upstream sync blocks.

The parser implementations in this directory are released under the repository's
CC0 terms. Separate Zeeschuimer/4CAT import adapters elsewhere in the repository
remain interoperability code and are not affected by this parser rewrite.

## Design rules

- Keep platform post IDs as strings.
- Prefer explicit endpoint/view routing over opaque recursive assumptions.
- Accept platform payload drift through small compatibility helpers.
- Keep raw platform objects separate from LaclauGPT normalised records.
- Preserve source URL and collection provenance.
- Filter obvious ads/live/non-post payloads where the platform shape permits it.
- Use synthetic fixtures for public tests.

The browser-side parsers in `collector/browser/modules/` use the same
LaclauGPT-owned design principles.
