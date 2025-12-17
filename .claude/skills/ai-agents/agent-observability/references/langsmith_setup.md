# LangSmith Setup Guide

Complete guide to setting up LangSmith for agent observability.

## Account Setup

1. Create account at https://smith.langchain.com
2. Navigate to Settings > API Keys
3. Create a new API key
4. Store securely (shown only once)

## Environment Variables

### Required

```bash
# Your LangSmith API key
LANGSMITH_API_KEY=lsv2_pt_xxxxx

# Enable tracing (must be "true")
LANGSMITH_TRACING=true

# Project for organizing traces
LANGSMITH_PROJECT=my-project
```

### Optional

```bash
# API endpoint (defaults to cloud)
LANGSMITH_ENDPOINT=https://api.smith.langchain.com

# Sample rate for tracing (0.0 to 1.0)
LANGSMITH_SAMPLE_RATE=1.0
```

## Configuration Methods

### Environment Variables

```bash
export LANGSMITH_API_KEY="lsv2_pt_xxxxx"
export LANGSMITH_TRACING="true"
export LANGSMITH_PROJECT="production-agent"
```

### Python Configuration

```python
import os

os.environ["LANGSMITH_API_KEY"] = "lsv2_pt_xxxxx"
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "production-agent"
```

### .env File

```
LANGSMITH_API_KEY=lsv2_pt_xxxxx
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=production-agent
```

Load with python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv()
```

## Project Organization

### Naming Convention

```
{environment}-{agent-name}
```

Examples:
- `dev-customer-support`
- `staging-sales-assistant`
- `prod-code-reviewer`

### Multi-Environment Setup

```python
import os

PROJECTS = {
    "development": "dev-agent",
    "staging": "staging-agent",
    "production": "prod-agent"
}

env = os.environ.get("ENVIRONMENT", "development")
os.environ["LANGSMITH_PROJECT"] = PROJECTS[env]
```

## Client Initialization

### Basic Client

```python
from langsmith import Client

client = Client()  # Uses environment variables

# Or with explicit config
client = Client(
    api_key="lsv2_pt_xxxxx",
    api_url="https://api.smith.langchain.com"
)
```

### Verify Connection

```python
from langsmith import Client

client = Client()

# Test connection
try:
    projects = list(client.list_projects(limit=1))
    print("Connected to LangSmith!")
except Exception as e:
    print(f"Connection failed: {e}")
```

## Automatic Tracing

### LangChain Integration

LangChain components are automatically traced when environment variables are set:

```python
from langchain_google_genai import ChatGoogleGenerativeAI

# Automatically traced
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
response = llm.invoke("Hello!")  # Traced automatically
```

### LangGraph Integration

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

# All graph invocations are traced
graph = builder.compile(checkpointer=MemorySaver())
result = graph.invoke(inputs, config)  # Traced automatically
```

### OpenAI Wrapper

```python
from langsmith.wrappers import wrap_openai
from openai import OpenAI

# Wrap for automatic tracing
client = wrap_openai(OpenAI())
response = client.chat.completions.create(...)  # Traced
```

## Disabling Tracing

### Per-Environment

```bash
# Development: full tracing
LANGSMITH_TRACING=true

# Production: sample 10%
LANGSMITH_SAMPLE_RATE=0.1

# Disable completely
LANGSMITH_TRACING=false
```

### Per-Call

```python
import os

# Temporarily disable
original = os.environ.get("LANGSMITH_TRACING")
os.environ["LANGSMITH_TRACING"] = "false"

# Do something without tracing
result = llm.invoke("Not traced")

# Restore
if original:
    os.environ["LANGSMITH_TRACING"] = original
```

## Self-Hosted Option

For enterprise deployments:

```python
# Point to self-hosted instance
os.environ["LANGSMITH_ENDPOINT"] = "https://langsmith.your-company.com"
os.environ["LANGSMITH_API_KEY"] = "your-self-hosted-key"
```

## Security Best Practices

1. **Never commit API keys** - Use environment variables or secret managers
2. **Rotate keys regularly** - Create new keys periodically
3. **Use project isolation** - Separate projects for different environments
4. **Enable team permissions** - Control who can view traces
5. **Review sensitive data** - Be mindful of PII in traces

## Troubleshooting

### Traces Not Appearing

1. Check `LANGSMITH_TRACING=true`
2. Verify API key is valid
3. Confirm project exists
4. Check network connectivity

### Rate Limiting

```python
# Reduce sampling in high-volume scenarios
os.environ["LANGSMITH_SAMPLE_RATE"] = "0.1"  # 10%
```

### Large Traces

```python
# For very large outputs, consider truncation
response = llm.invoke(prompt)
# LangSmith handles large payloads, but may truncate in UI
```
