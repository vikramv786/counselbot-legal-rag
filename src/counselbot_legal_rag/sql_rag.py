
import sqlite3
from pathlib import Path

import re

DATABASE_PATH = Path(
    "veridian_legal_dataset/veridian_legal.db"
)


def get_database_connection() -> sqlite3.Connection:
    """Open the legal SQLite database in read-only mode."""

    database_uri = DATABASE_PATH.resolve().as_uri() + "?mode=ro"

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")

    return connection


def build_matter_filter(user: dict) -> tuple[str, list]:
    """Build a parameterized SQL filter for authorized matters."""

    matters = user.get("matters", [])

    if "*" in matters:
        return "1 = 1", []

    authorized_matters = [
        matter
        for matter in matters
        if isinstance(matter, str) and matter.strip()
    ]

    if not authorized_matters:
        return "matter_id = ?", ["NONE"]

    placeholders = ", ".join(
        "?" for _ in authorized_matters
    )

    condition = (
        f"(matter_id = ? OR matter_id IN ({placeholders}))"
    )

    parameters = ["NONE", *authorized_matters]

    return condition, parameters


def get_authorized_contracts(
    user: dict,
    risk_tier: str | None = None,
    limit: int = 20,
    upcoming_only: bool = False,
) -> list[dict]:
    """Retrieve contracts belonging to authorized matters."""

    condition, parameters = build_matter_filter(user)

    query = f"""
        SELECT
            contract_id,
            counterparty,
            contract_type,
            contract_value_inr_lakh,
            status,
            expiry_date,
            risk_tier,
            matter_id
        FROM contracts_register
        WHERE {condition}
    """

    if risk_tier is not None:
        query += " AND risk_tier = ?"
        parameters.append(risk_tier)

    if upcoming_only:
        query += """
            AND date(expiry_date) >= date('now')
            AND date(expiry_date) <= date('now', '+90 days')
            AND status != 'Expired'
        """

    query += " ORDER BY expiry_date ASC LIMIT ?"

    parameters.append(max(1, min(limit, 100)))

    connection = get_database_connection()

    try:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def count_authorized_contracts(
    user: dict,
    risk_tier: str | None = None,
    upcoming_only: bool = False,
) -> int:
    """Count authorized contracts without a result limit."""

    condition, parameters = build_matter_filter(user)

    query = f"""
        SELECT COUNT(*)
        FROM contracts_register
        WHERE {condition}
    """

    if risk_tier is not None:
        query += " AND risk_tier = ?"
        parameters.append(risk_tier)

    if upcoming_only:
        query += """
            AND date(expiry_date) >= date('now')
            AND date(expiry_date) <= date('now', '+90 days')
            AND status != 'Expired'
        """

    connection = get_database_connection()

    try:
        count = connection.execute(
            query,
            parameters,
        ).fetchone()[0]

        return count

    finally:
        connection.close()


def get_authorized_litigation_cases(
    user: dict,
    status: str | None = None,
    limit: int = 20,
    upcoming_only: bool = False,
) -> list[dict]:
    """Retrieve authorized litigation cases, optionally upcoming only."""

    condition, parameters = build_matter_filter(user)

    query = f"""
        SELECT
            case_id,
            forum,
            case_type,
            counterparty,
            our_role,
            claim_amount_inr_lakh,
            status,
            filing_date,
            next_hearing_date,
            outside_counsel,
            exposure_category,
            matter_id
        FROM litigation_cases
        WHERE {condition}
    """

    if status is not None:
        query += " AND status = ?"
        parameters.append(status)

    if upcoming_only:
        query += """
            AND next_hearing_date IS NOT NULL
            AND date(next_hearing_date) >= date('now')
        """

    query += " ORDER BY next_hearing_date ASC LIMIT ?"

    parameters.append(max(1, min(limit, 100)))

    connection = get_database_connection()

    try:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def count_authorized_litigation_cases(
    user: dict,
    upcoming_only: bool = False,
) -> int:
    """Count authorized litigation cases without a result limit."""

    condition, parameters = build_matter_filter(user)

    query = f"""
        SELECT COUNT(*)
        FROM litigation_cases
        WHERE {condition}
    """

    if upcoming_only:
        query += """
            AND next_hearing_date IS NOT NULL
            AND date(next_hearing_date) >= date('now')
        """

    connection = get_database_connection()

    try:
        count = connection.execute(
            query,
            parameters,
        ).fetchone()[0]

        return count

    finally:
        connection.close()


def classify_sql_question(query: str) -> str | None:
    """Identify whether a question needs contract or litigation data."""

    question = query.lower()


    # Conceptual legal questions belong to document RAG.
    if re.match(
        r"^\s*(what is|what are|define|explain|meaning of|"
        r"what does|how does|why is)\b",
        question,
    ):
        return None


    litigation_keywords = (
        "litigation",
        "lawsuit",
        "court case",
        "hearing",
        "claim amount",
        "legal dispute",
    )

    contract_keywords = (
        "contract",
        "agreement",
        "counterparty",
        "expiry",
        "expiring",
        "renewal",
    )

    if any(
        keyword in question
        for keyword in litigation_keywords
    ):
        return "litigation"

    if any(
        keyword in question
        for keyword in contract_keywords
    ):
        return "contracts"

    return None


def retrieve_sql_context(
    query: str,
    user: dict,
    limit: int = 10,
) -> dict:
    """Route a legal question to authorized SQL retrieval."""

    question_type = classify_sql_question(query)

    if question_type == "contracts":
        question_lower = query.lower()

        expiry_keywords = (
            "expiring",
            "expire soon",
            "expiring soon",
            "upcoming expiry",
            "upcoming expiration",
            "due to expire",
        )

        upcoming_only = any(
            keyword in question_lower
            for keyword in expiry_keywords
        )

        records = get_authorized_contracts(
            user=user,
            limit=limit,
            upcoming_only=upcoming_only,
        )


    elif question_type == "litigation":
        question_lower = query.lower()

        hearing_keywords = (
            "upcoming hearing",
            "upcoming court hearing",
            "next hearing",
            "next court hearing",
            "future hearing",
            "future court hearing",
            "scheduled hearing",
            "scheduled court hearing",
        )

        upcoming_only = any(
            keyword in question_lower
            for keyword in hearing_keywords
        )

        records = get_authorized_litigation_cases(
            user=user,
            limit=limit,
            upcoming_only=upcoming_only,
        )


    else:
        return {
            "source": "documents",
            "records": [],
        }


    return {
        "source": question_type,
        "records": records,
        "upcoming_only": upcoming_only,
    }



def format_sql_context(result: dict) -> str:
    """Format authorized SQL records as numbered sources."""

    source = result["source"]
    records = result["records"]

    if not records:
        return ""

    if source == "contracts":
        table_name = "contracts_register"
        id_field = "contract_id"

    elif source == "litigation":
        table_name = "litigation_cases"
        id_field = "case_id"

    else:
        return ""

    formatted_records = []

    for index, record in enumerate(records, start=1):
        lines = [
            f"[{index}] Source: SQLite/{table_name}",
            f"Record ID: {record[id_field]}",
        ]

        for field, value in record.items():
            if field != id_field:
                lines.append(f"{field}: {value}")

        formatted_records.append(
            "\n".join(lines)
        )

    return "\n\n---\n\n".join(formatted_records)



def validate_sql_answer_completeness(
    answer: str,
    result: dict,
) -> bool:
    """Check that each SQL record appears with its correct citation."""

    records = result["records"]
    source = result["source"]

    if not records:
        return False

    if source == "contracts":
        id_field = "contract_id"
    elif source == "litigation":
        id_field = "case_id"
    else:
        return False

    # Normalize Unicode hyphens.
    normalized_answer = re.sub(
        r"[\u2010-\u2015\u2212]",
        "-",
        answer,
    )

    # Check each record and citation within the same line.
    lines = normalized_answer.splitlines()

    for index, record in enumerate(records, start=1):
        record_id = record[id_field]
        citation = f"[{index}]"

        matching_line_found = any(
            record_id in line and citation in line
            for line in lines
        )

        if not matching_line_found:
            return False

    return True
