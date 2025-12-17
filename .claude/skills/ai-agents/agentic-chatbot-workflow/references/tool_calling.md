# Tool Calling

## Overview

Tools extend agent capabilities by providing structured interfaces to external systems, APIs, and computations.

## Creating Tools

### Using @tool Decorator

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

@tool
def search_web(query: str) -> str:
    """Search the web for information.

    Args:
        query: The search query to execute
    """
    # Implementation
    return f"Results for: {query}"

@tool
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression.

    Args:
        expression: Math expression like '2 + 2' or 'sqrt(16)'
    """
    import math
    return eval(expression, {"__builtins__": {}}, {"sqrt": math.sqrt, "pi": math.pi})
```

### Using Pydantic Schema

```python
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    """Input for weather lookup."""
    city: str = Field(description="City name")
    units: str = Field(default="celsius", description="Temperature units")

def get_weather(city: str, units: str = "celsius") -> dict:
    """Get current weather for a city."""
    # API call implementation
    return {"city": city, "temp": 22, "units": units}

weather_tool = StructuredTool.from_function(
    func=get_weather,
    name="get_weather",
    description="Get current weather for a city",
    args_schema=WeatherInput
)
```

### Complex Tool with Multiple Parameters

```python
class DatabaseQueryInput(BaseModel):
    """Input for database queries."""
    table: str = Field(description="Table name to query")
    columns: list[str] = Field(description="Columns to select")
    where: dict = Field(default_factory=dict, description="Filter conditions")
    limit: int = Field(default=10, description="Max rows to return")

@tool(args_schema=DatabaseQueryInput)
def query_database(table: str, columns: list[str], where: dict, limit: int) -> list[dict]:
    """Query the database with specified parameters."""
    # Build and execute query
    pass
```

## ToolNode

ToolNode executes tool calls made by the LLM.

```python
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState, START, END

# Define tools
tools = [search_web, calculate, get_weather]

# Create ToolNode
tool_node = ToolNode(tools)

# Build graph with tool calling
def call_model(state: MessagesState) -> dict:
    response = llm.bind_tools(tools).invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: MessagesState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

builder = StateGraph(MessagesState)
builder.add_node("agent", call_model)
builder.add_node("tools", tool_node)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue, {
    "tools": "tools",
    END: END
})
builder.add_edge("tools", "agent")

graph = builder.compile()
```

## InjectedState

Access graph state within tools using InjectedState.

```python
from langgraph.prebuilt import InjectedState
from typing import Annotated

class AgentState(MessagesState):
    user_id: str
    session_data: dict

@tool
def get_user_preferences(
    state: Annotated[AgentState, InjectedState]
) -> dict:
    """Get preferences for the current user.

    This tool automatically receives the graph state.
    """
    user_id = state["user_id"]
    # Lookup preferences using user_id
    return {"theme": "dark", "language": "en"}

@tool
def save_to_session(
    key: str,
    value: str,
    state: Annotated[AgentState, InjectedState]
) -> str:
    """Save data to the user's session.

    Args:
        key: The key to store the value under
        value: The value to store
    """
    # Note: This modifies local copy, need to return state update
    return f"Saved {key}={value} for user {state['user_id']}"
```

## Error Handling

### Tool-Level Error Handling

```python
from langchain_core.tools import ToolException

@tool(handle_tool_error=True)
def risky_operation(param: str) -> str:
    """Perform an operation that might fail."""
    try:
        result = external_api_call(param)
        return result
    except APIError as e:
        raise ToolException(f"API error: {e}")

# Custom error handler
def handle_error(error: ToolException) -> str:
    return f"Tool failed: {error}. Please try a different approach."

@tool(handle_tool_error=handle_error)
def another_tool(x: int) -> int:
    """Another tool with custom error handling."""
    if x < 0:
        raise ToolException("Negative values not allowed")
    return x * 2
```

### Graph-Level Error Handling

```python
from langgraph.prebuilt import ToolNode

def handle_tool_errors(state: MessagesState) -> dict:
    """Handle errors from tool execution."""
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_call_id"):
        # This is a tool result - check for errors
        if "error" in last_message.content.lower():
            return {
                "messages": [AIMessage(content="I encountered an error. Let me try differently.")]
            }

    return state

# Or use ToolNode with error handling
tool_node = ToolNode(
    tools,
    handle_tool_errors=True  # Auto-convert exceptions to error messages
)
```

## Tool Categories

### Information Retrieval

```python
@tool
def search_documents(query: str, top_k: int = 5) -> list[str]:
    """Search internal documents for relevant information."""
    # Vector search implementation
    pass

@tool
def fetch_url(url: str) -> str:
    """Fetch and extract text content from a URL."""
    import requests
    from bs4 import BeautifulSoup
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text()[:5000]
```

### Actions

```python
@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient."""
    # Email sending implementation
    return f"Email sent to {to}"

@tool
def create_task(title: str, description: str, due_date: str) -> dict:
    """Create a new task in the task management system."""
    # Task creation implementation
    return {"id": "task-123", "title": title, "status": "created"}
```

### Computations

```python
@tool
def analyze_sentiment(text: str) -> dict:
    """Analyze the sentiment of the given text."""
    # Sentiment analysis
    return {"sentiment": "positive", "confidence": 0.85}

@tool
def extract_entities(text: str) -> list[dict]:
    """Extract named entities from text."""
    # NER implementation
    return [{"text": "John", "type": "PERSON"}]
```

## Tool Selection

### Conditional Tool Binding

```python
def get_tools_for_context(state: AgentState) -> list:
    """Return tools based on context."""
    base_tools = [search_web, calculate]

    if state.get("is_admin"):
        base_tools.extend([admin_tool, delete_tool])

    if state.get("has_api_access"):
        base_tools.append(api_tool)

    return base_tools

def call_model_with_dynamic_tools(state: AgentState) -> dict:
    tools = get_tools_for_context(state)
    response = llm.bind_tools(tools).invoke(state["messages"])
    return {"messages": [response]}
```

### Tool Descriptions Best Practices

```python
@tool
def good_tool(query: str) -> str:
    """Search the product catalog for items matching the query.

    Use this tool when the user asks about:
    - Product availability
    - Product specifications
    - Pricing information

    Args:
        query: Search terms, can include product names, categories, or features

    Returns:
        JSON string with matching products and their details
    """
    pass

# Bad: Vague description
@tool
def bad_tool(x: str) -> str:
    """Do something with x."""  # Don't do this
    pass
```

## Async Tools

```python
import asyncio
import httpx

@tool
async def async_fetch(url: str) -> str:
    """Asynchronously fetch content from a URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text[:5000]

@tool
async def parallel_search(queries: list[str]) -> list[str]:
    """Execute multiple searches in parallel."""
    async def single_search(q):
        # Search implementation
        return f"Results for {q}"

    results = await asyncio.gather(*[single_search(q) for q in queries])
    return results
```

## Tool Testing

```python
def test_weather_tool():
    """Test the weather tool."""
    result = get_weather.invoke({"city": "Tokyo", "units": "celsius"})
    assert "temp" in result
    assert result["city"] == "Tokyo"

def test_tool_schema():
    """Test tool schema is valid."""
    schema = weather_tool.args_schema.schema()
    assert "city" in schema["properties"]
    assert schema["required"] == ["city"]
```
