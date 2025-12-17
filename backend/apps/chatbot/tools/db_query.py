import logging
from typing import Dict, List, Any

from django.db import connection

logger = logging.getLogger(__name__)

# Allowed read-only SQL keywords
ALLOWED_KEYWORDS = ['SELECT', 'WITH']
FORBIDDEN_KEYWORDS = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE']


def is_safe_query(sql: str) -> bool:
    """Check if SQL query is read-only and safe to execute."""
    sql_upper = sql.strip().upper()

    # Must start with allowed keyword
    if not any(sql_upper.startswith(kw) for kw in ALLOWED_KEYWORDS):
        return False

    # Must not contain forbidden keywords
    for kw in FORBIDDEN_KEYWORDS:
        if kw in sql_upper:
            return False

    return True


def execute_read_query(
    sql: str,
    params: List[Any] = None,
    max_rows: int = 100
) -> Dict:
    """
    Execute a read-only SQL query.

    Args:
        sql: SQL query (must be SELECT or WITH)
        params: Query parameters
        max_rows: Maximum rows to return

    Returns:
        Dict with results, columns, and status
    """
    if not sql or not sql.strip():
        return {
            "success": False,
            "error": "Empty query",
            "results": [],
            "columns": []
        }

    if not is_safe_query(sql):
        return {
            "success": False,
            "error": "Only SELECT queries are allowed",
            "results": [],
            "columns": []
        }

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or [])

            # Get column names
            columns = [col[0] for col in cursor.description] if cursor.description else []

            # Fetch results with limit
            results = cursor.fetchmany(max_rows)

            # Convert to list of dicts
            rows = [dict(zip(columns, row)) for row in results]

            logger.info(f"Query returned {len(rows)} rows")

            return {
                "success": True,
                "columns": columns,
                "results": rows,
                "row_count": len(rows),
                "truncated": len(rows) >= max_rows
            }

    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "columns": []
        }


def get_table_info(table_name: str) -> Dict:
    """
    Get information about a database table.

    Args:
        table_name: Name of the table

    Returns:
        Dict with column info and status
    """
    # Sanitize table name (only allow alphanumeric and underscore)
    if not table_name.replace('_', '').isalnum():
        return {
            "success": False,
            "error": "Invalid table name",
            "columns": []
        }

    try:
        with connection.cursor() as cursor:
            # Get column information
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, [table_name])

            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == 'YES'
                })

            return {
                "success": True,
                "table_name": table_name,
                "columns": columns
            }

    except Exception as e:
        logger.error(f"Failed to get table info: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "columns": []
        }
