
from qdrant_client import models

from counselbot_legal_rag.vector_store import (
    get_qdrant_client,
    COLLECTION_NAME,
)

from counselbot_legal_rag.embeddings import (
    get_embedding_model,
    embed_texts,
    get_sparse_embedding_model,
    embed_sparse_texts,
)


def build_access_filter(user: dict) -> models.Filter:
    """Restrict search to documents the user is allowed to access."""

    role_condition = models.FieldCondition(
        key="access_roles",
        match=models.MatchValue(value=user["role"]),
    )

    if "*" in user["matters"]:
        return models.Filter(
            must=[role_condition],
        )

    matter_conditions = [
        models.FieldCondition(
            key="matter_id",
            match=models.MatchValue(value="NONE"),
        )
    ]

    for matter_id in user["matters"]:
        matter_conditions.append(
            models.FieldCondition(
                key="matter_id",
                match=models.MatchValue(value=matter_id),
            )
        )

    return models.Filter(
        must=[
            role_condition,
            models.Filter(
                min_should=models.MinShould(
                    conditions=matter_conditions,
                    min_count=1,
                ),
            ),
        ],
    )


def hybrid_search(
    query: str,
    user: dict,
    limit: int = 5,
):
    """Search legal documents using dense and BM25 retrieval."""

    dense_model = get_embedding_model()
    sparse_model = get_sparse_embedding_model()

    dense_vector = embed_texts(dense_model, [query])[0]
    sparse_vector = embed_sparse_texts(sparse_model, [query])[0]

    access_filter = build_access_filter(user)


    client = get_qdrant_client()

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    filter=access_filter,
                    limit=20,
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_vector["indices"],
                        values=sparse_vector["values"],
                    ),
                    using="sparse",
                    filter=access_filter,
                    limit=20,
                ),
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF,
            ),
            query_filter=access_filter,
            limit=limit,
            with_payload=True,
        )

        return results.points

    finally:
        client.close()
