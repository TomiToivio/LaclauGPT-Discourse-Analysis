# -*- coding: utf-8 -*-
"""Seed the LaclauGPT persistent codebook from the paper.

Every concept the paper names as an analytical object gets a stable ID:
signifiers, entities, actors, ideological formations, and the affect
vocabulary used by the Formula of Populism stage.

Seed definitions are deliberately *non-adjudicative*.  They may tell a model
what a label refers to, but they must not pre-assign a Laclaudian role, an Us /
Frontier side, or an affect polarity.  THEORY.md remains authoritative: roles
and political functions have to be demonstrated from source evidence and, when
required, corpus comparison.

Run (from this directory):
    python -m seed_codebook --memory-dir <persistent/dir>

Idempotent: re-running resolves to the same IDs (resolve-first policy).  A
re-run also migrates the exact role/side-coded legacy seed definitions shipped
before issue #61 to their neutral replacements without overwriting unrelated
human-edited definitions.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from laclaugpt_memory import Memory  # noqa: E402

ROLE_MUST_BE_DEMONSTRATED = (
    "Candidate signifier; any nodal, floating, empty, equivalential, frontier, "
    "or other discourse role must be demonstrated from source evidence and, "
    "where required, corpus comparison"
)
AFFECT_MUST_BE_DEMONSTRATED = (
    "Candidate affect term; its target, political side, contextual valence, "
    "and function must be demonstrated from source evidence"
)

# Exact historical definitions that encoded a role or Us/Frontier side.  These
# are used only for a conservative migration when an existing codebook is
# re-seeded.  We do not overwrite arbitrary human-edited definitions.
LEGACY_PRIMING_DEFINITIONS = {
    "artificial intelligence": {
        "Contested-signifier candidate; its nodal, floating, or empty role must be demonstrated comparatively",
    },
    "ai safety": {
        "Floating-signifier candidate whose articulation must be compared across discourses",
    },
    "ai regulation": {
        "Floating-signifier candidate whose meaning may differ across formations",
    },
    "risk": {
        "Nodal-point candidate in existential-risk discourse; not assumed in each document",
    },
    "innovation": {"Accelerationist nodal-point candidate"},
    "economic growth": {"Equivalence-chain element on the accelerationist Us side"},
    "abundance": {"Accelerationist Us element (Andreessen restatement)"},
    "human flourishing": {"Accelerationist Us terminal element"},
    "stagnation": {"Frontier element (Andreessen restatement)"},
    "deceleration": {"Frontier element; e/acc antagonism (Okolo 2025)"},
    "hope": {"Us-side affect (accelerationist example)"},
    "pride": {"Us-side affect"},
    "ambition": {"Us-side affect"},
    "confidence": {"Us-side affect"},
    "resentment": {"Frontier-side affect"},
    "anger": {"Frontier-side affect"},
    "fear": {"Frontier-side affect"},
    "contempt": {"Frontier-side affect"},
}

# (kind, label, neutral codebook definition)
SEEDS = [
    # ── signifiers (paper's discourse-theoretical vocabulary/corpus objects) ──
    ("signifier", "artificial intelligence", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "ai safety", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "ai regulation", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "risk", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "innovation", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "economic growth", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "abundance", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "human flourishing", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "stagnation", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "deceleration", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "existential risk", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "surveillance", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "data centre", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "job displacement", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "post-work society", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "postcapitalism", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "fully automated luxury communism", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "cyborg", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "technological singularity", ROLE_MUST_BE_DEMONSTRATED),
    ("signifier", "public interest ai", ROLE_MUST_BE_DEMONSTRATED),
    # ── actors (paper's named movements/institutions) ──
    ("actor", "Machine Intelligence Research Institute", "Named AI x-risk/safety research organisation in the paper corpus design"),
    ("actor", "Distributed AI Research Institute", "Named critical-AI research organisation in the paper corpus design"),
    ("actor", "PauseAI", "Named grassroots AI-pause movement in the paper corpus design"),
    ("actor", "Effective Accelerationism", "Named pro-acceleration movement in the paper corpus design"),
    # ── entities (people/artefacts the pipeline should recognise) ──
    ("entity", "Marc Andreessen", "Author of The Techno-Optimist Manifesto (2023)"),
    ("entity", "Bernie Sanders", "US politician discussed in the paper's anti-AI backlash material"),
    ("entity", "Donna Haraway", "Author associated with the cyborg-manifesto literature used in the paper"),
    ("entity", "Ernesto Laclau", "Discourse-theory source"),
    ("entity", "Chantal Mouffe", "Discourse-theory co-author"),
    ("entity", "Emilia Palonen", "Formula of Populism source"),
    ("entity", "Simon Lindgren", "Critical AI Studies and assemblage/empty-signifier source"),
    ("entity", "Manuel DeLanda", "Assemblage-theory source"),
    ("entity", "Timnit Gebru", "TESCREAL critique co-author"),
    ("entity", "Émile P. Torres", "TESCREAL critique co-author"),
    ("entity", "Ray Kurzweil", "Singularity theorist"),
    # ── ideological formations (F-kind; sensitising candidates, never direct classification) ──
    ("formation", "accelerationism", "Sensitising formation label used for comparative analysis; membership must be evidenced"),
    ("formation", "x-risk doomerism", "Sensitising formation label used for comparative analysis; membership must be evidenced"),
    ("formation", "critical ai studies", "Sensitising formation label used for comparative analysis; membership must be evidenced"),
    ("formation", "TESCREAL", "Sensitising formation label used for comparative analysis; membership must be evidenced"),
    ("formation", "anti-ai backlash", "Sensitising formation label used for comparative analysis; membership must be evidenced"),
    ("formation", "left techno-optimism", "Sensitising formation label used for comparative analysis; membership must be evidenced"),
    # ── affect vocabulary (stored as targets for stable-ID compatibility) ──
    ("target", "hope", AFFECT_MUST_BE_DEMONSTRATED),
    ("target", "pride", AFFECT_MUST_BE_DEMONSTRATED),
    ("target", "ambition", AFFECT_MUST_BE_DEMONSTRATED),
    ("target", "confidence", AFFECT_MUST_BE_DEMONSTRATED),
    ("target", "resentment", AFFECT_MUST_BE_DEMONSTRATED),
    ("target", "anger", AFFECT_MUST_BE_DEMONSTRATED),
    ("target", "fear", AFFECT_MUST_BE_DEMONSTRATED),
    ("target", "contempt", AFFECT_MUST_BE_DEMONSTRATED),
]


def _refresh_legacy_definition(memory: Memory, obj_id: str, label: str,
                               neutral_definition: str) -> bool:
    """Replace only an exact legacy priming definition.

    Human edits and other project-specific definitions are deliberately left
    untouched.  This makes re-seeding a safe migration path for stores created
    before issue #61.
    """
    current = memory.get(obj_id)
    if not current:
        return False
    legacy = LEGACY_PRIMING_DEFINITIONS.get(label, set())
    if current.get("definition", "") not in legacy:
        return False
    memory.conn.execute(
        "UPDATE objects SET definition = ? WHERE obj_id = ?",
        (neutral_definition, obj_id),
    )
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed LaclauGPT codebook from the AI edition paper")
    ap.add_argument("--memory-dir", default=None,
                    help="persistent memory dir (LACLAUGPT_MEMORY_DIR or ./data/memory)")
    args = ap.parse_args()

    # spaCy NER type -> seed entities it applies to. The 18 NER classes are
    # the closed kind_type vocabulary; known seed entities get their class
    # pre-assigned, subject to human review downstream.
    seed_ner_types = {
        "Marc Andreessen": "PERSON", "Bernie Sanders": "PERSON",
        "Donna Haraway": "PERSON", "Ernesto Laclau": "PERSON",
        "Chantal Mouffe": "PERSON", "Emilia Palonen": "PERSON",
        "Simon Lindgren": "PERSON", "Manuel DeLanda": "PERSON",
        "Timnit Gebru": "PERSON", "Émile P. Torres": "PERSON",
        "Ray Kurzweil": "PERSON",
    }

    m = Memory(memory_dir=args.memory_dir, embedding_backend="auto")
    created, existing, migrated = [], [], []
    for kind, label, definition in SEEDS:
        res = m.resolve(label, kind=kind, definition=definition,
                        type_=seed_ner_types.get(label, "") if kind == "entity" else "",
                        stage="ai-edition-seed", video_key="paper",
                        evidence="AI edition seed: Ideological contestation over AI")
        if _refresh_legacy_definition(m, res.obj_id, label, definition):
            migrated.append(res.obj_id)
        row = f"{res.obj_id:6} {kind:10} {label}  [{res.decision}]"
        (existing if res.decision.upper() == "EXISTING" else created).append(row)
    m.conn.commit()
    print(f"created: {len(created)}  existing: {len(existing)}  migrated definitions: {len(migrated)}")
    print("\n-- created --")
    print("\n".join(created))
    print("\n-- already present --")
    print("\n".join(existing))
    if migrated:
        print("\n-- neutralized legacy definitions --")
        print("\n".join(migrated))
    print("\nmemory dir:", m.dir)
    m.close()


if __name__ == "__main__":
    main()
