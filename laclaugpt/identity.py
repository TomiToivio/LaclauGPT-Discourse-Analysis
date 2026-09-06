"""Stable source identity and conservative URL normalisation."""
from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref_src"}


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS]
    host = (parts.hostname or "").lower()
    port = parts.port
    netloc = host if port is None else f"{host}:{port}"
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower() or "https", netloc, path,
                       urlencode(sorted(query)), ""))


def source_identity(*, url: str | None, platform: str | None,
                    native_id: str | None) -> str:
    if url:
        key = f"url\0{normalize_url(url)}"
    elif platform and native_id:
        key = f"native\0{platform.casefold()}\0{native_id}"
    else:
        raise ValueError("source identity needs a URL or (platform, native_id)")
    return "src_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]

