# -*- coding: utf-8 -*-
"""Seed the LaclauGPT persistent codebook from the paper.

Every concept the paper names as an analytical object gets a stable ID:
signifiers (empty/floating/nodal candidates), entities (the paper's own
examples), actors, ideological formations, and the affect vocabulary
used by the Formula of Populism stage.

Run (from this directory):  python -m seed_codebook --memory-dir <persistent/dir>
Idempotent: re-running resolves to the same IDs (resolve-first policy).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from laclaugpt_memory import Memory  # noqa: E402

# (kind, label, definition/role in the paper)
SEEDS = [
    # ── signifiers (paper's core discourse-theoretical objects) ──
    ("signifier", "artificial intelligence", "Contested-signifier candidate; its nodal, floating, or empty role must be demonstrated comparatively"),
    ("signifier", "ai safety", "Floating-signifier candidate whose articulation must be compared across discourses"),
    ("signifier", "ai regulation", "Floating-signifier candidate whose meaning may differ across formations"),
    ("signifier", "risk", "Nodal-point candidate in existential-risk discourse; not assumed in each document"),
    ("signifier", "innovation", "Accelerationist nodal-point candidate"),
    ("signifier", "economic growth", "Equivalence-chain element on the accelerationist Us side"),
    ("signifier", "abundance", "Accelerationist Us element (Andreessen restatement)"),
    ("signifier", "human flourishing", "Accelerationist Us terminal element"),
    ("signifier", "stagnation", "Frontier element (Andreessen restatement)"),
    ("signifier", "deceleration", "Frontier element; e/acc antagonism (Okolo 2025)"),
    ("signifier", "existential risk", "X-Risk doomer imaginary crystallisation (Yudkowsky & Soares 2025)"),
    ("signifier", "surveillance", "Backlash mobilisation issue (Borwein et al. 2026)"),
    ("signifier", "data centre", "Backlash mobilisation issue; environmental costs (paper 1)"),
    ("signifier", "job displacement", "Backlash mobilisation issue (employment concerns)"),
    ("signifier", "post-work society", "Left techno-optimist vision (Cugurullo 2025; Srnicek & Williams 2015)"),
    ("signifier", "postcapitalism", "Left techno-optimist articulation (Srnicek & Williams 2015; Bastani 2019)"),
    ("signifier", "fully automated luxury communism", "Left techno-optimist vision (Bastani 2019)"),
    ("signifier", "cyborg", "Haraway's boundary-crossing figure; socialist-feminist politics (Haraway 1991)"),
    ("signifier", "technological singularity", "Kurzweil's idea, most influential TESCREAL-adjacent notion"),
    ("signifier", "public interest ai", "Okolo 2025 counter-proposal to accelerationism"),
    # ── actors (paper's named movements/institutions) ──
    ("actor", "Machine Intelligence Research Institute", "X-Risk doomer example (paper 2.2)"),
    ("actor", "Distributed AI Research Institute", "Critical AI perspective example (paper 2.2)"),
    ("actor", "PauseAI", "Grassroots pause-movement example (paper 3.3)"),
    ("actor", "Effective Accelerationism", "Pro-acceleration movement (paper 2.2)"),
    # ── entities (people/artefacts the pipeline should recognise) ──
    ("entity", "Marc Andreessen", "Accelerationist author (The techno-optimist manifesto 2023)"),
    ("entity", "Bernie Sanders", "US anti-AI backlash politician (Sanders 2026)"),
    ("entity", "Donna Haraway", "Cyborg manifesto author (Haraway 1991)"),
    ("entity", "Ernesto Laclau", "Discourse theory source"),
    ("entity", "Chantal Mouffe", "Discourse theory co-author"),
    ("entity", "Emilia Palonen", "Formula of Populism author"),
    ("entity", "Simon Lindgren", "Critical AI Studies / empty signifier + assemblage framing"),
    ("entity", "Manuel DeLanda", "Assemblage theory source"),
    ("entity", "Timnit Gebru", "TESCREAL critique co-author"),
    ("entity", "Émile P. Torres", "TESCREAL critique co-author"),
    ("entity", "Ray Kurzweil", "Singularity theorist"),
    # ── ideological formations (F-kind) ──
    ("formation", "accelerationism", "e/acc + techno-optimist manifesto lineage"),
    ("formation", "x-risk doomerism", "MIRI/Yudkowsky imaginary"),
    ("formation", "critical ai studies", "DAIR-lineage power/labour perspective"),
    ("formation", "TESCREAL", "Transhumanism-Extropianism-Singularitarianism-Cosmism-Rationalism-EA-Longtermism bundle"),
    ("formation", "anti-ai backlash", "Emerging political backlash (Borwein et al. 2026; Sanders 2026)"),
    ("formation", "left techno-optimism", "AIdeology / postcapitalism / FALC / cyborg socialism"),
    # ── affects (A-kind, Formula of Populism vocabulary) ──
    ("target", "hope", "Us-side affect (accelerationist example)"),
    ("target", "pride", "Us-side affect"),
    ("target", "ambition", "Us-side affect"),
    ("target", "confidence", "Us-side affect"),
    ("target", "resentment", "Frontier-side affect"),
    ("target", "anger", "Frontier-side affect"),
    ("target", "fear", "Frontier-side affect"),
    ("target", "contempt", "Frontier-side affect"),
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed LaclauGPT codebook from the AI edition paper")
    ap.add_argument("--memory-dir", default=None,
                    help="persistent memory dir (LACLAUGPT_MEMORY_DIR or ./data/memory)")
    args = ap.parse_args()

    # spaCy NER type -> seed entities it applies to (maintainer's ruling
    # ruling: the 18 NER classes are the closed kind_type vocabulary;
    # known seed entities get their NER class pre-assigned).
    seed_ner_types = {
        "Marc Andreessen": "PERSON", "Bernie Sanders": "PERSON",
        "Donna Haraway": "PERSON", "Ernesto Laclau": "PERSON",
        "Chantal Mouffe": "PERSON", "Emilia Palonen": "PERSON",
        "Simon Lindgren": "PERSON", "Manuel DeLanda": "PERSON",
        "Timnit Gebru": "PERSON", "Émile P. Torres": "PERSON",
        "Ray Kurzweil": "PERSON",
    }

    m = Memory(memory_dir=args.memory_dir, embedding_backend="auto")
    created, existing = [], []
    for kind, label, definition in SEEDS:
        res = m.resolve(label, kind=kind, definition=definition,
                        type_=seed_ner_types.get(label, "") if kind == "entity" else "",
                        stage="ai-edition-seed", video_key="paper",
                        evidence="AI edition seed: Ideological contestation over AI")
        row = f"{res.obj_id:6} {kind:10} {label}  [{res.decision}]"
        (existing if res.decision.upper() == "EXISTING" else created).append(row)
    print(f"created: {len(created)}  existing: {len(existing)}")
    print("\n-- created --")
    print("\n".join(created))
    print("\n-- already present --")
    print("\n".join(existing))
    print("\nmemory dir:", m.dir)
    m.close()


if __name__ == "__main__":
    main()
