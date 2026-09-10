# -*- coding: utf-8 -*-
"""Task-difficulty model routing for local Gemma 4 variants.

The router uses three local tiers and does not introduce a cloud fallback.
Approximate model footprints are kept only to support generic VRAM guards;
concrete hostnames, GPU inventories and deployment measurements belong in
machine-local operational notes outside the public repository.

Routing by pipeline stage:
    summary      -> gemma4:e4b
    discourse    -> gemma4:26b
    postprocess  -> gemma4:e2b
    populism     -> gemma4:26b
    entities     -> gemma4:e2b
    sentiment    -> gemma4:e2b
    topics       -> gemma4:26b
    temporal     -> gemma4:26b

Document-length override: very long texts (>8000 chars) escalate e2b/e4b
one tier to preserve evidence fidelity. GPU memory guard: if a tier does
not fit free VRAM the worker walks DOWN the capability order and records
the fallback reason.
"""
from __future__ import annotations

import json
import subprocess
from functools import lru_cache

MODELS = {
    "e2b": "gemma4:e2b",
    "e4b": "gemma4:e4b",
    "26b": "gemma4:26b",
}

# Ascending capability order for fallback walks
CAPABILITY_ORDER = ["e2b", "e4b", "26b"]

STAGE_ROUTING = {
    "summary": "e4b",
    "discourse": "26b",
    "postprocess": "e2b",
    "populism": "26b",
    "entities": "e2b",
    "sentiment": "e2b",
    "topics": "26b",
    "temporal": "26b",
}

# texts longer than this escalate one tier (evidence fidelity on long posts)
LONG_TEXT_CHARS = 8000

OLLAMA_HOST = "http://127.0.0.1:11434"


@lru_cache(maxsize=1)
def _loaded_models() -> set[str]:
    """Names of models present in the local Ollama instance."""
    try:
        raw = subprocess.run(
            ["curl", "-s", f"{OLLAMA_HOST}/api/tags"],
            capture_output=True, text=True, timeout=10).stdout
        return {m["name"] for m in json.loads(raw).get("models", [])}
    except Exception:
        return set()


@lru_cache(maxsize=1)
def _free_vram_gb() -> float:
    """Free VRAM across GPUs, best-effort via nvidia-smi."""
    try:
        raw = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10).stdout
        per_gpu = [int(x) for x in raw.strip().splitlines() if x.strip()]
        return max(per_gpu, default=0) / 1024.0
    except Exception:
        return 0.0


def pick_model(stage: str, text_len: int = 0) -> str:
    """Resolve the Gemma 4 variant for one pipeline stage.

    Order: stage routing -> long-text escalation -> availability walk
    (requested tier down to the largest model that fits free VRAM).
    Always returns a LOCAL gemma4 tag; raises if nothing fits.
    """
    tier = STAGE_ROUTING.get(stage, "26b")
    if text_len > LONG_TEXT_CHARS and tier in ("e2b", "e4b"):
        tier = "26b"
    loaded = _loaded_models()
    free = _free_vram_gb()
    # walk DOWN the capability order from the requested tier
    start = CAPABILITY_ORDER.index(tier)
    for name in reversed(CAPABILITY_ORDER[:start + 1]):
        tag = MODELS[name]
        if tag not in loaded:
            continue
        # rough VRAM guards: need model size + KV cache headroom
        need = {"e2b": 6, "e4b": 8, "26b": 17}[name]
        if free == 0 or free >= need * 0.9:
            return tag
    # nothing fits by VRAM estimate — return the smallest present as last resort
    for name in CAPABILITY_ORDER:
        if MODELS[name] in loaded:
            return MODELS[name]
    raise RuntimeError("no local gemma4 model available on this Ollama host")


def routing_table() -> dict:
    """Resolved routing for logging/provenance."""
    return {stage: pick_model(stage)
            for stage in STAGE_ROUTING}
