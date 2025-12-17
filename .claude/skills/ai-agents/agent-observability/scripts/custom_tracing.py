#!/usr/bin/env python3
"""
Custom Tracing for LangGraph Agents.

Advanced tracing patterns using:
- @traceable decorator for custom spans
- Nested traces for complex workflows
- Custom metadata and tags
- Span attributes for filtering
"""

import os
import time
from typing import Optional, Any
from functools import wraps

from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver


# ============================================================================
# @traceable Decorator
# ============================================================================

@traceable(run_type="chain")
def process_query(query: str) -> dict:
    """
    Process a user query with automatic tracing.

    The @traceable decorator:
    - Creates a trace span automatically
    - Captures inputs and outputs
    - Records timing information
    - Supports nested traces
    """
    # Preprocessing (creates nested span)
    cleaned = clean_query(query)

    # Classification (creates nested span)
    category = classify_query(cleaned)

    return {
        "original": query,
        "cleaned": cleaned,
        "category": category
    }


@traceable(run_type="tool", name="query_cleaner")
def clean_query(query: str) -> str:
    """Clean and normalize a query."""
    return query.strip().lower()


@traceable(run_type="tool", name="query_classifier")
def classify_query(query: str) -> str:
    """Classify query into categories."""
    keywords = {
        "question": ["what", "how", "why", "when", "where", "who"],
        "request": ["please", "can you", "could you", "help"],
        "statement": []
    }

    query_lower = query.lower()
    for category, words in keywords.items():
        if any(word in query_lower for word in words):
            return category

    return "statement"


# ============================================================================
# Retrieval Tracing
# ============================================================================

@traceable(run_type="retriever", name="document_retriever")
def retrieve_documents(query: str, top_k: int = 5) -> list[dict]:
    """
    Retrieve relevant documents with retriever tracing.

    run_type="retriever" provides special handling in LangSmith:
    - Shows retrieval-specific metrics
    - Displays document chunks
    - Enables retrieval quality analysis
    """
    # Simulated retrieval
    documents = [
        {"content": f"Document {i} about {query}", "score": 0.9 - i * 0.1}
        for i in range(top_k)
    ]
    return documents


# ============================================================================
# LLM Tracing with Metadata
# ============================================================================

@traceable(
    run_type="llm",
    name="gemini_completion",
    metadata={"model_provider": "google"}
)
def generate_response(
    messages: list,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7
) -> str:
    """
    Generate LLM response with detailed tracing.

    Metadata in @traceable:
    - Persists across all invocations
    - Useful for static categorization
    """
    llm = ChatGoogleGenerativeAI(model=model, temperature=temperature)
    response = llm.invoke(messages)
    return response.content


# ============================================================================
# Custom Span Context
# ============================================================================

class SpanContext:
    """Context manager for custom trace spans."""

    def __init__(
        self,
        name: str,
        run_type: str = "chain",
        metadata: Optional[dict] = None,
        tags: Optional[list[str]] = None
    ):
        self.name = name
        self.run_type = run_type
        self.metadata = metadata or {}
        self.tags = tags or []
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        # Log span completion
        if exc_type:
            print(f"Span '{self.name}' failed after {duration:.3f}s: {exc_val}")
        else:
            print(f"Span '{self.name}' completed in {duration:.3f}s")


# ============================================================================
# Dynamic Metadata
# ============================================================================

def with_dynamic_metadata(metadata: dict):
    """
    Decorator factory for adding dynamic metadata to traces.

    Unlike static metadata in @traceable, this allows
    runtime-determined metadata.
    """
    def decorator(func):
        @wraps(func)
        @traceable(run_type="chain")
        def wrapper(*args, **kwargs):
            # Access current run tree to add metadata
            run_tree = get_current_run_tree()
            if run_tree:
                run_tree.extra["metadata"] = {
                    **(run_tree.extra.get("metadata", {})),
                    **metadata
                }
            return func(*args, **kwargs)
        return wrapper
    return decorator


@with_dynamic_metadata({"feature": "new_algorithm"})
def experimental_process(data: str) -> str:
    """Process data with experimental algorithm."""
    return data.upper()


# ============================================================================
# Traced Agent with Custom Spans
# ============================================================================

class TracedWorkflow:
    """
    Workflow with custom tracing spans.

    Demonstrates:
    - Nested trace hierarchy
    - Custom metadata per step
    - Error handling in traces
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    @traceable(run_type="chain", name="workflow_execution")
    def execute(self, query: str, user_id: str) -> dict:
        """Execute full workflow with tracing."""

        # Step 1: Preprocess
        processed = self._preprocess(query)

        # Step 2: Retrieve context
        context = self._retrieve(processed)

        # Step 3: Generate response
        response = self._generate(processed, context)

        return {
            "query": query,
            "response": response,
            "user_id": user_id
        }

    @traceable(run_type="tool", name="preprocess_step")
    def _preprocess(self, query: str) -> str:
        """Preprocess the query."""
        return query.strip().lower()

    @traceable(run_type="retriever", name="context_retrieval")
    def _retrieve(self, query: str) -> list[str]:
        """Retrieve relevant context."""
        # Simulated retrieval
        return [f"Context about: {query}"]

    @traceable(run_type="llm", name="response_generation")
    def _generate(self, query: str, context: list[str]) -> str:
        """Generate response using LLM."""
        context_text = "\n".join(context)
        response = self.llm.invoke([
            {"role": "system", "content": f"Context:\n{context_text}"},
            {"role": "user", "content": query}
        ])
        return response.content


# ============================================================================
# Error Tracing
# ============================================================================

@traceable(run_type="chain", name="safe_operation")
def safe_operation(data: Any) -> dict:
    """
    Operation with error handling that traces errors.

    Errors are automatically captured in traces:
    - Exception type and message
    - Stack trace
    - Partial outputs before error
    """
    try:
        result = risky_transform(data)
        return {"success": True, "result": result}
    except Exception as e:
        # Error is captured in trace
        return {"success": False, "error": str(e)}


def risky_transform(data: Any) -> Any:
    """Transform that might fail."""
    if data is None:
        raise ValueError("Data cannot be None")
    return str(data).upper()


# ============================================================================
# Batch Tracing
# ============================================================================

@traceable(run_type="chain", name="batch_process")
def batch_process(items: list[str]) -> list[dict]:
    """
    Process items in batch with individual item tracing.

    Each item gets its own nested span for debugging.
    """
    results = []
    for i, item in enumerate(items):
        result = process_single_item(item, index=i)
        results.append(result)
    return results


@traceable(run_type="tool", name="process_item")
def process_single_item(item: str, index: int) -> dict:
    """Process a single item."""
    return {
        "index": index,
        "original": item,
        "processed": item.upper(),
        "length": len(item)
    }


# ============================================================================
# Conditional Tracing
# ============================================================================

def create_conditional_tracer(sample_rate: float = 0.1):
    """
    Create a tracer that only traces a percentage of requests.

    Useful for high-volume production:
    - sample_rate=1.0: Trace all (development)
    - sample_rate=0.1: Trace 10% (production)
    """
    import random

    def conditional_trace(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if random.random() < sample_rate:
                # Trace this request
                traced_func = traceable(run_type="chain")(func)
                return traced_func(*args, **kwargs)
            else:
                # Skip tracing
                return func(*args, **kwargs)
        return wrapper
    return conditional_trace


# Usage: @create_conditional_tracer(sample_rate=0.1)
# def high_volume_endpoint(request): ...


# ============================================================================
# Demo Functions
# ============================================================================

def demo_traceable_decorator():
    """Demonstrate @traceable decorator usage."""

    print("=== @traceable Decorator Demo ===\n")

    # Nested traces
    result = process_query("How do I use LangGraph?")
    print(f"Processed query: {result}\n")


def demo_retriever_tracing():
    """Demonstrate retriever-specific tracing."""

    print("=== Retriever Tracing Demo ===\n")

    docs = retrieve_documents("LangGraph agents", top_k=3)
    print(f"Retrieved {len(docs)} documents")
    for doc in docs:
        print(f"  - {doc['content']} (score: {doc['score']:.2f})")


def demo_workflow_tracing():
    """Demonstrate full workflow tracing."""

    print("=== Workflow Tracing Demo ===\n")

    workflow = TracedWorkflow()
    result = workflow.execute(
        query="What is LangGraph?",
        user_id="demo-user"
    )
    print(f"Response: {result['response'][:100]}...")


def demo_batch_tracing():
    """Demonstrate batch processing with tracing."""

    print("=== Batch Tracing Demo ===\n")

    items = ["apple", "banana", "cherry"]
    results = batch_process(items)

    for r in results:
        print(f"  {r['index']}: {r['original']} -> {r['processed']}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("Custom Tracing Demonstrations\n")
    print("=" * 50 + "\n")

    # Ensure tracing is enabled
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = "demo-custom-tracing"

    demo_traceable_decorator()
    print("\n" + "=" * 50 + "\n")

    demo_retriever_tracing()
    print("\n" + "=" * 50 + "\n")

    demo_batch_tracing()
    print("\n" + "=" * 50 + "\n")

    demo_workflow_tracing()

    print("\nView traces at: https://smith.langchain.com")
