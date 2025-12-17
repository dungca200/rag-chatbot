#!/usr/bin/env python3
"""
Database Tools for AI Agents.

Provides tools for querying and manipulating databases.
Returns real data instead of AI-generated guesses.

Example:
    User: "How much revenue did we make from 2012-2020?"
    Agent uses: db_query("SELECT year, revenue FROM financials WHERE year BETWEEN 2012 AND 2020")
    Returns: Actual database records
"""

import os
from typing import Optional, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Schemas
# ============================================================================

class QueryInput(BaseModel):
    """Input for database query."""
    query: str = Field(description="SQL query to execute (SELECT only)")
    params: Optional[dict] = Field(default=None, description="Query parameters")
    database: str = Field(default="default", description="Database connection name")


class InsertInput(BaseModel):
    """Input for database insert."""
    table: str = Field(description="Table name")
    data: dict = Field(description="Data to insert as key-value pairs")
    database: str = Field(default="default", description="Database connection name")


class UpdateInput(BaseModel):
    """Input for database update."""
    table: str = Field(description="Table name")
    data: dict = Field(description="Data to update as key-value pairs")
    where: dict = Field(description="WHERE conditions as key-value pairs")
    database: str = Field(default="default", description="Database connection name")


class AggregateInput(BaseModel):
    """Input for database aggregation."""
    table: str = Field(description="Table name")
    column: str = Field(description="Column to aggregate")
    operation: str = Field(description="Aggregation: SUM, AVG, COUNT, MIN, MAX")
    where: Optional[dict] = Field(default=None, description="WHERE conditions")
    database: str = Field(default="default", description="Database connection name")


# ============================================================================
# Database Connection Manager
# ============================================================================

class DatabaseManager:
    """Manages database connections."""

    _connections = {}

    @classmethod
    def get_connection(cls, name: str = "default"):
        """Get or create a database connection."""
        if name not in cls._connections:
            # Get connection string from environment
            env_key = f"DATABASE_URL_{name.upper()}" if name != "default" else "DATABASE_URL"
            url = os.environ.get(env_key)

            if not url:
                raise ValueError(f"Database URL not found: {env_key}")

            from sqlalchemy import create_engine
            cls._connections[name] = create_engine(url)

        return cls._connections[name]

    @classmethod
    def close_all(cls):
        """Close all connections."""
        for conn in cls._connections.values():
            conn.dispose()
        cls._connections.clear()


# ============================================================================
# Database Tools
# ============================================================================

@tool(args_schema=QueryInput)
def db_query(query: str, params: dict = None, database: str = "default") -> list[dict]:
    """Execute a SQL SELECT query and return results.

    Use this tool when users ask for specific data from the database.
    Examples:
    - "How much revenue in 2020?" → Query financials table
    - "List all active users" → Query users table
    - "Show orders from last month" → Query orders table

    IMPORTANT: Only SELECT queries are allowed for safety.

    Args:
        query: SQL SELECT query to execute
        params: Optional query parameters for parameterized queries
        database: Database connection name (default: "default")

    Returns:
        List of dictionaries, each representing a row
    """
    # Safety check
    clean_query = query.strip().upper()
    if not clean_query.startswith("SELECT"):
        return {"error": "Only SELECT queries allowed. Use db_insert or db_update for modifications."}

    try:
        from sqlalchemy import text

        engine = DatabaseManager.get_connection(database)

        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            rows = result.fetchall()
            columns = result.keys()

            return [dict(zip(columns, row)) for row in rows]

    except Exception as e:
        return {"error": f"Query failed: {str(e)}"}


@tool(args_schema=InsertInput)
def db_insert(table: str, data: dict, database: str = "default") -> dict:
    """Insert a new record into the database.

    Use this tool when you need to add new data to the database.
    Examples:
    - Creating a new user record
    - Adding a transaction
    - Logging an event

    Args:
        table: Name of the table to insert into
        data: Dictionary of column-value pairs to insert
        database: Database connection name

    Returns:
        Result with inserted ID or error
    """
    if not data:
        return {"error": "No data provided for insert"}

    try:
        from sqlalchemy import text

        engine = DatabaseManager.get_connection(database)

        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"

        with engine.connect() as conn:
            result = conn.execute(text(query), data)
            conn.commit()
            row = result.fetchone()
            return {
                "success": True,
                "inserted_id": row[0] if row else None,
                "table": table
            }

    except Exception as e:
        return {"success": False, "error": f"Insert failed: {str(e)}"}


@tool(args_schema=UpdateInput)
def db_update(table: str, data: dict, where: dict, database: str = "default") -> dict:
    """Update records in the database.

    Use this tool when you need to modify existing data.
    Examples:
    - Updating user profile
    - Changing order status
    - Modifying settings

    Args:
        table: Name of the table to update
        data: Dictionary of column-value pairs to update
        where: Dictionary of conditions (all must match)
        database: Database connection name

    Returns:
        Result with number of rows affected
    """
    if not data:
        return {"error": "No data provided for update"}

    if not where:
        return {"error": "WHERE conditions required for safety"}

    try:
        from sqlalchemy import text

        engine = DatabaseManager.get_connection(database)

        set_clause = ", ".join(f"{k} = :set_{k}" for k in data.keys())
        where_clause = " AND ".join(f"{k} = :where_{k}" for k in where.keys())

        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

        # Prefix parameters to avoid collisions
        params = {f"set_{k}": v for k, v in data.items()}
        params.update({f"where_{k}": v for k, v in where.items()})

        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            conn.commit()
            return {
                "success": True,
                "rows_affected": result.rowcount,
                "table": table
            }

    except Exception as e:
        return {"success": False, "error": f"Update failed: {str(e)}"}


@tool(args_schema=AggregateInput)
def db_aggregate(
    table: str,
    column: str,
    operation: str,
    where: dict = None,
    database: str = "default"
) -> dict:
    """Perform aggregation operations on database columns.

    Use this tool for calculations like totals, averages, counts.
    Examples:
    - "Total revenue for 2023" → SUM on revenue column
    - "Average order value" → AVG on amount column
    - "Number of active users" → COUNT on users

    Args:
        table: Table name
        column: Column to aggregate
        operation: SUM, AVG, COUNT, MIN, or MAX
        where: Optional filter conditions
        database: Database connection name

    Returns:
        Aggregation result
    """
    operation = operation.upper()
    valid_ops = ["SUM", "AVG", "COUNT", "MIN", "MAX"]

    if operation not in valid_ops:
        return {"error": f"Invalid operation. Must be one of: {valid_ops}"}

    try:
        from sqlalchemy import text

        engine = DatabaseManager.get_connection(database)

        query = f"SELECT {operation}({column}) as result FROM {table}"

        params = {}
        if where:
            where_clause = " AND ".join(f"{k} = :{k}" for k in where.keys())
            query += f" WHERE {where_clause}"
            params = where

        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            row = result.fetchone()
            return {
                "success": True,
                "operation": operation,
                "column": column,
                "table": table,
                "result": row[0] if row else None
            }

    except Exception as e:
        return {"success": False, "error": f"Aggregation failed: {str(e)}"}


@tool
def db_table_info(table: str, database: str = "default") -> dict:
    """Get information about a database table.

    Use this tool to understand table structure before querying.

    Args:
        table: Table name to inspect
        database: Database connection name

    Returns:
        Table columns and their types
    """
    try:
        from sqlalchemy import text, inspect

        engine = DatabaseManager.get_connection(database)
        inspector = inspect(engine)

        columns = inspector.get_columns(table)
        pk = inspector.get_pk_constraint(table)

        return {
            "success": True,
            "table": table,
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True)
                }
                for col in columns
            ],
            "primary_key": pk.get("constrained_columns", [])
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to get table info: {str(e)}"}


# ============================================================================
# Convenience Tools
# ============================================================================

@tool
def db_count(table: str, where: dict = None, database: str = "default") -> dict:
    """Count records in a table.

    Use this tool for quick record counts.

    Args:
        table: Table name
        where: Optional filter conditions
        database: Database connection name

    Returns:
        Record count
    """
    return db_aggregate.invoke({
        "table": table,
        "column": "*",
        "operation": "COUNT",
        "where": where,
        "database": database
    })


@tool
def db_exists(table: str, where: dict, database: str = "default") -> dict:
    """Check if a record exists.

    Use this tool to verify record existence before operations.

    Args:
        table: Table name
        where: Conditions to match
        database: Database connection name

    Returns:
        Whether matching record exists
    """
    result = db_count.invoke({
        "table": table,
        "where": where,
        "database": database
    })

    if result.get("success"):
        return {
            "success": True,
            "exists": result.get("result", 0) > 0,
            "count": result.get("result", 0)
        }

    return result


# ============================================================================
# Export all tools
# ============================================================================

DATABASE_TOOLS = [
    db_query,
    db_insert,
    db_update,
    db_aggregate,
    db_table_info,
    db_count,
    db_exists
]
