"""scikit-learn backends: classical ML, clustering, baselines, validation.

Topics (sklearn_nmf, sklearn_kmeans): descriptive baselines comparable to
BERTopic/gensim/LLM methods. TF-IDF + classifier: the classical baseline
LLM-assisted analysis must be validated against (paper §4.2 robustness).
Clustering produces candidate groups, never ideological formations.
"""
from __future__ import annotations

from typing import Any, Iterable

from laclaugpt.analysis import (BackendUnavailable, ClassificationResult,
                                TopicModelResult)
from laclaugpt.model import Provenance, Topic, TopicAssignment

_BACKEND = "sklearn"


def is_available() -> bool:
    try:
        import sklearn  # noqa: F401
        return True
    except ImportError:
        return False


def _version() -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version("scikit-learn")
    except Exception:
        return ""


# ── topic baselines ──────────────────────────────────────────────────

def discover(documents: Iterable[str], *, model: str | None = None,
             timestamps: list[str] | None = None,
             provenance: Provenance | None = None) -> TopicModelResult:
    """sklearn_nmf (TF-IDF + NMF) or sklearn_kmeans (TF-IDF + KMeans)."""
    if not is_available():
        raise BackendUnavailable("scikit-learn is not installed")
    docs = [d for d in documents if d and d.strip()]
    method = (model or "sklearn_nmf").casefold()
    provenance_id = provenance.provenance_id if provenance else ""
    result = TopicModelResult(
        method=method, provenance_id=provenance_id,
        model_info={"library": "scikit-learn", "library_version": _version(),
                    "n_documents": len(docs)},
    )
    if not docs:
        return result
    from sklearn.feature_extraction.text import TfidfVectorizer
    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english",
                                 min_df=2, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(docs)
    feature_names = vectorizer.get_feature_names_out()

    if method == "sklearn_nmf":
        from sklearn.decomposition import NMF
        trained = NMF(n_components=8, random_state=42, init="nndsvda")
        weights = trained.fit_transform(matrix)
        components = trained.components_
    elif method == "sklearn_kmeans":
        from sklearn.cluster import KMeans
        from sklearn.decomposition import TruncatedSVD
        reduced = TruncatedSVD(n_components=min(50, matrix.shape[1] - 1 or 1),
                               random_state=42).fit_transform(matrix)
        trained = KMeans(n_clusters=8, random_state=42, n_init=10)
        weights = trained.fit_predict(reduced)
        import numpy as np
        order = np.argsort(trained.cluster_centers_, axis=1)[:, ::-1]
        components = np.zeros((trained.n_clusters, len(feature_names)))
        for cluster in range(trained.n_clusters):
            components[cluster, order[cluster][:8]] = 1.0
    else:
        raise ValueError(f"unknown sklearn topic method: {method}")

    for topic_id, component in enumerate(components):
        top = component.argsort()[::-1][:8]
        keywords = [feature_names[i] for i in top if component[i] > 0][:8]
        if not keywords:
            continue
        result.topics.append(Topic(
            topic_id=f"{method}_{topic_id}",
            canonical_label=", ".join(keywords[:4]),
            aliases=keywords,
            description=f"{method} topic {topic_id}: {', '.join(keywords[:5])}",
            metadata={"method": method, "sklearn_version": _version(),
                      "provenance_id": provenance_id},
        ))
        membership_column = topic_id
        for doc_index in range(len(docs)):
            if method == "sklearn_nmf":
                score = float(weights[doc_index][membership_column])
                if score < 0.05:
                    continue
            else:
                if int(weights[doc_index]) != topic_id:
                    continue
                score = None
            result.assignments.append(TopicAssignment(
                target_id=f"document_{doc_index}",
                topic_id=f"{method}_{topic_id}", score=score, confidence=None,
                provenance_id=provenance_id, review_status="model_proposed"))
    return result


# ── classification baselines ─────────────────────────────────────────

def tfidf_baseline(train_texts: list[str], train_labels: list[str],
                   test_texts: list[str], *,
                   classifier: str = "logreg") -> dict[str, Any]:
    """TF-IDF + classical classifier. Returns predictions, metrics and the
    confusion matrix — the cheap baseline LLM analysis must beat or justify
    itself against (paper §4.2 robustness checks)."""
    if not is_available():
        raise BackendUnavailable("scikit-learn is not installed")
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (confusion_matrix, f1_score,
                                 precision_recall_fscore_support)
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.svm import LinearSVC
    classifiers = {
        "logreg": LogisticRegression(max_iter=1000),
        "naive_bayes": MultinomialNB(),
        "linear_svc": LinearSVC(),
    }
    if classifier not in classifiers:
        raise ValueError(f"unknown classifier: {classifier}")
    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    features = vectorizer.fit_transform(train_texts)
    trained = classifiers[classifier].fit(features, train_labels)
    predictions = trained.predict(vectorizer.transform(test_texts))
    precision, recall, f1, _ = precision_recall_fscore_support(
        train_labels, predictions, average="weighted", zero_division=0)
    return {
        "classifier": classifier, "sklearn_version": _version(),
        "predictions": [str(p) for p in predictions],
        "precision": float(precision), "recall": float(recall),
        "f1": float(f1_score(train_labels, predictions, average="weighted",
                             zero_division=0)),
        "precision_recall_fscore": [float(precision), float(recall), float(f1)],
        "confusion_matrix": confusion_matrix(train_labels, predictions).tolist(),
    }