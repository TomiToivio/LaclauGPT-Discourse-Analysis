"""LaclauGPT-native platform parsing modules."""
from __future__ import annotations

from . import instagram, tiktok, twitter  # noqa: F401

PLATFORM_MODULES = {
    "tiktok": tiktok,
    "instagram": instagram,
    "x": twitter,
}
