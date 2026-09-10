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
        "Confidence values below are model-reported, uncalibrated self-reports. They are not probabilities "
        "of correctness and are separate from quotation verification, human review and substantive validity."
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
            "Document and corpus frequencies are descriptive evidence only. They do not by themselves establish "
            "nodal status, imaginary importance, empty/floating status, or hegemony."
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
            "review_status": annotation.review_status,
            "collection_provenance": annotation.collection_provenance,
            "transformations": annotation.transformations,
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


def main(argv: list[str] | None = None) -> None:
    require_dashboard_runtime()
    args = _arguments(argv)

    import networkx as nx
    import plotly.express as px
    import plotly.graph_objects as go
    import streamlit as st

    st.set_page_config(page_title="LaclauGPT Visualization", page_icon="🕸️", layout="wide")
    st.title("LaclauGPT Visualization")
    st.caption("Canonical discourse-analysis dashboard • local/Pouta runtime, not Roihu")

    projects = list_projects()
    if not projects:
        st.error("No canonical project profiles found under config/projects/.")
        return
    project_default = args.project if args.project in projects else projects[0]
    project = st.sidebar.selectbox("Project", projects, index=projects.index(project_default))
    arenas = list_arenas(project)
    if not arenas:
        st.error(f"Project {project!r} has no canonical arena profiles.")
        return
    arena_default = args.arena if args.arena in arenas else arenas[0]
    arena = st.sidebar.selectbox("Arena / profile", arenas, index=arenas.index(arena_default))
    project_config = load_project(project)
    arena_config = load_arena(arena, project)
    analysis = project_config.get("analysis", {})
    title = arena_config.get("dataset", {}).get("title") or project_config.get("dataset", {}).get("title") or project
    profile_id = f"{project}:{arena}"
    st.sidebar.caption(f"Analysis profile: {profile_id}")

    reviewer_id = st.sidebar.text_input(
        "Reviewer ID / pseudonym",
        value=args.reviewer,
        help="Use a stable local pseudonym. Do not commit private reviewer details to the repository.",
    ).strip()
    blind_initial = st.sidebar.checkbox(
        "Blind initial coding",
        value=bool(args.blind_initial),
        help="Hide model suggestions and peer assessments until explicitly revealed per document.",
    )

    data_path = st.sidebar.text_input("Canonical JSONL / NDJSON", value=args.data)
    if not data_path:
        st.info("Choose a canonical LaclauGPT JSONL/NDJSON output file in the sidebar.")
        return
    path = Path(data_path).expanduser()
    if not path.exists():
        st.error(f"Data file does not exist on this dashboard host: {path}")
        return
    try:
        annotations = load_annotations(path)
    except Exception as exc:
        st.error(f"Could not load canonical interchange output: {exc}")
        return
    frame = flatten_annotations(annotations)
    if frame.empty:
        st.warning("The selected output contains no annotations.")
        return

    # Blind coding must also protect the aggregate dashboard, not only the
    # document detail panel. Keep source metadata and the original annotation
    # object for later explicit reveal, but redact model-derived aggregate fields.
    if blind_initial:
        frame = frame.copy()
        for column in ("summary", "review_status"):
            if column in frame:
                frame[column] = ""
        if "populist" in frame:
            frame["populist"] = None
        for column in ("entities", "topics", "signifiers", "nodal_points", "us", "frontier", "imaginaries", "affects"):
            if column in frame:
                frame[column] = [[] for _ in range(len(frame))]
        if "searchable_text" in frame:
            source_columns = (
                "document_id", "source_platform", "source_country", "language",
                "source_author", "source_url", "project", "analysis_profile", "arena_id",
            )
            frame["searchable_text"] = frame.apply(
                lambda row: " ".join(
                    str(row.get(column, "") or "") for column in source_columns
                ),
                axis=1,
            )
        analysis = {}

    review_path = Path(args.review_db).expanduser() if args.review_db else path.with_suffix(path.suffix + ".reviews.sqlite3")
    review_store = ReviewStore(review_path)

    st.header(title)
    st.caption(f"{len(frame)} annotations loaded • review sidecar: {review_path}")
    if blind_initial:
        st.info(
            "Blind initial coding is active across the dashboard. Model-derived aggregate fields are redacted; "
            "each document can be explicitly revealed for comparison/adjudication after initial coding."
        )

    search = st.sidebar.text_input("Free search")
    platform_values = _unique(frame, "source_platform")
    language_values = _unique(frame, "language")
    country_values = _unique(frame, "source_country")
    review_values = _unique(frame, "review_status")
    author_values = _unique(frame, "source_author")
    platforms = st.sidebar.multiselect("Platform", platform_values)
    languages = st.sidebar.multiselect("Language", language_values)
    countries = st.sidebar.multiselect("Country", country_values)
    statuses = st.sidebar.multiselect("Model review status", review_values)
    authors = st.sidebar.multiselect("Author", author_values)
    entities = st.sidebar.multiselect("Entity", _list_unique(frame, "entities")) if analysis.get("entities") else []
    topics = st.sidebar.multiselect("Topic", _list_unique(frame, "topics")) if analysis.get("topics") else []
    signifiers = st.sidebar.multiselect("Signifier", _list_unique(frame, "signifiers")) if analysis.get("laclau") else []

    project_filter = [project] if project in _unique(frame, "project") else []
    profile_filter = [profile_id] if profile_id in _unique(frame, "analysis_profile") else []
    arena_filter = [arena] if arena in _unique(frame, "arena_id") else []
    filtered = filter_frame(
        frame,
        search=search,
        projects=project_filter,
        profiles=profile_filter,
        arenas=arena_filter,
        platforms=platforms,
        countries=countries,
        languages=languages,
        review_statuses=statuses,
        authors=authors,
        entities=entities,
        topics=topics,
        signifiers=signifiers,
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Documents", len(filtered))
    metric_cols[1].metric("Entities", len(_list_unique(filtered, "entities")))
    metric_cols[2].metric("Topics", len(_list_unique(filtered, "topics")))
    metric_cols[3].metric("Signifiers", len(_list_unique(filtered, "signifiers")))

    tab_names = ["Overview"]
    if analysis.get("entities"): tab_names.append("Entities")
    if analysis.get("topics"): tab_names.append("Topics")
    if analysis.get("laclau"): tab_names.append("Discourse")
    if analysis.get("palonen"): tab_names.append("Populism")
    if analysis.get("sociotechnical_imaginaries"): tab_names.append("Imaginaries")
    if analysis.get("palonen"): tab_names.append("Affects")
    tab_names.extend(["Documents", "Review"])
    tabs = dict(zip(tab_names, st.tabs(tab_names)))

    with tabs["Overview"]:
        left, right = st.columns(2)
        with left:
            platform_counts = filtered["source_platform"].replace("", "unknown").value_counts().rename_axis("label").reset_index(name="count")
            if not platform_counts.empty:
                st.plotly_chart(px.bar(platform_counts, x="label", y="count", title="Documents by platform"), use_container_width=True)
        with right:
            dated = filtered.dropna(subset=["source_timestamp"]).copy()
            if not dated.empty and analysis.get("temporal"):
                dated["date"] = dated["source_timestamp"].dt.date
                daily = dated.groupby("date").size().reset_index(name="count")
                st.plotly_chart(px.line(daily, x="date", y="count", markers=True, title="Documents over time"), use_container_width=True)
        st.dataframe(filtered[[
            "document_id", "source_platform", "language", "source_country", "source_author",
            "source_timestamp", "review_status", "populist", "summary"
        ]], use_container_width=True, hide_index=True)

    if "Entities" in tabs:
        with tabs["Entities"]:
            data = top_values(filtered, "entities", 30)
            figure = _bar(px, data, "Top entities", "Entity")
            if figure: st.plotly_chart(figure, use_container_width=True)
            st.dataframe(data, use_container_width=True, hide_index=True)

    if "Topics" in tabs:
        with tabs["Topics"]:
            data = top_values(filtered, "topics", 30)
            figure = _bar(px, data, "Top topics", "Topic")
            if figure: st.plotly_chart(figure, use_container_width=True)
            st.dataframe(data, use_container_width=True, hide_index=True)

    if "Discourse" in tabs:
        with tabs["Discourse"]:
            st.caption(
                "Counts below show document frequency only. Frequency is not theoretical importance, "
                "nodal status, empty/floating status, or hegemony; corpus and human adjudication remain required. "
                "Mean confidence is an uncalibrated mean of model self-reports, not a probability of correctness."
            )
            left, right = st.columns(2)
            with left:
                data = top_values(filtered, "signifiers", 30)
                figure = _bar(px, data, "Top signifiers", "Signifier")
                if figure: st.plotly_chart(figure, use_container_width=True)
            with right:
                data = top_values(filtered, "nodal_points", 30)
                figure = _bar(px, data, "Nodal-point candidates", "Signifier")
                if figure: st.plotly_chart(figure, use_container_width=True)
            filtered_annotations = filtered["annotation"].tolist()
            network = _articulation_figure(go, nx, filtered_annotations)
            if network:
                st.plotly_chart(network, use_container_width=True)
            edges = articulation_edges(filtered_annotations, limit=100)
            if not edges.empty:
                display_edges = edges.rename(columns={
                    "mean_confidence": "mean model-reported confidence (uncalibrated)"
                })
                st.dataframe(display_edges, use_container_width=True, hide_index=True)

    if "Populism" in tabs:
        with tabs["Populism"]:
            left, right = st.columns(2)
            with left:
                data = top_values(filtered, "us", 30)
                figure = _bar(px, data, "Us-chain elements", "Element")
                if figure: st.plotly_chart(figure, use_container_width=True)
            with right:
                data = top_values(filtered, "frontier", 30)
                figure = _bar(px, data, "Frontier elements", "Element")
                if figure: st.plotly_chart(figure, use_container_width=True)
            pop_counts = filtered["populist"].fillna("abstained").astype(str).value_counts().rename_axis("label").reset_index(name="count")
            st.plotly_chart(px.bar(pop_counts, x="label", y="count", title="Formula of Populism classifications"), use_container_width=True)
            non_populist_rows = [
                {
                    "document_id": ann.document_id,
                    "non_populist_reason": ann.non_populist_reason,
                }
                for ann in filtered["annotation"].tolist()
                if ann.populist is False and ann.non_populist_reason
            ]
            if non_populist_rows:
                st.write("**Non-populist / abstention reasons**")
                st.dataframe(pd.DataFrame(non_populist_rows), use_container_width=True, hide_index=True)

    if "Imaginaries" in tabs:
        with tabs["Imaginaries"]:
            st.caption(
                "These are provisional sociotechnical-imaginary candidates. Document frequency is descriptive "
                "and does not establish theoretical importance or corpus-level validity."
            )
            data = top_values(filtered, "imaginaries", 30)
            figure = _bar(px, data, "Sociotechnical-imaginary candidates", "Imaginary candidate")
            if figure: st.plotly_chart(figure, use_container_width=True)

    if "Affects" in tabs:
        with tabs["Affects"]:
            data = top_values(filtered, "affects", 30)
            figure = _bar(px, data, "Affective investments", "Target / affect")
            if figure: st.plotly_chart(figure, use_container_width=True)

    with tabs["Documents"]:
        options = filtered["document_id"].astype(str).tolist()
        if options:
            selected_id = st.selectbox("Inspect document", options)
            row = filtered[filtered["document_id"].astype(str) == selected_id].iloc[0]
            _display_document(
                st,
                row["annotation"],
                review_store,
                project_id=project,
                corpus_id=profile_id,
                reviewer_id=reviewer_id,
                blind_initial=blind_initial,
            )
        else:
            st.info("No documents match the current filters.")

    with tabs["Review"]:
        rows = review_store.dataframe_rows(
            viewer_reviewer_id=reviewer_id or None,
            blind=blind_initial,
        )
        if blind_initial:
            st.info("Blind mode: this table and download show only the current reviewer's records.")
        if rows:
            review_frame = pd.DataFrame(rows)
            st.dataframe(review_frame, use_container_width=True, hide_index=True)
            st.download_button(
                "Download assessment history CSV",
                data=review_frame.to_csv(index=False),
                file_name="laclaugpt-review-assessments.csv",
                mime="text/csv",
            )
        else:
            st.info("No researcher assessments are visible in the current review mode.")
        st.caption(
            "Assessment rows are append-only and retain project/corpus, run, artifact fingerprint, reviewer, "
            "target, revision/adjudication links and timestamps. Canonical analysis output is never rewritten."
        )

    review_store.close()


if __name__ == "__main__":
    main()
