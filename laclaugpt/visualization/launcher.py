"""Command-line launcher for the optional Streamlit visualization."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from laclaugpt.config import list_arenas, list_projects
from laclaugpt.visualization.runtime import require_dashboard_runtime


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="laclaugpt-dashboard")
    root.add_argument("data", help="canonical LaclauGPT JSONL/NDJSON output")
    root.add_argument("--project", required=True, choices=list_projects())
    root.add_argument("--arena", required=True, choices=list_arenas())
    root.add_argument("--review-db", default="")
    root.add_argument("--reviewer", default="", help="local reviewer ID/pseudonym")
    root.add_argument(
        "--blind-initial",
        action="store_true",
        help="hide model suggestions and peer assessments until explicit reveal",
    )
    root.add_argument("--host", default="127.0.0.1")
    root.add_argument("--port", type=int, default=8501)
    return root


def launch(
    data: str,
    *,
    project: str,
    arena: str,
    review_db: str = "",
    reviewer: str = "",
    blind_initial: bool = False,
    host: str = "127.0.0.1",
    port: int = 8501,
) -> int:
    require_dashboard_runtime()
    if arena not in list_arenas(project):
        raise SystemExit(f"arena {arena!r} does not belong to project {project!r}")
    path = Path(data).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"dashboard input does not exist: {path}")
    try:
        from streamlit.web import cli as stcli
    except ImportError as exc:
        raise SystemExit(
            "visualization dependencies are not installed; run "
            "`python -m pip install -e \".[visualization]\"`"
        ) from exc

    app_path = Path(__file__).with_name("app.py")
    streamlit_args = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--",
        "--data",
        str(path),
        "--project",
        project,
        "--arena",
        arena,
    ]
    if review_db:
        streamlit_args.extend(["--review-db", str(Path(review_db).expanduser())])
    if reviewer:
        streamlit_args.extend(["--reviewer", reviewer])
    if blind_initial:
        streamlit_args.append("--blind-initial")
    old_argv = sys.argv
    try:
        sys.argv = streamlit_args
        return int(stcli.main() or 0)
    finally:
        sys.argv = old_argv


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return launch(
        args.data,
        project=args.project,
        arena=args.arena,
        review_db=args.review_db,
        reviewer=args.reviewer,
        blind_initial=args.blind_initial,
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    raise SystemExit(main())
