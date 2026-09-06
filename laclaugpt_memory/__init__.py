# -*- coding: utf-8 -*-
"""LaclauGPT persistent analytical memory.

One module, one SQLite file, stable IDs, open-world codebook.
Works identically on the laptop and CSC Roihu; state lives in
persistent project/scratch storage via LACLAUGPT_MEMORY_DIR.

Design contract (from Tomi's spec):
- stable IDs: E001 entities, T001 topics, S001 signifiers, C001 targets, A001 actors, F001 formations
- codebook states: CANONICAL / PROVISIONAL / MERGED / DEPRECATED / REJECTED
- resolution workflow: EXTRACT -> RETRIEVE -> RESOLVE -> UPDATE
- new canonical objects are the LAST option; new objects start PROVISIONAL
- raw surface forms are always preserved (aliases) — discourse analysis
  needs the exact wording
- meanings may drift over time: relations are timestamped with provenance

Backends: SQLite (required) + optional local embedding index
(sentence-transformers if installed; graceful fallback to lexical match).
No external services, no cloud APIs, single-process Slurm safe.
"""
from __future__ import annotations

import difflib
import json
import os
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

# ── constants ────────────────────────────────────────────────────────

KINDS = ("entity", "topic", "signifier", "target", "actor", "formation")
STATES = ("CANONICAL", "PROVISIONAL", "MERGED", "DEPRECATED", "REJECTED")
KIND_PREFIX = {"entity": "E", "topic": "T", "signifier": "S",
               "target": "C", "actor": "A", "formation": "F"}
KIND_BY_PREFIX = {v: k for k, v in KIND_PREFIX.items()}

# spaCy NER entity classes (Tomi's 2026-09-06 ruling): the closed type
# vocabulary stored in objects.kind_type for kind='entity'. The LLM
# postprocess stage classifies each entity with one of these; humans can
# correct the label in review. Kept here so memory, prompts and adapters
# share one definition.
NER_TYPES = (
    "PERSON",       # People, including fictional
    "NORP",         # Nationalities or religious or political groups
    "FAC",          # Buildings, airports, highways, bridges, etc.
    "ORG",          # Companies, agencies, institutions, etc.
    "GPE",          # Countries, cities, states
    "LOC",          # Non-GPE locations, mountain ranges, bodies of water
    "PRODUCT",      # Objects, vehicles, foods, etc. (not services)
    "EVENT",        # Named hurricanes, battles, wars, sports events, etc.
    "WORK_OF_ART",  # Titles of books, songs, etc.
    "LAW",          # Named documents made into laws
    "LANGUAGE",     # Any named language
    "DATE",         # Absolute or relative dates or periods
    "TIME",         # Times smaller than a day
    "PERCENT",      # Percentage, including "%"
    "MONEY",        # Monetary values, including unit
    "QUANTITY",     # Measurements, as of weight or distance
    "ORDINAL",      # "first", "second", etc.
    "CARDINAL",     # Numerals that do not fall under another type
)
NER_TYPES_DESCRIPTION = {
    "PERSON": "People, including fictional",
    "NORP": "Nationalities or religious or political groups",
    "FAC": "Buildings, airports, highways, bridges, etc.",
    "ORG": "Companies, agencies, institutions, etc.",
    "GPE": "Countries, cities, states",
    "LOC": "Non-GPE locations, mountain ranges, bodies of water",
    "PRODUCT": "Objects, vehicles, foods, etc. (not services)",
    "EVENT": "Named hurricanes, battles, wars, sports events, etc.",
    "WORK_OF_ART": "Titles of books, songs, etc.",
    "LAW": "Named documents made into laws",
    "LANGUAGE": "Any named language",
    "DATE": "Absolute or relative dates or periods",
    "TIME": "Times smaller than a day",
    "PERCENT": "Percentage, including \"%\"",
    "MONEY": "Monetary values, including unit",
    "QUANTITY": "Measurements, as of weight or distance",
    "ORDINAL": "\"first\", \"second\", etc.",
    "CARDINAL": "Numerals that do not fall under another type",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
    obj_id    TEXT PRIMARY KEY,          -- E001 / T001 / S001 / C001 / A001 / F001
    kind      TEXT NOT NULL,             -- entity|topic|signifier|target|actor|formation
    label     TEXT NOT NULL,             -- canonical label (stable once CANONICAL)
    norm      TEXT NOT NULL,             -- normalised form for exact matching
    kind_type TEXT DEFAULT '',           -- finer type (person/org/policy/theme...)
    state     TEXT NOT NULL DEFAULT 'PROVISIONAL',
    definition TEXT DEFAULT '',
    example   TEXT DEFAULT '',           -- representative example quote
    centroid  TEXT DEFAULT '',           -- JSON embedding centroid (optional)
    uses      INTEGER DEFAULT 0,
    merged_into TEXT DEFAULT '',         -- for MERGED state: surviving obj_id
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_objects_kind ON objects(kind, state);
CREATE UNIQUE INDEX IF NOT EXISTS idx_objects_norm ON objects(kind, norm);

CREATE TABLE IF NOT EXISTS aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    obj_id   TEXT NOT NULL,
    alias    TEXT NOT NULL,              -- raw surface form as found
    norm     TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    source_ref TEXT DEFAULT '',          -- provenance: dataset/video_key/doc id
    UNIQUE(obj_id, alias)
);
CREATE INDEX IF NOT EXISTS idx_aliases_norm ON aliases(norm);
CREATE TABLE IF NOT EXISTS alias_meta (
    alias TEXT PRIMARY KEY,
    kind  TEXT NOT NULL,
    obj_id TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alias_meta_norm ON alias_meta(kind, alias);

CREATE TABLE IF NOT EXISTS embeddings (
    obj_id TEXT PRIMARY KEY,
    kind   TEXT NOT NULL,
    vector BLOB NOT NULL,                -- float32 little-endian bytes
    dim    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_embeddings_kind ON embeddings(kind);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    stage TEXT NOT NULL,                 -- summary|postprocess|populism|resolver|human
    video_key TEXT DEFAULT '',
    obj_id TEXT DEFAULT '',
    action TEXT NOT NULL,                -- created|matched|merged|promoted|deprecated|rejected|renamed
    detail TEXT DEFAULT '',              -- JSON: rationale, similarity, model, prompt_hash
    evidence TEXT DEFAULT ''             -- JSON: source quote + provenance
);

CREATE TABLE IF NOT EXISTS temporal (
    rel_id INTEGER PRIMARY KEY AUTOINCREMENT,
    obj_id TEXT NOT NULL,                -- canonical object
    related_obj TEXT NOT NULL,           -- other canonical object (or raw signifier id)
    relation TEXT DEFAULT 'relates_to',  -- relates_to|evolved_into|split_from|same_as
    period TEXT DEFAULT '',              -- e.g. '2024H1', '2026Q3'
    valid_from TEXT NOT NULL,
    valid_to TEXT DEFAULT '',
    source_ref TEXT DEFAULT '',          -- provenance
    UNIQUE(obj_id, related_obj, relation, period)
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    config TEXT DEFAULT ''
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_memory_dir() -> Path:
    """LACLAUGPT_MEMORY_DIR wins; else ./memory (laptop) / scratch (CSC)."""
    env = os.environ.get("LACLAUGPT_MEMORY_DIR")
    if env:
        return Path(env)
    return Path(os.environ.get("LACLAUGPT_DATA_DIR", "./data")) / "memory"


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


def normalize(text: str) -> str:
    """Deterministic surface normalisation (the first anti-explosion gate)."""
    if not text:
        return ""
    import re
    t = text.strip()
    t = _strip_accents(t).casefold()
    t = " ".join(t.split())
    # strip trailing parenthetical annotations ("Sam Altman (OpenAI CEO)")
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t).strip()
    t = t.strip(" \t\n.,;:!?\"'()[]{}")
    return t


def display_label(norm: str, kind: str) -> str:
    """Canonical display form: entities/actors Title Case, concepts lower."""
    if kind in ("entity", "actor"):
        return " ".join(w.capitalize() for w in norm.split())
    return norm


@dataclass
class Candidate:
    """One retrieved candidate shown to the LLM resolver."""
    obj_id: str
    kind: str
    label: str
    state: str
    score: float          # best combined similarity 0..1
    via: str              # exact|alias|fuzzy|embedding
    definition: str = ""


@dataclass
class Resolution:
    raw: str
    kind: str
    obj_id: str = ""
    label: str = ""
    decision: str = ""    # EXISTING | NEW | UNCERTAIN
    matched_via: str = ""
    score: float = 0.0


class MemoryRef:
    """Stable reference to a canonical memory object (interchange type)."""

    __slots__ = ("obj_id", "label", "kind", "raw")

    def __init__(self, obj_id: str, label: str, kind: str, raw: str = ""):
        self.obj_id = obj_id
        self.label = label
        self.kind = kind
        self.raw = raw

    def __repr__(self) -> str:
        return f"MemoryRef({self.obj_id}={self.label!r})"

    def __eq__(self, other) -> bool:
        return isinstance(other, MemoryRef) and self.obj_id == other.obj_id

    def __hash__(self) -> int:
        return hash(self.obj_id)



class Memory:
    """Persistent analytical memory. Instantiate once per job/CLI session.

    Same file works on laptop and Roihu:
        LACLAUGPT_MEMORY_DIR=/scratch/project_2009497/laclaugpt2/memory
    """

    def __init__(self, memory_dir: Optional[str] = None,
                 fuzzy_topic: float = 0.86, fuzzy_entity: float = 0.92,
                 embed_threshold: float = 0.88,
                 promote_threshold: int = 3,
                 max_context_items: int = 40,
                 embedding_backend: str = "auto"):
        base = Path(memory_dir) if memory_dir else default_memory_dir()
        base.mkdir(parents=True, exist_ok=True)
        self.dir = base
        self.db_path = base / "memory.sqlite3"
        self.fuzzy_topic = fuzzy_topic
        self.fuzzy_entity = fuzzy_entity
        self.embed_threshold = embed_threshold
        self.promote_threshold = promote_threshold
        self.max_context_items = max_context_items
        self.conn = sqlite3.connect(str(self.db_path), timeout=60)
        self.conn.row_factory = sqlite3.Row
        self._migrate()
        self._embedder = None
        self._embed_backend = (
            bool(embed_threshold)
            and embedding_backend not in ("none", "off", "disabled", "")
            and self._init_embedder(embedding=embedding_backend)
        )

    # ── schema & ids ─────────────────────────────────────────────────
    def _migrate(self) -> None:
        self.conn.executescript(SCHEMA)
        # drop a legacy bad index if present (v0.1 typo)
        self.conn.execute("DROP INDEX IF EXISTS idx_aliases_norm_bad")
        self.conn.commit()

    def _next_id(self, kind: str) -> str:
        prefix = KIND_PREFIX[kind]
        row = self.conn.execute(
            "SELECT obj_id FROM objects WHERE kind = ? ORDER BY obj_id DESC LIMIT 1",
            (kind,)).fetchone()
        n = int(row[0][1:]) + 1 if row else 1
        return f"{prefix}{n:03d}"

    def get(self, obj_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT obj_id, kind, label, state, kind_type, definition, example, "
            "uses, merged_into FROM objects WHERE obj_id = ?", (obj_id,)).fetchone()
        if not row:
            return None
        return {"obj_id": row[0], "kind": row[1], "label": row[2], "state": row[3],
                "type": row[4], "definition": row[5], "example": row[6],
                "uses": row[7], "merged_into": row[8]}

    # ── embeddings (optional, graceful) ──────────────────────────────
    def _init_embedder(self, embedding: str = "auto"):
        """Load a local sentence-transformers model if available.
        Fallback: None → similarity falls back to string metrics only."""
        try:
            from sentence_transformers import SentenceTransformer
            name = os.environ.get("LACLAUGPT_EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
            cache = self.dir / "embed-model"
            self._embedder = SentenceTransformer(name, cache_folder=str(cache))
        except Exception:
            self._embedder = None
            return False
        if self._embedder:
            self._backfill_embeddings()
        return True

    def _backfill_embeddings(self) -> None:
        """Embed any object that has no embedding row yet (batch, idempotent)."""
        try:
            import numpy as np
            rows = self.conn.execute(
                "SELECT o.obj_id, o.kind, o.label, o.norm FROM objects o "
                "LEFT JOIN embeddings e ON e.obj_id = o.obj_id "
                "WHERE e.obj_id IS NULL AND o.state IN ('CANONICAL','PROVISIONAL')").fetchall()
            for obj_id, kind, label, norm in rows:
                vec = self._embed(label)
                if vec:
                    self.conn.execute(
                        "INSERT OR REPLACE INTO embeddings (obj_id, kind, vector, dim) "
                        "VALUES (?, ?, ?, ?)",
                        (obj_id, kind, vec, int(len(np.frombuffer(vec, dtype="<f4")))))
            self.conn.commit()
        except Exception:
            pass  # embeddings optional

    def _embed(self, text: str):
        if not self._embedder:
            return None
        vec = self._embedder.encode(text, normalize_embeddings=True)
        import numpy as np
        return np.asarray(vec, dtype="<f4").tobytes()

    def _embed_similarities(self, query_vec, kind: str) -> list[tuple[str, float]]:
        """Scan embeddings for one kind. For ≤50k objects a linear scan in
        numpy is fast enough and needs no FAISS. Swap to FAISS later if the
        corpus grows — the table shape stays the same."""
        if query_vec is None:
            return []
        import numpy as np
        rows = self.conn.execute(
            "SELECT obj_id, vector FROM embeddings WHERE kind = ?",
            (kind,)).fetchall()
        if not rows:
            return []
        import struct
        out = []
        q = np.frombuffer(query_vec, dtype="<f4")
        for obj_id, blob in rows:
            v = np.frombuffer(blob, dtype="<f4")
            denom = (np.linalg.norm(q) * np.linalg.norm(v)) or 1.0
            out.append((obj_id, float(np.dot(q, v) / denom)))
        out.sort(key=lambda x: -x[1])
        return out

    # ── retrieval (what the LLM sees) ────────────────────────────────
    def retrieve_candidates(self, text: str, kind: str,
                            top_k: int = 5) -> list[Candidate]:
        """Retrieve the closest existing objects for a raw candidate string.
        Order: exact norm -> alias exact -> fuzzy string -> embedding."""
        norm = normalize(text)
        if not norm:
            return []
        out: dict[str, Candidate] = {}

        def add(obj_id: str, via: str, score: float):
            if obj_id in out and out[obj_id].score >= score:
                return
            o = self.get(obj_id)
            if o and o["state"] in ("CANONICAL", "PROVISIONAL"):
                out[obj_id] = Candidate(obj_id=obj_id, kind=kind, label=o["label"],
                                        state=o["state"], score=round(score, 4), via=via,
                                        definition=o["definition"])

        # exact on label
        for oid, lbl in self.conn.execute(
                "SELECT obj_id, label FROM objects WHERE kind = ? AND norm = ?",
                (kind, norm)).fetchall():
            add(oid, "exact", 1.0)
        # alias table
        for (oid,) in self.conn.execute(
                "SELECT obj_id FROM alias_meta WHERE kind = ? AND alias = ?",
                (kind, norm)).fetchall():
            add(oid, "alias", 0.99)
        # fuzzy over labels
        fuzzy_cut = self.fuzzy_entity if kind in ("entity", "actor", "target") else self.fuzzy_topic
        for oid, lbl in self.conn.execute(
                "SELECT obj_id, label FROM objects WHERE kind = ? AND state != 'MERGED'",
                (kind,)).fetchall():
            score = difflib.SequenceMatcher(None, normalize(lbl), norm).ratio()
            if score >= fuzzy_cut:
                add(oid, "fuzzy", score)
        # embeddings (optional)
        if self._embedder:
            vec = self._embed(text)
            for oid, score in self._embed_similarities(vec, kind):
                if score >= self.embed_threshold:
                    add(oid, "embedding", score)
        cands = sorted(out.values(), key=lambda c: -c.score)
        return cands[:top_k]

    # ── resolution API ───────────────────────────────────────────────
    def resolve(self, raw: str, kind: str,
                decision: Optional[str] = None,
                chosen_obj_id: Optional[str] = None,
                definition: str = "", example: str = "",
                type_: str = "", stage: str = "", video_key: str = "",
                evidence: str = "", model: str = "") -> Resolution:
        """EXTRACT -> RETRIEVE -> RESOLVE -> UPDATE.

        decision/chosen come from the LLM resolver when it is in the loop;
        when absent, auto-rules decide (high-confidence match = EXISTING).
        New objects are created PROVISIONAL, never CANONICAL, here.
        """
        raw = (raw or "").strip()
        if not raw:
            return Resolution(raw=raw, kind=kind, decision="UNCERTAIN")
        cands = self.retrieve_candidates(raw, kind)
        auto = None
        if cands and cands[0].score >= (1.0 if cands[0].via == "exact" else self.embed_threshold):
            auto = cands[0]
        if decision is None:
            decision = "EXISTING" if auto else "NEW"

        if decision == "EXISTING":
            obj_id = chosen_obj_id or (auto.obj_id if auto else "")
            if not obj_id and cands and cands[0].score >= 0.60:
                obj_id = cands[0].obj_id
            if not obj_id:
                return self._create_provisional(raw, kind, definition, example, type_,
                                                stage, video_key, evidence, model)
            via = cands[0].via if cands else ""
            score = cands[0].score if cands else 1.0
            self._add_alias(obj_id, raw)
            self._bump(obj_id)
            self._log(stage, video_key, obj_id, "matched",
                      {"via": via, "score": score, "model": model}, evidence)
            o = self.get(obj_id)
            return Resolution(raw=raw, kind=kind, obj_id=obj_id, label=o["label"],
                              decision="EXISTING", matched_via=via, score=score)

        if decision == "NEW":
            # NEW must still respect open-world: if a strong candidate exists,
            # treat as UNCERTAIN rather than silently creating a duplicate.
            if cands and cands[0].score >= min(self.fuzzy_topic, 0.80):
                return Resolution(raw=raw, kind=kind,
                                  obj_id=cands[0].obj_id, label=cands[0].label,
                                  decision="UNCERTAIN",
                                  matched_via=cands[0].via, score=cands[0].score)
            # containment guard: "openai inc" vs "openai" — a candidate whose
            # normalized form extends an existing label by 1-2 generic words
            # is treated as UNCERTAIN, not a fresh object.
            norm = normalize(raw)
            for oid, label in self.conn.execute(
                    "SELECT obj_id, label FROM objects WHERE kind = ? AND state IN ('CANONICAL','PROVISIONAL')",
                    (kind,)).fetchall():
                c = normalize(label)
                short, long = (c, norm) if len(c) <= len(norm) else (norm, c)
                extra = long[len(short):].strip() if long.startswith(short) else ""
                if short and extra and len(short) >= 4 and len(extra.split()) <= 2 and len(long) - len(short) <= 12:
                    self._add_alias(oid, raw)
                    self._log(stage, video_key, oid, "containment_uncertain",
                              {"raw": raw, "model": model})
                    return Resolution(raw=raw, kind=kind,
                                      obj_id=oid, label=label,
                                      decision="UNCERTAIN",
                                      matched_via="containment", score=0.80)
            return self._create_provisional(raw, kind, definition, example, type_,
                                            stage, video_key, evidence, model)

        # UNCERTAIN: store raw as an alias-less candidate for human review
        return self._create_provisional(raw, kind, definition, example, type_,
                                        stage, video_key, evidence,
                                        model=model,
                                        force_state="PROVISIONAL",
                                        note="resolver-uncertain")

    # ── object creation & lifecycle ──────────────────────────────────
    def _create_provisional(self, raw, kind, definition, example, type_,
                            stage, video_key, evidence, model="", force_state=None,
                            note="") -> Resolution:
        obj_id = self._next_id(kind)
        label = display_label(normalize(raw), kind)
        ts = now_iso()
        self.conn.execute(
            "INSERT INTO objects (obj_id, kind, label, norm, kind_type, state, "
            "definition, example, uses, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (obj_id, kind, label, normalize(raw), type_ or "",
             force_state or "PROVISIONAL", definition, example, ts, ts))
        self._add_alias(obj_id, raw)
        vec = self._embed(raw)
        if vec:
            import numpy as np
            self.conn.execute(
                "INSERT OR REPLACE INTO embeddings (obj_id, kind, vector, dim) "
                "VALUES (?, ?, ?, ?)",
                (obj_id, kind, vec, int(len(np.frombuffer(vec, dtype="<f4")))))
        self._log(stage, video_key, obj_id, "created",
                  {"initial_state": force_state or "PROVISIONAL", "model": model, "note": note},
                  evidence)
        self.conn.commit()
        return Resolution(raw=raw, kind=kind, obj_id=obj_id, label=label,
                          decision="NEW", matched_via="created",
                          score=0.0)

    _create_provisional_alias = _create_provisional  # legacy name

    def promote(self, obj_id: str, definition: str = "") -> None:
        """PROVISIONAL -> CANONICAL after repeated evidence/human validation."""
        o = self.get(obj_id)
        if not o:
            return
        ts = now_iso()
        self.conn.execute(
            "UPDATE objects SET state='CANONICAL', definition=CASE WHEN ?!='' THEN ? ELSE definition END, "
            "updated_at=? WHERE obj_id=?",
            (definition, definition, ts, obj_id))
        self._log("human", "", obj_id, "promoted", {})
        self.conn.commit()

    def merge(self, loser_id: str, winner_id: str, rationale: str = "",
              stage: str = "human") -> None:
        """Mark loser MERGED into winner. Both IDs preserved forever."""
        if loser_id == winner_id:
            return
        ts = now_iso()
        # move aliases to winner: keep history rows in aliases, repoint lookup
        for (alias, norm) in self.conn.execute(
                "SELECT a.alias, a.norm FROM aliases a WHERE a.obj_id = ?",
                (loser_id,)).fetchall():
            self.conn.execute(
                "INSERT OR IGNORE INTO aliases (obj_id, alias, norm, first_seen_at) "
                "VALUES (?, ?, ?, ?)",
                (winner_id, alias, norm, now_iso()))
            self.conn.execute(
                "INSERT OR REPLACE INTO alias_meta (alias, kind, obj_id) "
                "VALUES (?, (SELECT kind FROM objects WHERE obj_id = ?), ?)",
                (norm, winner_id, winner_id))
        w = self.get(winner_id)
        l = self.get(loser_id)
        self.conn.execute(
            "UPDATE objects SET state='MERGED', merged_into=?, updated_at=? WHERE obj_id=?",
            (winner_id, ts, loser_id))
        self.conn.execute("UPDATE objects SET uses = uses + ? WHERE obj_id = ?",
                          (l["uses"] if l else 0, winner_id))
        # move embeddings: recompute winner centroid as mean if present
        self._absorb_embedding(loser_id, winner_id)
        self._log(stage, "", loser_id, "merged",
                  {"winner": winner_id, "rationale": rationale})
        self.conn.commit()

    def deprecate(self, obj_id: str, rationale: str = "") -> None:
        self.conn.execute("UPDATE objects SET state='DEPRECATED', updated_at=? WHERE obj_id=?",
                          (now_iso(), obj_id))
        self._log("human", "", obj_id, "deprecated", {"rationale": rationale})
        self.conn.commit()

    def reject(self, obj_id: str, rationale: str = "") -> None:
        self.conn.execute("UPDATE objects SET state='REJECTED', updated_at=? WHERE obj_id=?",
                          (now_iso(), obj_id))
        self._log("human", "", obj_id, "rejected", {"rationale": rationale})
        self.conn.commit()

    def _add_alias(self, obj_id: str, raw: str) -> None:
        norm = normalize(raw)
        if not norm:
            return
        kind = self.get(obj_id)["kind"]
        ts = now_iso()
        self.conn.execute(
            "INSERT OR IGNORE INTO aliases (obj_id, alias, norm, first_seen_at) VALUES (?, ?, ?, ?)",
            (obj_id, raw.strip(), norm, ts))
        self.conn.execute(
            "INSERT OR REPLACE INTO alias_meta (alias, kind, obj_id) VALUES (?, ?, ?)",
            (norm, kind, obj_id))
        self.conn.commit()

    def _bump(self, obj_id: str) -> None:
        self.conn.execute("UPDATE objects SET uses = uses + 1, updated_at = ? WHERE obj_id = ?",
                          (now_iso(), obj_id))
        # Repetition by a model is not human validation. Objects remain
        # PROVISIONAL until the explicit promote() review action is invoked.
        self.conn.commit()

    def _absorb_embedding(self, loser_id: str, winner_id: str) -> None:
        try:
            import numpy as np
            a = self.conn.execute("SELECT vector FROM embeddings WHERE obj_id = ?", (loser_id,)).fetchone()
            b = self.conn.execute("SELECT vector FROM embeddings WHERE obj_id = ?", (winner_id,)).fetchone()
            if not a:
                return
            va = np.frombuffer(a[0], dtype="<f4")
            if b:
                vb = np.frombuffer(b[0], dtype="<f4")
                m = (va + vb) / 2.0
            else:
                m = va
            m = (m / (np.linalg.norm(m) or 1.0)).astype("<f4")
            self.conn.execute(
                "INSERT OR REPLACE INTO embeddings (obj_id, kind, vector, dim) "
                "VALUES (?, (SELECT kind FROM objects WHERE obj_id = ?), ?, ?)",
                (winner_id, winner_id, m.tobytes(), int(m.shape[0])))
        except Exception:
            pass  # embeddings are optional; merge must never fail because of them

    # ── logging / provenance ─────────────────────────────────────────
    def _log(self, stage, video_key, obj_id, action, detail: dict,
             evidence: str = "") -> None:
        self.conn.execute(
            "INSERT INTO decisions (ts, stage, video_key, obj_id, action, detail, evidence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (now_iso(), stage, video_key, obj_id, action, json.dumps(detail, ensure_ascii=False), evidence))

    # ── context building (small, relevant subset only) ───────────────
    def retrieve_context(self, text: str, top_k_per_kind: int = 5,
                         kinds: Iterable[str] = KINDS) -> dict[str, list[Candidate]]:
        """Retrieve relevant existing objects per kind for prompt injection.
        Never dumps the whole database into the prompt."""
        out = {}
        for kind in kinds:
            if kind not in KINDS:
                continue
            cands = [
                c for c in self.retrieve_candidates(text, kind, top_k_per_kind)
                if c.state == "CANONICAL"
            ]
            if not cands:
                # no direct match for this chunk: show the most-used entries
                # of that kind (usage-weighted codebook preview, capped) so
                # the model still knows what exists. Never the whole DB.
                rows = self.conn.execute(
                    "SELECT o.obj_id, o.label, o.state, o.definition "
                    "FROM objects o WHERE o.kind = ? AND o.state = 'CANONICAL' "
                    "ORDER BY o.uses DESC LIMIT ?", (kind, top_k_per_kind)).fetchall()
                cands = [Candidate(obj_id=r0[0], kind=kind, label=r0[1], state=r0[2],
                                   score=0.0, via="usage", definition=r0[3]) for r0 in rows]
            if cands:
                out[kind] = cands
        return out

    def context_prompt_block(self, text: str, top_k_per_kind: int = 5,
                             kinds: Iterable[str] = KINDS) -> str:
        """Render retrieved context for prompt injection (compact)."""
        ctx = self.retrieve_context(text, top_k_per_kind, kinds)
        if not ctx:
            return "(no established codebook entries match this chunk yet)"
        out_lines = []
        for kind, cands in ctx.items():
            out_lines.append(f"Established {kind} candidates (prefer EXISTING; use exact obj_id):")
            for c in cands:
                d = f" — {c.definition}" if c.definition else ""
                out_lines.append(f"- {c.obj_id} = {c.label}{d}")
        return "\n".join(out_lines)

    # ── analysis recording ───────────────────────────────────────────
    def record_analysis(self, video_key: str, stage: str, payload: dict,
                        evidence: str = "") -> None:
        """Store one coding decision with provenance."""
        self.conn.execute(
            "INSERT INTO decisions (ts, stage, video_key, obj_id, action, detail, evidence) "
            "VALUES (?, ?, ?, '', 'analysis', ?, ?)",
            (now_iso(), stage, video_key, json.dumps(payload, ensure_ascii=False), evidence))
        self.conn.commit()

    def record_relation(self, obj_id: str, related_obj: str, relation: str = "relates_to",
                        period: str = "", source_ref: str = "") -> None:
        """Temporal relations: meanings drift; keep the history."""
        self.conn.execute(
            "INSERT OR IGNORE INTO temporal (obj_id, related_obj, relation, period, "
            "valid_from, source_ref) VALUES (?, ?, ?, ?, ?, ?)",
            (obj_id, related_obj, relation, period, now_iso(), source_ref))
        self.conn.commit()

    # ── consolidation ────────────────────────────────────────────────
    def consolidate_memory(self, auto_merge_threshold: float | None = None) -> dict:
        """Periodic duplicate detection and human-review suggestions.

        Automatic merging is disabled by default because lexical similarity is
        not human validation. Pass a threshold explicitly only for a reviewed,
        controlled migration.
        Returns counts; writes merge_suggestions.csv for human review."""
        import csv
        suggestions = []
        auto_merged = 0
        for kind in KINDS:
            rows = self.conn.execute(
                "SELECT obj_id, label, uses FROM objects WHERE kind = ? AND state IN ('CANONICAL','PROVISIONAL')",
                (kind,)).fetchall()
            cut = self.fuzzy_entity if kind in ("entity", "actor", "target") else self.fuzzy_topic
            for i in range(len(rows)):
                for j in range(i + 1, len(rows)):
                    a, b = rows[i], rows[j]
                    score = difflib.SequenceMatcher(None, normalize(a[1]), normalize(b[1])).ratio()
                    if auto_merge_threshold is not None and score >= auto_merge_threshold:
                        winner, loser = (a, b) if a[2] >= b[2] else (b, a)
                        self.merge(loser[0], winner[0],
                                   rationale=f"auto: similarity {score:.3f}",
                                   stage="consolidation")
                        auto_merged += 1
                    elif score >= cut:
                        suggestions.append((kind, a[0], a[1], b[0], b[1], round(score, 4)))
        path = self.dir / "merge_suggestions.csv"
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["kind", "obj_id_a", "label_a", "obj_id_b", "label_b", "similarity"])
            w.writerows(suggestions)
        self._log("consolidation", "", "", "consolidated",
                  {"auto_merged": auto_merged, "suggestions": len(suggestions)})
        return {"auto_merged": auto_merged, "suggestions": len(suggestions),
                "review_file": str(path)}

    # ── exports ──────────────────────────────────────────────────────
    def export_review_csv(self, path: str) -> None:
        import csv
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["obj_id", "kind", "label", "state", "uses", "definition", "example"])
            for row in self.conn.execute(
                    "SELECT obj_id, kind, label, state, uses, definition, example "
                    "FROM objects WHERE state IN ('PROVISIONAL') ORDER BY kind, uses DESC"):
                w.writerow(row)

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()


# keep the old helper importable for compatibility shims
def resolve_candidates(candidates: list[str], kind: str,
                       memory: "Memory") -> tuple[list[str], list[str]]:
    """Compatibility wrapper matching the old pipeline.py call shape.
    Returns (matched_labels, new_labels)."""
    matched, new = [], []
    for cand in candidates:
        if not cand or not cand.strip():
            continue
        res = memory.resolve(cand, kind)
        if res.decision == "EXISTING":
            matched.append(res.label)
        elif res.decision == "NEW":
            new.append(res.label)
        else:
            matched.append(res.label)  # UNCERTAIN maps onto the proposed existing object
    matched, new = list(dict.fromkeys(matched)), list(dict.fromkeys(new))
    return matched, new
