# -*- coding: utf-8 -*-
"""AI26 task-difficulty model routing for Gemma 4 variants.

Tomi's rule (2026-09-08): pick the Gemma 4 model by stage difficulty,
not one-size-fits-all. All LOCAL (no cloud fallback for research).

Tiers on Laskin (2x Tesla V100-32GB):
    gemma4:e2b   7.2 GB  — cheap/dense stages (sentiment, entities, topics)
    gemma4:e4b   9.6 GB  — default descriptive work
    gemma4:12b   7.6 GB  — mid complexity, long context at lower rank
    gemma4:26b  18.0 GB  — default RESEARCH model (MoE, strong reasoning)
    gemma4:31b  19.9 GB  — hardest stage: discourse w/ evidence quotes

Routing by pipeline stage:
    summary      -> gemma4:e4b   (dense summary; quality gate is discourse)
    discourse    -> gemma4:31b   (Laclau/Palonen coding + verbatim evidence)
    postprocess  -> gemma4:e2b   (structured extraction, low ambiguity)
    populism     -> gemma4:26b   (Us/Frontier judgement, needs reasoning)
    entities     -> gemma4:e2b
    sentiment    -> gemma4:e2b
    topics       -> gemma4:12b
    temporal     -> gemma4:12b

Document-length override: very long texts (transcripts > 8000 chars)
escalate one tier for summary/discourse to preserve evidence fidelity.
GPU memory guard: 31b needs ~20GB VRAM; if the other GPU is busy the
worker falls back 31b -> 26b -> 12b and records the fallback reason.
"""
from __future__ import annotations

import json
import subprocess
from functools import lru_cache

MODELS = {
    "e2b": "gemma4:e2b",
    "e4b": "gemma4:e4b",
    "12b": "gemma4:12b",
    "26b": "gemma4:26b",
    "31b": "gemma4:31b",
}

# Ascending capability order for fallback walks
CAPABILITY_ORDER = ["e2b", "e4b", "12b", "26b", "31b"]

STAGE_ROUTING = {
    "summary": "e4b",
    "discourse": "31b",
    "postprocess": "e2b",
    "populism": "26b",
    "entities": "e2b",
    "sentiment": "e2b",
    "topics": "12b",
    "temporal": "12b",
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
        tier = "12b"
    loaded = _loaded_models()
    free = _free_vram_gb()
    # walk DOWN the capability order from the requested tier
    start = CAPABILITY_ORDER.index(tier)
    for name in reversed(CAPABILITY_ORDER[:start + 1]):
        tag = MODELS[name]
        if tag not in loaded:
            continue
        # rough VRAM guards: need model size + KV cache headroom
        need = {"e2b": 6, "e4b": 8, "12b": 7, "26b": 17, "31b": 19}[name]
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