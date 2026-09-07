"""Project/profile-aware local and web visualization for LaclauGPT.

The visualization layer consumes canonical interchange output and is deliberately
separate from HPC analysis execution.  New code should import pure helpers from
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
from .review import ReviewStore
from .runtime import dashboard_runtime_violation, require_dashboard_runtime

__all__ = [
    "ReviewStore",
    "annotation_to_row",
    "articulation_edges",
    "dashboard_runtime_violation",
    "filter_frame",
    "flatten_annotations",
    "load_annotations",
    "require_dashboard_runtime",
    "top_values",
]
