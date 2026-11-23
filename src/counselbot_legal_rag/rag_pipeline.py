
"""Authorized SQL and hybrid document retrieval for CounselBot Legal RAG."""

import re

from counselbot_legal_rag.retrieval import hybrid_search
from counselbot_legal_rag.answer_generator import (
    generate_legal_answer,
    validate_citations,
)
from counselbot_legal_rag.reranker import get_reranker_model, rerank_results
from counselbot_legal_rag.sql_rag import (
    retrieve_sql_context,
    format_sql_context,
    validate_sql_answer_completeness,
    count_authorized_litigation_cases,
    count_authorized_contracts,
)


def retrieve_legal_context(query: str, user: dict, top_k: int = 5):
    """Retrieve and rerank chunks using the user's access restrictions."""
    results = hybrid_search(query=query, user=user, limit=20)
    reranker_model = get_reranker_model()
    return rerank_results(
        query=query,
        results=results,
        model=reranker_model,
        top_k=top_k,
    )


def format_context_with_citations(results: list) -> str:
    """Give each retrieved document chunk a stable citation number."""
    formatted_chunks = []

    for index, point in enumerate(results, start=1):
        payload = point.payload
        formatted_chunks.append(
            f"[{index}] Source: {payload['source_document']}\n"
            f"Document ID: {payload['doc_id']}\n"
            f"Matter ID: {payload['matter_id']}\n"
            f"Content:\n{payload['text']}"
        )

    return "\n\n---\n\n".join(formatted_chunks)


def is_simple_count_question(query: str) -> bool:
    """Recognize straightforward record-count questions."""
    normalized = query.strip().lower()

    count_patterns = [
        r"\bhow many\b",
        r"\bnumber of\b",
        r"\bcount of\b",
        r"\btotal number of\b",
    ]

    return any(
        re.search(pattern, normalized)
        for pattern in count_patterns
    )


def get_retrieval_type(query: str) -> str:
    """Report the route chosen by the existing SQL classifier."""
    from counselbot_legal_rag.sql_rag import classify_sql_question

    return (
        "sql_rag"
        if classify_sql_question(query) in ("contracts", "litigation")
        else "hybrid_rag"
    )


def format_rag_response(
    answer: str,
    retrieval_type: str,
    sources: list,
    access_status: str,
    return_metadata: bool,
) -> str | dict:
    """Preserve string responses unless the caller requests metadata."""
    if not return_metadata:
        return answer

    return {
        "answer": answer,
        "sources": sources,
        "retrieval_type": retrieval_type,
        "access_status": access_status,
    }


def _cited_numbers(answer: str) -> set[int]:
    """Extract exact numbered citations."""
    return {
        int(value)
        for value in re.findall(r"\[(\d+)\]", answer)
    }


def _document_sources(results: list, answer: str) -> list[dict]:
    """Return metadata for cited authorized document chunks."""
    cited = _cited_numbers(answer)

    return [
        {
            "citation": f"[{index}]",
            "source_document": point.payload.get(
                "source_document", ""
            ),
            "section_title": point.payload.get(
                "section_title", ""
            ),
            "collection": point.payload.get(
                "collection", ""
            ),
        }
        for index, point in enumerate(results, start=1)
        if index in cited
    ]


def _sql_sources(
    records: list,
    source: str,
    answer: str,
) -> list[dict]:
    """Describe only cited, authorized SQL records."""
    cited = _cited_numbers(answer)
    sources = []

    for index, record in enumerate(records, start=1):
        if index not in cited:
            continue

        record_id = next(
            (
                str(record[key])
                for key in (
                    "contract_id",
                    "case_id",
                    "litigation_id",
                    "id",
                )
                if record.get(key) is not None
            ),
            f"record {index}",
        )

        sources.append(
            {
                "citation": f"[{index}]",
                "source_document": (
                    f"SQL {source}: {record_id}"
                ),
                "section_title": "Database record",
                "collection": source,
            }
        )

    return sources


def answer_legal_question(
    query: str,
    user: dict,
    top_k: int = 5,
    return_metadata: bool = False,
) -> str | dict:
    """Answer using authorized SQL records or legal documents."""

    # ---------------------------------------------------------
    # SECURITY: Explicit matter-access check
    # ---------------------------------------------------------
    # Reject requests mentioning matters outside the user's
    # assigned permissions before accessing SQL, Qdrant, or Groq.

    requested_matters = {
        matter.upper()
        for matter in re.findall(
            r"\bMTR-\d+\b",
            query,
            flags=re.IGNORECASE,
        )
    }

    authorized_matters = {
        matter.upper()
        for matter in user["matters"]
    }

    if "*" not in authorized_matters:
        unauthorized_matters = (
            requested_matters - authorized_matters
        )

        if unauthorized_matters:
            return format_rag_response(
                "I cannot provide information for the requested "
                "matter under your current access permissions.",
                "hybrid_rag",
                [],
                "role_restricted",
                return_metadata,
            )

    # ---------------------------------------------------------
    # SQL RAG
    # ---------------------------------------------------------

    sql_result = retrieve_sql_context(
        query=query,
        user=user,
        limit=20,
    )

    if sql_result["source"] != "documents":
        records = sql_result["records"]
        source = sql_result["source"]
        upcoming_only = sql_result.get(
            "upcoming_only", False
        )

        if is_simple_count_question(query):
            if source == "contracts":
                total_count = count_authorized_contracts(
                    user=user,
                    upcoming_only=upcoming_only,
                )

                answer = (
                    f"**Authorized contract count: {total_count}**\n\n"
                    "This count includes only contracts accessible "
                    "to the selected demo user under the configured "
                    "matter-access rules."
                )

                return format_rag_response(
                    answer,
                    "sql_rag",
                    [],
                    "ok",
                    return_metadata,
                )

            if source == "litigation":
                total_count = count_authorized_litigation_cases(
                    user=user,
                    upcoming_only=upcoming_only,
                )

                answer = (
                    f"**Authorized litigation case count: "
                    f"{total_count}**\n\n"
                    "This count includes only litigation cases "
                    "accessible to the selected demo user under "
                    "the configured matter-access rules."
                )

                return format_rag_response(
                    answer,
                    "sql_rag",
                    [],
                    "ok",
                    return_metadata,
                )

        if not records:
            return format_rag_response(
                "I could not find any authorized SQL records "
                "matching this question.",
                "sql_rag",
                [],
                "no_accessible_results",
                return_metadata,
            )

        context = format_sql_context(sql_result)

        sql_question = (
            f"{query}\n\n"
            "IMPORTANT: For contract expiry questions, "
            "'expiring soon' means within the next 90 days, "
            "not just the next month.\n"
            "The SQL records supplied below have already been "
            "filtered to match the requested criteria. "
            "Do not narrow the date range further.\n\n"
            "Instructions for structured database results:\n"
            "- Include every retrieved matching record in the answer.\n"
            "- Present records in a clear Markdown table.\n"
            "- Include the record ID and relevant dates.\n"
            "- Add a numbered citation such as [1] or [2] "
            "to each record.\n"
            "- Use only the supplied SQL records.\n"
            "- Do not invent missing information.\n"
        )

        answer = generate_legal_answer(
            query=sql_question,
            context=context,
        )

        if not validate_citations(
            answer,
            source_count=len(records),
        ):
            return format_rag_response(
                "I could not generate an answer with valid "
                "source citations. Please try again.",
                "sql_rag",
                [],
                "ok",
                return_metadata,
            )

        if not validate_sql_answer_completeness(
            answer=answer,
            result=sql_result,
        ):
            return format_rag_response(
                "I could not generate a complete SQL answer "
                "with all retrieved records and citations. "
                "Please try again.",
                "sql_rag",
                [],
                "ok",
                return_metadata,
            )

        if source == "litigation":
            total_count = count_authorized_litigation_cases(
                user=user,
                upcoming_only=upcoming_only,
            )
            record_type = "litigation"
        else:
            total_count = count_authorized_contracts(
                user=user,
                upcoming_only=upcoming_only,
            )
            record_type = "contract"

        if total_count > len(records):
            remaining = total_count - len(records)

            answer += (
                f"\n\n**Note:** Showing {len(records)} of "
                f"{total_count} authorized {record_type} records. "
                f"{remaining} additional records are available."
            )

        return format_rag_response(
            answer,
            "sql_rag",
            _sql_sources(records, source, answer),
            "ok",
            return_metadata,
        )

    # ---------------------------------------------------------
    # HYBRID RAG
    # ---------------------------------------------------------

    results = retrieve_legal_context(
        query=query,
        user=user,
        top_k=top_k,
    )

    if not results:
        return format_rag_response(
            "I could not find any authorized legal documents "
            "to answer this question.",
            "hybrid_rag",
            [],
            "no_accessible_results",
            return_metadata,
        )

    context = format_context_with_citations(results)

    answer = generate_legal_answer(
        query=query,
        context=context,
    )

    if not validate_citations(
        answer,
        source_count=len(results),
    ):
        return format_rag_response(
            "I could not generate an answer with valid "
            "source citations. Please try again.",
            "hybrid_rag",
            [],
            "ok",
            return_metadata,
        )

    return format_rag_response(
        answer,
        "hybrid_rag",
        _document_sources(results, answer),
        "ok",
        return_metadata,
    )
