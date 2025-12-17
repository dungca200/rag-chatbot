# Agent Tools

Build production-ready tools for AI agents. Provides database queries, API calls, file operations, calculations, and search that return **real data** instead of AI-generated guesses.

## Why Tools Matter

**Without tools:** User asks "How much revenue did we make from 2012-2020?"
- Agent **hallucinates** numbers based on training data
- Results are unreliable and potentially wrong

**With tools:** Same question
- Agent uses `db_query` tool with `SELECT year, revenue FROM financials WHERE year BETWEEN 2012 AND 2020`
- Returns **actual data** from the database
- Results are deterministic and accurate

Tools connect agents to:
- **Real data sources** (databases, APIs, files)
- **Deterministic operations** (calculations, validation)
- **External systems** (webhooks, services)

## Quick Start

### Simple Tool

```python
from langchain_core.tools import tool

@tool
def get_user_count() -> dict:
    """Get the total number of active users.

    Use this tool when users ask about user counts or statistics.
    """
    # Execute actual database query
    result = db.execute("SELECT COUNT(*) FROM users WHERE active = true")
    return {"success": True, "count": result.scalar()}
```

### Tool with Pydantic Schema

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class RevenueInput(BaseModel):
    """Input for revenue query."""
    start_year: int = Field(description="Start year (e.g., 2012)")
    end_year: int = Field(description="End year (e.g., 2020)")

@tool(args_schema=RevenueInput)
def get_revenue(start_year: int, end_year: int) -> dict:
    """Get revenue data for a date range.

    Use this tool when users ask about revenue, sales, or earnings.
    Examples:
    - "How much revenue from 2012-2020?"
    - "What were sales in 2023?"
    """
    query = """
        SELECT year, revenue
        FROM financials
        WHERE year BETWEEN :start AND :end
        ORDER BY year
    """
    results = db.execute(query, {"start": start_year, "end": end_year})
    return {
        "success": True,
        "data": [{"year": r.year, "revenue": r.revenue} for r in results]
    }
```

### Using Tools with Agent

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

# Import tools
from tools.database_tools import db_query, db_aggregate
from tools.calculation_tools import calculate, statistics

# Create agent with tools
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
tools = [db_query, db_aggregate, calculate, statistics]
agent = create_react_agent(llm, tools)

# Agent automatically selects appropriate tool
result = agent.invoke({
    "messages": [{"role": "user", "content": "What's the average revenue from 2015-2020?"}]
})
# Agent will: 1) Use db_query to fetch data, 2) Use statistics to calculate average
```

## Tool Categories

### Database Tools (`tools/database_tools.py`)

| Tool | Description | Use When |
|------|-------------|----------|
| `db_query` | Execute SELECT queries | Users ask for specific data |
| `db_insert` | Insert new records | Need to save data |
| `db_update` | Update existing records | Need to modify data |
| `db_aggregate` | SUM, AVG, COUNT, etc. | Users ask for totals/averages |
| `db_table_info` | Get table schema | Need to understand structure |
| `db_count` | Count records | Users ask "how many" |
| `db_exists` | Check if record exists | Need to verify existence |

```python
from tools.database_tools import db_query, db_aggregate

# Query specific data
result = db_query.invoke({
    "query": "SELECT name, email FROM users WHERE role = 'admin'",
    "database": "default"
})

# Aggregate operations
total = db_aggregate.invoke({
    "table": "orders",
    "column": "amount",
    "operation": "SUM",
    "where": {"status": "completed", "year": 2024}
})
```

### API Tools (`tools/api_tools.py`)

| Tool | Description | Use When |
|------|-------------|----------|
| `http_get` | GET requests | Fetching external data |
| `http_post` | POST requests | Sending data to APIs |
| `http_put` | PUT requests | Updating resources |
| `http_delete` | DELETE requests | Removing resources |
| `webhook_send` | Send webhooks | Notifying external systems |
| `api_paginate` | Fetch paginated data | Large result sets |
| `api_health_check` | Check API status | Monitoring/verification |

```python
from tools.api_tools import http_get, webhook_send

# Fetch external data
weather = http_get.invoke({
    "url": "https://api.weather.com/current",
    "params": {"city": "Tokyo"}
})

# Send notification
webhook_send.invoke({
    "url": "https://hooks.slack.com/...",
    "payload": {"text": "New order received!"}
})
```

### File Tools (`tools/file_tools.py`)

| Tool | Description | Use When |
|------|-------------|----------|
| `read_file` | Read file contents | Need file data |
| `read_file_lines` | Read specific lines | Large files |
| `write_file` | Write to file | Saving output |
| `search_files` | Find files by pattern | Locating files |
| `search_in_files` | Search file contents | Finding text in files |
| `parse_csv` | Parse CSV to records | Processing CSV data |
| `parse_json` | Parse JSON file | Processing JSON data |
| `file_info` | Get file metadata | Size, dates, permissions |

```python
from tools.file_tools import parse_csv, search_in_files

# Process CSV data
data = parse_csv.invoke({"path": "/data/sales.csv"})

# Search in files
matches = search_in_files.invoke({
    "directory": "/logs",
    "pattern": "ERROR",
    "file_pattern": "*.log"
})
```

### Calculation Tools (`tools/calculation_tools.py`)

| Tool | Description | Use When |
|------|-------------|----------|
| `calculate` | Math expressions | Basic calculations |
| `statistics` | Mean, median, std, etc. | Statistical analysis |
| `descriptive_stats` | Full statistical summary | Comprehensive analysis |
| `convert_units` | Unit conversion | Converting measurements |
| `financial_calc` | Interest, ROI, etc. | Financial calculations |
| `percentage` | Percentage operations | Change, of, increase |

```python
from tools.calculation_tools import calculate, statistics, financial_calc

# Safe math evaluation
result = calculate.invoke({"expression": "(1500 * 0.15) + 200"})

# Statistical analysis
stats = statistics.invoke({
    "numbers": [100, 150, 200, 175, 225],
    "operation": "mean"
})

# Financial calculation
interest = financial_calc.invoke({
    "principal": 10000,
    "rate": 5.5,
    "time": 3,
    "calc_type": "compound_interest"
})
```

### Search Tools (`tools/search_tools.py`)

| Tool | Description | Use When |
|------|-------------|----------|
| `web_search` | Search the web | Current information needed |
| `vector_search` | Semantic similarity search | Finding related documents |
| `text_search` | Exact text matching | Finding specific text |
| `fuzzy_search` | Approximate matching | Handling typos/variations |
| `regex_search` | Pattern matching | Complex text patterns |

```python
from tools.search_tools import web_search, vector_search

# Web search (requires SERP_API_KEY)
results = web_search.invoke({
    "query": "Python LangChain tutorial 2024",
    "num_results": 5
})

# Semantic search (requires vector store)
similar = vector_search.invoke({
    "query": "machine learning best practices",
    "collection": "documentation",
    "top_k": 10
})
```

### Utility Tools (`tools/utility_tools.py`)

| Tool | Description | Use When |
|------|-------------|----------|
| `get_datetime` | Current date/time | Time-sensitive operations |
| `parse_datetime` | Parse date strings | Processing date input |
| `date_diff` | Date difference | Calculating durations |
| `date_add` | Add to date | Future/past dates |
| `format_data` | Template formatting | Creating output |
| `format_number` | Number formatting | Display numbers |
| `validate_data` | Schema validation | Input validation |
| `validate_email` | Email validation | Email verification |
| `generate_id` | Unique ID generation | Creating identifiers |
| `generate_uuid` | UUID generation | Standard UUIDs |

```python
from tools.utility_tools import get_datetime, date_diff, validate_email

# Get current time in timezone
now = get_datetime.invoke({"timezone": "Asia/Tokyo"})

# Calculate days until deadline
diff = date_diff.invoke({
    "date1": "2024-01-15",
    "date2": "2024-03-01",
    "unit": "days"
})

# Validate user input
valid = validate_email.invoke({"email": "user@example.com"})
```

## Tool Development Patterns

### Standard Response Structure

Always return consistent response format:

```python
# Success response
{
    "success": True,
    "data": result,
    "count": len(result)  # if applicable
}

# Error response
{
    "success": False,
    "error": "Human-readable error message",
    "error_type": "validation"  # optional category
}
```

### Docstring Best Practices

The docstring is how the LLM decides when to use your tool:

```python
@tool
def my_tool(param: str) -> dict:
    """Short description of what the tool does.

    Use this tool when [specific use case].
    Examples:
    - "User question 1" → Use this tool
    - "User question 2" → Use this tool

    IMPORTANT: Any constraints or limitations.

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
```

### Input Validation with Pydantic

```python
from pydantic import BaseModel, Field, field_validator

class QueryInput(BaseModel):
    """Input for database query."""
    query: str = Field(description="SQL SELECT query")
    limit: int = Field(default=100, ge=1, le=1000, description="Max results")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        if not v.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries allowed")
        return v
```

### Error Handling

```python
@tool
def resilient_tool(param: str) -> dict:
    """Tool with proper error handling."""
    try:
        result = perform_operation(param)
        return {"success": True, "data": result}
    except ValidationError as e:
        return {"success": False, "error": str(e), "error_type": "validation"}
    except ConnectionError as e:
        return {"success": False, "error": "Service unavailable", "error_type": "connection", "recoverable": True}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}", "error_type": "unknown"}
```

## Templates

### Basic Tool Template (`templates/tool_template.py`)

Five patterns for creating tools:
1. Simple @tool decorator
2. Pydantic schema validation
3. StructuredTool class
4. Error handling pattern
5. Async tools

### MCP Integration (`templates/mcp_tool_template.py`)

Patterns for integrating MCP servers:
1. MCP client wrapper
2. Tool factory function
3. Tool registry

## Reference Documentation

- **[Tool Development Guide](references/tool_development.md)** - Anatomy, patterns, best practices
- **[Error Handling](references/error_handling.md)** - Error patterns, retry logic, graceful degradation
- **[Testing Tools](references/testing_tools.md)** - Unit tests, mocking, integration tests

## Dependencies

```
langchain-core>=0.3.0
pydantic>=2.0.0
httpx>=0.27.0
python-dateutil>=2.8.0
```

### Optional (based on tools used)

```
sqlalchemy>=2.0.0        # Database tools
supabase>=2.0.0          # Vector search with Supabase
google-generativeai      # Embeddings for vector search
tenacity>=8.0.0          # Retry logic
```

## Directory Structure

```
agent-tools/
├── SKILL.md                    # This file
├── LICENSE.txt                 # Apache 2.0
├── tools/
│   ├── database_tools.py       # SQL queries, CRUD
│   ├── api_tools.py            # HTTP requests
│   ├── file_tools.py           # File operations
│   ├── calculation_tools.py    # Math, statistics
│   ├── search_tools.py         # Web/vector search
│   └── utility_tools.py        # DateTime, formatting
├── templates/
│   ├── tool_template.py        # Base tool patterns
│   └── mcp_tool_template.py    # MCP integration
└── references/
    ├── tool_development.md     # Development guide
    ├── error_handling.md       # Error patterns
    └── testing_tools.md        # Testing guide
```
