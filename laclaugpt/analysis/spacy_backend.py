"""spaCy NLP backend: Representation → tokens/POS/dependencies/NER.

Maps spaCy entity labels onto canonical EntityMention candidates —
spaCy labels are NOT canonical entity types. Candidate entity
resolution goes through Context Memory (exact → alias → normalised →
embedding candidates) before any new entity is proposed.
"""
from __future__ import annotations

from typing import Any

from laclaugpt.analysis import BackendUnavailable, NlpDocument
from laclaugpt.model import EntityMention, Provenance, Representation

# spaCy label → canonical entity_type candidate (NOT the canonical entity
# itself; the registry decides). GPE/LOC → Place candidate, EVENT → Event.
_SPACY_TO_CANDIDATE_TYPE = {
    "PERSON": "person", "NORP": "group", "FAC": "facility",
    "ORG": "organization", "GPE": "place", "LOC": "place",
    "PRODUCT": "product", "EVENT": "event", "WORK_OF_ART": "work_of_art",
    "LAW": "law", "LANGUAGE": "language", "DATE": "temporal",
    "TIME": "temporal", "PERCENT": "quantity", "MONEY": "quantity",
    "QUANTITY": "quantity", "ORDINAL": "quantity", "CARDINAL": "quantity",
}

_BACKEND = "spacy"
_LOADED: dict[str, Any] = {}


def is_available() -> bool:
    try:
        import spacy  # noqa: F401
        return True
    except ImportError:
        return False


def _load(model_name: str):
    if model_name in _LOADED:
        return _LOADED[model_name]
    try:
        import spacy
        nlp = spacy.load(model_name)
    except Exception as exc:  # model or library missing
        raise BackendUnavailable(f"spaCy model {model_name!r} unavailable: {exc}") from exc
    _LOADED[model_name] = nlp
    return nlp


def _candidate_type(spacy_label: str) -> str:
    return _SPACY_TO_CANDIDATE_TYPE.get(spacy_label, "other")


_SPACY_TO_CANDIDATE_TYPE = _SPACY_TO_CANDIDATE_TYPE


def analyze(representation: Representation, model_name: str | None = None,
            provenance: Provenance | None = None) -> NlpDocument:
    """One spaCy pass: sentences, tokens, POS, dependencies, NER mentions."""
    if not is_available():
        raise BackendUnavailable("spaCy is not installed")
    model_name = model_name or "en_core_web_sm"
    doc = _load(model_name)
    parsed = doc(representation.text or "")
    provenance_id = provenance.provenance_id if provenance else ""
    result = NlpDocument(
        representation_id=representation.representation_id,
        sentences=[sent.text.strip() for sent in parsed.sents],
        tokens=[token.text for token in parsed],
        lemmas=[token.lemma_ for token in parsed],
        pos=[token.pos_ for token in parsed],
        dependencies=[
            {"token": token.text, "dep": token.dep_, "head": token.head.text,
             "head_index": token.head.i}
            for token in parsed if token.dep_ not in ("", "punct")
        ],
        language=representation.language,
        backend=_BACKEND,
        model=f"spacy:{model_name}",
        provenance_id=provenance_id,
    )
    for ent in parsed.ents:
        # spaCy label is a MENTION feature, never the canonical entity.
        # candidate_entity_id stays None — Context Memory decides whether
        # this mention maps to an existing entity or proposes a new one.
        result.mentions.append(EntityMention(
            representation_id=representation.representation_id,
            surface_form=ent.text,
            spacy_label=ent.label_,
            start_offset=ent.start_char, end_offset=ent.end_char,
            candidate_entity_type=_candidate_type(ent.label_),
        ))
    return result