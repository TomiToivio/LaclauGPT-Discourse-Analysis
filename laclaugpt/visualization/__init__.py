"""Project/profile-aware local and web visualization for LaclauGPT.

The visualization layer consumes canonical interchange output and is deliberately
separate from HPC analysis execution. New code should import pure helpers from
this package; Streamlit is an optional dependency loaded only by the dashboard.
"""

from .data import (
    annotation_to_row,
    articulation_edges,
    filter_frame,
    flatten_annotations,
    load_annotations,
    top_values,
)
from .graph import DASHBOARD_PROJECTIONS, graph_projection_data, graph_projection_options
from .review import ReviewStore
from .runtime import dashboard_runtime_violation, require_dashboard_runtime

__all__ = [
    "DASHBOARD_PROJECTIONS",
    "ReviewStore",
    "annotation_to_row",
    "articulation_edges",
    "dashboard_runtime_violation",
    "filter_frame",
    "flatten_annotations",
    "graph_projection_data",
    "graph_projection_options",
    "load_annotations",
    "require_dashboard_runtime",
    "top_values",
]
