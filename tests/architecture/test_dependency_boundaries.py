"""Architecture regression checks for the canonical LaclauGPT package.

These tests intentionally inspect source imports instead of importing runtime modules.
That keeps the check fast, offline, and independent of optional dependencies.
See docs/architecture/PYTHON_ARCHITECTURE.md and issue #145.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "laclaugpt"

# Optional laboratories are allowed to depend on core APIs. Core code must never
# depend on them. Keep both singular names used by the target architecture and
# plausible compatibility spellings here so a new optional package cannot leak
# into core unnoticed.
OPTIONAL_LABS = {
    "laclaugpt.assistant",
    "laclaugpt.research_assistant",
    "laclaugpt.simulation",
    "laclaugpt.simulations",
    "laclaugpt.experimental",
    "laclaugpt.experiments",
}

CORE_AREAS = {
    "collection": ("collection", "collect"),
    "storage": ("storage",),
    "analysis": ("analysis",),
    "visualization": ("visualization",),
}


def _python_files(path: Path):
    if path.is_file() and path.suffix == ".py":
        yield path
    elif path.is_dir():
        yield from path.rglob("*.py")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _area_files(area: str):
    for dirname in CORE_AREAS[area]:
        path = PACKAGE / dirname
        if path.exists():
            yield from _python_files(path)


def _matches_prefix(import_name: str, prefix: str) -> bool:
    return import_name == prefix or import_name.startswith(prefix + ".")


def test_core_subsystems_do_not_import_optional_labs() -> None:
    violations: list[str] = []
    for area in CORE_AREAS:
        for path in _area_files(area):
            for imported in _imports(path):
                if any(_matches_prefix(imported, lab) for lab in OPTIONAL_LABS):
                    violations.append(
                        f"{path.relative_to(ROOT)} imports optional lab {imported}"
                    )
    assert not violations, "Core -> optional dependency violations:\n" + "\n".join(violations)


def test_collection_does_not_import_visualization() -> None:
    violations: list[str] = []
    for path in _area_files("collection"):
        for imported in _imports(path):
            if _matches_prefix(imported, "laclaugpt.visualization"):
                violations.append(
                    f"{path.relative_to(ROOT)} imports visualization via {imported}"
                )
    assert not violations, "Collection -> visualization violations:\n" + "\n".join(violations)


def test_analysis_does_not_import_top_level_collector_internals() -> None:
    """Analysis must consume contracts/artifacts, not collector implementation.

    The historical top-level ``collector`` package remains a compatibility and
    migration source, so importing it from canonical analysis would freeze the
    wrong dependency direction into new maintained code.
    """

    violations: list[str] = []
    for path in _area_files("analysis"):
        for imported in _imports(path):
            if _matches_prefix(imported, "collector"):
                violations.append(
                    f"{path.relative_to(ROOT)} imports collector internal {imported}"
                )
    assert not violations, "Analysis -> collector violations:\n" + "\n".join(violations)


def test_storage_does_not_import_visualization() -> None:
    violations: list[str] = []
    for path in _area_files("storage"):
        for imported in _imports(path):
            if _matches_prefix(imported, "laclaugpt.visualization"):
                violations.append(
                    f"{path.relative_to(ROOT)} imports visualization via {imported}"
                )
    assert not violations, "Storage -> visualization violations:\n" + "\n".join(violations)
