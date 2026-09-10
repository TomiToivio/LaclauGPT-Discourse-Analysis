"""SentenceTransformers embedding backend: the primary embedding layer.

Serves Context Memory retrieval, vector RAG, entity/topic/concept
resolution candidates, duplicate detection and clustering. Embedding
similarity PROPOSES candidates; it never decides Laclaudian relations:

    embedding similarity != equivalence
    semantic similarity != articulation

Model name and version travel in every EmbeddingResult and in
Provenance for reproducibility (paper §3.3).
"""
from __future__ import annotations

from typing import Any, Iterable

from laclaugpt.analysis import BackendUnavailable, EmbeddingResult

_BACKEND = "sentence_transformers"
_DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
_ENGINE: dict[str, Any] = {}


def is_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _engine(model: str):
    if model not in _ENGINE:
        from sentence_transformers import SentenceTransformer
        _ENGINE[model] = SentenceTransformer(model)
    return _ENGINE[model]


def _version() -> str:
    try:
        import sentence_transformers
        return sentence_transformers.__version__
    except Exception:
        return ""


def embed(texts: Iterable[str], *, model: str | None = None,
          item_ids: list[str] | None = None) -> list[EmbeddingResult]:
    """Embed texts with provenance identity on every vector."""
    if not is_available():
        raise BackendUnavailable("sentence-transformers is not installed")
    model = model or _DEFAULT_MODEL
    engine = _engine(model)
    texts = list(texts)
    vectors = engine.encode(texts, normalize_embeddings=True)
    import importlib.metadata
    try:
        st_version = importlib.metadata.version("sentence-transformers")
    except Exception:
        st_version = ""
    results = []
    for index, (text, vector) in enumerate(zip(texts, vectors)):
        results.append(EmbeddingResult(
            item_id=item_ids[index] if item_ids else text,
            vector=[float(x) for x in vector],
            model=model, model_version=st_version,
            backend=_BACKEND, dimensions=len(vector),
        ))
    return results


def similarity(text_a: str, text_b: str, *, model: str | None = None) -> float:
    """Cosine similarity of normalized embeddings. A RETRIEVAL SCORE only:
    passing a threshold does not make two things equivalent or merged."""
    results = embed([text_a, text_b], model=model)
    a, b = results[0].vector, results[1].vector
    import math
    denom = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    if not denom:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / denom


def embedding_candidate_provider(registry):
    """Candidate provider hook for CanonicalRegistry.resolve(): proposes
    registry records as embedding-similar candidates. Proposals remain
    candidates — reuse above the auto-merge threshold is the registry's
    decision, and anything ambiguous goes to human review."""
    class _Provider:
        def __call__(self, mention: str, kind: str):
            records = [(record["id"], record["label"])
                       for record in registry.records.values()
                       if record["kind"] == kind]
            if not records:
                return []
            vectors = embed([mention] + [label for _, label in records])
            base = vectors[0].vector
            import math
            def cosine(vec):
                denom = (math.sqrt(sum(x * x for x in base))
                         * math.sqrt(sum(x * x for x in vec))) or 1.0
                return sum(x * y for x, y in zip(base, vec)) / denom
            scored = [(cid, cosine(result.vector))
                      for (cid, _), result in zip(records, vectors[1:])]
            return sorted(scored, key=lambda pair: -pair[1])[:5]

    return _Provider()