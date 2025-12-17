#!/usr/bin/env python3
"""
LangSmith Tracing Setup for LangGraph Agents.

Enables automatic tracing of agent runs for debugging and monitoring.
Captures LLM calls, tool executions, and graph traversals.

Prerequisites:
1. Create LangSmith account at https://smith.langchain.com
2. Create API key in settings
3. Set environment variables
"""

import os
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver


# ============================================================================
# Environment Configuration
# ============================================================================

def configure_langsmith(
    project_name: str = "default",
    tracing_enabled: bool = True,
    endpoint: str = "https://api.smith.langchain.com"
):
    """
    Configure LangSmith environment variables.

    Args:
        project_name: LangSmith project for organizing traces
        tracing_enabled: Enable/disable tracing
        endpoint: LangSmith API endpoint

    Environment variables that can be set:
        LANGSMITH_API_KEY: Your LangSmith API key (required)
        LANGSMITH_PROJECT: Project name for organizing traces
        LANGSMITH_TRACING: "true" to enable tracing
        LANGSMITH_ENDPOINT: API endpoint (defaults to cloud)
    """
    os.environ["LANGSMITH_TRACING"] = "true" if tracing_enabled else "false"
    os.environ["LANGSMITH_PROJECT"] = project_name
    os.environ["LANGSMITH_ENDPOINT"] = endpoint

    # Check for API key
    if not os.environ.get("LANGSMITH_API_KEY"):
        print("Warning: LANGSMITH_API_KEY not set. Tracing will not work.")
        print("Get your API key at: https://smith.langchain.com/settings")


def disable_tracing():
    """Disable LangSmith tracing."""
    os.environ["LANGSMITH_TRACING"] = "false"


def enable_tracing():
    """Enable LangSmith tracing."""
    os.environ["LANGSMITH_TRACING"] = "true"


# ============================================================================
# Traced Agent Setup
# ============================================================================

class TracedAgent:
    """
    LangGraph agent with automatic LangSmith tracing.

    All invocations are automatically traced when LANGSMITH_TRACING=true.
    Traces include:
    - LLM calls with inputs/outputs
    - Tool executions
    - Graph state transitions
    - Timing and token usage

    Example:
        configure_langsmith(project_name="my-agent")
        agent = TracedAgent()
        response = agent.chat("Hello!")
        # View traces at https://smith.langchain.com
    """

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.llm = ChatGoogleGenerativeAI(model=model)
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build agent graph with automatic tracing."""

        def call_model(state: MessagesState) -> dict:
            response = self.llm.invoke(state["messages"])
            return {"messages": [response]}

        builder = StateGraph(MessagesState)
        builder.add_node("agent", call_model)
        builder.add_edge(START, "agent")
        builder.add_edge("agent", END)

        return builder.compile(checkpointer=self.checkpointer)

    def chat(self, message: str, thread_id: str = "default") -> str:
        """
        Send a message and get a response.

        The entire execution is traced in LangSmith.
        """
        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config
        )
        return result["messages"][-1].content


# ============================================================================
# Project Organization
# ============================================================================

def create_project_structure():
    """
    Example project structure for organizing traces.

    Recommended project naming:
    - dev-agent-name: Development traces
    - staging-agent-name: Staging environment
    - prod-agent-name: Production traces

    Use tags for further organization:
    - model version
    - feature flags
    - user segments
    """
    projects = {
        "development": "dev-customer-support",
        "staging": "staging-customer-support",
        "production": "prod-customer-support"
    }

    environment = os.environ.get("ENVIRONMENT", "development")
    project = projects.get(environment, "default")

    configure_langsmith(project_name=project)
    return project


# ============================================================================
# Tracing Configuration Classes
# ============================================================================

class TracingConfig:
    """Configuration for LangSmith tracing."""

    def __init__(
        self,
        project_name: str,
        api_key: Optional[str] = None,
        tracing_enabled: bool = True,
        sample_rate: float = 1.0,  # 1.0 = trace all, 0.1 = trace 10%
        tags: Optional[list[str]] = None,
        metadata: Optional[dict] = None
    ):
        self.project_name = project_name
        self.api_key = api_key or os.environ.get("LANGSMITH_API_KEY")
        self.tracing_enabled = tracing_enabled
        self.sample_rate = sample_rate
        self.tags = tags or []
        self.metadata = metadata or {}

    def apply(self):
        """Apply tracing configuration."""
        if self.api_key:
            os.environ["LANGSMITH_API_KEY"] = self.api_key

        os.environ["LANGSMITH_TRACING"] = "true" if self.tracing_enabled else "false"
        os.environ["LANGSMITH_PROJECT"] = self.project_name

        return self

    def get_run_config(self) -> dict:
        """Get config dict for run metadata."""
        return {
            "tags": self.tags,
            "metadata": self.metadata
        }


# ============================================================================
# Run with Metadata
# ============================================================================

def run_with_metadata(
    graph,
    inputs: dict,
    thread_id: str,
    tags: list[str] = None,
    metadata: dict = None
) -> dict:
    """
    Run graph with custom tags and metadata for tracing.

    Args:
        graph: Compiled LangGraph
        inputs: Input state
        thread_id: Conversation thread ID
        tags: List of tags for filtering traces
        metadata: Additional metadata to attach to trace

    Example:
        result = run_with_metadata(
            graph,
            {"messages": [msg]},
            thread_id="user-123",
            tags=["production", "v2.1"],
            metadata={"user_tier": "premium", "feature_flag": "new_model"}
        )
    """
    config = {
        "configurable": {"thread_id": thread_id},
        "tags": tags or [],
        "metadata": metadata or {}
    }

    return graph.invoke(inputs, config)


# ============================================================================
# Demo Functions
# ============================================================================

def demo_basic_tracing():
    """Demonstrate basic tracing setup."""

    print("=== Basic Tracing Demo ===\n")

    # Configure LangSmith
    configure_langsmith(project_name="demo-tracing")

    # Create traced agent
    agent = TracedAgent()

    # This call is automatically traced
    response = agent.chat("What is the capital of France?")
    print(f"Response: {response}")
    print("\nView trace at: https://smith.langchain.com")


def demo_tagged_runs():
    """Demonstrate runs with tags and metadata."""

    print("=== Tagged Runs Demo ===\n")

    configure_langsmith(project_name="demo-tagged")

    agent = TracedAgent()

    # Run with tags and metadata
    result = run_with_metadata(
        agent.graph,
        {"messages": [HumanMessage(content="Hello!")]},
        thread_id="demo-user",
        tags=["demo", "tagged-run"],
        metadata={
            "user_id": "demo-user",
            "version": "1.0.0",
            "experiment": "baseline"
        }
    )

    print(f"Response: {result['messages'][-1].content}")
    print("\nFilter by tags in LangSmith to find this trace")


def demo_project_organization():
    """Demonstrate project organization patterns."""

    print("=== Project Organization Demo ===\n")

    # Different environments use different projects
    environments = ["development", "staging", "production"]

    for env in environments:
        os.environ["ENVIRONMENT"] = env
        project = create_project_structure()
        print(f"{env.upper():12} -> Project: {project}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("LangSmith Tracing Setup Demonstrations\n")
    print("=" * 50 + "\n")

    # Check for API key
    if not os.environ.get("LANGSMITH_API_KEY"):
        print("Note: Set LANGSMITH_API_KEY to enable actual tracing")
        print("Get your key at: https://smith.langchain.com/settings\n")

    demo_basic_tracing()
    print("\n" + "=" * 50 + "\n")

    demo_project_organization()
