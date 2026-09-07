"""Platform parsing modules (Zeeschuimer-derived, MPL-2.0)."""
from __future__ import annotations

from . import instagram, tiktok, twitter  # noqa: F401

PLATFORM_MODULES = {
    "tiktok": tiktok,
    "instagram": instagram,
    "x": twitter,
}