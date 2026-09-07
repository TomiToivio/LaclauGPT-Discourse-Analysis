# -*- coding: utf-8 -*-
"""LLM client wrapper: one place for model calls, options, structured output.

Machine-tier routing (maintainer rule):

    Machines with a real GPU (cluster nodes, workstation) -> LOCAL Ollama
    Machines with too little GPU / only micromodels            -> Ollama CLOUD

Selection order (LLM_MODE / LACLAUGPT_OLLAMA_MODE):
    1. explicit env (LLM_MODE=local|cloud) wins
    2. auto: local if a reachable Ollama endpoint reports usable VRAM
       (>= LLM_LOCAL_MIN_VRAM_GB, default 16), else cloud
    3. OLLAMA_HOST is honoured for remote/local Ollama servers alike
    4. local -> cloud fallback is forbidden by default and must be explicitly
       authorised by the caller or LLM_ALLOW_CLOUD_FALLBACK=1

Defaults follow the LaclauGPT model tiers: Gemma 4 models are typically
enough for LaclauGPT analysis stages.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Type
from urllib.parse import urlparse

import ollama

logger = logging.getLogger(__name__)

# ── machine-tier routing ─────────────────────────────────────────────
LLM_MODE_ENV = "LLM_MODE"                # local | cloud | external
LLM_MODE_ENV_ALIAS = "LACLAUGPT_OLLAMA_MODE"
LLM_HOST_ENV = "OLLAMA_HOST"             # standard Ollama var, honoured
LLM_CLOUD_ENV = "LLM_CLOUD_MODEL"        # model to use in cloud mode
LLM_LOCAL_MODEL_ENV = "LLM_LOCAL_MODEL"
LLM_ALLOW_CLOUD_FALLBACK_ENV = "LLM_ALLOW_CLOUD_FALLBACK"
LLM_LOCAL_MIN_VRAM_GB = float(os.environ.get("LLM_LOCAL_MIN_VRAM_GB", "16"))
LLM_DEFAULT_LOCAL = "gemma4:e4b"         # enough for LaclauGPT stages
LLM_DEFAULT_CLOUD = "gemma4:31b-cloud"   # cloud twin for weak machines
_CAPABLE_HOST_MARKERS = os.environ.get(
    "LACLAUGPT_GPU_HOST_MARKERS", "roihu,gpu,workstation").split(",")
_LOCAL_ENDPOINTS = {"", "127.0.0.1", "localhost", "::1"}
_TRUE_VALUES = {"1", "true", "yes", "on"}

# Ollama fallback options; callers normally override via ``options``.
DEFAULT_OPTIONS = {
    "temperature": 0.0,
    "num_ctx": 8192,
    "num_predict": 2048,
}


@dataclass(frozen=True)
class LLMCallProvenance:
    """The routing facts for one successful model response.

    ``requested_model`` is the caller's hint. ``resolved_model`` is the model
    chosen by routing before the request. ``actual_model`` is the model that
    produced the returned content. These values may differ only when an
    explicitly authorised fallback occurs.
    """

    requested_mode: str
    requested_model: str
    resolved_model: str
    actual_mode: str
    actual_model: str
    actual_model_digest: str = ""
    endpoint: str = ""
    fallback_used: bool = False
    fallback_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@lru_cache(maxsize=8)
def _probe_host(host: str) -> dict[str, Any] | None:
    """One cached probe per Ollama endpoint: None = unreachable."""
    try:
        client = ollama.Client(host=host) if host else ollama.Client()
        info = client.heartbeat() if hasattr(client, "heartbeat") else None
        vram = 0
        try:
            props = client._request("GET", "/api/gpu") if hasattr(client, "_request") else None
            if props and isinstance(props, (list, dict)):
                items = props if isinstance(props, list) else [props]
                for item in items:
                    # /api/gpu reports VRAM in MiB; accumulate in GB
                    vram += int(item.get("vram", 0) or 0) / 1024
        except Exception:
            pass
        return {"ok": True, "vram_gb": vram}
    except Exception as exc:
        logger.debug("Ollama probe failed for %s: %s", host or "default", exc)
        return None


@lru_cache(maxsize=64)
def model_digest(model: str) -> str:
    """Digest of a model build, for reproducible provenance (paper §3.3).

    The model name alone is insufficient: the same tag can resolve to
    different builds across hardware and time. Returns "" when the
    endpoint cannot report a digest, so callers must tolerate absence.
    """
    try:
        host = os.environ.get(LLM_HOST_ENV, "").strip()
        client = ollama.Client(host=host) if host else ollama.Client()
        info = client.show(model)
        digest = getattr(info, "digest", "") or ""
        if not digest and isinstance(info, dict):
            digest = str(info.get("digest", "") or "")
        return str(digest)
    except Exception as exc:
        logger.debug("model digest unavailable for %s: %s", model, exc)
        return ""


def _endpoint_hostname(endpoint: str) -> str:
    if not endpoint:
        return ""
    parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    return (parsed.hostname or "").casefold()


def _external_endpoint(endpoint: str) -> bool:
    return _endpoint_hostname(endpoint) not in _LOCAL_ENDPOINTS


def _detected_vram_gb() -> float:
    """Read the largest NVIDIA GPU; return zero on CPU-only hosts."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3, check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return 0.0
    if result.returncode:
        return 0.0
    sizes = []
    for line in result.stdout.splitlines():
        try:
            sizes.append(float(line.strip()) / 1024)
        except ValueError:
            continue
    return max(sizes, default=0.0)


def _capable_local_machine() -> bool:
    hostname = platform.node().casefold()
    if any(marker in hostname for marker in _CAPABLE_HOST_MARKERS):
        return True
    if os.environ.get("SLURM_JOB_GPUS"):
        return True
    return _detected_vram_gb() >= LLM_LOCAL_MIN_VRAM_GB


def resolve_endpoint(model_hint: str | None = None) -> tuple[str, str]:
    """Return (mode, model) following the machine-tier rule.

    mode is ``local``, ``cloud``, or ``external``.
    """
    mode_env = (os.environ.get(LLM_MODE_ENV)
                or os.environ.get(LLM_MODE_ENV_ALIAS) or "").strip().lower()
    allowed_modes = ("auto", "local", "cloud", "external")
    if mode_env and mode_env not in allowed_modes:
        raise ValueError(f"LLM mode must be one of: {', '.join(allowed_modes)}")
    host = os.environ.get(LLM_HOST_ENV, "")
    if mode_env in ("", "auto"):
        if host and _external_endpoint(host):
            mode = "external"
        elif _capable_local_machine():
            mode = "local"
        else:
            probe = _probe_host(host)
            vram = (probe or {}).get("vram_gb", 0) or 0
            mode = "local" if vram >= LLM_LOCAL_MIN_VRAM_GB else "cloud"
    else:
        mode = mode_env
    if mode == "external" and not host:
        raise ValueError("external Ollama mode requires OLLAMA_HOST")
    if model_hint and model_hint.casefold() == "auto":
        model_hint = None
    configured = (os.environ.get("LACLAUGPT_OLLAMA_MODEL")
                  or os.environ.get("OLLAMA_MODEL"))
    if mode == "cloud":
        model = configured or (model_hint if _looks_cloud(model_hint) else None) \
            or os.environ.get(LLM_CLOUD_ENV) or LLM_DEFAULT_CLOUD
    else:
        model = configured or (model_hint if not _looks_cloud(model_hint) else None) \
            or os.environ.get(LLM_LOCAL_MODEL_ENV) or LLM_DEFAULT_LOCAL
    return mode, model


def _looks_cloud(model: str | None) -> bool:
    return bool(model) and (model.endswith("-cloud") or model.endswith(":cloud"))


def describe_routing(model_hint: str | None = None) -> str:
    """Human-readable summary of the active machine-tier routing decision."""
    mode, model = resolve_endpoint(model_hint)
    host = os.environ.get(LLM_HOST_ENV, "").strip() or "default endpoint"
    if mode == "cloud":
        return f"cloud Ollama via {host} (weak-GPU machine) -> {model}"
    if mode == "external":
        return f"external Ollama at {host} -> {model}"
    return f"local Ollama at {host} -> {model}"


def _client() -> ollama.Client:
    host = os.environ.get(LLM_HOST_ENV, "").strip()
    kwargs: dict[str, Any] = {"host": host} if host else {}
    api_key = os.environ.get("OLLAMA_API_KEY", "").strip()
    if api_key and "ollama.com" in host:
        kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}
    return ollama.Client(**kwargs)


def _fallback_allowed(explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    return os.environ.get(LLM_ALLOW_CLOUD_FALLBACK_ENV, "").strip().casefold() in _TRUE_VALUES


def _retryable_local_error(exc: Exception) -> bool:
    """Return True only for transport/service failures worth one cloud retry.

    Validation, programming and client-side request errors must propagate.
    The Ollama Python package has changed exception classes across releases,
    so the check uses stable attributes/class names in addition to standard
    transport exceptions.
    """
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True
    name = type(exc).__name__.casefold()
    if any(token in name for token in ("connect", "timeout", "network", "transport")):
        return True
    status = getattr(exc, "status_code", None)
    try:
        if status is not None and int(status) >= 500:
            return True
    except (TypeError, ValueError):
        pass
    return False


# ── sampling defaults (paper §3.3: temperature 0.0 for verifiability) ─
DEFAULT_OPTIONS = {
    "repeat_last_n": 64,
    "repeat_penalty": 1.1,
    "num_ctx": 8192,
    "top_p": 0.9,
    "top_k": 40,
    "min_p": 0.0,
    "temperature": 0.0,
    "num_predict": 2048,
}


def chat_with_provenance(
    model: str,
    system_prompt: str,
    user_prompt: str,
    options: dict | None = None,
    schema: dict | None = None,
    *,
    allow_cloud_fallback: bool | None = None,
) -> tuple[str, LLMCallProvenance]:
    """One model call returning both content and the model that produced it.

    Explicit ``local`` routing is a hard data boundary. A failed local call is
    never sent to cloud unless fallback permission is separately granted and
    the failure is a retryable transport/service error.
    """
    mode, resolved = resolve_endpoint(model)
    use_model = resolved
    actual_mode = mode
    fallback_used = False
    fallback_reason = ""
    opts = dict(DEFAULT_OPTIONS)
    if options:
        opts.update(options)
    kwargs = {"format": schema} if schema is not None else {}
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        response = _client().chat(model=use_model, messages=messages, options=opts, **kwargs)
    except Exception as exc:
        can_fallback = (
            mode == "local"
            and not _looks_cloud(use_model)
            and _fallback_allowed(allow_cloud_fallback)
            and _retryable_local_error(exc)
        )
        if not can_fallback:
            raise
        cloud_model = os.environ.get(LLM_CLOUD_ENV) or LLM_DEFAULT_CLOUD
        logger.warning(
            "local Ollama failed with retryable error (%s); authorised fallback to %s",
            exc, cloud_model,
        )
        response = _client().chat(model=cloud_model, messages=messages, options=opts, **kwargs)
        use_model = cloud_model
        actual_mode = "cloud"
        fallback_used = True
        fallback_reason = f"{type(exc).__name__}: {exc}"

    content = response["message"]["content"]
    host = os.environ.get(LLM_HOST_ENV, "").strip() or "default endpoint"
    provenance = LLMCallProvenance(
        requested_mode=mode,
        requested_model=model,
        resolved_model=resolved,
        actual_mode=actual_mode,
        actual_model=use_model,
        actual_model_digest=model_digest(use_model),
        endpoint=host,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    )
    logger.debug(
        "LLM response requested=%s/%s actual=%s/%s fallback=%s: %s",
        mode, resolved, actual_mode, use_model, fallback_used, content,
    )
    return content, provenance


def chat(model: str, system_prompt: str, user_prompt: str,
         options: dict | None = None, schema: dict | None = None,
         *, allow_cloud_fallback: bool | None = None) -> str:
    """Backward-compatible text-only wrapper around :func:`chat_with_provenance`."""
    content, _ = chat_with_provenance(
        model, system_prompt, user_prompt, options, schema,
        allow_cloud_fallback=allow_cloud_fallback,
    )
    return content


def _strip_code_fences(content: str) -> str:
    """Remove markdown code fences some models wrap JSON in."""
    text = content.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _schema_example(model_cls: Type) -> str:
    """Compact JSON example showing the exact field names and nesting.

    Cloud Ollama models do not enforce the ``format`` schema (the remote
    API ignores it), so the expected shape must travel inside the prompt:
    a bare "return valid JSON" instruction let gemma4:31b-cloud invent its
    own structure (dicts where strings were required, missing fields).
    """
    schema = model_cls.model_json_schema()
    defs = schema.get("$defs", {})

    def render(node: dict, depth: int) -> str:
        if depth > 12:  # guard against self-referencing $defs
            return '"..."'
        if "$ref" in node:
            target = defs.get(str(node["$ref"]).rsplit("/", 1)[-1])
            return render(target, depth + 1) if target else '"..."'
        if "const" in node:
            return json.dumps(node["const"], ensure_ascii=False)
        if "enum" in node and node["enum"]:
            opts = " | ".join(str(opt) for opt in node["enum"])
            return f'"<{opts}>"'
        branches = node.get("anyOf")
        if branches:
            non_null = [b for b in branches if b.get("type") != "null"]
            return render((non_null or branches)[0], depth)
        t = node.get("type")
        if t == "boolean":
            return "true"
        if t in ("number", "integer"):
            return "0"
        if t == "array":
            return f'[{render(node.get("items") or {}, depth + 1)}]'
        if t == "object" or "properties" in node:
            props = node.get("properties") or {}
            if not props:
                return "{}"
            parts = [
                f'{"  " * (depth + 1)}"{key}": {render(sub, depth + 1)}'
                for key, sub in props.items()
            ]
            return "{\n" + ",\n".join(parts) + "\n" + "  " * depth + "}"
        return '"..."'

    return render(schema, 0)


def chat_structured(model: str, system_prompt: str, user_prompt: str,
                    model_cls: Type, options: dict | None = None, *,
                    allow_cloud_fallback: bool | None = None,
                    return_provenance: bool = False):
    """Structured output: pass a Pydantic model, get a validated instance.
    Retries once on JSON validation failure with a strict reminder.

    When ``return_provenance`` is true, return ``(instance, provenance)`` so
    callers can persist the actual endpoint/model used for the valid response.
    """
    schema = model_cls.model_json_schema()
    shape = _schema_example(model_cls)
    base_prompt = user_prompt + (
        "\n\n### **Required output JSON shape**\n"
        "Return ONLY a single JSON object (no markdown fences, no commentary) "
        "with EXACTLY the following field names and nesting:\n"
        f"{shape}\n"
        "Every listed field must be present (use [] for empty lists and \"\" for "
        "empty strings — never null); "
        "do not invent extra fields or nest fields differently."
    )
    for attempt in (1, 2):
        content, provenance = chat_with_provenance(
            model, system_prompt, base_prompt, options, schema,
            allow_cloud_fallback=allow_cloud_fallback,
        )
        try:
            parsed = model_cls.model_validate_json(_strip_code_fences(content))
            return (parsed, provenance) if return_provenance else parsed
        except Exception as exc:
            logger.warning("structured parse failed (attempt %d): %s", attempt, exc)
            if attempt == 2:
                raise
            base_prompt = base_prompt + "\n\nYour previous answer was not valid JSON for the schema. Return ONLY the JSON object with exactly the required fields."
    raise RuntimeError("unreachable")


def chat_text(model: str, system_prompt: str, user_prompt: str,
              options: dict | None = None, *,
              allow_cloud_fallback: bool | None = None) -> str:
    return chat(
        model, system_prompt, user_prompt, options, schema=None,
        allow_cloud_fallback=allow_cloud_fallback,
    )
