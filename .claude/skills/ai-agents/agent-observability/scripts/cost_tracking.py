#!/usr/bin/env python3
"""
Cost Tracking for LangGraph Agents.

Monitor token usage and estimate costs across:
- LLM calls
- Embedding operations
- Agent runs
- Batch processing

Supports Gemini and other popular models.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

from langsmith import traceable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver


# ============================================================================
# Pricing Configuration (as of 2024)
# ============================================================================

MODEL_PRICING = {
    # Gemini Models (per 1M tokens)
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},

    # OpenAI Models (per 1M tokens)
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},

    # Claude Models (per 1M tokens)
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},

    # Embedding Models (per 1M tokens)
    "text-embedding-004": {"input": 0.00, "output": 0.00},  # Free tier
    "text-embedding-3-small": {"input": 0.02, "output": 0.00},
    "text-embedding-3-large": {"input": 0.13, "output": 0.00},
}


# ============================================================================
# Token Counter
# ============================================================================

@dataclass
class TokenUsage:
    """Track token usage for a single operation."""
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def cost(self) -> float:
        """Calculate cost based on model pricing."""
        pricing = MODEL_PRICING.get(self.model, {"input": 0, "output": 0})
        input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


class TokenTracker:
    """
    Track token usage across multiple operations.

    Features:
    - Per-model usage tracking
    - Cost estimation
    - Usage history
    - Budget alerts
    """

    def __init__(self, budget_limit: Optional[float] = None):
        self.usage_history: list[TokenUsage] = []
        self.budget_limit = budget_limit

    def record(self, usage: TokenUsage):
        """Record a token usage event."""
        self.usage_history.append(usage)

        # Check budget
        if self.budget_limit:
            total_cost = self.total_cost()
            if total_cost >= self.budget_limit:
                print(f"WARNING: Budget limit ${self.budget_limit:.2f} reached!")

    def total_tokens(self) -> dict:
        """Get total tokens by model."""
        totals = {}
        for usage in self.usage_history:
            if usage.model not in totals:
                totals[usage.model] = {"input": 0, "output": 0}
            totals[usage.model]["input"] += usage.input_tokens
            totals[usage.model]["output"] += usage.output_tokens
        return totals

    def total_cost(self) -> float:
        """Calculate total cost across all usage."""
        return sum(usage.cost() for usage in self.usage_history)

    def cost_by_model(self) -> dict:
        """Get cost breakdown by model."""
        costs = {}
        for usage in self.usage_history:
            if usage.model not in costs:
                costs[usage.model] = 0.0
            costs[usage.model] += usage.cost()
        return costs

    def usage_since(self, hours: int = 24) -> list[TokenUsage]:
        """Get usage within the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [u for u in self.usage_history if u.timestamp >= cutoff]

    def summary(self) -> dict:
        """Generate usage summary."""
        return {
            "total_requests": len(self.usage_history),
            "total_tokens": self.total_tokens(),
            "total_cost": self.total_cost(),
            "cost_by_model": self.cost_by_model(),
            "budget_remaining": (
                self.budget_limit - self.total_cost()
                if self.budget_limit else None
            )
        }


# Global tracker instance
_tracker = TokenTracker()


def get_tracker() -> TokenTracker:
    """Get the global token tracker."""
    return _tracker


def set_budget(limit: float):
    """Set a budget limit for the tracker."""
    _tracker.budget_limit = limit


# ============================================================================
# Token Estimation
# ============================================================================

def estimate_tokens(text: str, model: str = "gemini-2.5-flash") -> int:
    """
    Estimate token count for text.

    This is a rough estimate. For accurate counts:
    - Gemini: Use the countTokens API
    - OpenAI: Use tiktoken library
    """
    # Rough estimate: ~4 characters per token for English
    # Adjust based on model family
    if "gemini" in model.lower():
        chars_per_token = 4
    elif "gpt" in model.lower():
        chars_per_token = 4
    elif "claude" in model.lower():
        chars_per_token = 3.5
    else:
        chars_per_token = 4

    return int(len(text) / chars_per_token)


def estimate_message_tokens(messages: list[BaseMessage], model: str) -> int:
    """Estimate tokens for a list of messages."""
    total = 0
    for msg in messages:
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        total += estimate_tokens(content, model)
        # Add overhead for message formatting
        total += 4  # Approximate overhead per message
    return total


# ============================================================================
# Cost-Tracked LLM Wrapper
# ============================================================================

class CostTrackedLLM:
    """
    LLM wrapper that tracks token usage and costs.

    Example:
        llm = CostTrackedLLM(model="gemini-2.5-flash")
        response = llm.invoke([HumanMessage("Hello!")])

        print(llm.tracker.summary())
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        tracker: Optional[TokenTracker] = None
    ):
        self.model = model
        self.llm = ChatGoogleGenerativeAI(model=model)
        self.tracker = tracker or get_tracker()

    @traceable(run_type="llm", name="cost_tracked_llm")
    def invoke(self, messages: list) -> AIMessage:
        """Invoke LLM with cost tracking."""

        # Estimate input tokens
        input_tokens = estimate_message_tokens(messages, self.model)

        # Call LLM
        response = self.llm.invoke(messages)

        # Estimate output tokens
        output_tokens = estimate_tokens(response.content, self.model)

        # Record usage
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model
        )
        self.tracker.record(usage)

        return response

    def get_cost_report(self) -> str:
        """Generate a cost report."""
        summary = self.tracker.summary()
        report = [
            "Cost Report",
            "=" * 40,
            f"Total Requests: {summary['total_requests']}",
            f"Total Cost: ${summary['total_cost']:.4f}",
            "",
            "By Model:"
        ]

        for model, cost in summary['cost_by_model'].items():
            tokens = summary['total_tokens'].get(model, {})
            report.append(
                f"  {model}: ${cost:.4f} "
                f"({tokens.get('input', 0):,} in / {tokens.get('output', 0):,} out)"
            )

        if summary['budget_remaining'] is not None:
            report.append(f"\nBudget Remaining: ${summary['budget_remaining']:.2f}")

        return "\n".join(report)


# ============================================================================
# Cost-Tracked Agent
# ============================================================================

class CostTrackedAgent:
    """
    LangGraph agent with built-in cost tracking.

    Tracks costs across:
    - All LLM calls in the graph
    - Multi-turn conversations
    - Tool-using agents
    """

    def __init__(self, budget_limit: Optional[float] = None):
        self.tracker = TokenTracker(budget_limit=budget_limit)
        self.llm = CostTrackedLLM(tracker=self.tracker)
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build agent graph."""

        def call_model(state: MessagesState) -> dict:
            response = self.llm.invoke(state["messages"])
            return {"messages": [response]}

        builder = StateGraph(MessagesState)
        builder.add_node("agent", call_model)
        builder.add_edge(START, "agent")
        builder.add_edge("agent", END)

        return builder.compile(checkpointer=self.checkpointer)

    def chat(self, message: str, thread_id: str = "default") -> str:
        """Chat with cost tracking."""
        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config
        )
        return result["messages"][-1].content

    def get_cost_summary(self) -> dict:
        """Get current cost summary."""
        return self.tracker.summary()

    def get_cost_report(self) -> str:
        """Get formatted cost report."""
        return self.llm.get_cost_report()


# ============================================================================
# Cost Estimation Utilities
# ============================================================================

def estimate_conversation_cost(
    messages: list[BaseMessage],
    model: str = "gemini-2.5-flash"
) -> dict:
    """
    Estimate the cost of a conversation.

    Returns:
        dict with input_tokens, output_tokens, estimated_cost
    """
    input_tokens = 0
    output_tokens = 0

    for msg in messages:
        tokens = estimate_tokens(msg.content, model)
        if isinstance(msg, HumanMessage):
            input_tokens += tokens
        elif isinstance(msg, AIMessage):
            output_tokens += tokens

    pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
    cost = (
        (input_tokens / 1_000_000) * pricing["input"] +
        (output_tokens / 1_000_000) * pricing["output"]
    )

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "estimated_cost": cost,
        "model": model
    }


def compare_model_costs(
    prompt: str,
    models: list[str] = None
) -> list[dict]:
    """
    Compare costs across different models for the same prompt.

    Returns list of cost estimates per model.
    """
    if models is None:
        models = ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o-mini", "gpt-4o"]

    input_tokens = estimate_tokens(prompt)
    output_tokens = input_tokens  # Assume similar output length

    results = []
    for model in models:
        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
        cost = (
            (input_tokens / 1_000_000) * pricing["input"] +
            (output_tokens / 1_000_000) * pricing["output"]
        )
        results.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost
        })

    return sorted(results, key=lambda x: x["cost"])


# ============================================================================
# Demo Functions
# ============================================================================

def demo_token_tracking():
    """Demonstrate token tracking."""

    print("=== Token Tracking Demo ===\n")

    tracker = TokenTracker(budget_limit=0.10)

    # Simulate some usage
    usages = [
        TokenUsage(input_tokens=1000, output_tokens=500, model="gemini-2.5-flash"),
        TokenUsage(input_tokens=2000, output_tokens=1000, model="gemini-2.5-flash"),
        TokenUsage(input_tokens=500, output_tokens=200, model="gpt-4o-mini"),
    ]

    for usage in usages:
        tracker.record(usage)
        print(f"Recorded: {usage.model} - {usage.total_tokens} tokens, ${usage.cost():.4f}")

    print("\nSummary:")
    summary = tracker.summary()
    print(f"  Total requests: {summary['total_requests']}")
    print(f"  Total cost: ${summary['total_cost']:.4f}")
    print(f"  Budget remaining: ${summary['budget_remaining']:.4f}")


def demo_cost_comparison():
    """Demonstrate model cost comparison."""

    print("=== Model Cost Comparison Demo ===\n")

    prompt = "Explain the key concepts of machine learning in detail." * 10

    results = compare_model_costs(prompt)

    print(f"Prompt length: ~{estimate_tokens(prompt)} tokens\n")
    print("Model costs (cheapest to most expensive):")
    for r in results:
        print(f"  {r['model']:20} ${r['cost']:.6f}")


def demo_cost_tracked_agent():
    """Demonstrate cost-tracked agent."""

    print("=== Cost-Tracked Agent Demo ===\n")

    agent = CostTrackedAgent(budget_limit=1.00)

    # Have a conversation
    messages = [
        "What is machine learning?",
        "How does it differ from traditional programming?",
        "Give me an example of a machine learning application."
    ]

    for msg in messages:
        print(f"User: {msg}")
        response = agent.chat(msg)
        print(f"Agent: {response[:100]}...\n")

    print(agent.get_cost_report())


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("Cost Tracking Demonstrations\n")
    print("=" * 50 + "\n")

    demo_token_tracking()
    print("\n" + "=" * 50 + "\n")

    demo_cost_comparison()
    print("\n" + "=" * 50 + "\n")

    demo_cost_tracked_agent()
