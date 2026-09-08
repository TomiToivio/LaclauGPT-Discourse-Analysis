"""Shared model-routing policy for agent-triggered LaclauGPT runs.

Both agent integrations in this repository — Hermes Agent
(`laclaugpt.integrations.hermes`) and Claude Code
(`laclaugpt.integrations.claude`) — are restricted to **local Ollama
open-source models**.  Agent tool calls never route analysis to Ollama cloud,
external hosted endpoints or any other provider, and never run with the
local→cloud fallback authorised.

The policy is enforced in the agent tool surface (``enforce_local_ollama_policy``)
so an agent cannot weaken it conversationally; human CLI invocations keep the
full machine-tier routing described in ``llm.py``.
"""
from __future__ import annotations

import os

# Environment contract strings (single source of runtime truth is llm.py;
# duplicated here as literals so the agent tool surface never imports the
# Ollama client stack just to check policy).
LLM_MODE_ENV = "LLM_MODE"
LLM_MODE_ENV_ALIAS = "LACLAUGPT_OLLAMA_MODE"
LLM_ALLOW_CLOUD_FALLBACK_ENV = "LLM_ALLOW_CLOUD_FALLBACK"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def enforce_local_ollama_policy() -> str:
    """Require the environment to route analysis to local Ollama only.

    Returns the confirmed mode (``"local"``) or raises ``PermissionError``.
    Cloud/auto/external modes are refused because they can route research
    data off the local machine, and an authorised cloud fallback would do the
    same mid-run even under ``LLM_MODE=local``.
    """
    mode = (os.environ.get(LLM_MODE_ENV)
            or os.environ.get(LLM_MODE_ENV_ALIAS) or "").strip().lower()
    if mode != "local":
        raise PermissionError(
            "agent-triggered LaclauGPT runs require LLM_MODE=local: agents "
            "use only local Ollama open-source models, never Ollama cloud, "
            "external endpoints or auto routing")
    if (os.environ.get(LLM_ALLOW_CLOUD_FALLBACK_ENV, "").strip().lower()
            in _TRUE_VALUES):
        raise PermissionError(
            "agent-triggered LaclauGPT runs forbid "
            "LLM_ALLOW_CLOUD_FALLBACK=1: agents never fall back to cloud models")
    return mode