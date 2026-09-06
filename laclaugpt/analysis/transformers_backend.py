"""Hugging Face Transformers backend: pretrained-model inference layer.

Configurable tasks: sentiment, zero-shot classification, NER, emotion.
The model is ALWAYS selected by project/machine config — never
hard-coded globally. Every result keeps model, version, task,
confidence and provenance identity. Classifier probability is
descriptive evidence, not theoretical confidence.
"""
from __future__ import annotations

from typing import Any

from laclaugpt.analysis import BackendUnavailable, ClassificationResult
from laclaugpt.model import Provenance

_BACKEND = "transformers"
_ENGINES: dict[str, Any] = {}


def is_available() -> bool:
    try:
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _version() -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version("transformers")
    except Exception:
        return ""


def _pipeline(task: str, model: str):
    key = f"{task}:{model}"
    if key not in _ENGINES:
        from transformers import pipeline as hf_pipeline
        _ENGINES[key] = hf_pipeline(task=task, model=model)
    return _ENGINES[key]


def classify(text: str, *, task: str, model: str | None = None,
             provenance: Provenance | None = None) -> ClassificationResult:
    """Run one configurable transformers task. model comes from project
    config (analysis.transformer_analysis.models.<task>.model)."""
    if not is_available():
        raise BackendUnavailable("transformers is not installed")
    tasks = {
        "sentiment": "sentiment-analysis",
        "text_classification": "text-classification",
        "zero_shot": "zero-shot-classification",
        "ner": "token-classification",
        "emotion": "text-classification",
    }
    hf_task = tasks.get(task)
    if hf_task is None:
        raise ValueError(f"unknown transformers task: {task}")
    if model is None:
        raise ValueError(
            f"transformers task {task!r} requires a configured model "
            "(project config: analysis.transformer_analysis.models)")
    engine = _pipeline(hf_task, model)
    output = engine(text)
    top = output[0] if isinstance(output, list) and output else output
    label = str(top.get("label", "")) if isinstance(top, dict) else ""
    confidence = None
    if isinstance(top, dict) and top.get("score") is not None:
        confidence = float(top["score"])
    if task == "zero_shot" and isinstance(output, dict):
        scores = output.get("scores") or []
        labels = output.get("labels") or []
        if labels and scores:
            label, confidence = str(labels[0]), float(scores[0])
    return ClassificationResult(
        label=label, confidence=confidence, task=task,
        model=model, model_version=_version(), backend=_BACKEND,
        provenance_id=provenance.provenance_id if provenance else "",
    )


def extract_mentions(text: str, *, model: str,
                     provenance: Provenance | None = None) -> list[dict[str, Any]]:
    """Transformers NER alternative to spaCy: token-classification spans
    grouped into words. Same rule: spans are EntityMention candidates."""
    if not is_available():
        raise BackendUnavailable("transformers is not installed")
    engine = _pipeline("token-classification", model)
    raw = engine(text)
    mentions: list[dict[str, Any]] = []
    for entry in raw:
        mentions.append({
            "surface_form": entry.get("word", ""),
            "transformers_label": entry.get("entity_group") or entry.get("entity", ""),
            "start_offset": entry.get("start"), "end_offset": entry.get("end"),
            "confidence": float(entry.get("score") or 0.0),
            "model": model, "backend": _BACKEND,
            "provenance_id": provenance.provenance_id if provenance else "",
        })
    return mentions