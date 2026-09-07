"""Optional Hermes Agent integration.

This package has no dependency on Hermes itself.  It exposes a narrow,
audited wrapper around LaclauGPT's canonical CLI/configuration layer so Hermes
or another agent framework can orchestrate research runs without duplicating
pipeline logic or bypassing policy.
"""

from .tools import HermesAuditLog, HermesTools

__all__ = ["HermesAuditLog", "HermesTools"]
