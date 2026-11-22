
import json
from pathlib import Path

from uuid import uuid5, NAMESPACE_URL

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

from qdrant_client import models

from counselbot_legal_rag.embeddings import (
    get_embedding_model,
    embed_texts,
    get_sparse_embedding_model,
    embed_sparse_texts,
)

from counselbot_legal_rag.vector_store import (
    get_qdrant_client,
    create_collection,
    COLLECTION_NAME,
)


DATASET_DIR = Path("veridian_legal_dataset")


def main():
    manifest_path = DATASET_DIR / "manifest.json"

    documents = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )


    converter = DocumentConverter()
    chunker = HybridChunker()

    print("Loading dense embedding model...")
    dense_model = get_embedding_model()

    print("Loading sparse BM25 embedding model...")
    sparse_model = get_sparse_embedding_model()


    print("Connecting to Qdrant...")
    client = get_qdrant_client()
    create_collection(client)

    total_chunks = 0

    for document in documents:

        file_path = DATASET_DIR / document["path"]

        print(f"\nProcessing: {document['doc_id']}")
        print(f"File: {file_path.name}")

        result = converter.convert(file_path)

        chunks = list(chunker.chunk(result.document))

        chunk_texts = [
            chunker.contextualize(chunk)
            for chunk in chunks
        ]


        dense_vectors = embed_texts(dense_model, chunk_texts)
        sparse_vectors = embed_sparse_texts(sparse_model, chunk_texts)

        print(f"Dense embeddings created: {len(dense_vectors)}")
        print(f"Sparse embeddings created: {len(sparse_vectors)}")

        points = []

        for chunk_index, chunk in enumerate(chunks):
            chunk_record = {
                "chunk_id": f"{document['doc_id']}-{chunk_index}",
                "doc_id": document["doc_id"],
                "collection": document["collection"],
                "matter_id": document["matter_id"],
                "access_roles": document["access_roles"],
                "source_document": document["source_document"],
                "text": chunk_texts[chunk_index],
            }


            point = models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, chunk_record["chunk_id"])),
                vector={
                    "dense": dense_vectors[chunk_index],
                    "sparse": models.SparseVector(
                        indices=sparse_vectors[chunk_index]["indices"],
                        values=sparse_vectors[chunk_index]["values"],
                    ),
                },
                payload=chunk_record,
            )

            points.append(point)

            # Display one example to verify its metadata
            if document["doc_id"] == "VLH-MTR-017" and chunk_index == 0:
                print("\nExample secured chunk:")
                print(json.dumps(chunk_record, indent=2))
        if points:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
                wait=True,
            )

            print(f"Points uploaded to Qdrant: {len(points)}")

        total_chunks += len(chunks)

        print(f"Chunks created: {len(chunks)}")


    print("\nIngestion completed!")
    print(f"Documents processed: {len(documents)}")
    print(f"Total chunks created: {total_chunks}")


    client.close()
    print("Qdrant connection closed.")

if __name__ == "__main__":
    main()
