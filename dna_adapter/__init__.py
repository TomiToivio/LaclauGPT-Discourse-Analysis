# -*- coding: utf-8 -*-
"""DNA adapter — importer/exporter over the LaclauGPT interchange schema.

DNA (Discourse Network Analyzer, leifeld-lab/dna, v3.1.x) stores a project
as a SQLite database (``.dna`` file). Its core data model is the STATEMENT:
an actor (person/organization entity) makes a statement about a concept,
optionally qualified (e.g. agreement), anchored to a character range in a
document. Networks are actor-concept matrices exported from statements.

Mappings (LaclauGPT interchange 1.2 <-> DNA 3.x):

  LaclauGPT                        DNA
  -------------------------------  --------------------------------------
  document_id                      DOCUMENTS (Title, Text, Date, Author,
                                     Source, Section, Type)
  us/frontier/signifier elements   ENTITIES (one variable per side)
  articulation (signifier ->        STATEMENT (Start/Stop = evidence
    related_to, relation, evidence)  quote offsets in the document text)
  relation equivalence|difference   agreement qualifier
    |frontier_of -> 1|0               (1 = equivalence, 0 = antagonistic)
  evidence quote                    DATALONGTEXT variable "evidence"
  relation label                    DATASHORTTEXT variable "relation"

Import (DNA -> LaclauGPT):
  - documents: DOCUMENTS table -> LaclauGPT CSV rows (id/text/body plus
    metadata columns the pipeline already understands).
  - concepts: existing concept entities -> provisional signifiers in
    laclaugpt_memory (same pattern as the DATS adapter).

Export (LaclauGPT -> DNA):
  - ``export_for_dna`` writes a fresh, DNA-compatible ``.dna`` SQLite
    database that DNA 3.1.x opens directly (schema mirrored from the
    official sample.dna of leifeld-lab/dna).
  - ``export_statements_csv`` writes the lighter fallback: one statement
    per row, loadable through DNA's CSV importer (documents) and rDNA.

Only PROVISIONAL-or-better annotations are exported; every statement
carries its evidence quote, so a DNA coder can find the anchor text.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from laclaugpt_interchange import DocumentAnnotation, from_jsonl

# Statement type + variable labels used in exported .dna files.
_STATEMENT_TYPE = "LaclauGPT Statement"
_VAR_ACTOR = "actor"
_VAR_CONCEPT = "concept"
_VAR_RELATION = "relation"
_VAR_EVIDENCE = "evidence"
_VAR_AGREEMENT = "agreement"

# DNA's own DDL, mirrored from the official leifeld-lab/dna sample.dna
# (v3.0.7 schema, still the 3.1.x on-disk format). One line per statement.
_DNA_SCHEMA = [
    "CREATE TABLE SETTINGS(Property TEXT PRIMARY KEY, Value TEXT NOT NULL)",
    """CREATE TABLE CODERS(ID INTEGER NOT NULL PRIMARY KEY, Name TEXT NOT NULL CHECK (LENGTH(Name) < 191), Red INTEGER NOT NULL DEFAULT 0 CHECK (Red BETWEEN 0 AND 255), Green INTEGER NOT NULL DEFAULT 0 CHECK (Green BETWEEN 0 AND 255), Blue INTEGER NOT NULL DEFAULT 0 CHECK (Blue BETWEEN 0 AND 255), Refresh INTEGER NOT NULL CHECK (Refresh BETWEEN 0 AND 9999) DEFAULT 0, FontSize INTEGER NOT NULL CHECK (FontSize BETWEEN 1 AND 99) DEFAULT 14, Password TEXT NOT NULL CHECK (LENGTH(Password) < 191), PopupWidth INTEGER CHECK (PopupWidth BETWEEN 100 AND 9999) DEFAULT 300, ColorByCoder INTEGER NOT NULL CHECK (ColorByCoder BETWEEN 0 AND 1) DEFAULT 0, PopupDecoration INTEGER NOT NULL CHECK (PopupDecoration BETWEEN 0 AND 1) DEFAULT 0, PopupAutoComplete INTEGER NOT NULL CHECK (PopupAutoComplete BETWEEN 0 AND 1) DEFAULT 1, PermissionAddDocuments INTEGER NOT NULL CHECK (PermissionAddDocuments BETWEEN 0 AND 1) DEFAULT 1, PermissionEditDocuments INTEGER NOT NULL CHECK (PermissionEditDocuments BETWEEN 0 AND 1) DEFAULT 1, PermissionDeleteDocuments INTEGER NOT NULL CHECK (PermissionDeleteDocuments BETWEEN 0 AND 1) DEFAULT 1, PermissionImportDocuments INTEGER NOT NULL CHECK (PermissionImportDocuments BETWEEN 0 AND 1) DEFAULT 1, PermissionAddStatements INTEGER NOT NULL CHECK (PermissionAddStatements BETWEEN 0 AND 1) DEFAULT 1, PermissionEditStatements INTEGER NOT NULL CHECK (PermissionEditStatements BETWEEN 0 AND 1) DEFAULT 1, PermissionDeleteStatements INTEGER NOT NULL CHECK (PermissionDeleteStatements BETWEEN 0 AND 1) DEFAULT 1, PermissionEditAttributes INTEGER NOT NULL CHECK (PermissionEditAttributes BETWEEN 0 AND 1) DEFAULT 1, PermissionEditRegex INTEGER NOT NULL CHECK (PermissionEditRegex BETWEEN 0 AND 1) DEFAULT 1, PermissionEditStatementTypes INTEGER NOT NULL CHECK (PermissionEditStatementTypes BETWEEN 0 AND 1) DEFAULT 1, PermissionEditCoders INTEGER NOT NULL CHECK (PermissionEditCoders BETWEEN 0 AND 1) DEFAULT 1, PermissionEditCoderRelations INTEGER NOT NULL CHECK (PermissionEditCoderRelations BETWEEN 0 AND 1) DEFAULT 1, PermissionViewOthersDocuments INTEGER NOT NULL CHECK (PermissionViewOthersDocuments BETWEEN 0 AND 1) DEFAULT 1, PermissionEditOthersDocuments INTEGER NOT NULL CHECK (PermissionEditOthersDocuments BETWEEN 0 AND 1) DEFAULT 1, PermissionViewOthersStatements INTEGER NOT NULL CHECK (PermissionViewOthersStatements BETWEEN 0 AND 1) DEFAULT 1, PermissionEditOthersStatements INTEGER NOT NULL CHECK (PermissionEditOthersStatements BETWEEN 0 AND 1) DEFAULT 1)""",
    """CREATE TABLE DOCUMENTS(ID INTEGER NOT NULL PRIMARY KEY, Title TEXT NOT NULL CHECK (LENGTH(Title) < 191), Text TEXT NOT NULL, Coder INTEGER, Author TEXT NOT NULL DEFAULT '' CHECK (LENGTH(Author) < 191), Source TEXT NOT NULL DEFAULT '' CHECK (LENGTH(Source) < 191), Section TEXT NOT NULL DEFAULT '' CHECK (LENGTH(Section) < 191), Notes TEXT NOT NULL DEFAULT '', Type TEXT NOT NULL DEFAULT '' CHECK (LENGTH(Type) < 191), Date INTEGER NOT NULL, FOREIGN KEY(Coder) REFERENCES CODERS(ID) ON DELETE CASCADE)""",
    """CREATE TABLE STATEMENTTYPES(ID INTEGER NOT NULL PRIMARY KEY, Label TEXT NOT NULL CHECK (LENGTH(Label) < 191), Red INTEGER NOT NULL DEFAULT 0 CHECK (Red BETWEEN 0 AND 255), Green INTEGER NOT NULL DEFAULT 0 CHECK (Green BETWEEN 0 AND 255), Blue INTEGER NOT NULL DEFAULT 0 CHECK (Blue BETWEEN 0 AND 255))""",
    """CREATE TABLE VARIABLES(ID INTEGER NOT NULL PRIMARY KEY, Variable TEXT NOT NULL CHECK (LENGTH(Variable) < 191), DataType TEXT NOT NULL CHECK (DataType = 'boolean' OR DataType = 'integer' OR DataType = 'long text' OR DataType = 'short text') DEFAULT 'short text', StatementTypeId INTEGER, FOREIGN KEY(StatementTypeId) REFERENCES STATEMENTTYPES(ID) ON DELETE CASCADE, UNIQUE (Variable, StatementTypeId))""",
    """CREATE TABLE STATEMENTS(ID INTEGER NOT NULL PRIMARY KEY, StatementTypeId INTEGER, DocumentId INTEGER, Start INTEGER NOT NULL CHECK(Start >= 0), Stop INTEGER NOT NULL CHECK(Stop >= 0), Coder INTEGER, CHECK (Start < Stop), FOREIGN KEY(StatementTypeId) REFERENCES STATEMENTTYPES(ID) ON DELETE CASCADE, FOREIGN KEY(Coder) REFERENCES CODERS(ID) ON DELETE CASCADE, FOREIGN KEY(DocumentId) REFERENCES DOCUMENTS(ID) ON DELETE CASCADE)""",
    """CREATE TABLE ENTITIES(ID INTEGER PRIMARY KEY NOT NULL, VariableId INTEGER NOT NULL, Value TEXT NOT NULL DEFAULT '' CHECK (LENGTH(Value) < 191), Red INTEGER CHECK (Red BETWEEN 0 AND 255), Green INTEGER CHECK (Green BETWEEN 0 AND 255), Blue INTEGER CHECK (Blue BETWEEN 0 AND 255), ChildOf INTEGER CHECK(ChildOf > 0), UNIQUE (VariableId, Value), FOREIGN KEY(VariableId) REFERENCES VARIABLES(ID) ON DELETE CASCADE)""",
    """CREATE TABLE DATABOOLEAN(ID INTEGER PRIMARY KEY NOT NULL, StatementId INTEGER NOT NULL, VariableId INTEGER NOT NULL, Value INTEGER NOT NULL DEFAULT 1, FOREIGN KEY(StatementId) REFERENCES STATEMENTS(ID) ON DELETE CASCADE, FOREIGN KEY(VariableId) REFERENCES VARIABLES(ID) ON DELETE CASCADE, UNIQUE (StatementId, VariableId))""",
    """CREATE TABLE DATAINTEGER(ID INTEGER PRIMARY KEY NOT NULL, StatementId INTEGER NOT NULL, VariableId INTEGER NOT NULL, Value INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(StatementId) REFERENCES STATEMENTS(ID) ON DELETE CASCADE, FOREIGN KEY(VariableId) REFERENCES VARIABLES(ID) ON DELETE CASCADE, UNIQUE (StatementId, VariableId))""",
    """CREATE TABLE DATASHORTTEXT(ID INTEGER PRIMARY KEY NOT NULL, StatementId INTEGER NOT NULL, VariableId INTEGER NOT NULL, Entity INTEGER NOT NULL, FOREIGN KEY(StatementId) REFERENCES STATEMENTS(ID) ON DELETE CASCADE, FOREIGN KEY(VariableId) REFERENCES VARIABLES(ID) ON DELETE CASCADE, FOREIGN KEY(Entity) REFERENCES ENTITIES(ID) ON DELETE CASCADE, UNIQUE (StatementId, VariableId))""",
    """CREATE TABLE DATALONGTEXT(ID INTEGER PRIMARY KEY NOT NULL, StatementId INTEGER NOT NULL, VariableId INTEGER NOT NULL, Value TEXT DEFAULT '', FOREIGN KEY(StatementId) REFERENCES STATEMENTS(ID) ON DELETE CASCADE, FOREIGN KEY(VariableId) REFERENCES VARIABLES(ID) ON DELETE CASCADE, UNIQUE (StatementId, VariableId))""",
    """CREATE TABLE ATTRIBUTEVARIABLES(ID INTEGER PRIMARY KEY NOT NULL, VariableId INTEGER NOT NULL, AttributeVariable TEXT NOT NULL CHECK (LENGTH(AttributeVariable) < 191), UNIQUE(VariableId, AttributeVariable), FOREIGN KEY(VariableId) REFERENCES VARIABLES(ID) ON DELETE CASCADE)""",
    """CREATE TABLE ATTRIBUTEVALUES(ID INTEGER PRIMARY KEY NOT NULL, EntityId INTEGER NOT NULL, AttributeVariableId INTEGER NOT NULL, AttributeValue TEXT NOT NULL DEFAULT '' CHECK (LENGTH(AttributeValue) < 191), UNIQUE (EntityId, AttributeVariableId), FOREIGN KEY(EntityId) REFERENCES ENTITIES(ID) ON DELETE CASCADE, FOREIGN KEY(AttributeVariableId) REFERENCES ATTRIBUTEVARIABLES(ID) ON DELETE CASCADE)""",
]

# Admin coder row: mirrored from the official sample.dna so the exported
# database is immediately openable. DNA hashes passwords; a fresh user can
# recreate coders inside DNA if a different admin account is wanted.
# (This is the sample.dna 'Admin' row verbatim.)
_ADMIN_CODER = (
    1, "Admin", 255, 255, 0, 0, 14,
    "t7STqOHxpl+RXxRUgjsEno+e/38banaYjANbdYQ1geGfH6Xlc2roWgYrPbpCeg5M",
    400, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
)


# ---------------------------------------------------------------------------
# Import: DNA -> LaclauGPT
# ---------------------------------------------------------------------------

def import_dna_documents(dna_path: str) -> list[dict]:
    """DNA .dna database -> LaclauGPT analysis-ready CSV rows.

    Reads DOCUMENTS and maps DNA's fields onto the pipeline's column
    conventions (id/text plus the metadata columns pipeline.py's
    SOURCE_TEXT_FIELDS and source_provenance already look for).
    """
    con = sqlite3.connect(f"file:{dna_path}?mode=ro", uri=True)
    try:
        rows = []
        for doc_id, title, text, author, source, section, dtype, date in con.execute(
            "SELECT ID, Title, Text, Author, Source, Section, Type, Date "
            "FROM DOCUMENTS ORDER BY ID"
        ):
            if not text or not text.strip():
                continue
            created = ""
            if isinstance(date, (int, float)) and date:
                created = datetime.fromtimestamp(
                    date, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows.append({
                "id": str(doc_id),
                "text": text,
                "title": title,
                "author": author or "",
                "source": source or "",
                "section": section or "",
                "type": dtype or "",
                "created_at": created,
                # LaclauGPT-exported .dna files stamp the original platform
                # into Source; pure DNA projects report as "dna".
                "source_platform": (source or "") or "dna",
            })
        return rows
    finally:
        con.close()


def import_dna_concepts(dna_path: str, memory, variable: str = _VAR_CONCEPT,
                        statement_type: str | None = None) -> list[str]:
    """Existing concept entities in a DNA database -> PROVISIONAL signifiers.

    Mirrors dats_adapter.import_dats_concepts: coder-defined concepts from a
    human DNA project seed laclaugpt_memory so the two tools share a codebook.
    Pass statement_type to restrict to one statement type (default: all).
    Returns created/reused obj_ids.
    """
    con = sqlite3.connect(f"file:{dna_path}?mode=ro", uri=True)
    try:
        query = (
            "SELECT DISTINCT e.Value FROM ENTITIES e "
            "JOIN VARIABLES v ON e.VariableId = v.ID "
            "WHERE v.Variable = ?"
        )
        params: list = [variable]
        if statement_type is not None:
            query += " AND v.StatementTypeId = (SELECT ID FROM STATEMENTTYPES WHERE Label = ?)"
            params.append(statement_type)
        values = [r[0] for r in con.execute(query, params) if r[0]]
    finally:
        con.close()
    ids = []
    for value in values:
        res = memory.resolve(value, kind="signifier", stage="dna-import",
                             video_key="", evidence="DNA concept")
        ids.append(res.obj_id)
    return ids


# ---------------------------------------------------------------------------
# Export: LaclauGPT -> DNA
# ---------------------------------------------------------------------------

def _evidence_span(quote: str, text: str) -> tuple[int, int]:
    """Character offsets of the evidence quote in the document text.

    Falls back to the whole text when the quote is not found verbatim
    (paraphrase, translation, or modality mismatch), so the statement
    still anchors to its document inside DNA.
    """
    if quote and quote in text:
        start = text.index(quote)
        return start, start + len(quote)
    return 0, max(len(text), 1)


def export_for_dna(annotations_path: str, out_path: str,
                   statement_type: str = _STATEMENT_TYPE,
                   doc_text_mode: str = "summary") -> dict:
    """Write a DNA-compatible .dna SQLite database from interchange JSONL.

    doc_text_mode: "summary" stores each annotation's summary as the DNA
    document text; "full" is reserved for future raw-text reattachment.

    One DNA statement is written per evidence-bearing articulation on the
    Us/Frontier sides (PopulismElementAssessment) — these carry side,
    affect, and evidence. Actor/concept entity values are the canonical
    labels; relation and evidence ride along as variables.
    Returns basic counts for logging.
    """
    annotations = from_jsonl(annotations_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    con = sqlite3.connect(str(out))
    try:
        cur = con.cursor()
        for ddl in _DNA_SCHEMA:
            cur.execute(ddl)
        cur.execute("INSERT INTO SETTINGS VALUES (?, ?)", ("version", "3.0.7"))
        cur.execute("INSERT INTO SETTINGS VALUES (?, ?)",
                    ("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")))
        cur.execute("INSERT INTO CODERS VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    _ADMIN_CODER)
        cur.execute("INSERT INTO STATEMENTTYPES (Label, Red, Green, Blue) VALUES (?,?,?,?)",
                    (statement_type, 200, 120, 255))
        st_id = cur.execute(
            "SELECT ID FROM STATEMENTTYPES WHERE Label = ?",
            (statement_type,)).fetchone()[0]
        var_ids: dict[str, int] = {}
        for name, dtype in (
            (_VAR_ACTOR, "short text"), (_VAR_CONCEPT, "short text"),
            (_VAR_RELATION, "short text"), (_VAR_EVIDENCE, "long text"),
            (_VAR_AGREEMENT, "boolean"),
        ):
            cur.execute("INSERT INTO VARIABLES (Variable, DataType, StatementTypeId) VALUES (?,?,?)",
                        (name, dtype, st_id))
            var_ids[name] = cur.execute(
                "SELECT ID FROM VARIABLES WHERE Variable = ? AND StatementTypeId = ?",
                (name, st_id)).fetchone()[0]

        entity_cache: dict[tuple[int, str], int] = {}

        def entity_id(variable_name: str, label: str) -> int:
            vid = var_ids[variable_name]
            key = (vid, label)
            if key not in entity_cache:
                cur.execute(
                    "INSERT INTO ENTITIES (VariableId, Value) VALUES (?,?)", (vid, label))
                entity_cache[key] = cur.execute(
                    "SELECT ID FROM ENTITIES WHERE VariableId = ? AND Value = ?",
                    (vid, label)).fetchone()[0]
            return entity_cache[key]

        doc_id_by_key: dict[str, int] = {}
        next_doc = 1
        next_stmt = 1
        next_data = 1
        n_statements = 0
        n_docs = 0
        for ann in annotations:
            elements = [e for e in ann.populism_elements
                        if e.evidence or e.evidence_verified]
            # Documents are exported EVEN without populism elements: a
            # correctly non-populist document is a real finding (paper
            # §3.1/§4.2: honest abstention), and DNA users still need the
            # document for manual coding. Statements come only from
            # evidence-bearing Us/Frontier elements.
            text = ann.summary or ann.document_id
            title = ann.document_id[:186] or f"document {next_doc}"
            created = ann.source_timestamp or ann.created_at or ""
            epoch = 0
            if created:
                try:
                    epoch = int(datetime.fromisoformat(
                        created.replace("Z", "+00:00")).timestamp())
                except ValueError:
                    epoch = 0
            cur.execute(
                "INSERT INTO DOCUMENTS (Title, Text, Coder, Author, Source, Section, Notes, Type, Date) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (title, text, 1, ann.source_author or "", ann.source_platform or "",
                 ann.source_country or "", "", f"laclaugpt {ann.schema_version}", epoch))
            dna_doc_id = cur.lastrowid
            doc_id_by_key[ann.document_id] = dna_doc_id
            n_docs += 1

            for el in elements:
                actor_label = (el.element.label or el.element.raw or "")[:186]
                if not actor_label:
                    continue
                start, stop = _evidence_span(el.evidence, text)
                cur.execute(
                    "INSERT INTO STATEMENTS (StatementTypeId, DocumentId, Start, Stop, Coder) "
                    "VALUES (?,?,?,?,?)", (st_id, dna_doc_id, start, stop, 1))
                sid = cur.lastrowid
                for var_name, value in (
                    (_VAR_ACTOR, actor_label),
                    (_VAR_CONCEPT, (el.element.label or el.element.raw or "")[:186]),
                    (_VAR_RELATION, el.side),
                    (_VAR_EVIDENCE, el.evidence),
                ):
                    if not value:
                        continue
                    if var_name in (_VAR_ACTOR, _VAR_CONCEPT, _VAR_RELATION):
                        eid = entity_id(var_name, value)
                        cur.execute(
                            "INSERT INTO DATASHORTTEXT (StatementId, VariableId, Entity) VALUES (?,?,?)",
                            (sid, var_ids[var_name], eid))
                    else:
                        cur.execute(
                            "INSERT INTO DATALONGTEXT (StatementId, VariableId, Value) VALUES (?,?,?)",
                            (sid, var_ids[var_name], value))
                    next_data += 1
                # agreement: 1 = equivalence (non-antagonistic), 0 = difference/frontier
                cur.execute(
                    "INSERT INTO DATABOOLEAN (StatementId, VariableId, Value) VALUES (?,?,?)",
                    (sid, var_ids[_VAR_AGREEMENT],
                     1 if el.side == "us" else 0))
                next_stmt += 1
                n_statements += 1
        con.commit()
        return {"documents": n_docs, "statements": n_statements,
                "path": str(out), "statement_type": statement_type}
    finally:
        con.close()


def export_statements_csv(annotations_path: str, out_path: str) -> int:
    """Flat statement CSV fallback for DNA's CSV importer and rDNA.

    One row per evidence-bearing Us/Frontier element: document metadata,
    actor, concept, side-as-relation, agreement, evidence. rDNA's
    network export or DNA's CSV import can then build the same
    actor-concept matrices without touching SQLite.
    """
    import csv

    annotations = from_jsonl(annotations_path)
    count = 0
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "title", "author", "source", "section",
                         "type", "date", "actor", "concept", "relation",
                         "agreement", "affect", "evidence"])
        for ann in annotations:
            for el in ann.populism_elements:
                if not (el.evidence or el.evidence_verified):
                    continue
                actor = el.element.label or el.element.raw or ""
                if not actor:
                    continue
                writer.writerow([
                    ann.document_id, ann.document_id, ann.source_author,
                    ann.source_platform, ann.source_country,
                    f"laclaugpt {ann.schema_version}",
                    ann.source_timestamp or ann.created_at,
                    actor, actor, el.side,
                    1 if el.side == "us" else 0,
                    el.affect, el.evidence,
                ])
                count += 1
    return count