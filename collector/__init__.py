"""LaclauGPT social-media collector.

Collection subsystem for systematic political research on public social
media content (TikTok, Instagram, X/Twitter). Collection produces source
material; LaclauGPT discourse analysis consumes it later.

Four layers (see collector/README.md):

1. browser/network capture   collector.browser    (pluggable drivers)
2. platform-specific parsing collector.modules   (Zeeschuimer-derived)
3. normalisation/provenance  collector.normalize, collector.provenance
4. durable metadata + media  collector.store, collector.media
"""
from __future__ import annotations

COLLECTOR_VERSION = "0.1.0"