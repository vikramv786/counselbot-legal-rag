"""Role-aware, matter-aware document RAG and scoped SQL RAG routing."""
import re

from counselbot_legal_rag.retrieval import ROLE_COLLECTIONS, hybrid_search
from counselbot_legal_rag.reranker import get_reranker_model, rerank_results
from counselbot_legal_rag.answer_generator import generate_legal_answer, validate_citations
from counselbot_legal_rag.sql_rag import classify_sql_question, sql_rag_for_user

MATTER_ALIASES = {
    "project falcon": "MTR-017",
    "project harbor": "MTR-023",
    "meridian arbitration": "MTR-031",
    "novagen patent dispute": "MTR-044",
}
NEUTRAL = "I couldn't find anything relevant in the documents or records you are authorised to access."
COLLECTION_WORDS = {
    "litigation": ("litigation", "settlement approval", "settlement authority", "court filing", "arbitration", "lawsuit"),
    "compliance": ("insider trading", "anti-bribery", "data protection", "compliance policy", "internal investigation"),
    "contracts": ("contract review", "contract negotiation", "vendor msa", "contract approval", "contract playbook"),
    "ip": ("patent", "trademark", "intellectual property"),
}


def retrieve_legal_context(query: str, user: dict, top_k: int = 5):
    candidates = hybrid_search(query=query, user=user, limit=20)
    if not candidates:
        return []
    return rerank_results(query=query, results=candidates, model=get_reranker_model(), top_k=top_k)


def format_context_with_citations(results: list) -> str:
    return "\n\n---\n\n".join(
        f"[{i}] Source: {point.payload['source_document']}\n"
        f"Section: {point.payload['section_title']}\n"
        f"Content:\n{point.payload['text']}"
        for i, point in enumerate(results, 1)
    )


def format_rag_response(answer, retrieval_type, sources, access_status, return_metadata):
    result = {"answer": answer, "sources": sources, "retrieval_type": retrieval_type,
              "access_status": access_status}
    return result if return_metadata else answer


def _matter_blocked(query: str, user: dict) -> bool:
    if "*" in user["matters"]:
        return False
    requested = {m.upper() for m in re.findall(r"\bMTR-\d+\b", query, re.I)}
    requested |= {matter for alias, matter in MATTER_ALIASES.items() if alias in query.lower()}
    return bool(requested - set(user["matters"]))


def _role_blocked(query: str, user: dict) -> str | None:
    allowed = ROLE_COLLECTIONS[user["role"]]
    q = query.lower()
    for collection, phrases in COLLECTION_WORDS.items():
        if collection not in allowed and any(p in q for p in phrases):
            return collection
    return None


def answer_legal_question(query: str, user: dict, top_k: int = 5,
                          return_metadata: bool = False) -> str | dict:
    sql_kind = classify_sql_question(query)
    retrieval_type = "sql_rag" if sql_kind else "hybrid_rag"
    role = user["role"]
    allowed = ROLE_COLLECTIONS[role]

    # The user's role is never read from the question or client request.
    if sql_kind and (role not in ("general_counsel", "corporate_counsel") or
                     (sql_kind == "litigation" and role != "general_counsel")):
        return format_rag_response(
            f"As a {role.replace('_', ' ')}, you cannot access {sql_kind} SQL records. "
            f"Your permitted document collections are: {', '.join(allowed)}.",
            retrieval_type, [], "role_restricted", return_metadata)

    forbidden_collection = _role_blocked(query, user)
    if forbidden_collection:
        return format_rag_response(
            f"As a {role.replace('_', ' ')}, you cannot access {forbidden_collection} documents. "
            f"Your permitted collections are: {', '.join(allowed)}.",
            retrieval_type, [], "role_restricted", return_metadata)

    # Matter refusals are indistinguishable from nonexistent documents.
    if _matter_blocked(query, user):
        return format_rag_response(NEUTRAL, retrieval_type, [], "no_accessible_results", return_metadata)

    if sql_kind:
        try:
            answer = sql_rag_for_user(query, user)
        except PermissionError:
            return format_rag_response(
                f"As a {role.replace('_', ' ')}, SQL access is restricted. "
                f"Your permitted collections are: {', '.join(allowed)}.",
                "sql_rag", [], "role_restricted", return_metadata)
        return format_rag_response(answer, "sql_rag", [], "ok", return_metadata)

    results = retrieve_legal_context(query, user, top_k)
    if not results:
        return format_rag_response(NEUTRAL, "hybrid_rag", [], "no_accessible_results", return_metadata)

    answer = generate_legal_answer(query, format_context_with_citations(results))
    if not validate_citations(answer, len(results)):
        return format_rag_response("I couldn't generate a supported answer with valid citations.",
                                   "hybrid_rag", [], "no_accessible_results", return_metadata)
    citations = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    sources = [{"citation": f"[{i}]", "source_document": p.payload["source_document"],
                "section_title": p.payload["section_title"], "collection": p.payload["collection"]}
               for i, p in enumerate(results, 1) if i in citations]
    return format_rag_response(answer, "hybrid_rag", sources, "ok", return_metadata)
