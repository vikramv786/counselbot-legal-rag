
from sentence_transformers import CrossEncoder


RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def get_reranker_model():
    """Load the cross-encoder reranking model."""
    return CrossEncoder(RERANKER_MODEL)


def rerank_results(
    query: str,
    results: list,
    model,
    top_k: int = 5,
):
    """Rerank retrieved document chunks using a cross-encoder."""

    if not results:
        return []

    pairs = [
        (query, point.payload["text"])
        for point in results
    ]

    scores = model.predict(pairs)

    ranked_results = sorted(
        zip(results, scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )

    return [
        point
        for point, score in ranked_results[:top_k]
    ]
