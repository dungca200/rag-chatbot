# Error Handling in Tools

## Overview

Good error handling ensures tools fail gracefully and provide useful information to the agent for recovery.

## Basic Pattern

```python
@tool
def my_tool(param: str) -> dict:
    """Tool with proper error handling."""
    try:
        result = perform_operation(param)
        return {
            "success": True,
            "data": result
        }
    except SpecificError as e:
        return {
            "success": False,
            "error": f"Specific error: {str(e)}",
            "error_type": "specific_error"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "unknown"
        }
```

## Error Response Structure

### Standard Error Response

```python
{
    "success": False,
    "error": "Human-readable error message",
    "error_type": "category_of_error",  # Optional
    "details": {},  # Optional additional context
    "recoverable": True,  # Optional hint for agent
    "suggestions": []  # Optional recovery suggestions
}
```

### Error Categories

```python
ERROR_TYPES = {
    "validation": "Input validation failed",
    "not_found": "Resource not found",
    "permission": "Permission denied",
    "timeout": "Operation timed out",
    "rate_limit": "Rate limit exceeded",
    "connection": "Connection failed",
    "parse": "Failed to parse response",
    "unknown": "Unknown error"
}
```

## Validation Errors

### Input Validation

```python
@tool
def validated_tool(email: str, age: int) -> dict:
    """Tool with input validation."""
    errors = []

    # Validate email
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        errors.append("Invalid email format")

    # Validate age
    if age < 0 or age > 150:
        errors.append("Age must be between 0 and 150")

    if errors:
        return {
            "success": False,
            "error": "Validation failed",
            "error_type": "validation",
            "validation_errors": errors
        }

    # Proceed with valid input
    return {"success": True, "data": process(email, age)}
```

### Schema Validation

```python
from pydantic import BaseModel, ValidationError

class StrictInput(BaseModel):
    email: str
    age: int

@tool
def strict_tool(email: str, age: int) -> dict:
    """Tool with Pydantic validation."""
    try:
        validated = StrictInput(email=email, age=age)
    except ValidationError as e:
        return {
            "success": False,
            "error": "Invalid input",
            "error_type": "validation",
            "details": e.errors()
        }

    return {"success": True}
```

## External Service Errors

### API Errors

```python
import httpx

@tool
def api_tool(url: str) -> dict:
    """Tool with API error handling."""
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(url)

            # Handle HTTP errors
            if response.status_code == 404:
                return {
                    "success": False,
                    "error": "Resource not found",
                    "error_type": "not_found",
                    "status_code": 404
                }
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error": "Rate limit exceeded. Try again later.",
                    "error_type": "rate_limit",
                    "status_code": 429,
                    "retry_after": response.headers.get("Retry-After")
                }
            elif response.status_code >= 500:
                return {
                    "success": False,
                    "error": "Server error. Service may be unavailable.",
                    "error_type": "server_error",
                    "status_code": response.status_code,
                    "recoverable": True
                }

            response.raise_for_status()
            return {"success": True, "data": response.json()}

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Request timed out",
            "error_type": "timeout",
            "recoverable": True,
            "suggestions": ["Try again", "Check network connection"]
        }
    except httpx.ConnectError:
        return {
            "success": False,
            "error": "Could not connect to server",
            "error_type": "connection",
            "recoverable": True
        }
```

### Database Errors

```python
from sqlalchemy.exc import IntegrityError, OperationalError

@tool
def db_tool(query: str) -> dict:
    """Tool with database error handling."""
    try:
        result = execute_query(query)
        return {"success": True, "data": result}

    except IntegrityError as e:
        return {
            "success": False,
            "error": "Data integrity violation (duplicate key or constraint)",
            "error_type": "integrity",
            "details": str(e.orig)
        }
    except OperationalError as e:
        return {
            "success": False,
            "error": "Database connection error",
            "error_type": "connection",
            "recoverable": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Database error: {str(e)}",
            "error_type": "database"
        }
```

## Retry Logic

### Simple Retry

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def unreliable_operation():
    """Operation that might fail."""
    return external_service_call()

@tool
def resilient_tool(param: str) -> dict:
    """Tool with automatic retry."""
    try:
        result = unreliable_operation()
        return {"success": True, "data": result}
    except Exception as e:
        return {
            "success": False,
            "error": "Operation failed after 3 attempts",
            "error_type": "persistent_failure",
            "last_error": str(e)
        }
```

### Manual Retry with Backoff

```python
import time

@tool
def manual_retry_tool(url: str, max_retries: int = 3) -> dict:
    """Tool with manual retry logic."""
    last_error = None

    for attempt in range(max_retries):
        try:
            result = fetch_data(url)
            return {"success": True, "data": result, "attempts": attempt + 1}

        except TemporaryError as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
            continue

        except PermanentError as e:
            # Don't retry permanent errors
            return {
                "success": False,
                "error": str(e),
                "error_type": "permanent",
                "recoverable": False
            }

    return {
        "success": False,
        "error": f"Failed after {max_retries} attempts: {last_error}",
        "error_type": "max_retries",
        "attempts": max_retries
    }
```

## Graceful Degradation

### Fallback Values

```python
@tool
def degraded_tool(param: str) -> dict:
    """Tool with fallback behavior."""
    try:
        # Try primary source
        result = primary_source(param)
        return {"success": True, "data": result, "source": "primary"}

    except PrimarySourceError:
        try:
            # Fall back to secondary
            result = secondary_source(param)
            return {
                "success": True,
                "data": result,
                "source": "secondary",
                "warning": "Using fallback data source"
            }

        except SecondarySourceError:
            # Return cached/default
            return {
                "success": True,
                "data": get_cached_or_default(param),
                "source": "cache",
                "warning": "Using cached data - may be stale"
            }
```

### Partial Results

```python
@tool
def multi_source_tool(sources: list[str]) -> dict:
    """Tool that returns partial results on errors."""
    results = []
    errors = []

    for source in sources:
        try:
            data = fetch_from_source(source)
            results.append({"source": source, "data": data})
        except Exception as e:
            errors.append({"source": source, "error": str(e)})

    return {
        "success": len(results) > 0,
        "data": results,
        "errors": errors if errors else None,
        "partial": len(errors) > 0,
        "message": f"Retrieved {len(results)}/{len(sources)} sources"
    }
```

## Error Messages for LLM

### Clear, Actionable Messages

```python
# Good - tells LLM what to do
{
    "success": False,
    "error": "Table 'users' not found. Available tables: customers, orders, products",
    "suggestions": ["Use 'customers' table instead", "Check table name spelling"]
}

# Bad - not helpful
{
    "success": False,
    "error": "Error: relation does not exist"
}
```

### Context-Aware Messages

```python
@tool
def context_aware_tool(query: str) -> dict:
    """Tool with contextual error messages."""
    if "DELETE" in query.upper():
        return {
            "success": False,
            "error": "DELETE operations are not allowed. This tool only supports SELECT queries.",
            "error_type": "permission",
            "suggestions": ["Use db_delete tool instead", "Remove DELETE from query"]
        }

    if "DROP" in query.upper():
        return {
            "success": False,
            "error": "Schema modifications are not allowed.",
            "error_type": "permission"
        }

    # ... execute query
```

## Built-in Error Handling

### Using handle_tool_error

```python
from langchain_core.tools import ToolException

def custom_error_handler(error: ToolException) -> str:
    """Custom error handler for tool errors."""
    return f"Tool failed: {error}. Please try a different approach."

@tool(handle_tool_error=custom_error_handler)
def handled_tool(param: str) -> str:
    """Tool with custom error handling."""
    if not param:
        raise ToolException("Parameter cannot be empty")
    return f"Processed: {param}"
```

### Auto Error Handling

```python
@tool(handle_tool_error=True)
def auto_handled_tool(param: str) -> str:
    """Tool with automatic error handling.

    Exceptions are automatically caught and returned as error messages.
    """
    if not param:
        raise ValueError("Parameter cannot be empty")
    return f"Processed: {param}"
```
