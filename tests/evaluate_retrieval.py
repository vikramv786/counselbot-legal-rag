
"""Compare dense, hybrid, and reranked retrieval for five legal questions."""

import csv
import sys
import time
from pathlib import Path

from qdrant_client import models

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from counselbot_legal_rag.demo_users import get_demo_user
from counselbot_legal_rag.embeddings import (
    get_embedding_model,
    embed_texts,
)
from counselbot_legal_rag.retrieval import (
    build_access_filter,
    hybrid_search,
)
from counselbot_legal_rag.reranker import (
    get_reranker_model,
    rerank_results,
)
from counselbot_legal_rag.vector_store import (
    COLLECTION_NAME,
    get_qdrant_client,
)


QUESTIONS = [
    "What is a non-disclosure agreement?",
    "What are the standard exclusions from confidentiality?",
    "What obligations apply to vendor confidentiality?",
    "What are the key intellectual property ownership provisions?",
    "What happens when a contract is terminated?",
]

USERNAME = "gc.sharma"
TOP_K = 5
HYBRID_CANDIDATES = 20

OUTPUT_FILE = PROJECT_ROOT / "retrieval_evaluation.csv"


def dense_search(query, user, model, limit=TOP_K):
    """Search dense vectors with the same access filter as hybrid search."""

    dense_vector = embed_texts(model, [query])[0]
    access_filter = build_access_filter(user)

    client = get_qdrant_client()

    try:
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=dense_vector,
            using="dense",
            query_filter=access_filter,
            limit=limit,
            with_payload=True,
        )
        return response.points

    finally:
        client.close()


def describe_result(point):
    """Extract readable metadata from a Qdrant result."""

    payload = point.payload or {}

    return {
        "document": payload.get("source_document", ""),
        "section": payload.get("section_title", ""),
        "matter": payload.get("matter_id", ""),
        "collection": payload.get("collection", ""),
        "chunk_id": str(
            payload.get("doc_id", "")
        ),
        "score": (
            round(float(point.score), 6)
            if point.score is not None
            else ""
        ),
    }


def run_evaluation():
    user = get_demo_user(USERNAME)

    if user is None:
        raise ValueError(f"Unknown evaluation user: {USERNAME}")

    print(f"Evaluation user: {USERNAME}")
    print(f"Role: {user['role']}")
    print(f"Questions: {len(QUESTIONS)}")
    print()

    dense_model = get_embedding_model()
    reranker_model = get_reranker_model()

    rows = []

    for question_number, question in enumerate(
        QUESTIONS,
        start=1,
    ):
        print(f"Question {question_number}: {question}")

        start = time.perf_counter()
        dense_results = dense_search(
            question,
            user,
            dense_model,
            limit=TOP_K,
        )
        dense_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        start = time.perf_counter()
        hybrid_candidates = hybrid_search(
            query=question,
            user=user,
            limit=HYBRID_CANDIDATES,
        )
        hybrid_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        hybrid_results = hybrid_candidates[:TOP_K]

        start = time.perf_counter()
        reranked_results = rerank_results(
            query=question,
            results=hybrid_candidates,
            model=reranker_model,
            top_k=TOP_K,
        )
        rerank_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        methods = [
            ("dense", dense_results, dense_ms),
            ("hybrid", hybrid_results, hybrid_ms),
            (
                "hybrid_reranked",
                reranked_results,
                hybrid_ms + rerank_ms,
            ),
        ]

        for method, results, elapsed_ms in methods:
            print(
                f"  {method}: "
                f"{len(results)} results, "
                f"{elapsed_ms} ms"
            )

            for rank, point in enumerate(
                results,
                start=1,
            ):
                info = describe_result(point)

                rows.append(
                    {
                        "question_number": question_number,
                        "question": question,
                        "username": USERNAME,
                        "method": method,
                        "rank": rank,
                        "document": info["document"],
                        "section": info["section"],
                        "matter": info["matter"],
                        "collection": info["collection"],
                        "chunk_id": info["chunk_id"],
                        "retrieval_score": info["score"],
                        "elapsed_ms": elapsed_ms,
                    }
                )

                print(
                    f"    [{rank}] "
                    f"{info['document']} | "
                    f"{info['section']}"
                )

        print()

    fieldnames = [
        "question_number",
        "question",
        "username",
        "method",
        "rank",
        "document",
        "section",
        "matter",
        "collection",
        "chunk_id",
        "retrieval_score",
        "elapsed_ms",
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output:
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)

    print("=" * 60)
    print("EVALUATION COMPLETE")
    print(f"Questions evaluated: {len(QUESTIONS)}")
    print("Methods compared: dense, hybrid, hybrid_reranked")
    print(f"Rows saved: {len(rows)}")
    print(f"CSV file: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    run_evaluation()
