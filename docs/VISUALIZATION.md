# LaclauGPT visualization

LaclauGPT ships an optional Streamlit visualization layer for exploring canonical
interchange output. It is inspired by the older EP2024 video dashboard, but it is
not tied to one election, country, platform, classifier or database table.

## Runtime boundary

**Do not run the visualization on CSC Roihu.** Roihu is the batch-analysis side of
the architecture. The interactive dashboard is designed for:

- a local workstation or laptop; or
- a persistent Linux web server / virtual machine such as CSC Pouta.

The launcher rejects Roihu markers and active Slurm allocations. A normal pattern
is therefore:

1. run LaclauGPT analysis on Roihu;
2. copy/sync the resulting canonical `.jsonl`/`.ndjson` file to the local machine
   or Pouta VM;
3. launch the dashboard there.

This separation is deliberate. Streamlit is a persistent interactive web process,
not a batch/HPC workload.

## Installation

Visualization dependencies are optional:

```bash
python -m pip install -e ".[visualization]"
```

This adds Streamlit and Plotly. NetworkX and pandas are already core dependencies.

## Launch locally

```bash
laclaugpt dashboard data/annotations.jsonl \
  --project ai26 \
  --arena elites
```

The equivalent standalone command is:

```bash
laclaugpt-dashboard data/annotations.jsonl \
  --project ai26 \
  --arena elites
```

The default bind address is `127.0.0.1:8501`.

## Launch on a Pouta/Linux web server

After copying the analysis output to the server:

```bash
laclaugpt dashboard /srv/laclaugpt/annotations.jsonl \
  --project ai26 \
  --arena elites \
  --host 0.0.0.0 \
  --port 8501 \
  --review-db /srv/laclaugpt/reviews.sqlite3
```

For an internet- or institution-facing deployment, put Streamlit behind the
server's normal HTTPS reverse proxy and authentication/access-control layer. Do
not expose research data or an unauthenticated Streamlit port directly to the
public internet. Keep project data, review databases, credentials and TLS keys
outside the repository.

A production Pouta deployment may run the command under `systemd` or another
service manager. The repository intentionally does not ship site-specific IPs,
credentials, firewall rules or authentication secrets.

## Project and profile awareness

The dashboard uses the same canonical configuration hierarchy as analysis:

- `config/projects/<project>.yaml` supplies the project title and authoritative
  `analysis` module switches;
- `config/arenas/<arena>.yaml` supplies the arena/profile identity and label;
- the stable dashboard profile identity is `<project>:<arena>`.

The visible analytical tabs are derived from those switches rather than being
hard-coded for AI26. For example:

- `entities: true` enables entity views;
- `topics: true` enables topic views;
- `laclau: true` enables signifier and articulation-network views;
- `palonen: true` enables Us/Frontier and Formula-of-Populism views;
- `sociotechnical_imaginaries: true` enables imaginary views;
- `sentiment`/`palonen` enable affect views;
- `temporal: true` enables time-series views when source timestamps exist.

A future project/profile therefore inherits the same visualization engine by
adding canonical project/arena profiles and producing standard interchange
annotations. It does not require a new dashboard function.

## Data contract

The dashboard consumes the current `laclaugpt_interchange.DocumentAnnotation`
JSONL/NDJSON output. It does not read a project-specific DuckDB table or make
project-specific MongoDB queries.

The flattened UI surface includes, when present:

- source platform, country, language, author, timestamp and URL;
- summary and provenance;
- entities and topics;
- signifiers and nodal-point candidates;
- articulations and an aggregated articulation graph;
- candidate discourses/formations;
- sociotechnical imaginaries;
- Palonen Us/Frontier elements and classification/abstention;
- affects;
- evidence, uncertainty, prompt/model provenance and review status.

Filters are generic: free search, platform, language, country, author, model
review status, entity, topic and signifier. No country, party family, classifier
or platform is assumed.

## Researcher review notes

The old dashboard mixed visualization and study-specific correction state. The
new dashboard keeps that useful human-review workflow but stores it separately in
a local SQLite sidecar, by default next to the input file:

```text
annotations.jsonl.reviews.sqlite3
```

Review records contain only:

- canonical `document_id`;
- researcher review status;
- free-text note;
- comma-separated tags;
- update time.

Saving a dashboard review **never rewrites the canonical JSONL**. This preserves
the distinction between provisional model output and human review data.

## What was intentionally not copied from EP2024

The reusable interaction pattern was retained, but these old assumptions are not
part of the new architecture:

- a fixed `ep24_new` DuckDB table;
- Finland as the default country;
- fixed `Far right` / `Centre right` / `Red-green` categories;
- ManifestoBERTa-specific tabs and filters;
- Whisper/video columns as mandatory fields;
- one particular MongoDB notes collection;
- embedded database host/user/password configuration;
- project-specific logo/auth files.

If a future project needs a specialized view, add it as a profile-driven optional
view over the canonical schema rather than forking the dashboard into a new
project-specific application.
