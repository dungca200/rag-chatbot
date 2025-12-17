# Tracing Patterns Guide

Common patterns for tracing LangGraph agents with LangSmith.

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
# Run types: chain, llm, tool, retriever, parser, prompt
@traceable(run_type="tool")
def search(query: str) -> list:
    return results

@traceable(run_type="retriever")
def retrieve_docs(query: str) -> list:
    return documents

@traceable(run_type="llm")
def generate(prompt: str) -> str:
    return llm.invoke(prompt)
```

### With Custom Name

```python
@traceable(name="document_processor")
def process(doc: str) -> dict:
    return {"processed": doc}
```

### With Metadata

```python
@traceable(
    run_type="chain",
    name="rag_pipeline",
    metadata={
        "version": "2.0",
        "model": "gemini-2.5-flash"
    }
)
def rag_pipeline(query: str) -> str:
    return answer
```

## Nested Traces

### Automatic Nesting

```python
@traceable(name="main_workflow")
def main_workflow(input: str) -> dict:
    # Creates nested span
    cleaned = preprocess(input)

    # Creates another nested span
    result = process(cleaned)

    return result

@traceable(name="preprocess")
def preprocess(text: str) -> str:
    return text.strip()

@traceable(name="process")
def process(text: str) -> dict:
    return {"result": text}
```

Trace hierarchy:
```
main_workflow
├── preprocess
└── process
```

### Deep Nesting

```python
@traceable(name="pipeline")
def pipeline(query: str) -> str:
    docs = retrieve(query)
    context = rerank(docs)
    response = generate(query, context)
    return response

@traceable(name="retrieve")
def retrieve(query: str) -> list:
    embedded = embed(query)  # Nested
    return search(embedded)  # Nested

@traceable(name="embed")
def embed(text: str) -> list:
    return embeddings.embed_query(text)
```

## Tags and Metadata

### Static Tags

```python
@traceable(tags=["production", "v2.0"])
def production_endpoint(request):
    return process(request)
```

### Dynamic Tags

```python
from langsmith.run_helpers import get_current_run_tree

@traceable
def dynamic_tagged_function(user_type: str):
    run_tree = get_current_run_tree()
    if run_tree:
        run_tree.tags = [user_type, "dynamic"]
    return result
```

### Rich Metadata

```python
@traceable
def rich_metadata_function(user_id: str, request_id: str):
    run_tree = get_current_run_tree()
    if run_tree:
        run_tree.extra["metadata"] = {
            "user_id": user_id,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "environment": os.environ.get("ENV"),
            "feature_flags": {"new_model": True}
        }
    return result
```

## Run Configuration

### With Config Object

```python
# Pass config to graph invocations
config = {
    "configurable": {"thread_id": "user-123"},
    "tags": ["production", "experiment-A"],
    "metadata": {
        "user_tier": "premium",
        "session_id": "abc123"
    }
}

result = graph.invoke(inputs, config)
```

### Custom Run Name

```python
config = {
    "run_name": "customer_support_query",
    "tags": ["support"],
    "metadata": {"ticket_id": "T-12345"}
}
```

## Retriever Tracing

### Standard Pattern

```python
@traceable(run_type="retriever", name="vector_search")
def vector_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Retriever run_type provides:
    - Special UI for viewing documents
    - Relevance score display
    - Source tracking
    """
    results = vector_store.similarity_search(query, k=top_k)
    return [
        {"content": doc.page_content, "score": doc.metadata.get("score")}
        for doc in results
    ]
```

### With Source Tracking

```python
@traceable(run_type="retriever")
def search_with_sources(query: str) -> list[dict]:
    results = []
    for doc in vector_store.search(query):
        results.append({
            "content": doc.page_content,
            "score": doc.metadata.get("score", 0),
            "source": doc.metadata.get("source"),
            "page": doc.metadata.get("page")
        })
    return results
```

## Error Handling

### Automatic Error Capture

```python
@traceable(name="risky_operation")
def risky_operation(data):
    # Errors are automatically captured in the trace
    if not data:
        raise ValueError("Data cannot be empty")
    return process(data)
```

### Error with Context

```python
@traceable(name="operation_with_context")
def operation_with_context(data):
    run_tree = get_current_run_tree()

    try:
        result = process(data)
        return result
    except Exception as e:
        # Add context before error
        if run_tree:
            run_tree.extra["metadata"]["error_context"] = {
                "data_type": type(data).__name__,
                "data_size": len(str(data))
            }
        raise
```

## Async Tracing

### Async Functions

```python
@traceable(name="async_operation")
async def async_operation(query: str) -> str:
    # Works with async functions
    result = await async_llm.ainvoke(query)
    return result
```

### Parallel Operations

```python
import asyncio

@traceable(name="parallel_search")
async def parallel_search(queries: list[str]) -> list[list]:
    # Each search creates its own span
    tasks = [search(q) for q in queries]
    results = await asyncio.gather(*tasks)
    return results

@traceable(name="single_search")
async def search(query: str) -> list:
    return await vector_store.asimilarity_search(query)
```

## Streaming Traces

### Stream with Tracing

```python
@traceable(name="streaming_response")
def streaming_response(prompt: str):
    # Streaming is captured in trace
    for chunk in llm.stream(prompt):
        yield chunk
```

### Graph Streaming

```python
# Stream events are traced
for event in graph.stream(inputs, config, stream_mode="values"):
    print(event)  # Each event is part of the trace
```

## Conditional Tracing

### Sample Rate

```python
import random

def create_sampled_tracer(sample_rate: float):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if random.random() < sample_rate:
                return traceable(func)(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@create_sampled_tracer(0.1)  # 10% sampling
def high_volume_function(data):
    return process(data)
```

### Feature Flag Based

```python
def trace_if_enabled(feature_flag: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if os.environ.get(feature_flag) == "true":
                return traceable(func)(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@trace_if_enabled("ENABLE_DETAILED_TRACING")
def detailed_operation(data):
    return process(data)
```

## Best Practices

### 1. Meaningful Names

```python
# Good
@traceable(name="search_product_catalog")
@traceable(name="generate_email_response")
@traceable(name="validate_user_input")

# Bad
@traceable(name="func1")
@traceable(name="process")
@traceable(name="do_thing")
```

### 2. Appropriate Run Types

```python
# Match run_type to operation
@traceable(run_type="retriever")  # For document retrieval
@traceable(run_type="llm")        # For LLM calls
@traceable(run_type="tool")       # For tool/function execution
@traceable(run_type="chain")      # For workflows/pipelines
```

### 3. Useful Metadata

```python
@traceable(metadata={
    "version": "2.0",
    "model": "gemini-2.5-flash",
    "team": "ml-platform"
})
```

### 4. Trace Boundaries

```python
# Good: Trace at meaningful boundaries
@traceable(name="handle_customer_request")
def handle_request(request):
    # Multiple internal operations
    validated = validate(request)
    processed = process(validated)
    return format_response(processed)

# Avoid: Tracing every tiny function
# This creates noise and overhead
```
