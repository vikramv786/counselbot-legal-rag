
from sentence_transformers import SentenceTransformer

from fastembed import SparseTextEmbedding

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_embedding_model():
    """Load the dense embedding model."""
    return SentenceTransformer(MODEL_NAME)


def embed_texts(model, texts):
    """Convert a list of text strings into dense vectors."""
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
    )

    return embeddings.tolist()


def get_sparse_embedding_model():
    """Load the BM25 sparse embedding model."""
    return SparseTextEmbedding(model_name="Qdrant/bm25")


def embed_sparse_texts(model, texts):
    """Convert text strings into sparse token indices and weights."""
    embeddings = list(model.embed(texts))

    return [
        {
            "indices": embedding.indices.tolist(),
            "values": embedding.values.tolist(),
        }
        for embedding in embeddings
    ]
