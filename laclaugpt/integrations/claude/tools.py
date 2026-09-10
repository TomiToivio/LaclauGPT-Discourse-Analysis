"""Claude Code tool surface over the audited agent wrapper.

No Claude/Anthropic SDK is imported here.  ``ClaudeTools`` is the Hermes tool
surface with a different audit actor and log path: Claude Code participates as
an ordinary caller of the canonical CLI, never as a parallel implementation of
the methodology.  All model routing stays on local Ollama open-source models
(``laclaugpt.integrations.agent_policy``).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from laclaugpt.cli import main as cli_main
from laclaugpt.integrations.hermes.tools import HermesTools


class ClaudeTools(HermesTools):
    """Audited tool surface for Claude Code sessions in this repository.

    Same allowlist and restrictions as ``HermesTools``: canonical CLI entry
    points only, forced ``--execution agent`` provenance, an append-only JSONL
    audit trail, no destructive/publishing/repository-writing operations, and
    local Ollama open-source models only.
    """

    def __init__(
        self,
        audit_log: str | Path = "data/audit/claude-actions.jsonl",
        *,
        cli: Callable[[list[str] | None], int] = cli_main,
    ) -> None:
        super().__init__(audit_log, actor="claude-code", cli=cli)

    def request_destructive_action(self, action: str) -> None:
        """Fail-closed boundary: never executes destructive operations."""
        self.audit.append("destructive_action", "rejected", {"requested_action": action})
        raise PermissionError(
            "Claude Code integration does not execute destructive, publishing, "
            "or repository-changing actions"
        )