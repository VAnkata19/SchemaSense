"""SQL query execution."""

import sqlite3
import re
import os
from typing import Any, Dict, List, Optional

# Hard block anything that can mutate the DB
FORBIDDEN_SQL = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|truncate|create|replace|grant|revoke|attach|detach|pragma"
    r")\b",
    re.IGNORECASE
)


def _validate_sql(sql: str) -> None:
    """Validate SQL query for safety."""
    sql_clean = sql.strip().lower()

    if not sql_clean:
        raise ValueError("Empty SQL query")

    # Must start with SELECT
    if not sql_clean.startswith("select"):
        raise ValueError("Only SELECT queries are allowed")

    # Block dangerous keywords
    if FORBIDDEN_SQL.search(sql_clean):
        raise ValueError("Forbidden SQL keyword detected")

    # Block multiple statements
    if ";" in sql_clean[:-1]:
        raise ValueError("Multiple SQL statements are not allowed")


def run_sql_query(
    sql: str,
    db_path: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Safely execute a SELECT-only SQL query against SQLite.

    Returns a dict with either:
      - {"rows": [...]} on success
      - {"error": "error message"} on failure
    """

    _validate_sql(sql)

    sql = sql.strip().rstrip(";")

    # Enforce LIMIT if missing
    if " limit " not in f" {sql.lower()} ":
        sql = f"{sql} LIMIT {limit}"

    # Use absolute path to avoid relative path issues with Streamlit reruns
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "northwind.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        return {"rows": [dict(row) for row in rows]}

    except sqlite3.Error as e:
        # Return the SQLite error message instead of raising so UI can display it
        return {"error": str(e)}

    finally:
        conn.close()
