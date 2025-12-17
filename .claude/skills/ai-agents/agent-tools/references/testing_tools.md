# Testing Tools Guide

## Overview

Thorough testing ensures tools work correctly in isolation and when used by agents.

## Unit Testing Tools

### Basic Unit Test

```python
import pytest
from tools.database_tools import db_query

def test_db_query_success():
    """Test successful query execution."""
    result = db_query.invoke({
        "query": "SELECT * FROM users LIMIT 1",
        "database": "test"
    })

    assert result["success"] == True
    assert "data" in result
    assert isinstance(result["data"], list)

def test_db_query_invalid_query():
    """Test rejection of non-SELECT queries."""
    result = db_query.invoke({
        "query": "DELETE FROM users",
        "database": "test"
    })

    assert result["success"] == False
    assert "error" in result
    assert "SELECT" in result["error"]
```

### Testing Input Validation

```python
def test_tool_validates_email():
    """Test email validation."""
    result = validate_email.invoke({"email": "invalid"})
    assert result["valid"] == False

    result = validate_email.invoke({"email": "user@example.com"})
    assert result["valid"] == True

def test_tool_validates_bounds():
    """Test numeric bounds validation."""
    result = statistics.invoke({
        "numbers": [],
        "operation": "mean"
    })
    assert result["success"] == False
    assert "empty" in result["error"].lower()
```

### Testing Error Handling

```python
def test_tool_handles_missing_params():
    """Test handling of missing required parameters."""
    # This should raise or return error
    with pytest.raises(Exception):
        my_tool.invoke({})  # Missing required params

def test_tool_handles_network_error(mocker):
    """Test handling of network errors."""
    mocker.patch('httpx.Client.get', side_effect=httpx.ConnectError("Network error"))

    result = http_get.invoke({"url": "https://example.com"})

    assert result["success"] == False
    assert "connect" in result["error"].lower()
```

## Mocking External Services

### Mocking HTTP Requests

```python
import pytest
import httpx
from unittest.mock import Mock, patch

@pytest.fixture
def mock_httpx():
    """Mock httpx for API tests."""
    with patch('httpx.Client') as mock:
        client = Mock()
        mock.return_value.__enter__ = Mock(return_value=client)
        mock.return_value.__exit__ = Mock(return_value=False)
        yield client

def test_api_tool_success(mock_httpx):
    """Test successful API call."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    mock_response.headers = {"content-type": "application/json"}

    mock_httpx.get.return_value = mock_response

    result = http_get.invoke({"url": "https://api.example.com/data"})

    assert result["success"] == True
    assert result["data"] == {"data": "test"}

def test_api_tool_timeout(mock_httpx):
    """Test API timeout handling."""
    mock_httpx.get.side_effect = httpx.TimeoutException("Timeout")

    result = http_get.invoke({"url": "https://slow-api.example.com"})

    assert result["success"] == False
    assert "timeout" in result["error"].lower()
```

### Mocking Database

```python
@pytest.fixture
def mock_database(mocker):
    """Mock database connection."""
    mock_engine = mocker.Mock()
    mock_conn = mocker.Mock()
    mock_result = mocker.Mock()

    mock_engine.connect.return_value.__enter__ = mocker.Mock(return_value=mock_conn)
    mock_engine.connect.return_value.__exit__ = mocker.Mock(return_value=False)

    mocker.patch('tools.database_tools.DatabaseManager.get_connection', return_value=mock_engine)

    return mock_conn, mock_result

def test_db_query_returns_results(mock_database):
    """Test database query returns results."""
    mock_conn, mock_result = mock_database

    mock_result.fetchall.return_value = [
        ("John", 30),
        ("Jane", 25)
    ]
    mock_result.keys.return_value = ["name", "age"]
    mock_conn.execute.return_value = mock_result

    result = db_query.invoke({
        "query": "SELECT name, age FROM users",
        "database": "default"
    })

    assert result["success"] == True
    assert len(result["data"]) == 2
    assert result["data"][0]["name"] == "John"
```

### Mocking File System

```python
import os
import tempfile

@pytest.fixture
def temp_files():
    """Create temporary files for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Test content")

        yield tmpdir, test_file

def test_read_file_success(temp_files):
    """Test reading a file."""
    tmpdir, test_file = temp_files

    result = read_file.invoke({"path": test_file})

    assert result["success"] == True
    assert result["content"] == "Test content"

def test_read_file_not_found():
    """Test reading non-existent file."""
    result = read_file.invoke({"path": "/nonexistent/file.txt"})

    assert result["success"] == False
    assert "not found" in result["error"].lower()
```

## Integration Testing

### Testing Tool with Real Services

```python
import pytest

@pytest.mark.integration
def test_real_database_connection():
    """Test actual database connection (requires TEST_DATABASE_URL)."""
    import os
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL not set")

    result = db_query.invoke({
        "query": "SELECT 1 as test",
        "database": "test"
    })

    assert result["success"] == True
    assert result["data"][0]["test"] == 1

@pytest.mark.integration
def test_real_api_call():
    """Test actual API call (requires network)."""
    result = http_get.invoke({
        "url": "https://httpbin.org/get"
    })

    assert result["success"] == True
    assert result["status_code"] == 200
```

### Testing Tool Combinations

```python
def test_tool_pipeline(mock_database, mock_httpx):
    """Test tools working together."""
    # Setup mocks
    mock_database[1].fetchall.return_value = [("user@example.com",)]
    mock_database[1].keys.return_value = ["email"]
    mock_database[0].execute.return_value = mock_database[1]

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"sent": True}
    mock_httpx.post.return_value = mock_response

    # Execute pipeline
    # 1. Query users
    users = db_query.invoke({"query": "SELECT email FROM users"})
    assert users["success"] == True

    # 2. Send notification for each
    for user in users["data"]:
        result = http_post.invoke({
            "url": "https://api.example.com/notify",
            "data": {"email": user["email"]}
        })
        assert result["success"] == True
```

## Testing with Agents

### Testing Tool Selection

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

def test_agent_selects_correct_tool():
    """Test that agent chooses the right tool."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    tools = [db_query, calculate, get_datetime]

    agent = create_react_agent(llm, tools)

    # Test calculation query
    result = agent.invoke({
        "messages": [{"role": "user", "content": "What is 15% of 200?"}]
    })

    # Check that calculate tool was used
    messages = result["messages"]
    tool_calls = [m for m in messages if hasattr(m, "tool_calls") and m.tool_calls]

    assert len(tool_calls) > 0
    assert any("calculate" in str(tc) for tc in tool_calls)

def test_agent_handles_tool_error():
    """Test that agent handles tool errors gracefully."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    # Create tool that always fails
    @tool
    def failing_tool(param: str) -> dict:
        """A tool that always fails."""
        return {"success": False, "error": "Always fails"}

    agent = create_react_agent(llm, [failing_tool])

    result = agent.invoke({
        "messages": [{"role": "user", "content": "Use the failing tool"}]
    })

    # Agent should acknowledge the failure
    final_message = result["messages"][-1].content
    assert "fail" in final_message.lower() or "error" in final_message.lower()
```

## Test Fixtures and Utilities

### Common Test Fixtures

```python
# conftest.py

import pytest
import os

@pytest.fixture(scope="session")
def test_config():
    """Test configuration."""
    return {
        "database": os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:"),
        "api_key": os.environ.get("TEST_API_KEY", "test-key")
    }

@pytest.fixture
def sample_data():
    """Sample data for tests."""
    return {
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"}
        ],
        "numbers": [10, 20, 30, 40, 50]
    }

@pytest.fixture(autouse=True)
def reset_tool_state():
    """Reset tool state before each test."""
    # Clear any caches
    yield
    # Cleanup after test
```

### Test Utilities

```python
# test_utils.py

def assert_tool_success(result: dict, expected_keys: list = None):
    """Assert tool returned success with expected keys."""
    assert result["success"] == True, f"Tool failed: {result.get('error')}"
    if expected_keys:
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

def assert_tool_failure(result: dict, error_contains: str = None):
    """Assert tool returned failure."""
    assert result["success"] == False
    if error_contains:
        assert error_contains.lower() in result.get("error", "").lower()
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tools --cov-report=html

# Run only unit tests
pytest -m "not integration"

# Run specific tool tests
pytest tests/test_database_tools.py -v

# Run with verbose output
pytest -v --tb=short
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_utils.py            # Test utilities
├── unit/
│   ├── test_database_tools.py
│   ├── test_api_tools.py
│   ├── test_file_tools.py
│   ├── test_calculation_tools.py
│   └── test_utility_tools.py
├── integration/
│   ├── test_real_database.py
│   └── test_real_api.py
└── agent/
    └── test_tool_selection.py
```
