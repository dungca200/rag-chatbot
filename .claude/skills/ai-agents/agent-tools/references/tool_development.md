# Tool Development Guide

## Overview

Tools are functions that agents use to perform deterministic operations. Unlike AI-generated responses, tools return real data from databases, APIs, and calculations.

## Tool Anatomy

### Basic Structure

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    """Input schema for my_tool."""
    param1: str = Field(description="Description for LLM")
    param2: int = Field(default=10, description="Optional with default")

@tool(args_schema=MyToolInput)
def my_tool(param1: str, param2: int = 10) -> dict:
    """Short description of what the tool does.

    Use this tool when [specific use case].
    Examples: [2-3 examples of when to use]

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value
    """
    # Implementation
    return {"success": True, "data": result}
```

### Key Components

1. **Pydantic Schema**: Type validation and descriptions for LLM
2. **@tool Decorator**: Converts function to LangChain tool
3. **Docstring**: Critical for LLM to understand when to use
4. **Return Type**: Consistent structure (usually dict with success field)

## Docstring Best Practices

The docstring is how the LLM decides whether to use your tool.

### Good Docstring

```python
@tool
def db_query(query: str) -> list[dict]:
    """Execute a SQL SELECT query and return results.

    Use this tool when users ask for specific data from the database.
    Examples:
    - "How much revenue in 2020?" → Query financials table
    - "List all active users" → Query users table
    - "Show orders from last month" → Query orders table

    IMPORTANT: Only SELECT queries are allowed for safety.

    Args:
        query: SQL SELECT query to execute

    Returns:
        List of dictionaries, each representing a row
    """
```

### Bad Docstring

```python
@tool
def db_query(query: str) -> list[dict]:
    """Query the database."""  # Too vague - LLM won't know when to use
```

## Pydantic Schemas

### Field Descriptions

```python
class SearchInput(BaseModel):
    """Input for search operations."""
    query: str = Field(
        description="Search query - can include keywords or phrases"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum results to return (1-100)"
    )
    include_metadata: bool = Field(
        default=False,
        description="Whether to include document metadata in results"
    )
```

### Complex Types

```python
class FilterInput(BaseModel):
    """Input with complex filters."""
    filters: dict = Field(
        default_factory=dict,
        description="Filter conditions as key-value pairs"
    )
    date_range: Optional[tuple[str, str]] = Field(
        default=None,
        description="Start and end dates as tuple"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags to filter by"
    )
```

## Return Value Patterns

### Standard Response

```python
@tool
def my_tool(param: str) -> dict:
    """Tool description."""
    try:
        result = perform_operation(param)
        return {
            "success": True,
            "data": result,
            "count": len(result) if isinstance(result, list) else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

### List Results

```python
@tool
def search_tool(query: str) -> dict:
    """Search tool."""
    results = perform_search(query)
    return {
        "success": True,
        "query": query,
        "results": results,
        "count": len(results),
        "truncated": len(results) >= MAX_RESULTS
    }
```

### Operation Results

```python
@tool
def action_tool(action: str) -> dict:
    """Action tool."""
    if action not in VALID_ACTIONS:
        return {"success": False, "error": f"Invalid action: {action}"}

    result = execute_action(action)
    return {
        "success": True,
        "action": action,
        "result": result,
        "message": f"Successfully executed {action}"
    }
```

## When to Use Tools vs Agent Reasoning

### Use Tools For

- **Factual Data**: Database queries, API calls
- **Calculations**: Math, statistics, conversions
- **External Systems**: File operations, HTTP requests
- **Deterministic Operations**: ID generation, validation
- **Current Information**: Time, weather, prices

### Use Agent Reasoning For

- **Interpretation**: Understanding context
- **Decision Making**: Choosing which tool to use
- **Synthesis**: Combining tool results
- **Explanation**: Describing results to users
- **Planning**: Breaking down complex tasks

## Tool Composition

### Combining Tools

```python
@tool
def comprehensive_search(query: str, include_web: bool = True) -> dict:
    """Search multiple sources and combine results."""
    results = {"local": [], "web": []}

    # Search local database
    local_results = db_query.invoke({"query": f"SELECT * FROM docs WHERE content LIKE '%{query}%'"})
    if local_results.get("success"):
        results["local"] = local_results["data"]

    # Optionally search web
    if include_web:
        web_results = web_search.invoke({"query": query})
        if web_results.get("success"):
            results["web"] = web_results["results"]

    return {
        "success": True,
        "query": query,
        "results": results,
        "sources": ["local", "web"] if include_web else ["local"]
    }
```

### Tool Pipelines

```python
@tool
def analyze_and_report(data_source: str) -> dict:
    """Fetch data, analyze it, and generate report."""
    # Step 1: Fetch data
    data = db_query.invoke({"query": f"SELECT * FROM {data_source}"})
    if not data.get("success"):
        return data

    # Step 2: Calculate statistics
    values = [row["value"] for row in data["data"]]
    stats = descriptive_stats.invoke({"numbers": values})

    # Step 3: Format report
    report = format_data.invoke({
        "data": {**stats, "source": data_source},
        "template": "Report for {source}:\nMean: {mean}\nMedian: {median}"
    })

    return {
        "success": True,
        "data": data["data"],
        "statistics": stats,
        "report": report["result"]
    }
```

## Security Considerations

### Input Validation

```python
@tool
def safe_query(table: str, column: str) -> dict:
    """Safe query with validation."""
    # Whitelist allowed tables
    ALLOWED_TABLES = ["users", "orders", "products"]
    if table not in ALLOWED_TABLES:
        return {"success": False, "error": f"Invalid table: {table}"}

    # Sanitize column name
    if not column.isalnum():
        return {"success": False, "error": "Invalid column name"}

    query = f"SELECT {column} FROM {table}"
    # ... execute
```

### Path Traversal Prevention

```python
@tool
def read_file(path: str) -> dict:
    """Read file with path validation."""
    import os

    # Get absolute path
    abs_path = os.path.abspath(path)

    # Check against allowed directories
    ALLOWED_DIRS = ["/app/data", "/app/config"]
    if not any(abs_path.startswith(d) for d in ALLOWED_DIRS):
        return {"success": False, "error": "Access denied"}

    # ... read file
```

### Rate Limiting

```python
from functools import lru_cache
import time

_last_call = {}
RATE_LIMIT_SECONDS = 1

@tool
def rate_limited_api(endpoint: str) -> dict:
    """API call with rate limiting."""
    global _last_call

    now = time.time()
    if endpoint in _last_call:
        elapsed = now - _last_call[endpoint]
        if elapsed < RATE_LIMIT_SECONDS:
            return {"success": False, "error": f"Rate limited. Wait {RATE_LIMIT_SECONDS - elapsed:.1f}s"}

    _last_call[endpoint] = now
    # ... make API call
```

## Testing Tools

See [testing_tools.md](testing_tools.md) for comprehensive testing strategies.

### Quick Test

```python
if __name__ == "__main__":
    # Test the tool
    result = my_tool.invoke({"param1": "test", "param2": 5})
    print(result)
    assert result["success"] == True
```
