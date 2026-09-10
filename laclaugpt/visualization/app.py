"""Streamlit dashboard for canonical LaclauGPT interchange output."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from laclaugpt.config import list_arenas, list_projects, load_arena, load_project
from laclaugpt.visualization.data import articulation_edges, filter_frame, flatten_annotations, load_annotations, top_values
from laclaugpt.visualization.review import ReviewStore, assessment_context, canonical_review_targets
from laclaugpt.visualization.runtime import require_dashboard_runtime


MODEL_CONFIDENCE_LABEL = "model-reported confidence (uncalibrated)"


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--data", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--arena", default="")
    parser.add_argument("--review-db", default="")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--blind-initial", action="store_true")
    args, _ = parser.parse_known_args(sys.argv[1:] if argv is None else argv)
    return args


def _unique(frame: pd.DataFrame, column: str) -> list[str]:
    if frame.empty or column not in frame:
        return []
    return sorted({str(value) for value in frame[column].dropna() if str(value).strip()})


def _list_unique(frame: pd.DataFrame, column: str) -> list[str]:
    if frame.empty or column not in frame:
        return []
    values: set[str] = set()
    for row in frame[column]:
        if isinstance(row, (list, tuple, set)):
            values.update(str(value) for value in row if str(value).strip())
    return sorted(values)


def _bar(px, data: pd.DataFrame, title: str, label: str):
    if data.empty:
        return None
    return px.bar(data.sort_values("count"), x="count", y="label", orientation="h", title=title,
                  labels={"label": label, "count": "Documents"})


def _articulation_figure(go, nx, annotations):
    edges = articulation_edges(annotations, limit=80)
    if edges.empty:
        return None
    graph = nx.Graph()
    for row in edges.itertuples(index=False):
        graph.add_edge(row.source, row.target, weight=row.count, relation=row.relation)
    positions = nx.spring_layout(graph, seed=42, weight="weight")
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", hoverinfo="none", line={"width": 1})
    node_x = [positions[node][0] for node in graph.nodes()]
    node_y = [positions[node][1] for node in graph.nodes()]
    labels = list(graph.nodes())
    degrees = [max(8, graph.degree(node) * 4) for node in graph.nodes()]
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text", text=labels, textposition="top center",
        hovertext=[f"{node}<br>degree={graph.degree(node)}" for node in graph.nodes()],
        hoverinfo="text", marker={"size": degrees},
    )
    figure = go.Figure(data=[edge_trace, node_trace])
    figure.update_layout(
        title="Articulation network",
        showlegend=False,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
    )
    return figure


def _review_panel(
    st,
    annotation,
    review_store: ReviewStore,
    *,
    project_id: str,
    corpus_id: str,
    reviewer_id: str,
    blind: bool,
) -> None:
    context = assessment_context(annotation, project_id=project_id, corpus_id=corpus_id)
    scope = f"{annotation.document_id}-{context['artifact_fingerprint']}"
    st.caption(
        f"Project/corpus: {context['project_id']} / {context['corpus_id']} · "
        f"run: {context['run_id']} · artifact: {context['artifact_fingerprint'][:22]}…"
    )
    if not reviewer_id.strip():
        st.warning("Enter a local reviewer pseudonym in the sidebar before saving an assessment.")

    if blind:
        target_type = st.selectbox(
            "Assessment target type",
            ["document", "code", "claim"],
            key=f"review-target-type-{scope}",
        )
        target_id = ""
        if target_type != "document":
            target_id = st.text_input(
                "Canonical code / claim ID",
                help=(
                    "Enter the code or claim identifier independently. Model-proposed target labels are "
                    "intentionally hidden during blind initial coding."
                ),
                key=f"review-target-id-{scope}-{target_type}",
            ).strip()
        target = {"target_type": target_type, "target_id": target_id}
    else:
        targets = canonical_review_targets(annotation)
        labels = [item["label"] for item in targets]
        selected_label = st.selectbox(
            "Assessment target",
            labels,
            key=f"review-target-{scope}",
        )
        target = targets[labels.index(selected_label)]

    target_ready = target["target_type"] == "document" or bool(target["target_id"].strip())
    if not target_ready:
        st.caption("Enter a code/claim ID before saving this target.")

    current = review_store.get(
        annotation.document_id,
        reviewer_id=reviewer_id or "unknown",
        target_type=target["target_type"],
        target_id=target["target_id"],
        **context,
    )

    status_options = ["", "unchecked", "accepted", "needs_revision", "rejected", "ambiguous"]
    current_status = current["review_status"] if current["review_status"] in status_options else ""
    status = st.selectbox(
        "Researcher review status",
        status_options,
        index=status_options.index(current_status),
        key=f"review-status-{scope}-{target['target_type']}-{target['target_id']}",
    )
    tags = st.text_input(
        "Tags",
        value=", ".join(current["tags"]),
        key=f"review-tags-{scope}-{target['target_type']}-{target['target_id']}",
    )
    note = st.text_area(
        "Researcher note",
        value=current["note"],
        height=160,
        key=f"review-note-{scope}-{target['target_type']}-{target['target_id']}",
    )

    history = review_store.history(
        annotation.document_id,
        project_id=context["project_id"],
        corpus_id=context["corpus_id"],
        run_id=context["run_id"],
        artifact_fingerprint=context["artifact_fingerprint"],
        target_type=target["target_type"],
        target_id=target["target_id"],
        viewer_reviewer_id=reviewer_id or None,
        blind=blind,
    )
    record_types = ["assessment"]
    if current["id"] is not None:
        record_types.append("revision")
    if not blind and len(history) >= 2:
        record_types.append("adjudication")
    record_type = st.selectbox(
        "Record type",
        record_types,
        key=f"review-record-type-{scope}-{target['target_type']}-{target['target_id']}",
    )

    linked_ids: list[int] = []
    if record_type == "adjudication":
        choices = [int(row["id"]) for row in history if row["id"] is not None]
        linked_ids = st.multiselect(
            "Prior assessment IDs to adjudicate",
            choices,
            default=choices,
            key=f"review-links-{scope}-{target['target_type']}-{target['target_id']}",
        )

    if st.button(
        "Save assessment",
        key=f"review-save-{scope}-{target['target_type']}-{target['target_id']}",
        disabled=not bool(reviewer_id.strip()) or not target_ready,
    ):
        if record_type == "adjudication" and len(linked_ids) < 2:
            st.error("Adjudication must link at least two prior assessments.")
        else:
            try:
                review_store.save(
                    annotation.document_id,
                    review_status=status,
                    note=note,
                    tags=[part.strip() for part in tags.split(",") if part.strip()],
                    reviewer_id=reviewer_id,
                    target_type=target["target_type"],
                    target_id=target["target_id"],
                    record_type=record_type,
                    supersedes_id=current["id"] if record_type == "revision" else None,
                    linked_assessment_ids=linked_ids if record_type == "adjudication" else (),
                    blind_initial=blind,
                    **context,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Assessment appended to the review-history sidecar.")
                st.rerun()

    if history:
        st.write("**Assessment history**")
        display_columns = [
            "id", "record_type", "reviewer_id", "target_type", "target_id", "review_status",
            "note", "tags", "supersedes_id", "linked_assessment_ids", "blind_initial", "created_at",
        ]
        st.dataframe(pd.DataFrame(history)[display_columns], use_container_width=True, hide_index=True)
    else:
        st.caption("No assessment history for this exact run/artifact/target yet.")


def _display_document(
    st,
    annotation,
    review_store: ReviewStore,
    *,
    project_id: str,
    corpus_id: str,
    reviewer_id: str,
    blind_initial: bool,
) -> None:
    st.subheader(annotation.document_id)
    context = assessment_context(annotation, project_id=project_id, corpus_id=corpus_id)
    reveal_key = (
        f"review-reveal-{reviewer_id}-{annotation.document_id}-"
        f"{context['run_id']}-{context['artifact_fingerprint']}"
    )
    revealed = bool(st.session_state.get(reveal_key, False))

    if blind_initial and not revealed:
        meta = st.columns(2)
        meta[0].metric("Platform", annotation.source_platform or "unknown")
        meta[1].metric("Language", annotation.language or "unknown")
        if annotation.source_url:
            st.markdown(f"[Open source]({annotation.source_url})")
        if annotation.source_author:
            st.caption(f"Author: {annotation.source_author}")
        st.info(
            "Blind initial-coding mode is active. Model summary, model suggestions, provenance and peer "
            "assessments are hidden until you explicitly reveal them for comparison/adjudication."
        )
        _review_panel(
            st,
            annotation,
            review_store,
            project_id=project_id,
            corpus_id=corpus_id,
            reviewer_id=reviewer_id,
            blind=True,
        )
        if st.button("Reveal model and peer assessments", key=f"reveal-{reveal_key}"):
            st.session_state[reveal_key] = True
            st.rerun()
        return

    meta = st.columns(4)
    meta[0].metric("Platform", annotation.source_platform or "unknown")
    meta[1].metric("Language", annotation.language or "unknown")
    meta[2].metric("Review", annotation.review_status)
    meta[3].metric("Evidence quotes", len(annotation.evidence_quotes or []))
    if annotation.source_url:
        st.markdown(f"[Open source]({annotation.source_url})")
    if annotation.source_author:
        st.caption(f"Author: {annotation.source_author}")
    if blind_initial and revealed:
        st.caption("Blind coding has been explicitly revealed for comparison/adjudication.")
    st.markdown("#### Summary")
    st.write(annotation.summary or "No summary")
    st.caption(
        "Confidence values below are model-reported, uncalibrated self-reports, not probabilities of correctness. "
        "They are separate from quotation verification, human review and substantive validity."
    )

    tabs = st.tabs(["Discourse", "Populism", "Evidence", "Provenance", "Researcher review"])
    with tabs[0]:
        st.write("**Signifiers:**", ", ".join(item.label for item in annotation.signifiers) or "None")
        st.write("**Nodal-point candidates:**", ", ".join(item.label for item in annotation.nodal_points) or "None")
        if annotation.signifier_roles:
            st.write("**Signifier-role candidates**")
            st.dataframe(pd.DataFrame([
                {
                    "signifier": item.signifier.label,
                    "role": item.role,
                    MODEL_CONFIDENCE_LABEL: item.confidence,
                    "needs_corpus_validation": item.needs_corpus_validation,
                    "verified": item.evidence_verified,
                    "evidence": item.evidence,
                }
                for item in annotation.signifier_roles
            ]), use_container_width=True, hide_index=True)
        if annotation.articulations:
            st.write("**Articulations**")
            st.dataframe(pd.DataFrame([
                {
                    "signifier": item.signifier.label,
                    "related_to": ", ".join(ref.label for ref in item.related_to),
                    "relation": item.relation,
                    "claim_status": item.claim_status,
                    MODEL_CONFIDENCE_LABEL: item.confidence,
                    "verified": item.evidence_verified,
                    "evidence": item.evidence,
                }
                for item in annotation.articulations
            ]), use_container_width=True, hide_index=True)
        if annotation.imaginaries:
            st.write("**Sociotechnical-imaginary candidates:**", ", ".join(item.label for item in annotation.imaginaries))
        st.caption(
            "Frequency is not theoretical importance. Descriptive frequency does not establish theoretical importance, "
            "nodal status, imaginary importance, empty/floating status, or hegemony; corpus and human adjudication "
            "remain required."
        )
    with tabs[1]:
        st.write("**Populist:**", annotation.populist)
        if annotation.populist is False and annotation.non_populist_reason:
            st.write("**Reason for non-populist / abstention coding:**", annotation.non_populist_reason)
        if annotation.populism_analysis:
            st.write(annotation.populism_analysis)
        st.write("**Us:**", ", ".join(item.label for item in annotation.us) or "None")
        st.write("**Frontier:**", ", ".join(item.label for item in annotation.frontier) or "None")
        if annotation.affects:
            st.dataframe(pd.DataFrame([
                {
                    "target": item.target.label,
                    "affect": item.affect,
                    "side": item.side,
                    MODEL_CONFIDENCE_LABEL: item.confidence,
                    "evidence": item.evidence,
                }
                for item in annotation.affects
            ]), use_container_width=True, hide_index=True)
    with tabs[2]:
        for quote in annotation.evidence_quotes:
            st.quote(quote)
        for quote in annotation.hegemonic_evidence:
            text = getattr(quote, "quote", quote)
            st.quote(text)
        if annotation.counter_evidence:
            st.write("**Counter-evidence**")
            for item in annotation.counter_evidence:
                st.write(f"• {item}")
        if annotation.uncertainties:
            st.write("**Uncertainties**")
            for item in annotation.uncertainties:
                st.write(f"• {item}")
    with tabs[3]:
        st.json({
            "schema_version": annotation.schema_version,
            "run_id": annotation.run_id,
            "artifact_fingerprint": context["artifact_fingerprint"],
            "model": annotation.model,
            "model_digest": annotation.model_digest,
            "prompt_versions": annotation.prompt_versions,
            "collection_provenance": annotation.collection_provenance,
        })
    with tabs[4]:
        _review_panel(
            st,
            annotation,
            review_store,
            project_id=project_id,
            corpus_id=corpus_id,
            reviewer_id=reviewer_id,
            blind=False,
        )


def main() -> None:
    args = _arguments()
    st, px, go, nx = require_dashboard_runtime()
    st.set_page_config(page_title="LaclauGPT", layout="wide")
    st.title("LaclauGPT research dashboard")

    data_path = args.data or st.sidebar.text_input("Canonical JSONL/NDJSON", "")
    project_id = args.project or st.sidebar.text_input("Project", "")
    arena_id = args.arena or st.sidebar.text_input("Arena", "")
    reviewer_id = args.reviewer or st.sidebar.text_input("Reviewer pseudonym", "")
    blind_initial = bool(args.blind_initial or st.sidebar.checkbox("Blind initial coding", value=False))
    review_db = args.review_db or st.sidebar.text_input("Review sidecar SQLite", "")

    if not data_path:
        st.info("Provide canonical LaclauGPT JSONL/NDJSON output.")
        return
    annotations = load_annotations(data_path)
    frame = flatten_annotations(annotations)
    if frame.empty:
        st.info("No annotations found.")
        return

    if not project_id:
        projects = _unique(frame, "project")
        project_id = projects[0] if len(projects) == 1 else ""
    if not arena_id:
        arenas = _unique(frame, "arena_id")
        arena_id = arenas[0] if len(arenas) == 1 else ""
    corpus_id = Path(data_path).stem
    review_path = Path(review_db) if review_db else Path(data_path).with_suffix(".reviews.sqlite3")
    review_store = ReviewStore(review_path)

    search = st.sidebar.text_input("Search", "")
    filtered = filter_frame(
        frame,
        search=search,
        projects=st.sidebar.multiselect("Projects", _unique(frame, "project")),
        profiles=st.sidebar.multiselect("Profiles", _unique(frame, "analysis_profile")),
        arenas=st.sidebar.multiselect("Arenas", _unique(frame, "arena_id")),
        platforms=st.sidebar.multiselect("Platforms", _unique(frame, "source_platform")),
        countries=st.sidebar.multiselect("Countries", _unique(frame, "source_country")),
        languages=st.sidebar.multiselect("Languages", _unique(frame, "language")),
        review_statuses=st.sidebar.multiselect("Review status", _unique(frame, "review_status")),
        authors=st.sidebar.multiselect("Authors", _unique(frame, "source_author")),
        entities=st.sidebar.multiselect("Entities", _list_unique(frame, "entities")),
        topics=st.sidebar.multiselect("Topics", _list_unique(frame, "topics")),
        signifiers=st.sidebar.multiselect("Signifiers", _list_unique(frame, "signifiers")),
    )

    st.metric("Documents", len(filtered))
    if not filtered.empty:
        cols = st.columns(3)
        for column, title, label, col in (
            ("signifiers", "Top signifiers", "Signifier", cols[0]),
            ("topics", "Top topics", "Topic", cols[1]),
            ("formations", "Formation candidates", "Formation", cols[2]),
        ):
            chart = _bar(px, top_values(filtered, column), title, label)
            if chart is not None:
                col.plotly_chart(chart, use_container_width=True)

        selected_annotations = [row.annotation for row in filtered.itertuples(index=False)]
        edges = articulation_edges(selected_annotations, limit=80)
        if not edges.empty:
            st.caption(
                "Articulation edge counts are descriptive. Mean model-reported confidence (uncalibrated) values "
                "are not probabilities of correctness and do not substitute for quotation verification, human "
                "review, or substantive validity."
            )
            figure = _articulation_figure(go, nx, selected_annotations)
            if figure is not None:
                st.plotly_chart(figure, use_container_width=True)

        labels = [str(row.document_id) for row in filtered.itertuples(index=False)]
        selected = st.selectbox("Document", labels)
        annotation = next(a for a in selected_annotations if a.document_id == selected)
        _display_document(
            st,
            annotation,
            review_store,
            project_id=project_id,
            corpus_id=corpus_id,
            reviewer_id=reviewer_id,
            blind_initial=blind_initial,
        )

    st.caption(
        "Research dashboard only. All model-generated codings remain provisional and human-reviewable. "
        "Review history is stored separately with reviewer pseudonyms and timestamps. Canonical analysis output is never rewritten."
    )
    review_store.close()


if __name__ == "__main__":
    main()
