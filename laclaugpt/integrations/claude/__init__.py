"""Optional Claude Code integration.

This package has no dependency on Claude Code itself and adds no dependency to
the core package.  It reuses the audited Hermes tool surface with a
``claude-code`` audit actor so a Claude Code session can drive the canonical
pipeline under exactly the same boundaries: canonical CLI only, ``--execution
agent`` provenance, no destructive/publishing operations, and local Ollama
open-source models only.
"""

from .tools import ClaudeTools

__all__ = ["ClaudeTools"]