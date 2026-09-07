# Platform parsing modules

Python ports of the Zeeschuimer platform modules, kept line-comparable
with upstream so future upstream fixes can be merged by diff.

## Attribution

Zeeschuimer — https://github.com/digitalmethodsinitiative/zeeschuimer
Copyright (c) Stijn Peeters <stijn.peeters@uva.nl>
License: Mozilla Public License 2.0 (MPL-2.0).

Ported upstream files (2026, LaclauGPT adaptation):

| LaclauGPT file  | Upstream source                    |
|-----------------|------------------------------------|
| `tiktok.py`     | `modules/tiktok.js`                |
| `instagram.py`  | `modules/instagram.js`             |
| `twitter.py`    | `modules/twitter.js`               |

Under MPL 2.0 this adaptation must remain available under MPL-2.0; the
upstream copyright notice is retained in each module header. Logic-level
changes (vs. plain translation): `capture()` also accepts pre-parsed
dict payloads (CDP/HAR driver shortcut); `map_item()` emits plain dicts
instead of 4CAT `MappedItem` objects; upstream endpoint/operation
allowlists, dedup semantics and partial-item handling are preserved.

The X/Twitter module deliberately follows upstream's operation-name
endpoint matching (never hard-coded GraphQL query IDs) and keeps all
post IDs as exact strings (they exceed 2^53).