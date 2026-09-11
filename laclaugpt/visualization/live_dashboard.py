"""Near-real-time Streamlit research dashboard for canonical LaclauGPT output.

The dashboard polls the canonical JSONL/NDJSON export. It deliberately does not
query project-specific databases or perform discourse analysis in the UI layer.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from laclaugpt.config import load_project
from laclaugpt.visualization.app import MODEL_CONFIDENCE_LABEL, _arguments, _list_unique, _unique
from laclaugpt.visualization.dashboard import (
    _analysis_switches,
    _document_view,
    _graph_edges,
    _graph_figure,
    _review_export,
)
from laclaugpt.visualization.data import filter_frame, load_annotations, top_values
from laclaugpt.visualization.graph import graph_projection_data, graph_projection_options
from laclaugpt.visualization.live import (
    TIME_WINDOWS,
    actor_summary,
    apply_time_window,
    build_live_frame,
    explode_timeline,
    filter_list_value,
    first_seen,
    relation_rows,
    signifier_role_rows,
    signifier_summary,
)
from laclaugpt.visualization.review import ReviewStore
from laclaugpt.visualization.runtime import require_dashboard_runtime


def _safe_load(path: str, *, project: str, arena: str):
    try:
        return load_annotations(path, project=project, arena=arena), None
    except (OSError, ValueError) as exc:
        return [], str(exc)


def _apply_filters(frame: pd.DataFrame, filters: dict) -> pd.DataFrame:
    filtered = apply_time_window(frame, filters["time_window"])
    filtered = filter_frame(
        filtered,
        search=filters["search"],
        platforms=filters["platforms"],
        languages=filters["languages"],
        authors=filters["actors"],
        signifiers=filters["signifiers"],
    )
    filtered = filter_list_value(filtered, "formations", filters["formations"])
    return filtered


def _selected_annotations(filtered: pd.DataFrame):
    if filtered.empty or "annotation" not in filtered:
        return []
    return [row.annotation for row in filtered.itertuples(index=False)]


def _metric_timestamp(value) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    timestamp = pd.Timestamp(value)
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


def _documents_timeline(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or frame["source_timestamp"].dropna().empty:
        return pd.DataFrame(columns=["day", "documents"])
    return (
        frame.dropna(subset=["source_timestamp"])
        .assign(day=lambda value: value["source_timestamp"].dt.floor("D"))
        .groupby("day")
        .size()
        .reset_index(name="documents")
    )


def _formation_actor_counts(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["formation", "actors", "documents"])
    rows = frame[["document_id", "source_author", "formations"]].explode("formations")
    rows["formations"] = rows["formations"].fillna("").astype(str).str.strip()
    rows = rows[rows["formations"] != ""]
    if rows.empty:
        return pd.DataFrame(columns=["formation", "actors", "documents"])
    return (
        rows.groupby("formations")
        .agg(
            actors=(
                "source_author",
                lambda values: len({str(v) for v in values if str(v).strip()}),
            ),
            documents=("document_id", "nunique"),
        )
        .reset_index()
        .rename(columns={"formations": "formation"})
        .sort_values(["documents", "formation"], ascending=[False, True])
    )


def _equivalence_components(nx, relations: pd.DataFrame) -> pd.DataFrame:
    if relations.empty:
        return pd.DataFrame(columns=["component", "members", "edges", "documents"])
    graph = nx.Graph()
    for row in relations.itertuples(index=False):
        graph.add_edge(str(row.source), str(row.target))
    rows = []
    for index, members in enumerate(
        sorted(nx.connected_components(graph), key=lambda values: (-len(values), sorted(values))),
        1,
    ):
        if len(members) < 2:
            continue
        subset = relations[
            relations["source"].astype(str).isin(members)
            & relations["target"].astype(str).isin(members)
        ]
        rows.append(
            {
                "component": index,
                "members": " ≡ ".join(sorted(str(value) for value in members)),
                "edges": len(subset),
                "documents": subset["document_id"].nunique(),
            }
        )
    return pd.DataFrame(rows)


def _render_overview(st, px, frame: pd.DataFrame, *, blind: bool) -> None:
    latest_source = frame["source_timestamp"].max() if not frame.empty else None
    latest_analysis = frame["analysis_timestamp"].max() if not frame.empty else None
    analyzed = (
        int((frame["analysis_status"] != "collection-only").sum()) if not frame.empty else 0
    )
    collection_only = (
        int((frame["analysis_status"] == "collection-only").sum()) if not frame.empty else 0
    )
    cols = st.columns(5)
    cols[0].metric("Documents in view", len(frame))
    cols[1].metric("Analyzed", analyzed)
    cols[2].metric("Awaiting analysis", collection_only)
    cols[3].metric("Latest source", _metric_timestamp(latest_source))
    cols[4].metric("Latest analysis", _metric_timestamp(latest_analysis))

    timeline = _documents_timeline(frame)
    if not timeline.empty:
        st.plotly_chart(
            px.line(
                timeline,
                x="day",
                y="documents",
                markers=True,
                title="Corpus activity over time",
                labels={"documents": "Documents", "day": "Source date"},
            ),
            width="stretch",
        )

    if blind:
        st.info(
            "Blind initial-coding mode hides model-derived formations, signifiers, "
            "relations and graph views. Operational/source coverage remains visible."
        )
        return

    columns = st.columns(3)
    for target, title, target_col in (
        ("formations", "Candidate formations", columns[0]),
        ("signifiers", "Observed signifiers", columns[1]),
        ("source_author", "Active source authors", columns[2]),
    ):
        if target == "source_author":
            values = (
                frame[target]
                .fillna("")
                .astype(str)
                .loc[lambda value: value.str.strip() != ""]
                .value_counts()
                .head(12)
                .rename_axis("label")
                .reset_index(name="count")
            )
        else:
            values = top_values(frame, target, limit=12)
        if not values.empty:
            target_col.plotly_chart(
                px.bar(
                    values.sort_values("count"),
                    x="count",
                    y="label",
                    orientation="h",
                    title=title,
                    labels={"count": "Documents", "label": ""},
                ),
                width="stretch",
            )

    st.caption(
        "Counts describe this collected corpus, not public opinion. Frequency, graph degree "
        "and model-reported confidence do not establish hegemony, nodal status, empty or "
        "floating signification, antagonism, or theoretical validity."
    )


def _render_ideologies(st, px, frame: pd.DataFrame) -> None:
    st.subheader("Candidate ideological formations")
    st.caption(
        "Formation labels come from canonical analyzed records. The dashboard does not "
        "hard-code a closed ideology taxonomy."
    )
    counts = top_values(frame, "formations", limit=30)
    if counts.empty:
        st.info("No formation candidates in the current view.")
        return
    st.plotly_chart(
        px.bar(
            counts.sort_values("count"),
            x="count",
            y="label",
            orientation="h",
            title="Candidate formation document counts",
            labels={"count": "Documents", "label": "Candidate formation"},
        ),
        width="stretch",
    )
    timeline = explode_timeline(frame, "formations", value_name="formation")
    top = set(counts.head(8)["label"])
    timeline = timeline[timeline["formation"].isin(top)]
    if not timeline.empty:
        st.plotly_chart(
            px.line(
                timeline,
                x="period",
                y="documents",
                color="formation",
                markers=True,
                title="Leading formation candidates over time",
                labels={"period": "Source date", "documents": "Documents"},
            ),
            width="stretch",
        )
    actors = _formation_actor_counts(frame)
    if not actors.empty:
        st.dataframe(actors.head(30), width="stretch", hide_index=True)


def _render_signifiers(st, px, annotations, frame: pd.DataFrame) -> None:
    st.subheader("Signifier monitor")
    summary = signifier_summary(frame)
    if summary.empty:
        st.info("No signifiers in the current view.")
        return
    st.dataframe(summary.head(40), width="stretch", hide_index=True)
    selected = st.selectbox("Inspect signifier", summary["signifier"].tolist())
    subset = filter_list_value(frame, "signifiers", [selected])
    timeline = explode_timeline(subset, "signifiers", value_name="signifier")
    timeline = timeline[timeline["signifier"] == selected]
    if not timeline.empty:
        st.plotly_chart(
            px.line(
                timeline,
                x="period",
                y="documents",
                markers=True,
                title=f"{selected}: source-time trajectory",
                labels={"period": "Source date", "documents": "Documents"},
            ),
            width="stretch",
        )
    cols = st.columns(2)
    formation_counts = top_values(subset, "formations", limit=15)
    if not formation_counts.empty:
        cols[0].dataframe(
            formation_counts.rename(columns={"label": "candidate formation"}),
            width="stretch",
            hide_index=True,
        )
    actors = actor_summary(subset)
    if not actors.empty:
        cols[1].dataframe(actors.head(15), width="stretch", hide_index=True)

    roles = signifier_role_rows(annotations)
    if not roles.empty:
        roles = roles[roles["signifier"] == selected]
        if not roles.empty:
            st.markdown("##### Provisional signifier-role claims")
            st.dataframe(roles, width="stretch", hide_index=True)
            st.caption(
                "Empty/floating status is corpus-level and remains a candidate until competing "
                "fixations or representational expansion are validated by a researcher."
            )


def _render_network(st, go, nx, annotations, *, modules: dict[str, bool]) -> None:
    st.subheader("Canonical discourse network")
    projections = graph_projection_options(
        laclau=modules.get("laclau", False),
        palonen=modules.get("palonen", False),
        temporal=modules.get("temporal", False),
    )
    if not projections:
        st.info("No graph projections are enabled for this project profile.")
        return
    default = "signifier_field" if "signifier_field" in projections else projections[0]
    projection = st.selectbox(
        "Graph projection",
        projections,
        index=projections.index(default),
    )
    graph_data = graph_projection_data(annotations, projection)
    figure = _graph_figure(go, nx, graph_data, projection.replace("_", " ").title())
    if figure is None:
        st.info("No graph nodes in the current view.")
        return
    st.plotly_chart(figure, width="stretch")
    st.caption(
        "The graph uses canonical discourse-graph relations. Layout, node size and degree are "
        "descriptive visual aids, not theoretical measurements."
    )
    edges = _graph_edges(graph_data)
    if not edges.empty:
        with st.expander("Graph relations and claim context"):
            st.dataframe(edges, width="stretch", hide_index=True)


def _render_chains_frontiers(st, nx, annotations, frame: pd.DataFrame) -> None:
    st.subheader("Equivalence, antagonism and political frontiers")
    relations = relation_rows(annotations)
    if relations.empty:
        st.info("No evidence-bearing articulation relations in the current view.")
    else:
        relation_text = relations["relation"].fillna("").astype(str).str.casefold()
        equivalence = relations[relation_text.str.contains("equiv", regex=False)]
        antagonism = relations[relation_text.str.contains("antagon", regex=False)]
        difference = relations[relation_text.str.contains("differ", regex=False)]

        st.markdown("##### Candidate equivalential components")
        components = _equivalence_components(nx, equivalence)
        if components.empty:
            st.caption("No explicit equivalence relations in the filtered records.")
        else:
            st.dataframe(components, width="stretch", hide_index=True)
        if not equivalence.empty:
            with st.expander("Equivalence evidence"):
                st.dataframe(equivalence, width="stretch", hide_index=True)

        st.markdown("##### Detected antagonism relations")
        if antagonism.empty:
            st.caption("No explicit antagonism relations in the filtered records.")
        else:
            st.dataframe(antagonism, width="stretch", hide_index=True)

        if not difference.empty:
            with st.expander("Difference relations"):
                st.dataframe(difference, width="stretch", hide_index=True)

    frontiers = top_values(frame, "frontier", limit=30)
    if not frontiers.empty:
        st.markdown("##### Palonen Frontier elements")
        st.dataframe(
            frontiers.rename(columns={"label": "frontier element", "count": "documents"}),
            width="stretch",
            hide_index=True,
        )
    st.caption(
        "Connected equivalence components are a visualization of explicitly coded relations, "
        "not automatic proof of a validated equivalential chain. Criticism or negative sentiment "
        "alone is not antagonism."
    )


def _render_actors(st, frame: pd.DataFrame) -> None:
    st.subheader("Actor explorer")
    summary = actor_summary(frame)
    if summary.empty:
        st.info("No source authors/actors in the current view.")
        return
    st.dataframe(summary.head(60), width="stretch", hide_index=True)
    selected = st.selectbox("Inspect actor", summary["actor"].tolist())
    subset = frame[frame["source_author"].fillna("").astype(str) == selected]
    cols = st.columns(3)
    cols[0].metric("Documents", len(subset))
    cols[1].metric("Signifiers", len(_list_unique(subset, "signifiers")))
    cols[2].metric("Candidate formations", len(_list_unique(subset, "formations")))
    details = {
        "Platforms": ", ".join(_unique(subset, "source_platform")) or "n/a",
        "Candidate formations": ", ".join(_list_unique(subset, "formations")) or "n/a",
        "Signifiers": ", ".join(_list_unique(subset, "signifiers")[:30]) or "n/a",
    }
    for label, value in details.items():
        st.write(f"**{label}:** {value}")
    st.caption(
        "Actor associations are corpus observations, not permanent ideological identities."
    )


def _render_timeline(st, px, frame: pd.DataFrame) -> None:
    st.subheader("Discourse timeline")
    docs = _documents_timeline(frame)
    if not docs.empty:
        st.plotly_chart(
            px.line(
                docs,
                x="day",
                y="documents",
                markers=True,
                title="Documents over time",
                labels={"day": "Source date", "documents": "Documents"},
            ),
            width="stretch",
        )
    cols = st.columns(2)
    emerging_signifiers = first_seen(frame, "signifiers", "signifier")
    emerging_formations = first_seen(frame, "formations", "candidate formation")
    if not emerging_signifiers.empty:
        cols[0].markdown("##### Recently first-seen signifiers")
        cols[0].dataframe(emerging_signifiers.head(25), width="stretch", hide_index=True)
    if not emerging_formations.empty:
        cols[1].markdown("##### Recently first-seen formation candidates")
        cols[1].dataframe(emerging_formations.head(25), width="stretch", hide_index=True)
    st.caption(
        "First-seen means first observed in the currently loaded corpus, not first historical use."
    )


def _render_sources(st, px, frame: pd.DataFrame) -> None:
    st.subheader("Corpus and source monitor")
    if frame.empty:
        st.info("No source records in the current view.")
        return
    columns = st.columns(3)
    for column, title, target in (
        ("source_platform", "Platforms / source families", columns[0]),
        ("language", "Detected languages", columns[1]),
        ("analysis_status", "Pipeline status", columns[2]),
    ):
        values = (
            frame[column]
            .fillna("unknown")
            .astype(str)
            .replace("", "unknown")
            .value_counts()
            .rename_axis("label")
            .reset_index(name="count")
        )
        target.plotly_chart(
            px.bar(
                values.sort_values("count"),
                x="count",
                y="label",
                orientation="h",
                title=title,
                labels={"count": "Documents", "label": ""},
            ),
            width="stretch",
        )
    collector_values = (
        frame["collector"]
        .fillna("")
        .astype(str)
        .loc[lambda value: value.str.strip() != ""]
        .value_counts()
        .rename_axis("collector")
        .reset_index(name="documents")
    )
    if not collector_values.empty:
        st.dataframe(collector_values, width="stretch", hide_index=True)
    st.warning(
        "Platform/source differences may reflect collection coverage, availability and sampling "
        "rather than differences in the wider public discourse."
    )


def _render_live_region(
    st,
    px,
    go,
    nx,
    *,
    data_path: str,
    project_id: str,
    arena_id: str,
    modules: dict[str, bool],
    filters: dict,
    blind_initial: bool,
) -> None:
    annotations, error = _safe_load(data_path, project=project_id, arena=arena_id)
    if error:
        st.error(f"Could not reload canonical dashboard input: {error}")
        return
    frame = build_live_frame(annotations)
    if frame.empty:
        st.info(
            "No canonical annotations are available yet. Live polling is active; this view will "
            "populate when the export file receives analyzed AI26 records."
        )
        return
    filtered = _apply_filters(frame, filters)
    st.caption(
        f"Live source: {Path(data_path).name} · {len(filtered)}/{len(frame)} records in view"
    )
    if filtered.empty:
        st.info("No documents match the current filters.")
        return
    selected_annotations = _selected_annotations(filtered)

    if blind_initial:
        tabs = st.tabs(["Overview", "Sources"])
        with tabs[0]:
            _render_overview(st, px, filtered, blind=True)
        with tabs[1]:
            _render_sources(st, px, filtered)
        return

    names = ["Overview", "Ideologies", "Signifiers", "Network", "Chains & frontiers", "Actors"]
    if modules.get("temporal", False):
        names.append("Timeline")
    names.append("Sources")
    tabs = dict(zip(names, st.tabs(names)))
    with tabs["Overview"]:
        _render_overview(st, px, filtered, blind=False)
    with tabs["Ideologies"]:
        _render_ideologies(st, px, filtered)
    with tabs["Signifiers"]:
        _render_signifiers(st, px, selected_annotations, filtered)
    with tabs["Network"]:
        _render_network(st, go, nx, selected_annotations, modules=modules)
    with tabs["Chains & frontiers"]:
        _render_chains_frontiers(st, nx, selected_annotations, filtered)
    with tabs["Actors"]:
        _render_actors(st, filtered)
    if "Timeline" in tabs:
        with tabs["Timeline"]:
            _render_timeline(st, px, filtered)
    with tabs["Sources"]:
        _render_sources(st, px, filtered)


def main() -> None:
    args = _arguments()
    st, px, go, nx = require_dashboard_runtime()
    st.set_page_config(page_title="LaclauGPT Live", page_icon="📡", layout="wide")
    st.title("LaclauGPT · live discourse topology")
    st.caption(
        "Near-real-time, evidence-linked exploration of canonical analyzed records. "
        "Machine codings remain provisional and human-reviewable."
    )

    data_path = args.data or st.sidebar.text_input("Canonical JSONL/NDJSON", "")
    if not data_path:
        st.info("Provide a canonical LaclauGPT JSONL/NDJSON export.")
        return

    project_id = args.project.strip()
    arena_id = args.arena.strip()
    reviewer_id = args.reviewer or st.sidebar.text_input("Reviewer pseudonym", "")
    blind_initial = bool(
        args.blind_initial or st.sidebar.checkbox("Blind initial coding", value=False)
    )
    review_db = args.review_db or st.sidebar.text_input("Review sidecar SQLite", "")

    initial_annotations, error = _safe_load(data_path, project=project_id, arena=arena_id)
    if error:
        st.error(f"Could not load canonical interchange output: {error}")
        return
    initial_frame = build_live_frame(initial_annotations)
    modules = _analysis_switches(project_id)

    if project_id:
        project = load_project(project_id)
        title = str(project.get("dataset", {}).get("title") or project_id)
        st.caption(f"{title} · profile: {project_id}:{arena_id or 'all'}")

    live_mode = st.sidebar.toggle("Live polling", value=True)
    refresh_seconds = st.sidebar.slider(
        "Refresh every (seconds)", min_value=10, max_value=300, value=30, step=10
    )
    st.sidebar.button("Refresh whole dashboard")
    run_every = refresh_seconds if live_mode else None

    time_window = st.sidebar.selectbox("Time window", list(TIME_WINDOWS), index=2)
    search = st.sidebar.text_input("Search", "") if not blind_initial else ""
    platforms = st.sidebar.multiselect("Platforms", _unique(initial_frame, "source_platform"))
    languages = st.sidebar.multiselect("Languages", _unique(initial_frame, "language"))
    actors = st.sidebar.multiselect(
        "Actors / source authors", _unique(initial_frame, "source_author")
    )
    formations = []
    signifiers = []
    if blind_initial:
        st.sidebar.caption("Model-derived formation/signifier filters are hidden in blind mode.")
    else:
        formations = st.sidebar.multiselect(
            "Candidate formations", _list_unique(initial_frame, "formations")
        )
        signifiers = st.sidebar.multiselect("Signifiers", _list_unique(initial_frame, "signifiers"))

    filters = {
        "time_window": time_window,
        "search": search,
        "platforms": platforms,
        "languages": languages,
        "actors": actors,
        "formations": formations,
        "signifiers": signifiers,
    }

    @st.fragment(run_every=run_every)
    def live_region() -> None:
        _render_live_region(
            st,
            px,
            go,
            nx,
            data_path=data_path,
            project_id=project_id,
            arena_id=arena_id,
            modules=modules,
            filters=filters,
            blind_initial=blind_initial,
        )

    live_region()

    st.divider()
    st.header("Evidence inspector & researcher review")
    st.caption(
        "This section is intentionally a stable snapshot while live polling runs, so automatic "
        "refreshes do not interrupt coding notes. Use the button below or any sidebar change to "
        "reload it from the latest canonical export."
    )
    st.button("Reload evidence snapshot")

    snapshot = _apply_filters(initial_frame, filters)
    if snapshot.empty:
        st.info("No snapshot documents match the current filters.")
        return

    selected_annotations = _selected_annotations(snapshot)
    labels = []
    for index, row in enumerate(snapshot.itertuples(index=False)):
        timestamp = (
            row.source_timestamp.isoformat() if pd.notna(row.source_timestamp) else ""
        )
        title = str(getattr(row, "source_title", "") or "").strip()
        suffix = f" · {timestamp}" if timestamp else ""
        title_suffix = f" · {title[:70]}" if title else ""
        labels.append(f"{row.document_id}{title_suffix}{suffix} · row {index + 1}")
    selected_label = st.selectbox("Evidence document", labels)
    annotation = selected_annotations[labels.index(selected_label)]

    corpus_id = Path(data_path).stem
    review_path = Path(review_db) if review_db else Path(f"{data_path}.reviews.sqlite3")
    review_store = ReviewStore(review_path)
    try:
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
    finally:
        review_store.close()

    st.caption(
        "Research dashboard only. Canonical analysis output is read-only here; researcher "
        "assessments remain separate in the local review sidecar."
    )


if __name__ == "__main__":
    main()
