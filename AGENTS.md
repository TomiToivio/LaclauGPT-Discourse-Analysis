# Agent instructions for LaclauGPT

This repository may be maintained by different coding/research agents. The agent framework is replaceable; the research semantics are not.

## Required reading before theory-facing work

Before changing prompts, schemas, analysis logic, Context Memory/codebook behaviour, corpus synthesis, visualisations, or theory/methodology documentation, **read [`THEORY.md`](THEORY.md) in full**.

`THEORY.md` is the canonical human- and machine-readable semantic contract for the discourse-theoretical methodology used in this repository. The original works by Laclau, Laclau & Mouffe, and Palonen remain authoritative if a definition in `THEORY.md` is questioned or changed.

For each theory-facing change:

1. Identify the relevant concept IDs and `theory_invariants` in `THEORY.md`.
2. Inspect the existing implementation before editing.
3. Preserve evidence links, uncertainty, counter-evidence, abstention, provenance, and human review.
4. Keep document-level outputs provisional when a concept requires corpus-level validation.
5. Report a theory/implementation mismatch explicitly instead of silently changing either side to fit the other.
6. If the theory definition itself must change, verify it against the original source literature first.

## Non-negotiable theory invariants

At minimum, agents must preserve these rules:

- `INV_EVIDENCE`: substantive theoretical coding preserves source evidence.
- `INV_ABSTAIN`: empty/non-applicable results are valid.
- `INV_RELATIONAL`: discourse-theory concepts are relations/functions, not keyword categories.
- `INV_FLOAT_CORPUS`: floating-signifier status requires competing contextual fixations.
- `INV_EMPTY_CHAIN`: empty-signifier status requires representational expansion over a heterogeneous chain or absent fullness.
- `INV_HEGEMONY_CORPUS`: frequency or one document cannot establish hegemony.
- `INV_ANTAGONISM`: criticism/negative sentiment alone cannot establish antagonism.
- `INV_AFFECT`: sentiment polarity cannot substitute for affective investment.
- `INV_POPULISM`: `populist=true` requires evidenced Us and Frontier construction.
- `INV_DYNAMIC_LABELS`: fringe/mainstream/competing populism are relational dynamics, not permanent actor labels.
- `INV_HUMAN_REVIEW`: LLM outputs are preliminary and must remain human-reviewable and human-rejectable.
- `INV_CONTEXT`: quoted, reported, rejected, or parodied claims must not be silently attributed as asserted author positions.

## Human-in-the-loop boundary

LaclauGPT is for **human-in-the-loop, human-verified research only**. Machine-generated summaries, classifications, discourse codes, populism analyses, signifier roles, ideological formations, affects, and corpus syntheses are preliminary analysis. Agents must not describe them as final findings, ground truth, or autonomous scholarly judgement.

No repository agent may bypass or weaken human review in order to make the pipeline appear more autonomous.

## Descriptive computation is subordinate to interpretation

NER, topics, embeddings, similarity, sentiment, graph centrality, frequency, clustering, and other computational features can supply evidence or candidate structures. They do not, by themselves, establish articulation, equivalence, antagonism, nodal status, emptiness, floating status, affective investment, populism, polarisation, or hegemony.

## Repository boundaries

- Keep the canonical CLI/config/execution path intact unless a task explicitly changes it.
- Keep collector/source acquisition separate from discourse-theoretical interpretation.
- Do not commit research data, credentials, or private operational details.
- Agent integrations such as Hermes are callers of the canonical pipeline, not parallel implementations of the methodology.
- Run the relevant offline tests before declaring a change complete. The full public suite is `python -m pytest -q tests` after installing the documented test/collector extras.

## Audit expectation

When touching theory-facing code, check nearby tests and documentation for the same invariant. Machine-checkable constraints should be tested where practical, but do not claim that unit tests can establish interpretive validity. Corpus-level theoretical judgements remain substantive human research tasks.
