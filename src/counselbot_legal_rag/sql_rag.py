"""Read-only LLM-to-SQL over a *physically isolated* authorized SQLite snapshot.

The LLM and its generated SQL never see the original database connection.
Only authorized rows are copied into an in-memory database, so aggregates cannot
include restricted matters even if the generated WHERE clause omits the wall.
"""
import os
import re
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

DATABASE_PATH = Path("veridian_legal_dataset/veridian_legal.db")
TABLES = {"contracts_register", "litigation_cases"}


def get_database_connection():
    uri = DATABASE_PATH.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def build_matter_filter(user: dict) -> tuple[str, list]:
    matters = user.get("matters", [])
    if "*" in matters:
        return "1=1", []
    allowed = [m for m in matters if isinstance(m, str) and m.startswith("MTR-")]
    return "matter_id IN (" + ",".join("?" for _ in ["NONE", *allowed]) + ")", ["NONE", *allowed]


def allowed_tables(role: str) -> list[str]:
    if role == "general_counsel":
        return ["contracts_register", "litigation_cases"]
    if role == "corporate_counsel":
        return ["contracts_register"]
    return []


def scoped_database(allowed_matters: list[str], role: str) -> sqlite3.Connection:
    """Copy only visible rows and role-allowed tables to a private database."""
    tables = allowed_tables(role)
    if not tables:
        raise PermissionError("SQL RAG is not available to this role")
    source = get_database_connection()
    scoped = sqlite3.connect(":memory:")
    scoped.row_factory = sqlite3.Row
    condition, params = build_matter_filter({"matters": allowed_matters})
    try:
        for table in tables:  # fixed allowlist, never an LLM-generated identifier
            columns = source.execute(f"PRAGMA table_info({table})").fetchall()
            definitions = ", ".join(
                '"' + col[1] + '" ' + (col[2] or "TEXT") for col in columns
            )
            scoped.execute(f'CREATE TABLE "{table}" ({definitions})')
            rows = source.execute(f"SELECT * FROM {table} WHERE {condition}", params).fetchall()
            if rows:
                marks = ",".join("?" for _ in columns)
                scoped.executemany(
                    f'INSERT INTO "{table}" VALUES ({marks})',
                    [tuple(row) for row in rows],
                )
        scoped.commit()
        scoped.execute("PRAGMA query_only=ON")
        return scoped
    except Exception:
        scoped.close()
        raise
    finally:
        source.close()


def classify_sql_question(query: str) -> str | None:
    """Route aggregate/register questions to SQL, not document lookup requests.

    This is a routing heuristic, not an authorization mechanism. The caller
    and scoped_database independently enforce the user's role and matters.
    """
    q = re.sub(r"\s+", " ", query.lower()).strip()

    # A request to read or summarize a playbook, clause, policy, memo, etc.
    # is document retrieval even if it contains words like 'show' or 'claim'.
    document_request = re.search(
        r"\b(?:playbook|memo|memorandum|policy|procedure|guide|template|"
        r"clause|section|handbook|due diligence|document|settlement approval "
        r"limits|settlement authority matrix)\b", q
    )
    aggregate_request = re.search(
        r"\b(?:how many|count|number of|total|sum|average|mean|"
        r"highest|lowest|maximum|minimum|aggregate|breakdown|"
        r"how much|total value|total exposure|total claim|"
        r"expir(?:e|es|ed|ing|y)|next quarter|by risk|by status)\b", q
    )
    register_request = re.search(
        r"\b(?:list|show|which)\b.*\b(?:records|rows|entries|"
        r"contracts? (?:in the database|in the register|expir(?:e|ing))|"
        r"cases? (?:in the database|in the register|with hearings))\b", q
    )

    if document_request and not aggregate_request:
        return None
    if not (aggregate_request or register_request):
        return None

    # 'What is the total ...?' is analytical; other definitional questions
    # such as 'What is a claim?' should stay in document RAG.
    if re.match(r"^(?:what is|what are|define|explain|meaning of|what does|how does|why is)\b", q):
        if not aggregate_request:
            return None

    if re.search(
        r"\b(?:litigation|lawsuits?|court cases?|hearings?|claims?|"
        r"arbitration|defendants?|cases?)\b", q
    ):
        return "litigation"
    if re.search(
        r"\b(?:contracts?|agreements?|counterpart(?:y|ies)|renewals?|"
        r"expir(?:y|ies|ing|e|es|ed))\b", q
    ):
        return "contracts"
    return None


def _groq_text(messages: list[dict], tokens: int = 700) -> str:
    load_dotenv()
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    result = Groq(api_key=key).chat.completions.create(
        model="openai/gpt-oss-20b", messages=messages,
        temperature=0, max_completion_tokens=tokens,
    )
    return (result.choices[0].message.content or "").strip()


def clean_select(raw: str) -> str:
    """Allow one SELECT or WITH...SELECT statement, never multi-statements."""
    raw = re.sub(r"^\s*```(?:sql)?\s*|\s*```\s*$", "", raw.strip(), flags=re.I)
    if "--" in raw or "/*" in raw or "*/" in raw:
        raise ValueError("SQL comments are not permitted")
    match = re.search(r"\b(?:SELECT|WITH)\b", raw, re.I)
    if not match:
        raise ValueError("No SELECT found")
    sql = raw[match.start():].strip()
    # Remove only a trailing semicolon; reject embedded statements and comments.
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()
    if ";" in sql or "--" in sql or "/*" in sql or "*/" in sql:
        raise ValueError("Multiple statements or comments are not permitted")
    if not re.match(r"^(?:SELECT|WITH)\b", sql, re.I):
        raise ValueError("Only read-only SELECT is allowed")
    return sql


def _execute_select(conn: sqlite3.Connection, sql: str) -> list[dict]:
    def authorizer(action, arg1, arg2, db_name, trigger):
        return sqlite3.SQLITE_OK if action in (
            sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
            sqlite3.SQLITE_RECURSIVE,
        ) else sqlite3.SQLITE_DENY
    conn.set_authorizer(authorizer)
    try:
        cursor = conn.execute(sql)
        return [dict(row) for row in cursor.fetchmany(101)]
    finally:
        conn.set_authorizer(None)


def sql_rag_chain(question: str, allowed_matters: list[str]) -> str:
    """Assignment-required entry point; SQL role is supplied by trusted caller context.

    The two-argument function defaults to corporate-counsel contract scope;
    the API uses sql_rag_for_user for role-specific table restrictions.
    """
    return sql_rag_for_user(question, {"role": "corporate_counsel", "matters": allowed_matters})


def sql_rag_for_user(question: str, user: dict) -> str:
    kind = classify_sql_question(question)
    if kind is None:
        raise ValueError("Question is not a recognized analytical SQL question")
    table = "contracts_register" if kind == "contracts" else "litigation_cases"
    if table not in allowed_tables(user["role"]):
        raise PermissionError("This role cannot query that SQL collection")
    conn = scoped_database(user["matters"], user["role"])
    try:
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        prompt = (
            "Generate exactly one SQLite SELECT statement (or WITH...SELECT) and nothing else. "
            "You can query ONLY this pre-filtered table; it contains only rows authorized for the user. "
            "Never refer to other tables. Monetary columns are INR lakh (100 lakh = 1 crore). "
            "For relative dates use SQLite date('now'). For next quarter use a three-month window. "
            f"Table: {table}. Columns: {', '.join(columns)}. Question: {question}"
        )
        sql = clean_select(_groq_text([
            {"role": "system", "content": "You generate read-only SQLite SELECT queries only."},
            {"role": "user", "content": prompt},
        ]))
        records = _execute_select(conn, sql)
        if len(records) > 100:
            raise ValueError("Result too large; refine the question")
        return _groq_text([
            {"role": "system", "content": "Answer ONLY from supplied authorized SQL rows. State figures accurately. Monetary amounts are INR lakh unless converted explicitly. Do not invent records. Do not mention inaccessible matters."},
            {"role": "user", "content": f"Question: {question}\nAuthorized SQL result rows: {records!r}\nAnswer clearly and concisely. If zero rows, say no matching authorized records were found."},
        ], tokens=1200)
    finally:
        conn.close()


def count_authorized_contracts(user: dict, **kwargs) -> int:
    conn = scoped_database(user["matters"], "corporate_counsel")
    try:
        return conn.execute("SELECT COUNT(*) FROM contracts_register").fetchone()[0]
    finally:
        conn.close()


def count_authorized_litigation_cases(user: dict, **kwargs) -> int:
    conn = scoped_database(user["matters"], "general_counsel")
    try:
        return conn.execute("SELECT COUNT(*) FROM litigation_cases").fetchone()[0]
    finally:
        conn.close()
