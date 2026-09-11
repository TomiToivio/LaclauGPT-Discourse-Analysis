"""Current Streamlit dashboard wired to canonical project profiles and schema 1.7+."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from laclaugpt.config import list_arenas, list_projects, load_arena, load_project
from laclaugpt.visualization.app import (
    MODEL_CONFIDENCE_LABEL,
    _arguments,
    _bar,
    _list_unique,
    _review_panel,
    _unique,
)
from laclaugpt.visualization.data import (
    filter_frame,
    flatten_annotations,
    load_annotations,
    top_values,
)
from laclaugpt.visualization.graph import graph_projection_data, graph_projection_options
from laclaugpt.visualization.review import ReviewStore
from laclaugpt.visualization.runtime import require_dashboard_runtime


def _analysis_switches(project_id: str) -> dict[str, bool]:
    if not project_id:
        return {
            "entities": True,
            "topics": True,
            "laclau": True,
            "palonen": True,
            "sociotechnical_imaginaries": True,
            "sentiment": True,
            "temporal": True,
        }
    return {
        str(key): bool(value)
        for key, value in load_project(project_id).get("analysis", {}).items()
    }


def _resolve_profile(st, frame: pd.DataFrame, args) -> tuple[str, str]:
    provenance_projects = _unique(frame, "project")
    project_id = args.project.strip()
    if not project_id:
        options = [""] + sorted(set(list_projects()) | set(provenance_projects))
        inferred = provenance_projects[0] if len(provenance_projects) == 1 else ""
        project_id = st.sidebar.selectbox(
            "Project profile",
            options,
            index=options.index(inferred) if inferred in options else 0,
        )
    if project_id:
        try:
            load_project(project_id)
        except (KeyError, ValueError) as exc:
            st.error(f"Invalid project profile {project_id!r}: {exc}")
            st.stop()

    provenance_arenas = _unique(frame, "arena_id")
    configured = list_arenas(project_id) if project_id else list_arenas()
    arena_id = args.arena.strip()
    if not arena_id:
        options = [""] + sorted(set(configured) | set(provenance_arenas))
        inferred = provenance_arenas[0] if len(provenance_arenas) == 1 else ""
        arena_id = st.sidebar.selectbox(
            "Arena profile",
            options,
            index=options.index(inferred) if inferred in options else 0,
        )
    if arena_id:
        try:
            load_arena(arena_id, project_id or None)
        except (KeyError, ValueError) as exc:
            st.error(f"Invalid arena profile {arena_id!r}: {exc}")
            st.stop()
    return project_id, arena_id


def _graph_figure(go, nx, graph_data: dict, title: str):
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    if not nodes:
        return None

    node_meta = {str(node["id"]): node for node in nodes}
    graph = nx.Graph()
    graph.add_nodes_from(node_meta)
    for edge in edges:
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source in node_meta and target in node_meta:
            graph.add_edge(source, target)

    if graph.number_of_nodes() > 250:
        keep = {
            node
            for node, _degree in sorted(
                graph.degree(),
                key=lambda item: (-item[1], str(item[0])),
            )[:250]
        }
        graph = graph.subgraph(keep).copy()

    positions = nx.spring_layout(graph, seed=42)
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        hoverinfo="none",
        line={"width": 1},
    )
    labels = [str(node_meta[node].get("label") or node) for node in graph.nodes()]
    types = [str(node_meta[node].get("type") or "") for node in graph.nodes()]
    node_trace = go.Scatter(
        x=[positions[node][0] for node in graph.nodes()],
        y=[positions[node][1] for node in graph.nodes()],
        mode="markers+text",
        text=labels,
        textposition="top center",
        hovertext=[
            f"{label}<br>type={node_type}<br>degree={graph.degree(node)}"
            for node, label, node_type in zip(graph.nodes(), labels, types)
        ],
        hoverinfo="text",
        marker={"size": [max(8, graph.degree(node) * 3) for node in graph.nodes()]},
    )
    figure = go.Figure(data=[edge_trace, node_trace])
    figure.update_layout(
        title=title,
        showlegend=False,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
    )
    return figure


def _graph_edges(graph_data: dict) -> pd.DataFrame:
    nodes = {
        str(node.get("id", "")): str(node.get("label") or node.get("id", ""))
        for node in graph_data.get("nodes", [])
    }
    rows = []
    for edge in graph_data.get("edges", []):
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source not in nodes or target not in nodes:
            continue
        rows.append(
            {
                "source": nodes[source],
                "relation": edge.get("relation", ""),
                "target": nodes[target],
                "claim_status": edge.get("claim_status", ""),
                MODEL_CONFIDENCE_LABEL: (
                    float(edge["confidence"])
                    if edge.get("confidence") not in (None, "")
                    else None
                ),
                "evidence_verified": (
                    bool(edge["evidence_verified"])
                    if edge.get("evidence_verified") is not None
                    else None
                ),
            }
        )
    return pd.DataFrame(rows)


def _document_view(
    st,
    annotation,
    review_store: ReviewStore,
    *,
    project_id: str,
    corpus_id: str,
    reviewer_id: str,
    blind_initial: bool,
    modules: dict[str, bool],
) -> None:
    st.subheader(annotation.document_id)
    source_title = (annotation.transformations or {}).get("source_title", "")
    if source_title:
        st.markdown(f"#### {source_title}")

    collection_only = bool((annotation.transformations or {}).get("collection_only"))
    if collection_only:
        source_text = (annotation.transformations or {}).get("source_text", "")
        st.info(
            "Collection-only source: no model analysis or discourse-theoretical coding "
            "has been produced for this item."
        )
        if annotation.source_url:
            st.markdown(f"[Open source]({annotation.source_url})")
        if annotation.source_author:
            st.caption(f"Author: {annotation.source_author}")
        st.markdown("#### Source text")
        st.text_area(
            "Collected source text",
            value=source_text or "No collected text available.",
            height=420,
            disabled=True,
            key=f"collection-source-{annotation.document_id}",
        )
        st.caption("Analytical fields remain empty until the canonical analysis pipeline runs.")
        return
    if blind_initial:
        cols = st.columns(3)
        cols[0].metric("Platform", annotation.source_platform or "unknown")
        cols[1].metric("Language", annotation.language or "unknown")
        cols[2].metric("Country", annotation.source_country or "unknown")
        if annotation.source_url:
            st.markdown(f"[Open source]({annotation.source_url})")
        if annotation.source_author:
            st.caption(f"Author: {annotation.source_author}")
        st.info(
            "Blind initial-coding mode hides model-derived summaries, analytical codings, "
            "relevance/applicability decisions, provenance and peer assessments."
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
        return

    cols = st.columns(6)
    cols[0].metric("Platform", annotation.source_platform or "unknown")
    cols[1].metric("Language", annotation.language or "unknown")
    cols[2].metric("Country", annotation.source_country or "unknown")
    cols[3].metric("Review", annotation.review_status)
    cols[4].metric("Relevance", annotation.relevance or "unreviewed")
    discourse_state = (
        "unreviewed"
        if annotation.discourse_applicable is None
        else "applicable" if annotation.discourse_applicable else "not applicable"
    )
    cols[5].metric("Discourse", discourse_state)

    if annotation.source_url:
        st.markdown(f"[Open source]({annotation.source_url})")
    if annotation.source_author:
        st.caption(f"Author: {annotation.source_author}")

    st.markdown("#### Summary")
    st.write(annotation.summary or "No summary")
    if annotation.relevance_reason:
        st.write("**Relevance rationale:**", annotation.relevance_reason)
    if annotation.discourse_applicability_reason:
        st.write(
            "**Discourse applicability rationale:**",
            annotation.discourse_applicability_reason,
        )

    tab_names = ["Overview"]
    if modules.get("laclau", False):
        tab_names.append("Discourse")
    if modules.get("palonen", False):
        tab_names.append("Populism")
    if modules.get("sociotechnical_imaginaries", False):
        tab_names.append("Imaginaries")
    if modules.get("sentiment", False):
        tab_names.append("Sentiment")
    tab_names.extend(["Evidence", "Provenance", "Researcher review"])
    tabs = dict(zip(tab_names, st.tabs(tab_names)))

    with tabs["Overview"]:
        if modules.get("entities", False):
            st.write(
                "**Entities:**",
                ", ".join(item.label for item in annotation.entities) or "None",
            )
        if modules.get("topics", False):
            st.write(
                "**Topics:**",
                ", ".join(item.label for item in annotation.topics) or "None",
            )
        st.write(
            "**Source modalities:**",
            ", ".join(annotation.source_modalities or []) or "None",
        )
        if annotation.source_timestamp:
            st.write("**Source timestamp:**", annotation.source_timestamp)

    if "Discourse" in tabs:
        with tabs["Discourse"]:
            st.write(
                "**Signifiers:**",
                ", ".join(item.label for item in annotation.signifiers) or "None",
            )
            st.write(
                "**Nodal-point candidates:**",
                ", ".join(item.label for item in annotation.nodal_points) or "None",
            )
            if annotation.discourses:
                st.write("**Candidate discourses**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "label": item.label,
                                MODEL_CONFIDENCE_LABEL: item.confidence,
                                "evidence": item.evidence,
                                "elements": ", ".join(
                                    ref.label for ref in item.elements
                                ),
                            }
                            for item in annotation.discourses
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )
            if annotation.formation_candidates:
                st.write("**Formation candidates**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "formation": item.formation.label,
                                MODEL_CONFIDENCE_LABEL: item.confidence,
                                "verified": item.evidence_verified,
                                "supporting_features": ", ".join(
                                    item.supporting_features
                                ),
                                "counter_evidence": " | ".join(
                                    item.counter_evidence
                                ),
                                "evidence": item.evidence,
                            }
                            for item in annotation.formation_candidates
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )
            if annotation.signifier_roles:
                st.write("**Signifier-role candidates**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "signifier": item.signifier.label,
                                "role": item.role,
                                MODEL_CONFIDENCE_LABEL: item.confidence,
                                "needs_corpus_validation": (
                                    item.needs_corpus_validation
                                ),
                                "verified": item.evidence_verified,
                                "evidence": item.evidence,
                            }
                            for item in annotation.signifier_roles
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )
            if annotation.articulations:
                st.write("**Articulations**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "signifier": item.signifier.label,
                                "related_to": ", ".join(
                                    ref.label for ref in item.related_to
                                ),
                                "relation": item.relation,
                                "claim_status": item.claim_status,
                                MODEL_CONFIDENCE_LABEL: item.confidence,
                                "verified": item.evidence_verified,
                                "evidence": item.evidence,
                            }
                            for item in annotation.articulations
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )
            st.caption(
                "Frequency is not theoretical importance. Descriptive frequency "
                "does not establish theoretical importance, nodal status, "
                "empty/floating status, or hegemony."
            )

    if "Populism" in tabs:
        with tabs["Populism"]:
            st.write("**Populist:**", annotation.populist)
            if annotation.non_populist_reason:
                st.write(
                    "**Reason for non-populist / abstention coding:**",
                    annotation.non_populist_reason,
                )
            if annotation.populism_analysis:
                st.write(annotation.populism_analysis)
            st.write("**Us:**", ", ".join(item.label for item in annotation.us) or "None")
            st.write(
                "**Frontier:**",
                ", ".join(item.label for item in annotation.frontier) or "None",
            )
            if annotation.populism_elements:
                st.write("**Evidence-bearing Us/Frontier elements**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "element": item.element.label,
                                "side": item.side,
                                "affect": item.affect,
                                "claim_status": item.claim_status,
                                "nodal_candidate": item.nodal_candidate,
                                "empty_candidate": item.empty_candidate,
                                MODEL_CONFIDENCE_LABEL: item.confidence,
                                "verified": item.evidence_verified,
                                "evidence": item.evidence,
                            }
                            for item in annotation.populism_elements
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )
            if annotation.affects:
                st.write("**Affective investments (not sentiment polarity)**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "target": item.target.label,
                                "affect": item.affect,
                                "side": item.side,
                                MODEL_CONFIDENCE_LABEL: item.confidence,
                                "verified": item.evidence_verified,
                                "evidence": item.evidence,
                            }
                            for item in annotation.affects
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )

    if "Imaginaries" in tabs:
        with tabs["Imaginaries"]:
            if annotation.imaginaries:
                st.write("**Sociotechnical-imaginary candidates**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "label": item.label,
                                "normative_future": item.normative_future,
                                "present_diagnosis": item.present_diagnosis,
                                "technology_role": item.technology_role,
                                "human_agency": item.human_agency,
                                "claim_status": item.claim_status,
                                MODEL_CONFIDENCE_LABEL: item.confidence,
                                "verified": item.evidence_verified,
                                "evidence": item.evidence,
                            }
                            for item in annotation.imaginaries
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.caption("No sociotechnical-imaginary candidates.")

    if "Sentiment" in tabs:
        with tabs["Sentiment"]:
            st.caption(
                "Descriptive positive/neutral/negative sentiment is auxiliary "
                "metadata and is not Laclaudian affective investment."
            )
            if annotation.sentiment_observations:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "target": item.target.label,
                                "target_id": item.target.obj_id,
                                "polarity": item.polarity,
                                "uncertainty": item.uncertainty,
                                "model": item.model,
                                "prompt_version": item.prompt_version,
                                "review_status": item.review_status,
                                "evidence_source": item.evidence_source,
                            }
                            for item in annotation.sentiment_observations
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.caption("No descriptive sentiment observations.")

    with tabs["Evidence"]:
        for quote in annotation.evidence_quotes:
            st.quote(quote)
        for span in annotation.hegemonic_evidence:
            st.quote(getattr(span, "quote", span))
        if annotation.counter_evidence:
            st.write("**Counter-evidence**")
            for item in annotation.counter_evidence:
                st.write(f"• {item}")
        if annotation.uncertainties:
            st.write("**Uncertainties**")
            for item in annotation.uncertainties:
                st.write(f"• {item}")

    with tabs["Provenance"]:
        st.json(
            {
                "schema_version": annotation.schema_version,
                "run_id": annotation.run_id,
                "model": annotation.model,
                "model_digest": annotation.model_digest,
                "prompt_versions": annotation.prompt_versions,
                "collection_provenance": annotation.collection_provenance,
                "transformations": annotation.transformations,
            }
        )

    with tabs["Researcher review"]:
        _review_panel(
            st,
            annotation,
            review_store,
            project_id=project_id,
            corpus_id=corpus_id,
            reviewer_id=reviewer_id,
            blind=False,
        )


def _review_export(
    st,
    review_store: ReviewStore,
    *,
    reviewer_id: str,
    blind: bool,
) -> None:
    rows = review_store.dataframe_rows(
        viewer_reviewer_id=reviewer_id or None,
        blind=blind,
    )
    with st.expander("Assessment history & CSV export"):
        if blind:
            st.caption(
                "Blind mode restricts export to the current reviewer's records."
            )
        if not rows:
            st.caption("No assessment records available.")
            return
        frame = pd.DataFrame(rows)
        st.dataframe(frame, width="stretch", hide_index=True)
        st.download_button(
            "Download assessment history CSV",
            frame.to_csv(index=False).encode("utf-8"),
            file_name="laclaugpt-review-history.csv",
            mime="text/csv",
        )


def main() -> None:
    args = _arguments()
    st, px, go, nx = require_dashboard_runtime()
    st.set_page_config(page_title="LaclauGPT", layout="wide")
    st.title("LaclauGPT research dashboard")

    data_path = args.data or st.sidebar.text_input(
        "Canonical JSONL/NDJSON",
        "",
    )
    reviewer_id = args.reviewer or st.sidebar.text_input(
        "Reviewer pseudonym",
        "",
    )
    blind_initial = bool(
        args.blind_initial
        or st.sidebar.checkbox("Blind initial coding", value=False)
    )
    review_db = args.review_db or st.sidebar.text_input(
        "Review sidecar SQLite",
        "",
    )

    if not data_path:
        st.info("Provide canonical LaclauGPT JSONL/NDJSON output.")
        return
    try:
        annotations = load_annotations(
            data_path,
            project=args.project.strip(),
            arena=args.arena.strip(),
        )
    except (OSError, ValueError) as exc:
        st.error(f"Could not load canonical interchange output: {exc}")
        return

    frame = flatten_annotations(annotations)
    if frame.empty:
        st.info("No annotations found.")
        return

    project_id, arena_id = _resolve_profile(st, frame, args)
    modules = _analysis_switches(project_id)

    if project_id:
        project = load_project(project_id)
        title = str(project.get("dataset", {}).get("title") or project_id)
        profile = f"{project_id}:{arena_id}" if arena_id else project_id
        schema_version = frame["schema_version"].iloc[0]
        st.caption(
            f"{title} · profile: {profile} · interchange schema: {schema_version}"
        )

    corpus_id = Path(data_path).stem
    review_path = (
        Path(review_db)
        if review_db
        else Path(f"{data_path}.reviews.sqlite3")
    )
    review_store = ReviewStore(review_path)

    try:
        source_filters = {
            "projects": st.sidebar.multiselect(
                "Projects",
                _unique(frame, "project"),
            ),
            "profiles": st.sidebar.multiselect(
                "Profiles",
                _unique(frame, "analysis_profile"),
            ),
            "arenas": st.sidebar.multiselect(
                "Arenas",
                _unique(frame, "arena_id"),
            ),
            "platforms": st.sidebar.multiselect(
                "Platforms",
                _unique(frame, "source_platform"),
            ),
            "countries": st.sidebar.multiselect(
                "Countries",
                _unique(frame, "source_country"),
            ),
            "languages": st.sidebar.multiselect(
                "Languages",
                _unique(frame, "language"),
            ),
            "authors": st.sidebar.multiselect(
                "Authors",
                _unique(frame, "source_author"),
            ),
        }

        start = end = None
        timestamps = frame["source_timestamp"].dropna()
        if modules.get("temporal", False) and not timestamps.empty:
            min_date = timestamps.min().date()
            max_date = timestamps.max().date()
            start = st.sidebar.date_input(
                "From",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
            )
            end = st.sidebar.date_input(
                "To",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
            )

        derived = {
            "search": "",
            "models": (),
            "review_statuses": (),
            "relevance_states": (),
            "discourse_applicabilities": (),
            "entities": (),
            "topics": (),
            "signifiers": (),
            "sentiment_polarities": (),
            "sentiment_targets": (),
        }
        if blind_initial:
            st.sidebar.caption(
                "Model-derived search/filter vocabularies are hidden during "
                "blind initial coding."
            )
        else:
            derived["search"] = st.sidebar.text_input("Search", "")
            derived["models"] = st.sidebar.multiselect(
                "Models",
                _unique(frame, "model"),
            )
            derived["review_statuses"] = st.sidebar.multiselect(
                "Model review status",
                _unique(frame, "review_status"),
            )
            derived["relevance_states"] = st.sidebar.multiselect(
                "Relevance",
                _unique(frame, "relevance_state"),
            )
            derived["discourse_applicabilities"] = st.sidebar.multiselect(
                "Discourse applicability",
                _unique(frame, "discourse_applicability"),
            )
            if modules.get("entities", False):
                derived["entities"] = st.sidebar.multiselect(
                    "Entities",
                    _list_unique(frame, "entities"),
                )
            if modules.get("topics", False):
                derived["topics"] = st.sidebar.multiselect(
                    "Topics",
                    _list_unique(frame, "topics"),
                )
            if modules.get("laclau", False):
                derived["signifiers"] = st.sidebar.multiselect(
                    "Signifiers",
                    _list_unique(frame, "signifiers"),
                )
            if modules.get("sentiment", False):
                derived["sentiment_polarities"] = st.sidebar.multiselect(
                    "Sentiment polarity",
                    _list_unique(frame, "sentiment_polarities"),
                )
                derived["sentiment_targets"] = st.sidebar.multiselect(
                    "Sentiment targets",
                    _list_unique(frame, "sentiment_targets"),
                )

        filtered = filter_frame(
            frame,
            start=start,
            end=end,
            **source_filters,
            **derived,
        )

        st.metric("Documents", len(filtered))
        if filtered.empty:
            st.info("No documents match the current filters.")
            _review_export(
                st,
                review_store,
                reviewer_id=reviewer_id,
                blind=blind_initial,
            )
            return

        selected_annotations = [
            row.annotation for row in filtered.itertuples(index=False)
        ]

        if blind_initial:
            st.info(
                "Blind initial-coding mode suppresses aggregate model-derived "
                "charts, graph projections and derived filter vocabularies."
            )
        else:
            chart_specs = []
            if modules.get("laclau", False):
                chart_specs.append(
                    ("signifiers", "Top signifiers", "Signifier")
                )
                chart_specs.append(
                    ("formations", "Formation candidates", "Formation")
                )
            if modules.get("topics", False):
                chart_specs.append(("topics", "Top topics", "Topic"))
            if modules.get("entities", False):
                chart_specs.append(("entities", "Top entities", "Entity"))
            if modules.get("sentiment", False):
                chart_specs.append(
                    (
                        "sentiment_polarities",
                        "Descriptive sentiment",
                        "Polarity",
                    )
                )

            if chart_specs:
                columns = st.columns(min(3, len(chart_specs)))
                for index, (column, title, label) in enumerate(chart_specs):
                    chart = _bar(
                        px,
                        top_values(filtered, column),
                        title,
                        label,
                    )
                    if chart is not None:
                        columns[index % len(columns)].plotly_chart(
                            chart,
                            width="stretch",
                        )

            if (
                modules.get("temporal", False)
                and filtered["source_timestamp"].notna().any()
            ):
                timeline = (
                    filtered.dropna(subset=["source_timestamp"])
                    .assign(
                        day=lambda value: value[
                            "source_timestamp"
                        ].dt.floor("D")
                    )
                    .groupby("day")
                    .size()
                    .reset_index(name="documents")
                )
                st.plotly_chart(
                    px.line(
                        timeline,
                        x="day",
                        y="documents",
                        markers=True,
                        title="Documents over time",
                    ),
                    width="stretch",
                )

            projections = graph_projection_options(
                laclau=modules.get("laclau", False),
                palonen=modules.get("palonen", False),
                temporal=modules.get("temporal", False),
            )
            if projections:
                projection = st.selectbox(
                    "Canonical discourse graph projection",
                    projections,
                )
                graph_data = graph_projection_data(
                    selected_annotations,
                    projection,
                )
                figure = _graph_figure(
                    go,
                    nx,
                    graph_data,
                    projection.replace("_", " ").title(),
                )
                if figure is not None:
                    st.caption(
                        "Graph layout, degree and frequency are descriptive "
                        "visual aids, not evidence of hegemony or nodal status."
                    )
                    st.plotly_chart(
                        figure,
                        width="stretch",
                    )
                    edge_frame = _graph_edges(graph_data)
                    if not edge_frame.empty:
                        with st.expander(
                            "Graph relations and claim context"
                        ):
                            st.dataframe(
                                edge_frame,
                                width="stretch",
                                hide_index=True,
                            )

        labels = []
        for index, row in enumerate(
            filtered.itertuples(index=False)
        ):
            timestamp = (
                row.source_timestamp.isoformat()
                if pd.notna(row.source_timestamp)
                else ""
            )
            suffix = f" · {timestamp}" if timestamp else ""
            labels.append(
                f"{row.document_id}{suffix} · row {index + 1}"
            )
        selected_label = st.selectbox("Document", labels)
        annotation = selected_annotations[labels.index(selected_label)]

        _document_view(
            st,
            annotation,
            review_store,
            project_id=project_id,
            corpus_id=corpus_id,
            reviewer_id=reviewer_id,
            blind_initial=blind_initial,
            modules=modules,
        )
        _review_export(
            st,
            review_store,
            reviewer_id=reviewer_id,
            blind=blind_initial,
        )

        st.caption(
            "Research dashboard only. Model-generated codings remain "
            "provisional and human-reviewable. Canonical analysis output "
            "is never rewritten by the dashboard."
        )
    finally:
        review_store.close()


if __name__ == "__main__":
    main()
