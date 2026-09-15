# Context & memory architecture (issue #140)

This note defines **what context each analysis stage receives, what persists
across documents and runs, and which profiles are supported** — and the
rationale for each decision. It is the architecture note the issue asks for;
the implementation lands as `laclaugpt/context_profiles.py` (profiles) and a
benchmark harness, feature-flagged so current production behaviour is
unchanged until benchmarks justify a switch.

## 1. Stage map and context requirements

| Stage | What it needs as context | Current mechanism | Gap |
|---|---|---|---|
| summary | transcript/OCR/frame text; topic background; entity glossary | `memory_context(text)` + topic background | corpus stats absent |
| discourse | summary; glossary (topic/entity/target); codebook hints; analytic hints | memory retrieval block | codebook block implicit, not logged |
| postprocess | glossary (topic/entity/target); source row | memory retrieval | — |
| populism | glossary (signifier/target); discourse output | memory retrieval | — |
| corpus synthesis (new, #136) | grouped annotations; formation stats; previous windows | `laclaugpt/synthesis.py` | provenance exists |
| researcher renderer | canonical record | `researcher_reporting.py` | — |

**Principle already enforced in code:** context blocks are *retrieval
suggestions*, never authoritative prior findings (neutral framing, issue #62
finding 4). That wording is load-bearing against anchoring bias and stays.

## 2. Memory architecture (what persists and why)

Six layers, in increasing persistence:

1. **Static research context** — theory text, ontology, codebooks. Loaded per
   stage; version-tracked (`prompt_versions` already in provenance).
2. **Corpus context** — known actors/formations/frames statistics from
   `laclaugpt/formations.py` + corpus counts. Descriptive only.
3. **Run context** — run config fingerprint (already recorded per row).
4. **Short-term memory** — the SQLite Context Memory glossary
   (`laclaugpt_memory`): canonical entity/topic strings + aliases + embeddings,
   injected per stage with stable IDs. This is the *glossary + normalisation
   loop*, deliberately not RAG (see `docs/CONTEXT_MEMORY_DESIGN.md`).
5. **Long-term retrieval memory** — prior analyses remain in the canonical
   JSONL/SQLite; retrieval is by entity (memory) not by embedding search.
   Vector RAG stays an **opt-in benchmark-gated add-on** (`vector_rag: false`).
6. **Temporal situational state** — previous batch/daily structured summary
   (issue #136 synthesis output). Opt-in per profile; benchmarked against
   stateless runs before production default (anchoring-bias risk documented).

## 3. Approaches evaluated (issue-mandated list)

| Approach | Verdict for LaclauGPT | Reason |
|---|---|---|
| Plain message/history between stages | **kept** (stages already chain structured outputs) | cheap, proven |
| Structured rolling summaries / state objects | **adopted as opt-in** (`inject_previous_batch_summary`) | matches daily-report experiment |
| Previous-stage outputs passed forward | **already canonical** | summary_json flows into discourse/populism |
| Previous batch summaries / daily report | **opt-in, benchmark-gated** | anchoring bias risk; harness in `scripts/benchmark_context.py` |
| Claude-Code-style project memory files | **kept** — `docs/`, `sources/codebooks/`, run YAMLs are the project memory | already deterministic, versioned in git |
| LangChain memory | **rejected for now** | framework overhead without a benchmark win; adds a dependency for what SQLite already does |
| LlamaIndex retrieval | **rejected for now** | same; corpus is small and structured |
| Vector RAG (standalone store) | **opt-in flag, off by default** | useful only when corpus outgrows glossary (≫100k entities); Qdrant/ChromaDB are new services to operate |
| Graph RAG / hybrid | **not adopted** | the canonical SQLite graph (`laclaugpt/graph.py`) already stores the discourse graph; a second graph store adds drift risk |
| Entity-centric memory | **already the core design** | glossary + alias resolution *is* entity-centric memory |
| Temporal memory | **adopted via corpus synthesis windows** (#136 date grouping + baseline comparison) | temporal analysis happens at synthesis level, not per-prompt |
| Episodic memory of corrections | **adopted** — human-rejected merges (`rejected_merges`) and review state are first-class in Context Memory | INV_HUMAN_REVIEW |
| Hierarchical memory | **partially adopted** — profile knobs express retrieval depth per level; deeper hierarchy deferred to benchmark | — |
| Cached prompt/context bundles | **partially present** — stage cache fingerprints; context fingerprint added with profiles | — |

## 4. Codebook audit per stage

Audit result (verified against `pipeline.py`, `prompts/*.py`):

| Stage | Codebook use | Mandatory? | Recorded? | Missing behaviour |
|---|---|---|---|---|
| summary | topic background + glossary | optional (descriptive) | ✓ prompt version | proceeds with warning |
| discourse | codebook hints + glossary + analytic hints | **required by profile** | ✓ prompt versions | profile gate |
| postprocess | glossary (topics/entities) | optional | ✓ | — |
| populism | glossary (signifier/target) + codebook hints | **required by profile** | ✓ | profile gate |

**Fail-loudly rule:** with `inject_codebook: true` and
`codebook_required_stages` set, a run whose `memory_context()` returns an
empty block (disabled run / empty glossary / missing codebook) for a required
stage logs a loud warning AND marks the row's provenance
(`codebook_missing: true`) so validation sweeps detect it. The run does not
fail closed — it flags, keeping INV_HUMAN_REVIEW (the EP24 private-repo
policy of hard-failing a *pilot* stays in the private repo; the public repo
records and surfaces).

## 5. Profiles

Four bundled profiles (see `laclaugpt/context_profiles.py`; YAML overrides in
`laclaugpt/profiles/`):

| Profile | Glossary top-k | Codebook | Batch state | Corpus stats | Context budget | Provenance | Use |
|---|---|---|---|---|---|---|---|
| `fast_local` | 3 | ✓ | ✗ | ✗ | 2 000 / 4 000 | off | laptop, pilots, debugging |
| `balanced` (default) | 5 | ✓ | ✗ | ✗ | 6 000 / 12 000 | ✓ | routine production |
| `high_accuracy` | 8 | ✓ | ✓ | ✓ | 12 000 / 20 000 | ✓ | research runs, Roihu |
| `validation` | 5 | ✓ | ✓ | ✓ | 6 000 / 12 000 | ✓ | memory on/off comparisons |

Selection is configuration only:

```yaml
context_profile: balanced      # or fast_local / high_accuracy / validation
```

Switching profiles never changes models, stages, evidence gates, or relevance
handling — those stay the run YAML's authority.

## 6. Benchmark harness

`scripts/benchmark_context.py` runs the same human-reviewed sample under two
profiles and reports: agreement, evidence fidelity (quote verification rate),
glossary consistency, latency, tokens, and per-stage model usage. Usage:

```bash
python3 scripts/benchmark_context.py --sample data/gold_sample.csv \
    --runs balanced,validation,fast_local
```

Results are recorded as JSON next to the sample; aggregate, non-sensitive
numbers may be published (methodology-only in docs). The first benchmark
question is the **daily-report experiment**: stateless vs
`inject_previous_batch_summary` on the same sample, scored on agreement and
anchoring-bias symptoms (repetition of prior frames not supported by the
source).

## 7. Safety against analytical drift

- **Human vs model memory:** glossary candidates are suggestions with stable
  IDs; human-rejected merges are unreproposable (INV_HUMAN_REVIEW).
- **Model-generated memory is never ground truth:** neutral framing in all
  prompt blocks (issue #62 finding 4); formation labels stay provisional;
  frequency is never hegemony (INV_HEGEMONY_CORPUS).
- **TTL / staleness:** situational batch state is regenerated per run and
  never trusted older than the run's own window; codebooks are versioned by
  git and their prompt versions recorded.
- **Reproducibility:** `context_provenance: true` (default in
  `balanced`/`high_accuracy`) records which context block, at which top-k,
  was injected into which stage — enough to rebuild a prompt byte-stably.

## 8. Recommended defaults

- **Local / Laskin:** `balanced` with `context_memory: true`,
  top-k 5, codebook injection on. No vector store; embeddings via
  sentence-transformers MiniLM (CPU is sufficient at current corpus size).
- **CSC Roihu:** `high_accuracy` for validation passes; `balanced` for
  routine scale-ups. Deeper retrieval only if the benchmark shows gains.
- **Corpus synthesis:** synthesis consumes canonical outputs directly and
  inherits the run's profile for its own prompts (#136 module).

Migration plan: profiles are additive; default behaviour is unchanged until a
run explicitly sets `context_profile`. No schema break: profile knobs are new
optional RunConfig fields.