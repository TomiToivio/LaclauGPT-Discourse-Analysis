"""Runtime policy for the interactive visualization service."""
from __future__ import annotations

import os
import socket
from collections.abc import Mapping


def dashboard_runtime_violation(
    environment: Mapping[str, str] | None = None,
    hostname: str | None = None,
) -> str | None:
    """Return a reason when interactive visualization must not run here.

    The dashboard is intended for a workstation/laptop or a persistent Linux web
    server such as CSC Pouta. It is not an HPC batch workload and must not be run
    inside Roihu/Slurm allocations.
    """
    env = dict(os.environ if environment is None else environment)
    host = (hostname or socket.gethostname()).casefold()
    cluster = " ".join(
        str(env.get(key, ""))
        for key in (
            "SLURM_CLUSTER_NAME",
            "CSC_COMPUTING_ENV",
            "LACLAUGPT_RUNTIME",
            "HOSTNAME",
        )
    ).casefold()
    if env.get("SLURM_JOB_ID"):
        return "interactive visualization is disabled inside Slurm/HPC allocations"
    if "roihu" in host or "roihu" in cluster:
        return "interactive visualization is disabled on CSC Roihu"
    return None


def require_dashboard_runtime():
    """Validate the host and return lazily imported visualization libraries."""
    reason = dashboard_runtime_violation()
    if reason:
        raise RuntimeError(
            f"{reason}; run the dashboard locally or on a persistent Linux web server "
            "such as CSC Pouta instead"
        )
    try:
        import networkx as nx
        import plotly.express as px
        import plotly.graph_objects as go
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError(
            "visualization dependencies are not installed; run "
            '`python -m pip install -e ".[visualization]"`'
        ) from exc
    return st, px, go, nx
