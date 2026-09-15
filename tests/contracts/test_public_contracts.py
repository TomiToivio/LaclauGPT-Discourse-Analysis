from __future__ import annotations

from laclaugpt.contracts import (
    AnalysisJob,
    CONTRACT_VERSION,
    JobEvent,
    JobState,
    SourceItem,
    VisualizationAggregate,
)


def test_source_item_is_backend_neutral_and_versioned() -> None:
    item = SourceItem(
        document_id="doc-1",
        source_platform="synthetic",
        text="example",
        provenance={"fixture": True},
    )
    assert item.schema_version == CONTRACT_VERSION
    assert item.document_id == "doc-1"
    assert item.provenance["fixture"] is True


def test_analysis_job_and_event_are_serial_service_neutral_values() -> None:
    job = AnalysisJob(
        run_id="run-1",
        document_ids=("doc-1",),
        project="fixture",
        arena="fixture",
        machine_profile="local",
        execution_profile="manual",
    )
    event = JobEvent(run_id=job.run_id, document_id="doc-1", state=JobState.DONE)
    assert event.state.value == "done"
    assert job.schema_version == event.schema_version == CONTRACT_VERSION


def test_visualization_aggregate_contains_no_runtime_dependency() -> None:
    row = VisualizationAggregate(
        key="formation:critical",
        label="critical",
        count=2,
        dimensions={"country": "FI"},
        measures={"share": 0.5},
    )
    assert row.count == 2
    assert row.measures["share"] == 0.5
