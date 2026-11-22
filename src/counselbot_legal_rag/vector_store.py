
from pathlib import Path

from qdrant_client import QdrantClient, models


QDRANT_PATH = Path("data/qdrant")


def get_qdrant_client():
    """Create or open a persistent local Qdrant database."""

    QDRANT_PATH.mkdir(parents=True, exist_ok=True)

    client = QdrantClient(path=str(QDRANT_PATH))

    return client


COLLECTION_NAME = "legal_documents"


def create_collection(client):
    """Create the hybrid-search collection if it does not exist."""

    if client.collection_exists(COLLECTION_NAME):
        print("Collection already exists:", COLLECTION_NAME)
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": models.VectorParams(
                size=384,
                distance=models.Distance.COSINE,
            )
        },

        sparse_vectors_config={
            "sparse": models.SparseVectorParams(
                modifier=models.Modifier.IDF,
            )
        },

    )

    print("Collection created:", COLLECTION_NAME)


if __name__ == "__main__":
    client = get_qdrant_client()


    try:
        print("Persistent Qdrant database initialized!")
        print("Storage location:", QDRANT_PATH)

        create_collection(client)

        print("Existing collections:", client.get_collections())

    finally:
        client.close()
