---
name: agent-observability
description: Monitor, debug, and trace LangGraph agents with LangSmith. Covers tracing setup, custom spans, cost tracking, and production debugging. Use when building agents that need observability, debugging complex workflows, or monitoring production deployments.
license: Complete terms in LICENSE.txt
---

# Agent Observability Guide

## Overview

Implement comprehensive observability for LangGraph agents using LangSmith tracing, custom spans, cost tracking, and production debugging patterns.

**Observability Stack:**
```
LangSmith     → Automatic tracing of LLM calls and graph execution
@traceable    → Custom spans for non-LLM operations
Metadata      → Tags and metadata for filtering traces
Cost Tracking → Token usage and cost estimation
```

## Quick Start

### Enable Tracing

```bash
export LANGSMITH_API_KEY="lsv2_pt_xxxxx"
export LANGSMITH_TRACING="true"
export LANGSMITH_PROJECT="my-agent"
```

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

# Automatically traced when environment variables are set
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
agent = create_react_agent(llm, tools=[])

response = agent.invoke({"messages": [{"role": "user", "content": "Hello!"}]})
# View trace at https://smith.langchain.com
```

### Custom Tracing

```python
from langsmith import traceable

@traceable(run_type="retriever", name="document_search")
def search_documents(query: str) -> list:
    # This function is traced as a retriever
    return results

@traceable(run_type="tool", name="data_processor")
def process_data(data: dict) -> dict:
    # Nested traces are automatically linked
    cleaned = clean_data(data)
    return transform(cleaned)
```

### Cost Tracking

```python
from scripts.cost_tracking import CostTrackedAgent

agent = CostTrackedAgent(budget_limit=10.00)
response = agent.chat("What is machine learning?")

print(agent.get_cost_report())
# Total Cost: $0.0012
# Budget Remaining: $9.9988
```

## Environment Setup

### Required Variables

```bash
LANGSMITH_API_KEY=lsv2_pt_xxxxx    # Your API key
LANGSMITH_TRACING=true             # Enable tracing
LANGSMITH_PROJECT=my-project       # Project name
```

### Configuration in Python

```python
from scripts.tracing_setup import configure_langsmith

configure_langsmith(
    project_name="production-agent",
    tracing_enabled=True
)
```

## @traceable Decorator

### Basic Usage

```python
from langsmith import traceable

@traceable
def my_function(input: str) -> str:
    return process(input)
```

### With Run Type

```python
# Run types: chain, llm, tool, retriever, parser
@traceable(run_type="retriever")
def retrieve_docs(query: str) -> list:
    return documents

@traceable(run_type="tool")
def execute_action(params: dict) -> dict:
    return result
```

### With Metadata

```python
@traceable(
    run_type="chain",
    name="rag_pipeline",
    metadata={"version": "2.0", "model": "gemini-2.5-flash"},
    tags=["production", "rag"]
)
def rag_pipeline(query: str) -> str:
    docs = retrieve(query)
    return generate(query, docs)
```

## Nested Traces

```python
@traceable(name="main_workflow")
def main_workflow(query: str) -> dict:
    # Each decorated function creates a nested span
    processed = preprocess(query)      # Nested
    docs = retrieve(processed)         # Nested
    response = generate(query, docs)   # Nested
    return {"response": response}

@traceable(name="preprocess")
def preprocess(text: str) -> str:
    return text.strip().lower()

@traceable(name="retrieve", run_type="retriever")
def retrieve(query: str) -> list:
    return vector_store.search(query)

@traceable(name="generate", run_type="llm")
def generate(query: str, docs: list) -> str:
    return llm.invoke(prompt)
```

Trace hierarchy:
```
main_workflow
├── preprocess
├── retrieve
└── generate
```

## Dynamic Tags and Metadata

```python
from langsmith.run_helpers import get_current_run_tree

@traceable
def operation_with_context(user_id: str, request_id: str):
    run_tree = get_current_run_tree()
    if run_tree:
        run_tree.tags = ["production", "v2.0"]
        run_tree.extra["metadata"] = {
            "user_id": user_id,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }
    return process()
```

## Run Configuration

```python
# Add tags and metadata to graph invocations
config = {
    "configurable": {"thread_id": "user-123"},
    "tags": ["production", "experiment-A"],
    "metadata": {
        "user_tier": "premium",
        "feature_flag": "new_model"
    }
}

result = graph.invoke(inputs, config)
```

## Cost Tracking

### Token Estimation

```python
from scripts.cost_tracking import estimate_tokens, compare_model_costs

# Estimate tokens
tokens = estimate_tokens("Your prompt text here")

# Compare costs across models
comparison = compare_model_costs(
    prompt="Long prompt...",
    models=["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o"]
)
for model in comparison:
    print(f"{model['model']}: ${model['cost']:.6f}")
```

### Budget Management

```python
from scripts.cost_tracking import TokenTracker, set_budget

# Set global budget
set_budget(limit=50.00)

# Track usage
tracker = TokenTracker(budget_limit=10.00)
tracker.record(TokenUsage(
    input_tokens=1000,
    output_tokens=500,
    model="gemini-2.5-flash"
))

print(tracker.summary())
# {'total_cost': 0.000225, 'budget_remaining': 9.999775}
```

## Debugging

### State Inspection

```python
from scripts.debugging_workflow import DebugAgent

agent = DebugAgent(verbose=True)

# Chat with debug output
response = agent.chat("What is Python?", thread_id="debug-session")

# Inspect thread state
state = agent.inspect_thread("debug-session")
print(f"Messages: {len(state['values']['messages'])}")
print(f"Next nodes: {state['next']}")
```

### Checkpoint History

```python
# List all checkpoints
checkpoints = agent.get_history("debug-session", limit=10)
for cp in checkpoints:
    print(f"Checkpoint: {cp['checkpoint_id'][:20]}...")

# Replay from specific checkpoint
response = agent.replay_from_checkpoint(
    thread_id="debug-session",
    checkpoint_id="abc123...",
    new_message="Different question"
)
```

### Error Analysis

```python
from scripts.debugging_workflow import ErrorAnalyzer

analyzer = ErrorAnalyzer()

try:
    result = risky_operation()
except Exception as e:
    analysis = analyzer.categorize(e)
    print(f"Category: {analysis['category']}")
    print(f"Recoverable: {analysis['recoverable']}")
    print(f"Fix: {analyzer.suggest_fix(analysis)}")
```

## Production Monitoring

### Project Organization

```python
# Environment-based projects
PROJECTS = {
    "development": "dev-agent",
    "staging": "staging-agent",
    "production": "prod-agent"
}

env = os.environ.get("ENVIRONMENT", "development")
os.environ["LANGSMITH_PROJECT"] = PROJECTS[env]
```

### Sampling for High Volume

```python
# Sample 10% of requests in production
os.environ["LANGSMITH_SAMPLE_RATE"] = "0.1"
```

### Conditional Tracing

```python
from scripts.custom_tracing import create_conditional_tracer

@create_conditional_tracer(sample_rate=0.1)
def high_volume_endpoint(request):
    return process(request)
```

## Model Pricing Reference

| Model | Input (per 1M) | Output (per 1M) |
|-------|----------------|-----------------|
| gemini-2.5-flash | $0.075 | $0.30 |
| gemini-2.5-pro | $1.25 | $5.00 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| claude-3-5-sonnet | $3.00 | $15.00 |

## Environment Variables

```bash
# Required
LANGSMITH_API_KEY=lsv2_pt_xxxxx
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=my-project

# Optional
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_SAMPLE_RATE=1.0
GOOGLE_API_KEY=your-gemini-api-key
```

## Dependencies

```
langsmith>=0.1.0
langchain>=0.3.0
langchain-google-genai>=2.0.0
langgraph>=0.2.0
```

## Reference Files

- [references/langsmith_setup.md](references/langsmith_setup.md) - Environment setup, API keys
- [references/tracing_patterns.md](references/tracing_patterns.md) - @traceable, nested traces, metadata
- [references/monitoring_guide.md](references/monitoring_guide.md) - Dashboards, alerts, debugging

## Scripts

- `scripts/tracing_setup.py` - LangSmith configuration, basic tracing
- `scripts/custom_tracing.py` - @traceable patterns, nested spans
- `scripts/cost_tracking.py` - Token usage, cost estimation
- `scripts/debugging_workflow.py` - State inspection, error analysis
