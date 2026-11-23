"""Five grounded exact-identifier queries; MRR@5 and hit@5 by source document.

Relevance labels are document-level, chosen by checking the supplied PDFs.
Run against your local Qdrant index. No scores are fabricated.
"""
import csv
from pathlib import Path

from evaluate_retrieval import dense_search
from counselbot_legal_rag.demo_users import get_demo_user
from counselbot_legal_rag.embeddings import get_embedding_model
from counselbot_legal_rag.retrieval import hybrid_search
from counselbot_legal_rag.reranker import get_reranker_model, rerank_results

CASES = [
    ("What does Clause 12.1 say about exceptions to liability?", "Vendor_MSA_Template.pdf"),
    ("What is the registration status of trademark TM-4851122?", "Trademark_and_Brand_Protection_Guide.pdf"),
    ("What is patent IN 512345 and its expiry?", "Patent_and_Invention_Disclosure_Process.pdf"),
    ("What is the Section 12A mediation requirement?", "Court_Filing_and_Limitation_Guide.pdf"),
    ("What does Clause 7 say about confidentiality in the vendor MSA?", "Vendor_MSA_Template.pdf"),
]


def main():
    user = get_demo_user("gc.sharma")
    dense_model = get_embedding_model()
    reranker = get_reranker_model()
    rows = []
    for question, relevant_doc in CASES:
        dense = dense_search(question, user, dense_model, limit=5)
        candidates = hybrid_search(question, user, limit=20)
        methods = {"dense": dense, "hybrid": candidates[:5],
                   "hybrid_reranked": rerank_results(question, candidates, reranker, top_k=5)}
        print("\n", question, "EXPECTED:", relevant_doc)
        for name, results in methods.items():
            docs = [point.payload.get("source_document", "") for point in results]
            rank = next((i for i, doc in enumerate(docs, 1) if doc == relevant_doc), None)
            rows.append({"question": question, "relevant_document": relevant_doc,
                         "method": name, "rank": rank or "", "hit_at_5": int(rank is not None),
                         "reciprocal_rank": round(1 / rank, 4) if rank else 0,
                         "retrieved_documents": " | ".join(docs)})
            print(f"  {name}: rank={rank}, docs={docs}")
    dest = Path("retrieval_exact_identifier_evaluation.csv")
    with dest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for method in ("dense", "hybrid", "hybrid_reranked"):
        subset = [row for row in rows if row["method"] == method]
        print(f"{method}: MRR@5={sum(row['reciprocal_rank'] for row in subset)/len(subset):.3f}, "
              f"Hit@5={sum(row['hit_at_5'] for row in subset)/len(subset):.1%}")
    print("Saved:", dest)


if __name__ == "__main__":
    main()
