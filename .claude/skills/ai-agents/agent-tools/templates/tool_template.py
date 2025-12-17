#!/usr/bin/env python3
"""
Tool Template for AI Agents.

Use this template to create custom tools that agents can use
to perform deterministic operations.

Copy this file and modify for your use case.
"""

from typing import Optional, Any
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field


# ============================================================================
# Option 1: Simple @tool Decorator
# ============================================================================

@tool
def simple_tool(param1: str, param2: int = 10) -> str:
    """Short description of what the tool does.

    Use this tool when [specific use case description].
    Examples: [give 2-3 examples of when to use this tool]

    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2 (default: 10)

    Returns:
        Description of return value
    """
    try:
        # Your implementation here
        result = f"Processed {param1} with value {param2}"
        return result
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================================
# Option 2: @tool with Pydantic Schema (Recommended)
# ============================================================================

class MyToolInput(BaseModel):
    """Input schema for my_structured_tool.

    Pydantic schemas provide:
    - Type validation
    - Default values
    - Clear descriptions for LLM
    """
    query: str = Field(description="The query to process")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")
    include_metadata: bool = Field(default=False, description="Include metadata in response")


class MyToolOutput(BaseModel):
    """Output schema for my_structured_tool."""
    success: bool
    data: Any
    error: Optional[str] = None


@tool(args_schema=MyToolInput)
def my_structured_tool(query: str, limit: int = 10, include_metadata: bool = False) -> dict:
    """Process a query and return structured results.

    Use this tool when you need to [specific use case].
    This tool is appropriate for:
    - [Use case 1]
    - [Use case 2]

    Args:
        query: The query to process
        limit: Maximum number of results (1-100)
        include_metadata: Whether to include metadata

    Returns:
        Dictionary with success status, data, and optional error
    """
    try:
        # Your implementation here
        results = [{"id": i, "value": f"Result {i}"} for i in range(limit)]

        response = {
            "success": True,
            "data": results,
            "error": None
        }

        if include_metadata:
            response["metadata"] = {
                "query": query,
                "count": len(results)
            }

        return response

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


# ============================================================================
# Option 3: StructuredTool from Function
# ============================================================================

def my_function(param1: str, param2: int = 10) -> dict:
    """Implementation function (no decorator)."""
    return {"result": f"{param1}: {param2}"}


my_structured_tool_v2 = StructuredTool.from_function(
    func=my_function,
    name="my_tool_name",
    description="Description for the LLM. Use when [specific case].",
    args_schema=MyToolInput,
    return_direct=False  # Set True if tool output should be final response
)


# ============================================================================
# Option 4: Tool with Error Handling
# ============================================================================

class SafeToolInput(BaseModel):
    """Input for safe_tool."""
    operation: str = Field(description="Operation to perform")
    data: dict = Field(default_factory=dict, description="Data to process")


@tool(args_schema=SafeToolInput, handle_tool_error=True)
def safe_tool(operation: str, data: dict = None) -> dict:
    """Perform an operation with built-in error handling.

    Use this tool when you need to safely perform operations
    that might fail. Errors are caught and returned gracefully.

    Args:
        operation: The operation to perform
        data: Optional data dictionary

    Returns:
        Result dictionary with success status
    """
    data = data or {}

    # Validate operation
    valid_operations = ["create", "read", "update", "delete"]
    if operation not in valid_operations:
        return {
            "success": False,
            "error": f"Invalid operation. Must be one of: {valid_operations}"
        }

    # Perform operation
    try:
        if operation == "create":
            result = {"created": True, "data": data}
        elif operation == "read":
            result = {"data": data}
        elif operation == "update":
            result = {"updated": True, "data": data}
        elif operation == "delete":
            result = {"deleted": True}
        else:
            result = {}

        return {"success": True, **result}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Option 5: Async Tool
# ============================================================================

@tool
async def async_tool(url: str) -> dict:
    """Fetch data from URL asynchronously.

    Use this tool when you need to fetch data from external URLs.

    Args:
        url: The URL to fetch

    Returns:
        Response data
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            return {
                "success": True,
                "status": response.status_code,
                "data": response.text[:1000]  # Limit response size
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # Test simple tool
    print("Simple tool:", simple_tool.invoke({"param1": "test", "param2": 5}))

    # Test structured tool
    print("Structured tool:", my_structured_tool.invoke({
        "query": "test query",
        "limit": 3,
        "include_metadata": True
    }))

    # Test safe tool
    print("Safe tool:", safe_tool.invoke({
        "operation": "create",
        "data": {"name": "test"}
    }))
